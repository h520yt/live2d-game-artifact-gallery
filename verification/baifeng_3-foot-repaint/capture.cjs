// Run from the repository with baifeng_3, qiye_10, Playwright and Chrome installed.
const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '../..');
const origin = 'http://azur-repaint.test';
const MIME = {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
  '.json': 'application/json', '.png': 'image/png'};
const feet = ['ArtMesh13', 'ArtMesh18', 'ArtMesh214', 'ArtMesh156',
  ...Array.from({length: 6}, (_, i) => `ArtMesh${230 + i}`)];
const layers = [...feet, 'ArtMesh12', 'ArtMesh17', 'ArtMesh100', 'ArtMesh216', 'ArtMesh217'];
const crop = [1630, 1160, 1910, 1450];
const artScale = 3;

async function setup(browser, errors) {
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}, deviceScaleFactor: 2});
  page.on('pageerror', error => errors.push(error.message));
  const atlas = 'outfit_01_repaint.png';
  let failOnce = process.argv.includes('--verify');
  await page.route(`${origin}/**`, async route => {
    const pathname = decodeURIComponent(new URL(route.request().url()).pathname);
    const file = path.join(root, pathname);
    const contentType = MIME[path.extname(file)] || 'application/octet-stream';
    if (pathname === '/azur_lane/viewer/manifest.json') {
      const manifest = JSON.parse(await fs.readFile(file, 'utf8'));
      const models = manifest.models.filter(({name}) => ['baifeng_3', 'qiye_10'].includes(name));
      assert.equal(models.length, 2);
      return route.fulfill({json: {...manifest, models, characters: []}});
    }
    if (failOnce && pathname.endsWith(`/${atlas}`)) {
      failOnce = false;
      return route.fulfill({status: 404});
    }
    try {
      if (route.request().method() === 'HEAD') {
        return await route.fulfill({contentType, headers: {'content-length': String((await fs.stat(file)).size)}});
      }
      return await route.fulfill({contentType, path: file});
    } catch {
      return route.fulfill({status: 404});
    }
  });
  await page.goto(`${origin}/azur_lane/viewer/index.html`);
  await page.evaluate(() => { PIXI.live2d.config.sound = false; });
  await page.getByText('Sunshower Fox Bride', {exact: true}).click();
  await page.locator('#outfit-select').waitFor({state: 'visible'});
  return page;
}

function render(area) {
  app.renderer.render(app.stage);
  const gl = app.renderer.gl;
  const [left, top, width, height] = area || [0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight];
  const row = width * 4;
  const rgba = new Uint8ClampedArray(row * height);
  gl.readPixels(left, gl.drawingBufferHeight - top - height, width, height, gl.RGBA, gl.UNSIGNED_BYTE, rgba);
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  const pixels = ctx.createImageData(width, height);
  for (let y = 0; y < height; y++) {
    pixels.data.set(rgba.subarray((height - 1 - y) * row, (height - y) * row), y * row);
  }
  // The WebGL framebuffer stores premultiplied RGB.
  for (let i = 0; i < pixels.data.length; i += 4) {
    const alpha = pixels.data[i + 3];
    if (alpha && alpha < 255) {
      for (let c = 0; c < 3; c++) pixels.data[i + c] *= 255 / alpha;
    }
  }
  ctx.putImageData(pixels, 0, 0);
  return {png: canvas.toDataURL().split(',')[1], glError: gl.getError()};
}

async function writePng(name, result) {
  assert.equal(result.glError, 0);
  const png = Buffer.from(result.png, 'base64');
  await fs.writeFile(path.join(__dirname, `${name}.png`), png);
  return png;
}

async function freeze(page) {
  await page.evaluate(() => {
    app.stop();
    current.autoUpdate = false;
    current.deltaTime = 0;
    const core = current.internalModel.coreModel;
    core._model.parameters.values.set(core._model.parameters.defaultValues);
    core.saveParameters();
    core.update();
    app.renderer.render(app.stage);
  });
}

async function detailCamera(page) {
  const area = await page.evaluate(({crop: [left, top, right, bottom], artScale}) => {
    const {resolution, screen} = app.renderer;
    const x = Math.round((screen.width * resolution - (right - left) * artScale) / 2);
    const y = Math.round((screen.height * resolution - (bottom - top) * artScale) / 2);
    window.originalCamera = [current.x, current.y, current.scale.x, current.scale.y];
    current.position.set(x / resolution + (current.x - left / resolution) * artScale,
      y / resolution + (current.y - top / resolution) * artScale);
    current.scale.set(current.scale.x * artScale, current.scale.y * artScale);
    return [x, y, (right - left) * artScale, (bottom - top) * artScale];
  }, {crop, artScale});
  return area;
}

async function restoreCamera(page) {
  await page.evaluate(() => {
    const [x, y, sx, sy] = window.originalCamera;
    current.position.set(x, y);
    current.scale.set(sx, sy);
  });
}

