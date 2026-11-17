const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const out = path.resolve(__dirname, '..');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 3840, height: 2160 }, deviceScaleFactor: 1, offline: true });
  const page = await context.newPage();
  const errors = [], network = [], requests = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('request', r => { requests.push(r.url()); if (/^https?:/.test(r.url())) network.push(r.url()); });
  await page.addInitScript(() => {
    window.textureUploads = 0;
    window.contextCount = 0;
    const getContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type, ...args) {
      const result = getContext.call(this, type, ...args);
      if (/^webgl/.test(type) && result) window.contextCount++;
      return result;
    };
    for (const api of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
      if (!api) continue;
      const upload = api.prototype.texImage2D;
      api.prototype.texImage2D = function (...args) { window.textureUploads++; return upload.apply(this, args); };
    }
  });
  try {
    await page.goto(pathToFileURL(path.join(out, 'index.html')).href);
    await page.waitForFunction(() => window.wallpaperStatus?.ready, { timeout: 60000 });
    await page.waitForTimeout(1100);
    const initial = await page.evaluate(() => getWallpaperDiagnostics());
    assert.equal(initial.skin, 'default');
    assert.equal(initial.animation, 'idle1');
    assert.equal(initial.loopSeconds, 2);
    await page.screenshot({ path: path.join(out, 'preview.png') });

    // Freeze one frame. Only the final compositor transform is changed.
    await page.evaluate(() => wallpaperPropertyListener.setPaused(true));
    await page.waitForTimeout(100);
    await page.screenshot({ path: path.join(__dirname, 'mirrored.png') });
    await page.evaluate(() => document.querySelector('#spine-root').style.transform = 'none');
    await page.screenshot({ path: path.join(__dirname, 'unmirrored.png') });
    await page.evaluate(() => document.querySelector('#spine-root').removeAttribute('style'));
    // Prove no pixels expose the backdrop: change its colour under a frozen frame.
    await page.evaluate(() => document.querySelector('#backdrop').style.background = '#ffffff');
    const white = await page.screenshot();
    await page.evaluate(() => document.querySelector('#backdrop').style.background = '#ff00ff');
    const magenta = await page.screenshot();
    assert(white.equals(magenta), 'No transparent borders / backing colour at 4K');
    await page.evaluate(() => document.querySelector('#backdrop').removeAttribute('style'));
    const pauseStart = await page.evaluate(() => getWallpaperDiagnostics());
    await page.waitForTimeout(1200);
    const paused = await page.evaluate(() => getWallpaperDiagnostics());
    assert.equal(pauseStart.frames, paused.frames);
    assert.equal(pauseStart.tracks[0].time, paused.tracks[0].time);
    await page.evaluate(() => wallpaperPropertyListener.setPaused(false));

    const started = Date.now(), samples = [];
    const minutes = Number(process.env.SYLVIA_TEST_MINUTES || 5);
    const uploadStart = await page.evaluate(() => textureUploads);
    for (let n = 0; n < minutes * 6; n++) {
      await page.waitForTimeout(10000);
      const d = await page.evaluate(() => getWallpaperDiagnostics());
      assert.deepEqual(d.canvas, [3840, 2160]);
      assert.equal(d.tracks.length, 1);
      assert.equal(d.tracks[0].animation, 'idle1');
      assert.equal(d.tracks[0].loop, true);
      assert.equal(d.textureCount, 6);
      assert.equal(d.errors.length, 0);
      assert(!d.contextLost);
      assert.deepEqual(d.camera, initial.camera);
      samples.push({ elapsedMs: Date.now() - started, frames: d.frames, loops: d.loops, trackTime: d.tracks[0].time });
      if (n % 6 === 0) console.log(JSON.stringify(samples.at(-1)));
    }
    assert.equal(await page.evaluate(() => textureUploads), uploadStart, 'No texture re-uploads during soak');
    assert.equal(await page.evaluate(() => contextCount), 1, 'One WebGL context');
    const camera = initial.camera, c = camera.characterBounds;
    assert(c.left >= camera.x - 1920 * camera.zoom && c.right <= camera.x + 1920 * camera.zoom);
    assert(c.bottom >= camera.y - 1080 * camera.zoom && c.top <= camera.y + 1080 * camera.zoom);
    await page.evaluate(() => wallpaperPropertyListener.applyGeneralProperties({ fps: 12 }));
    const fpsStart = await page.evaluate(() => getWallpaperDiagnostics());
    await page.waitForTimeout(2200);
    const limited = await page.evaluate(() => getWallpaperDiagnostics());
    assert(limited.frames - fpsStart.frames <= 29 && limited.frames - fpsStart.frames > 15);
    const animationSeconds = limited.tracks[0].time - fpsStart.tracks[0].time;
    assert(animationSeconds > 1.8 && animationSeconds < 2.6, '12 FPS retains real-time animation speed');
    await page.evaluate(() => wallpaperPropertyListener.applyGeneralProperties({ fps: 60 }));
    assert.equal(await page.evaluate(() => getWallpaperDiagnostics().fpsLimit), 30);
    await page.mouse.click(1400, 900); await page.mouse.wheel(0, 600);
    const final = await page.evaluate(() => getWallpaperDiagnostics());
    assert(final.frames > initial.frames && final.loops >= minutes * 20);
    assert.equal(final.tracks.length, 1);
    assert.equal(final.tracks[0].animation, 'idle1');
    assert.deepEqual(final.camera, initial.camera);
    assert.equal(await page.locator('button,input,select,audio,video,a').count(), 0);
    assert.equal(network.length, 0);
    assert.equal(errors.length, 0);
    assert(requests.every(u => u.startsWith(pathToFileURL(out + path.sep).href) || u.startsWith('data:')));
    await page.screenshot({ path: path.join(__dirname, 'after-soak.png') });
    const report = { environment: 'Installed Chrome / headless / file:// / offline:true / 3840x2160',
      browserVersion: browser.version(), initial, final, elapsedMs: Date.now() - started, samples,
      pauseResumePassed: true, fpsLimitPassed: true, lowFpsAnimationSeconds: animationSeconds,
      fullyOpaqueAt4k: true, characterFitsEntireCycle: true,
      textureUploadsAtStart: uploadStart, textureUploadsAtEnd: await page.evaluate(() => textureUploads),
      webglContexts: await page.evaluate(() => contextCount), noInteractiveControls: true, errors, network,
      requestedFiles: requests.filter(u => !u.startsWith('data:')) };
    await context.close();

    // A relocated copy proves runtime independence from the repository paths.
    const relocated = fs.mkdtempSync(path.join(os.tmpdir(), 'sylvia-wallpaper-'));
    try {
      for (const file of ['index.html', 'css', 'js']) fs.cpSync(path.join(out, file), path.join(relocated, file), { recursive: true });
      const dpi = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, offline: true });
      const moved = await dpi.newPage();
      moved.on('pageerror', e => errors.push(e.message));
      await moved.goto(pathToFileURL(path.join(relocated, 'index.html')).href);
      await moved.waitForFunction(() => window.wallpaperStatus?.ready, { timeout: 60000 });
      report.relocatedDpi2 = await moved.evaluate(() => getWallpaperDiagnostics());
      assert.deepEqual(report.relocatedDpi2.canvas, [3840, 2160]);
      assert.equal(report.relocatedDpi2.errors.length, 0);
      await dpi.close();
      report.relocatedOfflinePassed = true;
    } finally {
      assert(path.resolve(relocated).startsWith(path.resolve(os.tmpdir()) + path.sep));
      fs.rmSync(relocated, { recursive: true, force: true });
    }
    fs.writeFileSync(path.join(__dirname, 'browser-test.json'), JSON.stringify(report, null, 2));
    console.log('PASS ' + JSON.stringify({ loops: final.loops, frames: final.frames, elapsedMs: report.elapsedMs, errors, network }));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
