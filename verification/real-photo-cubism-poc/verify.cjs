const assert = require('node:assert/strict');
const { readFile, writeFile } = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '../..');
const base = '/verification/real-photo-cubism-poc/';
const origin = 'http://cubism-proof.test';
const assets = new Map([
  [`${base}preview.html`, 'text/html; charset=utf-8'],
  [`${base}preview.js`, 'text/javascript'],
  [`${base}portrait.model3.json`, 'application/json'],
  [`${base}portrait.moc3`, 'application/octet-stream'],
  [`${base}portrait-texture.png`, 'image/png'],
  ['/shared/vendor/live2dcubismcore.min.js', 'text/javascript'],
]);

async function verifyLocalFile(browser) {
  const page = await browser.newPage();
  try {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(message.text());
    });
    await page.goto(pathToFileURL(path.join(__dirname, 'preview.html')).href);
    try {
      await page.waitForFunction(() => window.portraitProof, null, { timeout: 8000 });
    } catch {
      throw new Error(`file:// ${await page.locator('#status').textContent()} ${errors.join(' ')}`);
    }

    const neutral = await page.locator('canvas').evaluate(canvas => canvas.toDataURL());
    await page.locator('#ParamAngleZ').press('End');
    await page.locator('#ParamEyeLOpen').press('Home');
    await page.locator('#ParamEyeROpen').press('Home');
    const state = await page.locator('canvas').evaluate(canvas => ({
      frame: canvas.toDataURL(),
      values: Array.from(window.portraitProof.model.parameters.values),
      opacities: Array.from(window.portraitProof.model.drawables.opacities),
    }));
    assert.deepEqual(state.values, [6, 0, 0]);
    assert.deepEqual(state.opacities, [1, 1, 1]);
    assert.notEqual(state.frame, neutral);
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
}

(async () => {
  const browser = await chromium.launch({
    channel: 'chrome',
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 800 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(message.text());
    });
    await page.route(`${origin}/**`, async route => {
      const url = new URL(route.request().url());
      const contentType = assets.get(url.pathname);
      if (!contentType) return route.fulfill({ status: 204, body: '' });
      const body = await readFile(path.join(root, url.pathname));
      await route.fulfill({ contentType, body });
    });
    await page.goto(`${origin}${base}preview.html`);
    try {
      await page.waitForFunction(() => window.portraitProof, null, { timeout: 8000 });
    } catch {
      throw new Error(`${await page.locator('#status').textContent()} ${errors.join(' ')}`);
    }

    async function state(values, capture = false) {
      return page.evaluate(({ values, capture }) => {
        for (const [id, value] of Object.entries(values)) {
          const slider = document.getElementById(id);
          slider.value = value;
          slider.dispatchEvent(new Event('input'));
        }
        const { core, gl, model } = window.portraitProof;
        const { drawables } = model;
        const pixels = new Uint8Array(512 * 512 * 4);
        gl.readPixels(0, 0, 512, 512, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
        let checksum = 2166136261;
        for (const value of pixels) checksum = Math.imul(checksum ^ value, 16777619);
        let transparentPixels = 0;
        for (let i = 3; i < pixels.length; i += 4) {
          if (pixels[i] !== 255) transparentPixels++;
        }
        return {
          core: core.Version.csmGetVersion(),
          parameters: Array.from(model.parameters.ids),
          drawables: Array.from(drawables.ids),
          opacities: Array.from(drawables.opacities),
          vertices: Array.from(drawables.vertexPositions[0]),
          checksum: checksum >>> 0,
          transparentPixels,
          glError: gl.getError(),
          frame: capture ? document.querySelector('canvas').toDataURL() : null,
        };
      }, { values, capture });
    }

    const neutral = await state({}, true);
    assert.deepEqual(neutral.parameters, ['ParamAngleZ', 'ParamEyeLOpen', 'ParamEyeROpen']);
    assert.deepEqual(neutral.drawables, ['Portrait', 'ClosedLeft', 'ClosedRight']);
    assert.deepEqual(neutral.opacities, [1, 0, 0]);
    const left = await state({ ParamEyeLOpen: 0 }, true);
    assert.deepEqual(left.opacities, [1, 1, 0]);
    const right = await state({ ParamEyeLOpen: 1, ParamEyeROpen: 0 });
    assert.deepEqual(right.opacities, [1, 0, 1]);
    const tilt = await state({ ParamEyeROpen: 1, ParamAngleZ: 6 });
    assert.deepEqual(tilt.opacities, [1, 0, 0]);
    assert(tilt.vertices.some((value, index) => Math.abs(value - neutral.vertices[index]) > 0.01));
    const combined = await state({ ParamEyeLOpen: 0, ParamEyeROpen: 0 }, true);
    assert.deepEqual(combined.opacities, [1, 1, 1]);
    const cases = [neutral, left, right, tilt, combined];
    assert(cases.every(result => result.glError === 0));
    assert(cases.every(result => result.transparentPixels === 0));
    assert.equal(new Set(cases.map(result => result.checksum)).size, cases.length);
    assert.deepEqual(errors, []);

    const comparison = await page.evaluate(async urls => {
      const output = document.createElement('canvas');
      const width = 230;
      const gutter = 8;
      output.width = urls.length * width + (urls.length - 1) * gutter;
      output.height = 260;
      const context = output.getContext('2d');
      context.fillStyle = '#fff';
      context.fillRect(0, 0, output.width, output.height);
      for (const [index, url] of urls.entries()) {
        const frame = new Image();
        frame.src = url;
        await frame.decode();
        context.drawImage(frame, 137, 9, 178, 201, index * (width + gutter), 0, width, output.height);
      }
      return output.toDataURL().split(',')[1];
    }, [neutral.frame, left.frame, combined.frame]);
    await verifyLocalFile(browser);
    await writeFile(path.join(__dirname, 'comparison.png'), Buffer.from(comparison, 'base64'));
    console.log(JSON.stringify({ browser: browser.version(), core: neutral.core,
      parameters: neutral.parameters, drawables: neutral.drawables,
      localFile: 'preview loaded and sliders changed the frame',
      verified: ['neutral', 'left-eye close', 'right-eye close', 'head tilt', 'tilt with both eyes closed'],
      frameChecksums: cases.map(result => result.checksum) }, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