async function exportGeometry(page) {
  const geometry = await page.evaluate(() => {
    const {coreModel: core, renderer} = current.internalModel;
    const d = core._model.drawables;
    const m = [...renderer.getMvpMatrix().getArray()];
    const {width, height} = app.renderer;
    return {
      canvas: [width, height], matrix: m,
      textures: current.textures.map(({width, height}) => [width, height]),
      drawables: Array.from(d.ids, (id, i) => ({id,
        visible: core.getDrawableDynamicFlagIsVisible(i), opacity: d.opacities[i], order: d.renderOrders[i],
        texture: d.textureIndices[i], masks: Array.from(d.masks[i], index => d.ids[index]),
        vertices: [...d.vertexPositions[i]], uv: [...d.vertexUvs[i]], triangles: [...d.indices[i]],
      })),
    };
  });
  await fs.writeFile(path.join(__dirname, 'geometry.local.json'), JSON.stringify({...geometry, crop, artScale}));
  const detail = await detailCamera(page);
  for (const id of layers) {
    await page.evaluate(id => {
      const {coreModel: core, renderer} = current.internalModel;
      const {ids, vertexUvs} = core._model.drawables;
      const selectedUV = vertexUvs[ids.indexOf(id)];
      window.restoreMesh = renderer.drawMesh;
      renderer.drawMesh = function (texture, count, vertices, indices, positions, uv, ...rest) {
        if (this.getClippingContextBufferForMask() || uv === selectedUV) {
          return window.restoreMesh.call(this, texture, count, vertices, indices, positions, uv, ...rest);
        }
      };
    }, id);
    await writePng(`${id}.local`, await page.evaluate(render, detail));
    await page.evaluate(() => { current.internalModel.renderer.drawMesh = window.restoreMesh; });
  }
  await restoreCamera(page);
}

async function exportArtwork(browser) {
  const width = (crop[2] - crop[0]) * artScale;
  const height = (crop[3] - crop[1]) * artScale;
  const page = await browser.newPage({viewport: {width, height}, deviceScaleFactor: 1});
  const artwork = await fs.readFile(path.join(__dirname, 'footwear.svg'), 'utf8');
  await page.setContent(`<style>html,body{margin:0}svg{width:${width}px;height:${height}px;display:block}</style>${artwork}`);
  for (const id of ['fore-paint', 'rear-paint', 'fore-keep', 'rear-keep']) {
    await page.evaluate(id => {
      for (const item of document.querySelectorAll('svg > :is(g,path)')) {
        item.style.display = item.id === id ? '' : 'none';
      }
    }, id);
    await page.screenshot({path: path.join(__dirname, `${id}.local.png`), omitBackground: true});
  }
  await page.close();
}

async function selectDressed(page) {
  await page.locator('#outfit-select').selectOption('outfit_01');
  await page.waitForFunction(() => current?.textures.length === 3);
}

async function verify(page, original) {
  const select = page.locator('#outfit-select');
  assert.deepEqual(await select.locator('option').allTextContents(), ['原始装扮', '换装 01 · 黑丝皮鞋']);

  await select.selectOption('outfit_01');
  await page.getByText('换装加载失败，可重试', {exact: true}).waitFor();
  assert.equal(await select.inputValue(), 'original');
  assert.deepEqual(Buffer.from((await page.evaluate(render)).png, 'base64'), original);
  const detail = await detailCamera(page);
  await writePng('original-detail.local', await page.evaluate(render, detail));
  await restoreCamera(page);

  await selectDressed(page);
  const dressed = await writePng('dressed', await page.evaluate(render));
  assert.notDeepEqual(dressed, original);
  for (let attempt = 0; attempt < 2; attempt++) {
    await select.selectOption('original');
    const restored = await page.evaluate(render);
    assert.equal(restored.glError, 0);
    assert.deepEqual(Buffer.from(restored.png, 'base64'), original);
    await selectDressed(page);
    assert.deepEqual(Buffer.from((await page.evaluate(render)).png, 'base64'), dressed);
  }

  assert.deepEqual(await detailCamera(page), detail);
  await writePng('dressed-detail.local', await page.evaluate(render, detail));
  await restoreCamera(page);

  await page.locator('#l2d-back').click();
  await page.locator('#l2d-grid .card .name').filter({hasText: /^qiye_10$/}).click();
  await page.waitForFunction(() => current?.internalModel.settings.url.includes('/qiye_10/'));
  assert.equal(await select.isVisible(), false);
  assert.equal(await page.evaluate(() => current.textures.length), 2);
  assert.equal((await page.evaluate(render)).glError, 0);

  await page.locator('#l2d-back').click();
  await page.getByText('Sunshower Fox Bride', {exact: true}).click();
  await select.waitFor({state: 'visible'});
  assert.equal(await select.inputValue(), 'original');
  assert.equal(await page.evaluate(() => current.textures.length), 2);
  await page.evaluate(() => { current.autoUpdate = true; app.start(); });
  await selectDressed(page);
  assert.equal(await select.inputValue(), 'outfit_01');

  const {sourceSha256} = JSON.parse(await fs.readFile(path.join(__dirname, 'analysis.json'), 'utf8'));
  const modelDir = path.join(root, 'azur_lane/data/models/baifeng_3');
  for (const [file, expected] of Object.entries(sourceSha256)) {
    const actual = createHash('sha256').update(await fs.readFile(path.join(modelDir, file))).digest('hex');
    assert.equal(actual, expected, `${file} changed`);
  }
}

async function main() {
  const browser = await chromium.launch({channel: 'chrome',
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
  try {
    if (process.argv.includes('--art')) return await exportArtwork(browser);
    const errors = [];
    const page = await setup(browser, errors);
    await freeze(page);
    const original = await writePng('original', await page.evaluate(render));
    if (process.argv.includes('--verify')) await verify(page, original);
    else await exportGeometry(page);
    assert.deepEqual(errors, []);
    console.log(process.argv.includes('--verify') ? 'Default-pose viewer checks passed.' : 'Default geometry exported.');
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
