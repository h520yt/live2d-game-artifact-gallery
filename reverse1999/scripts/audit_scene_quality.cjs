#!/usr/bin/env node
"use strict";

/**
 * 《重返未来：1999》本机皮肤展示质量检查。
 * 按真实文件核验 4K 场景图、同皮肤背景和动态模型贴图；
 * 不下载资源、不借用其他衣着的图片，也不把独立角色原画当作场景背景。
 *
 * node reverse1999/scripts/audit_scene_quality.cjs
 * node reverse1999/scripts/audit_scene_quality.cjs --json
 */
const fs = require("node:fs");
const path = require("node:path");

const GAME = path.resolve(__dirname, "..");
const VIEWER = path.join(GAME, "viewer");
const MANIFEST = path.join(VIEWER, "manifest.json");
const MIN_WIDTH = 3840;
const MIN_HEIGHT = 2160;
const PNG = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

function assetPath(relative) {
  if (typeof relative !== "string" || !relative.startsWith("../data/") ||
      relative.includes("\\") || relative.includes("?") || relative.includes("#")) {
    return null;
  }
  const resolved = path.resolve(VIEWER, relative);
  const base = path.join(GAME, "data") + path.sep;
  return resolved.startsWith(base) ? resolved : null;
}

function pngInfo(filename) {
  try {
    const stats = fs.statSync(filename);
    if (!stats.isFile() || stats.size < 24) return null;
    const fd = fs.openSync(filename, "r");
    const head = Buffer.alloc(24);
    try { fs.readSync(fd, head, 0, head.length, 0); }
    finally { fs.closeSync(fd); }
    if (!head.subarray(0, 8).equals(PNG)) return null;
    return { width: head.readUInt32BE(16), height: head.readUInt32BE(20),
      bytes: stats.size };
  } catch {
    return null;
  }
}

function exists(filename) {
  try { return !!filename && fs.statSync(filename).isFile(); }
  catch { return false; }
}

function modelTextureAudit(model) {
  const config = assetPath(model.path);
  if (!config || !exists(config)) return { problem: "模型配置缺失", lowTextures: [] };
  let refs;
  try {
    const data = JSON.parse(fs.readFileSync(config, "utf8").replace(/^\uFEFF/, ""));
    refs = data.FileReferences || {};
  } catch {
    return { problem: "模型 JSON 无法解析", lowTextures: [] };
  }
  const base = path.dirname(config);
  const moc = refs.Moc;
  if (typeof moc !== "string" || moc.includes("..") ||
      !exists(path.resolve(base, moc))) {
    return { problem: "模型 moc3 缺失", lowTextures: [] };
  }
  const textures = Array.isArray(refs.Textures) ? refs.Textures : [];
  const lowTextures = [];
  for (const value of textures) {
    if (typeof value !== "string" || value.includes("..") || value.includes("\\")) {
      return { problem: "模型纹理路径非法", lowTextures };
    }
    const location = path.resolve(base, value);
    if (!location.startsWith(base + path.sep)) {
      return { problem: "模型纹理路径越界", lowTextures };
    }
    const info = pngInfo(location);
    if (!info) return { problem: "模型贴图缺失或损坏：" + value, lowTextures };
    if (info.width < 1024 || info.height < 1024) {
      lowTextures.push(value + " (" + info.width + "×" + info.height + ")");
    }
  }
  return { problem: null, lowTextures: lowTextures.slice(0, 8),
    textureCount: textures.length };
}

function main() {
  const manifest = JSON.parse(fs.readFileSync(MANIFEST, "utf8"));
  const models = Array.isArray(manifest.models) ? manifest.models : [];
  const grouped = new Map();
  for (const item of models) {
    if (!/^\d{6}$/.test(String(item.id))) continue;
    const id = String(item.id);
    if (!grouped.has(id)) grouped.set(id, []);
    grouped.get(id).push(item);
  }
  const details = [];
  for (const [id, variants] of grouped) {
    const rows = [];
    let confirmedBg = false;
    let full = null;
    for (const item of variants) {
      const bgRef = item.background || item.scene?.background || null;
      const bgLocation = assetPath(bgRef);
      const bgInfo = bgLocation ? pngInfo(bgLocation) : null;
      // 唯有相同衣着 ID 的唯一背景可视为已核实背景。
      const sameIdUnique = bgRef && bgRef.includes("/unique/" + id + "/background.png");
      const sameIdScene = bgRef && bgRef.includes("/scenes/" + id + "/background.png");
      const sameIdShowcase = bgRef && bgRef.includes("/showcase/" + id + "/background.png");
      const verified = !!(sameIdUnique || sameIdScene || sameIdShowcase);
      if (verified && bgInfo) confirmedBg = true;
      const sceneRef = assetPath(item.full_scene);
      const sceneInfo = sceneRef ? pngInfo(sceneRef) : null;
      if (item.full_scene) {
        full = sceneInfo ? { ...sceneInfo, status:
          sceneInfo.width >= MIN_WIDTH && sceneInfo.height >= MIN_HEIGHT
            ? "4K" : "需要重新导出 4K" } : { status: "清单引用的场景图不存在或损坏" };
      }
      const model = item.type === "cubism" || item.type === "scene-live2d"
        ? modelTextureAudit(item) : null;
      rows.push({ type: item.type, channel: item.channel || item.tier || null,
        backgroundSource: bgRef, verifiedSameSkin: verified,
        background: bgRef ? (bgInfo || "缺失或不是有效 PNG") : null,
        model, fullScene: sceneInfo });
    }
    const problems = [];
    if (rows.some(x => x.verifiedSameSkin && typeof x.background === "string")) {
      problems.push("同 ID 专属背景文件缺失/损坏");
    }
    for (const row of rows) {
      if (row.model?.problem) problems.push(row.type + ": " + row.model.problem);
    }
    if (full && full.status !== "4K") problems.push(full.status);
    details.push({ id, name: variants[0].name || "", skin: variants[0].skin || "",
      verifiedBackgroundReady: confirmedBg, fullScene: full,
      noVerifiedBackground: !rows.some(x => x.verifiedSameSkin),
      problems: [...new Set(problems)], variants: rows });
  }
  details.sort((a, b) => Number(b.id) - Number(a.id));
  const summary = { assets: details.length, entries: models.length,
    verifiedBackgroundReady: details.filter(x => x.verifiedBackgroundReady).length,
    noVerifiedBackground: details.filter(x => x.noVerifiedBackground).length,
    fullScene4K: details.filter(x => x.fullScene?.status === "4K").length,
    issues: details.filter(x => x.problems.length).length };
  const report = { summary, details };
  if (process.argv.includes("--json")) {
    process.stdout.write(JSON.stringify(report, null, 2) + "\n");
  } else {
    console.log("重返未来：1999 本地质量审计：" + JSON.stringify(summary));
    for (const item of details) {
      const state = item.problems.length ? "待修复" :
        item.verifiedBackgroundReady ? "专属背景就绪" : "未核实独立背景";
      console.log("[" + state + "] " + item.id + " " + item.name + " · " + item.skin);
      for (const problem of item.problems) console.log("   - " + problem);
    }
    console.log("说明：未核实背景不代表下载失败；禁止把角色原画或其他衣着的背景强行拼接。");
    console.log("修复旧版模糊截图：node reverse1999/scripts/export_full_scenes.cjs all --download --force");
  }
  if (summary.issues > 0) process.exitCode = 1;
}

try { main(); }
catch (error) { console.error("资源质量审计失败：" + error.message); process.exitCode = 1; }
