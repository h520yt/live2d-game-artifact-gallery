const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const out = path.join(root, 'wallpapers/brown_dust2/ventana_onsen_practitioner');
const reportFile = process.env.VENTANA_TEST_REPORT || 'browser-test.json';
const shotPrefix = reportFile === 'browser-test.json' ? 'browser' : path.basename(reportFile, '.json');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 3840, height: 2160 }, deviceScaleFactor: 1, offline: true });
    const page = await context.newPage();
    const errors = [], network = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
    page.on('request', req => { if (/^https?:/.test(req.url())) network.push(req.url()); });
    await page.goto(pathToFileURL(path.join(out, 'index.html')).href);
    await page.waitForFunction(() => window.wallpaperStatus?.ready || window.wallpaperStatus?.errors.length, { timeout: 60000 });
    const initial = await page.evaluate(() => window.getWallpaperDiagnostics?.() || window.wallpaperStatus);
    if (!initial.ready || initial.errors.length) throw new Error('Wallpaper initialization failed');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(out, 'verification', shotPrefix + '-initial.png') });
    await page.screenshot({ path: path.join(out, 'preview.png') });
    const started = Date.now(), samples = [];
    const minutes = Number(process.env.VENTANA_TEST_MINUTES || 5);
    for (let n = 0; n < minutes * 6; n++) {
      await page.waitForTimeout(10000);
      const d = await page.evaluate(() => window.getWallpaperDiagnostics());
      assert.deepEqual(d.canvas, [3840, 2160]);
      assert.equal(d.tracks.length, 1);
      assert.equal(d.tracks[0].animation, 'idle2');
      assert.equal(d.tracks[0].loop, true);
      assert.equal(d.textureCount, 7);
      assert.equal(d.errors.length, 0);
      assert.equal(d.contextLost || false, false);
      assert.deepEqual(d.camera, initial.camera);
      samples.push({ elapsedMs: Date.now() - started, frames: d.frames, loops: d.loops, trackTime: d.tracks[0].time });
      if (n % 6 === 0) console.log(JSON.stringify(samples.at(-1)));
    }
    const beforePause = await page.evaluate(() => { window.wallpaperPropertyListener.setPaused(true); return window.getWallpaperDiagnostics(); });
    let fullyOpaqueAt4k = null;
    if (beforePause.framing === 'cover') {
      const c = beforePause.camera, halfH = 2160 * c.zoom / 2;
      assert(c.characterBounds.bottom >= c.y - halfH && c.characterBounds.top <= c.y + halfH,
        'Sampled head, hands and legs must fit vertically through the entire loop');
      // Freeze the same frame and change only the backing colour. Identical pixels
      // prove that the scene fills the entire screen without blurred filler/bars.
      await page.evaluate(() => { document.querySelector('#backdrop').style.background = '#ffffff'; });
      const white = await page.screenshot();
      await page.evaluate(() => { document.querySelector('#backdrop').style.background = '#ff00ff'; });
      const magenta = await page.screenshot();
      fullyOpaqueAt4k = white.equals(magenta);
      assert(fullyOpaqueAt4k, '4K cover must not expose the backing colour anywhere');
      await page.evaluate(() => document.querySelector('#backdrop').removeAttribute('style'));
    }
    await page.waitForTimeout(1200);
    const duringPause = await page.evaluate(() => window.getWallpaperDiagnostics());
    assert.equal(beforePause.frames, duringPause.frames);
    assert.equal(beforePause.tracks[0].time, duringPause.tracks[0].time);
    await page.evaluate(() => { window.wallpaperPropertyListener.setPaused(false); window.wallpaperPropertyListener.applyGeneralProperties({fps:12}); });
    const fpsStart = await page.evaluate(() => window.getWallpaperDiagnostics());
    await page.waitForTimeout(2200);
    const limited = await page.evaluate(() => window.getWallpaperDiagnostics());
    assert(limited.frames - fpsStart.frames <= 29 && limited.frames - fpsStart.frames > 15, '12 FPS limit');
    const lowFpsTime = limited.tracks[0].time - fpsStart.tracks[0].time;
    assert(lowFpsTime > 1.8 * limited.playbackSpeed && lowFpsTime < 2.6 * limited.playbackSpeed,
      'Animation must retain its configured playback speed at 12 FPS');
    await page.evaluate(() => window.wallpaperPropertyListener.applyGeneralProperties({fps:60}));
    assert.equal(await page.evaluate(() => window.getWallpaperDiagnostics().fpsLimit), 30);
    await page.mouse.move(1400, 900); await page.mouse.click(1400, 900); await page.mouse.wheel(0, 600);
    const final = await page.evaluate(() => window.getWallpaperDiagnostics());
    assert.equal(final.tracks.length, 1);
    assert(final.loops > 0, 'Animation must actually complete loops');
    assert.equal(await page.locator('button,input,select,audio,video').count(), 0);
    assert.equal(network.length, 0);
    assert.equal(errors.length, 0);
    await page.screenshot({ path: path.join(out, 'verification', shotPrefix + '-after-soak.png') });
    const report = { environment: 'Playwright / installed Chrome / file:// / offline:true / 3840x2160', initial, final,
      elapsedMs: Date.now() - started, samples, pausePassed: true, fpsLimitPassed: true,
      fullyOpaqueAt4k, lowFpsAnimationSeconds: lowFpsTime, noInteractiveControls: true, errors, network };
    await context.close();
    const dpi = await browser.newContext({ viewport: {width:1920,height:1080}, deviceScaleFactor:2, offline:true });
    const dpiPage = await dpi.newPage();
    await dpiPage.goto(pathToFileURL(path.join(out, 'index.html')).href);
    await dpiPage.waitForFunction(() => window.wallpaperStatus?.ready);
    report.dpi2 = await dpiPage.evaluate(() => window.getWallpaperDiagnostics());
    assert.deepEqual(report.dpi2.canvas, [3840,2160]);
    await dpi.close();
    fs.writeFileSync(path.join(out, 'verification', reportFile), JSON.stringify(report, null, 2));
    console.log('PASS ' + JSON.stringify({loops:final.loops, frames:final.frames, elapsedMs:report.elapsedMs, errors, network}));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
