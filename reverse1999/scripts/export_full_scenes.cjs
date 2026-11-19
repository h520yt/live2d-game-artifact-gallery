#!/usr/bin/env node
"use strict";

/**
 * 《重返未来：1999》完整场景图批量导出。
 * 仅使用 UNIQUE 已核实的「相同衣着 ID 专属背景 + 原生 Live2D」；
 * Playwright 截取浏览器实际合成的舞台，不会把背景单独当成成品。
 *
 * 在仓库根目录运行：
 *   node reverse1999/scripts/export_full_scenes.cjs all
 *   node reverse1999/scripts/export_full_scenes.cjs 308603
 *   node reverse1999/scripts/export_full_scenes.cjs all --download
 *
 * 输出：reverse1999/data/full_scenes/<皮肤ID>.png（Git 忽略）
 */
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const { spawnSync } = require("node:child_process");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "../..");
const GAME = path.join(ROOT, "reverse1999");
const OUTPUT = path.join(GAME, "data", "full_scenes");
const MANIFEST = path.join(GAME, "viewer", "manifest.json");
const CATALOG = path.join(GAME, "viewer", "unique-catalog.json");
const PNG = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

function validPng(filename) {
  try {
    const stat = fs.statSync(filename);
    if (stat.size < 24000) return false;
    const fd = fs.openSync(filename, "r");
    const head = Buffer.alloc(24);
    try { fs.readSync(fd, head, 0, 24, 0); } finally { fs.closeSync(fd); }
    return head.subarray(0, 8).equals(PNG) &&
      head.readUInt32BE(16) >= 640 && head.readUInt32BE(20) >= 640;
  } catch { return false; }
}

function mime(filename) {
  const type = path.extname(filename).toLowerCase();
  return ({
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp",
    ".wasm": "application/wasm", ".moc3": "application/octet-stream",
    ".atlas": "text/plain; charset=utf-8",
  })[type] || "application/octet-stream";
}

function localServer() {
  const server = http.createServer((req, res) => {
    let pathname;
    try { pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname); }
    catch { res.writeHead(400).end(); return; }
    const filename = path.resolve(ROOT, "." + pathname);
    if (filename !== ROOT && !filename.startsWith(ROOT + path.sep)) {
      res.writeHead(403).end(); return;
    }
    fs.stat(filename, (err, stat) => {
      if (err || !stat.isFile()) { res.writeHead(404).end(); return; }
      res.setHeader("Content-Type", mime(filename));
      const stream = fs.createReadStream(filename);
      stream.on("error", () => { if (!res.headersSent) res.writeHead(500); res.end(); });
      stream.pipe(res);
    });
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve({
      server, port: server.address().port,
    }));
  });
}

function runPython(args) {
  const python = process.env.PYTHON || "python";
  const result = spawnSync(python, args, { cwd: ROOT, stdio: "inherit" });
  if (result.error || result.status !== 0) {
    throw new Error(python + " " + args.join(" ") + " 执行失败");
  }
}

async function main() {
  const args = process.argv.slice(2);
  const target = args.find(x => !x.startsWith("--")) || "all";
  const download = args.includes("--download");
  const force = args.includes("--force");
  const catalog = JSON.parse(fs.readFileSync(CATALOG, "utf8")).skins;
  const selected = target === "all" ? catalog :
    catalog.filter(row => String(row.id) === target);
  if (!selected.length) throw new Error("未收录皮肤 ID：" + target);

  // 可选下载：只会从已核对的上游固定路径获取同一皮肤的资源。
  if (download) {
    for (const row of selected) {
      runPython(["reverse1999/scripts/sync.py", "unique", String(row.id)]);
    }
  }
  // 下载完成后的清单已更新；离线模式沿用已有清单。
  const models = JSON.parse(fs.readFileSync(MANIFEST, "utf8")).models;
  const available = new Map(models.filter(m => m.tier === "UNIQUE" &&
    m.type === "scene-live2d").map(m => [String(m.id), m]));
  const missing = selected.filter(row => !available.has(String(row.id)));
  if (missing.length) {
    console.log("尚未安装同 ID 背景和角色资源：" +
      missing.map(row => row.id + " " + row.name).join("、"));
    console.log("先执行 python reverse1999/scripts/sync.py unique all，或加 --download 自动安装。");
  }
  const todo = selected.filter(row => available.has(String(row.id)) &&
    (force || !validPng(path.join(OUTPUT, row.id + ".png"))));
  if (todo.length) fs.mkdirSync(OUTPUT, { recursive: true });

  let service = null, browser = null, failed = 0;
  try {
    if (todo.length) {
      service = await localServer();
      browser = await chromium.launch({ headless: true, args: [
        "--enable-webgl", "--use-gl=angle", "--enable-unsafe-swiftshader"
      ] });
      const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1,
      });
      for (const row of todo) {
        const model = available.get(String(row.id));
        const sourceId = String(row.id) + ":" + model.folder;
        const url = "http://127.0.0.1:" + service.port +
          "/reverse1999/viewer/index.html?gallery_asset=" +
          encodeURIComponent(sourceId);
        const filename = path.join(OUTPUT, row.id + ".png");
        const temporary = filename + ".tmp";
        try {
          await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
          await page.waitForFunction(() => {
            const bg = document.getElementById("live2d-background");
            const status = document.getElementById("status");
            const title = document.getElementById("model-info");
            const stage = document.getElementById("stage-area");
            return bg && !bg.hidden && bg.complete && bg.naturalWidth > 0 &&
              status.hidden && !title.hidden && !stage.hidden;
          }, null, { timeout: 90000 });
          // 仅让合成舞台占据输出画布，不截取搜索框、按钮或文字标签。
          await page.addStyleTag({ content: [
            "header,aside,.stage-toolbar{display:none!important}",
            "html,body,main{margin:0!important;padding:0!important;width:100%!important;height:100%!important;overflow:hidden!important}",
            "main{display:block!important;min-height:0!important}",
            "section.stage,#stage-area{width:100vw!important;height:100vh!important;min-height:0!important}",
            "section.stage{position:fixed!important;inset:0!important}",
          ].join("") });
          await page.evaluate(() => window.dispatchEvent(new Event("resize")));
          await page.waitForTimeout(1000);
          await page.locator("#stage-area").screenshot({
            path: temporary, animations: "disabled", timeout: 90000,
          });
          if (!validPng(temporary)) throw new Error("导出的 PNG 尺寸或内容校验失败");
          fs.renameSync(temporary, filename);
          console.log("[完成] " + row.id + " " + row.name + " · " + row.skin +
            " -> " + path.relative(ROOT, filename));
        } catch (error) {
          failed += 1;
          console.error("[失败] " + row.id + ": " + error.message);
          fs.rmSync(temporary, { force: true });
        }
      }
    }
  } finally {
    if (browser) await browser.close();
    if (service) await new Promise(resolve => service.server.close(resolve));
  }

  // 资源实际落盘后再登记；丢失或失败的 PNG 不进入清单。
  runPython(["reverse1999/scripts/sync.py", "manifest"]);
  runPython(["scripts/gallery.py", "sync-index"]);
  console.log("完整场景导出完成，成功/复用：" +
    selected.filter(row => validPng(path.join(OUTPUT, row.id + ".png"))).length +
    " / " + selected.length + "；失败：" + failed);
  console.log("打开 http://127.0.0.1:8000/gallery/（先执行 python scripts/gallery.py serve）");
  if (missing.length || failed) process.exitCode = 1;
}

main().catch(error => { console.error("完整场景导出失败：" + error.message); process.exitCode = 1; });
