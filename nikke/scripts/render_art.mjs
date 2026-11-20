// 将 NIKKE Spine 待机首帧批量导出为透明静态 PNG（不是独立官方原画）。
// 使用方式（在仓库根目录启动 python -m http.server 8000 后）：
//   node nikke/scripts/render_art.mjs c272_01 c202_01
//   node nikke/scripts/render_art.mjs --all
// 可配置：NIKKE_VIEWER_URL=http://127.0.0.1:8000 CHROMIUM_PATH=...
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const nikkeDir = path.resolve(scriptDir, '..');
const dataDir = path.join(nikkeDir, 'data');
const manifestPath = path.join(nikkeDir, 'viewer', 'nikke_manifest.json');
const args = process.argv.slice(2);
const force = args.includes('--force');
const all = args.includes('--all');
const ids = args.filter(arg => !arg.startsWith('--'));
const baseUrl = (process.env.NIKKE_VIEWER_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

if (!all && !ids.length) {
  console.error('使用方式: node nikke/scripts/render_art.mjs <角色ID ...> 或 --all [--force]');
  process.exit(1);
}
if (!fs.existsSync(manifestPath)) {
  console.error('缺少清单，请先执行 python nikke/scripts/gen_nikke_manifest.py');
  process.exit(1);
}
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const characters = manifest.characters || [];
const requested = all
  ? characters.filter(c => c.poses && c.poses.fb).map(c => c.id)
  : ids;
const allowed = new Set(characters.filter(c => c.poses && c.poses.fb).map(c => c.id));
const targets = [...new Set(requested)].filter(id => {
  if (!allowed.has(id)) {
    console.warn(id + ': 不存在或没有完整立绘(fb)，跳过');
    return false;
  }
  return true;
});

const launch = { headless: true };
if (process.env.CHROMIUM_PATH) launch.executablePath = process.env.CHROMIUM_PATH;
const browser = await chromium.launch(launch);
const page = await browser.newPage({
  viewport: { width: 1440, height: 1900 },
  deviceScaleFactor: 2,
});
let passed = 0, failed = 0, skipped = 0;
try {
  for (const id of targets) {
    const dir = path.join(dataDir, id);
    const dest = path.join(dir, 'art_render.png');
    if (!force && fs.existsSync(dest)) {
      skipped++;
      console.log(id + ': 已有静态图，跳过');
      continue;
    }
    try {
      await page.goto(baseUrl + '/nikke/viewer/index.html', { waitUntil: 'load', timeout: 30000 });
      await page.waitForFunction(() => window.NikkeArt && typeof manifest !== 'undefined' && !!manifest, null, { timeout: 30000 });
      const found = await page.evaluate(cid => {
        const index = manifest.characters.findIndex(c => c.id === cid);
        if (index < 0) return false;
        enterStage(index, 'fb');
        return true;
      }, id);
      if (!found) throw new Error('查看器中找不到该角色');
      await page.waitForFunction(() => window.NikkeArt.ready, null, { timeout: 45000 });
      // 动态模式显示 WebGL；待首帧稳定后按原生画布像素导出透明立绘。
      await page.evaluate(() => window.NikkeArt.switchMode('dynamic'));
      await page.waitForTimeout(250);
      const url = await page.evaluate(() => window.NikkeArt.exportPoseFrame());
      if (!url || !url.startsWith('data:image/png;base64,')) {
        throw new Error('无法提取透明 Spine 画面');
      }
      const bytes = Buffer.from(url.split(',')[1], 'base64');
      if (bytes.length < 1024) throw new Error('图片内容过小，可能渲染失败');
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(dest, bytes);
      passed++;
      console.log(id + ': OK -> ' + dest + ' (' + bytes.length + ' bytes)');
    } catch (error) {
      failed++;
      console.error(id + ': ' + error.message);
    }
  }
} finally {
  await browser.close();
}
console.log('完成: 成功 ' + passed + ' / 跳过 ' + skipped + ' / 失败 ' + failed);
// 导出完成后需执行 gen_nikke_manifest.py 才会被查看器作为静态图引用。
if (failed) process.exitCode = 1;
