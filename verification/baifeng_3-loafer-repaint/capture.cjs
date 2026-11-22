// Run at the project root: node verification/baifeng_3-loafer-repaint/capture.cjs MODE
const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '../..');
const previous = path.resolve(__dirname, '../baifeng_3-foot-repaint');
const origin = 'http://azur-loafers.test';
const configDir = '/azur_lane/config/outfits/';
const mime = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.png': 'image/png'};
const mode = process.argv[2];
const refine = process.argv.includes('--refine');
const finalRepaint = process.argv.includes('--final-repaint');
const foreground = process.argv.includes('--foreground');
const output = finalRepaint ? path.resolve(__dirname, '../baifeng_3-loafer-final') :
  refine ? path.resolve(__dirname, '../baifeng_3-loafer-detail') : __dirname;
const baselineAtlas = finalRepaint ? 'outfit_01_loafer_detail' : refine ? 'outfit_01_loafers' : 'outfit_01_repaint';
const finalAtlas = finalRepaint ? 'outfit_01_final_repaint' : refine ? 'outfit_01_loafer_detail' : 'outfit_01_loafers';

async function exportPaint(browser, structure) {
  const base = await fs.readFile(path.join(previous, 'footwear.svg'), 'utf8');
  // Clip the two independently painted plates to the exact existing shell.
  const clips = ['frontOutline', 'rearOutline', 'frontClip', 'rearClip'].map(id => {
    const node = base.match(new RegExp(`<(?:path|clipPath) id="${id}"[^\n]+`));
    assert.ok(node, id);
    return node[0];
  }).join('\n');
  const plate = paint => paint.replace('<defs>', `<defs>${clips}`)
    .replace('<svg ', structure ? '<svg class="structure" ' : '<svg ');
  const style = '<style>body{margin:0} svg{width:840px;height:870px;display:block}</style>';
  const page = await browser.newPage({viewport: {width: 840, height: 870}});
  if (finalRepaint) {
    for (const foot of (foreground ? ['fore'] : ['fore', 'rear'])) {
      const paint = await fs.readFile(path.join(output, `${foot}.svg`), 'utf8');
      await page.setContent(style + plate(paint));
      await page.screenshot({path: path.join(output, `${foot}-${mode}.local.png`), omitBackground: true});
    }
    await page.close();
    return;
  }
  await page.setContent(style + plate(await fs.readFile(path.join(__dirname, 'paint.svg'), 'utf8')));
  if (refine) {
    const detail = await fs.readFile(path.join(output, 'detail.svg'), 'utf8');
    await page.evaluate(detail => {
      const additions = new DOMParser().parseFromString(detail, 'image/svg+xml');
      if (additions.querySelector('parsererror')) throw new Error('Invalid detail.svg');
      const canvas = document.querySelector('svg');
      canvas.append(document.importNode(additions.querySelector('style'), true));
      for (const node of additions.querySelector('defs').children) {
        const copy = document.importNode(node, true);
        const old = canvas.querySelector(`#${node.id}`);
        if (old) old.replaceWith(copy);
        else canvas.querySelector('defs').append(copy);
      }
      for (const [foot, surface] of [['fore', 'front'], ['rear', 'rear']]) {
        const shoe = canvas.querySelector(`#${foot}-paint`);
        const overlay = additions.querySelector(`#${surface}-vamp-detail`);
        shoe.querySelector(`g[clip-path="url(#${surface}ApronClip)"]`).replaceWith(document.importNode(overlay, true));
        const saddle = shoe.querySelector(`.${surface}-saddle`);
        const edge = saddle.nextElementSibling;
        const glint = edge.nextElementSibling;
        const hardware = glint.nextElementSibling;
        if (!hardware.matches('g[transform^="matrix("]')) throw new Error('Old saddle elements moved');
        const assembly = additions.querySelector(`#${surface}-assembly`);
        saddle.replaceWith(document.importNode(assembly, true));
        edge.remove();
        glint.remove();
        hardware.remove();
      }
    }, detail);
  }
  for (const foot of ['fore', 'rear']) {
    await page.evaluate(foot => {
      for (const group of document.querySelectorAll('svg > g')) {
        group.style.display = group.id === `${foot}-paint` ? '' : 'none';
      }
    }, foot);
    await page.screenshot({path: path.join(output, `${foot}-${mode}.local.png`), omitBackground: true});
  }
  await page.close();
}

async function captureViewer(browser, variant) {
  const errors = [];
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}, deviceScaleFactor: 2});
  page.on('pageerror', error => errors.push(error.message));
  let failFinalAtlasOnce = variant === 'final';
  await page.route(origin + '/**', async route => {
    const url = decodeURIComponent(new URL(route.request().url()).pathname);
    const file = path.join(root, url);
    const contentType = mime[path.extname(file)] || 'application/octet-stream';
    if (url === '/azur_lane/viewer/manifest.json') {
      const manifest = JSON.parse(await fs.readFile(file, 'utf8'));
      const models = manifest.models.filter(entry => entry.name === 'baifeng_3');
      assert.equal(models.length, 1);
      return route.fulfill({json: {...manifest, models, characters: []}});
    }
    if (url === configDir + 'index.json' && (variant !== 'final' || !finalRepaint)) {
      const index = JSON.parse(await fs.readFile(file, 'utf8'));
      index.models.baifeng_3[0].file = `baifeng_3/${variant === 'final' ? finalAtlas : baselineAtlas}.json`;
      return route.fulfill({json: index});
    }
    if (url.endsWith(`/${baselineAtlas}.png`) && ['structure', 'preview'].includes(variant)) {
      return route.fulfill({contentType, path: path.join(output, `${variant}-atlas.local.png`)});
    }
    if (url.endsWith(`/${finalAtlas}.png`) && failFinalAtlasOnce) {
      failFinalAtlasOnce = false;
      return route.fulfill({status: 404});
    }
    if (route.request().method() === 'HEAD') {
      const stat = await fs.stat(file).catch(() => null);
      if (!stat) return route.fulfill({status: 404});
      return route.fulfill({contentType, headers: {'content-length': String(stat.size)}});
    }
    try {
      return await route.fulfill({contentType, path: file});
    } catch {
      return route.fulfill({status: 404});
    }
  });
  await page.goto(origin + '/azur_lane/viewer/index.html');
  await page.evaluate(() => { PIXI.live2d.config.sound = false; });
  await page.getByText('Sunshower Fox Bride', {exact: true}).click();
  const select = page.locator('#outfit-select');
  await select.waitFor({state: 'visible'});
  assert.deepEqual(await select.locator('option').allTextContents(), ['原始装扮', '换装 01 · 黑丝皮鞋']);
  assert.equal(await select.inputValue(), 'original');
  await page.evaluate(() => {
    app.stop();
    current.autoUpdate = false;
    current.deltaTime = 0;
    const core = current.internalModel.coreModel;
    core._model.parameters.values.set(core._model.parameters.defaultValues);
    core.saveParameters();
    core.update();
  });

  const original = await snapshot(page);
  if (variant === 'final' && finalRepaint) {
    await fs.writeFile(path.join(output, 'original-render.png'), Buffer.from(original.png, 'base64'));
  }
  if (variant === 'final') {
    await select.selectOption('outfit_01');
    await page.getByText('换装加载失败，可重试', {exact: true}).waitFor();
    assert.equal(await select.inputValue(), 'original');
    assert.deepEqual(await snapshot(page), original);
  }
  await selectOutfit();
  const dressed = await snapshot(page);
  assert.notEqual(dressed.png, original.png);
  assert.deepEqual(dressed.state, original.state);

  if (variant === 'final') {
    for (let attempt = 0; attempt < 2; attempt++) {
      await select.selectOption('original');
      await page.waitForFunction(() => current.textures.length === 2);
      assert.deepEqual(await snapshot(page), original);
      await selectOutfit();
      assert.deepEqual(await snapshot(page), dressed);
    }
    const {sourceSha256} = JSON.parse(await fs.readFile(path.join(previous, 'analysis.json'), 'utf8'));
    for (const [file, expected] of Object.entries(sourceSha256)) {
      const bytes = await fs.readFile(path.join(root, 'azur_lane/data/models/baifeng_3', file));
      assert.equal(createHash('sha256').update(bytes).digest('hex'), expected, file);
    }
  }

  const proof = foreground ? `foreground-${variant}` : variant;
  const renderFile = variant === 'baseline' || foreground ? `${proof}-render.local.png` : `${proof}-render.png`;
  await fs.writeFile(path.join(output, renderFile), Buffer.from(dressed.png, 'base64'));
  const detail = await snapshot(page, true);
  await fs.writeFile(path.join(output, `${proof}-detail.local.png`), Buffer.from(detail.png, 'base64'));
  const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
  await fs.writeFile(path.join(output, `${proof}-check.local.json`), JSON.stringify({
    defaultCamera: dressed.state.camera, detailCamera: detail.state.camera, framebuffer: dressed.state.framebuffer,
    pose: digest(dressed.state.parameters), drawCalls: dressed.drawCalls,
    drawSequence: digest(dressed.trace), original: digest(original.png),
  }, null, 2));
  assert.deepEqual(errors, []);
  console.log(`${variant}: ${dressed.drawCalls} draw calls, WebGL capture verified`);
  await page.close();

  async function selectOutfit() {
    await select.selectOption('outfit_01');
    await page.waitForFunction(() => current.textures.length === 3 && document.querySelector('#outfit-status').hidden);
  }
}

async function snapshot(page, detail = false) {
  const result = await page.evaluate(detail => {
    const renderer = app.renderer;
    const {resolution, width, height} = renderer;
    const camera = [current.x, current.y, current.scale.x, current.scale.y];
    let crop = [0, 0, width, height];
    if (detail) {
      const [left, top, w, h] = [1630, 1160, 840, 870];
      const x = Math.round((width - w) / 2), y = Math.round((height - h) / 2);
      current.position.set(x / resolution + (camera[0] - left / resolution) * 3,
        y / resolution + (camera[1] - top / resolution) * 3);
      current.scale.set(camera[2] * 3, camera[3] * 3);
      crop = [x, y, w, h];
    }
    const state = {framebuffer: [width, height], camera: [current.x, current.y, current.scale.x, current.scale.y],
      parameters: [...current.internalModel.coreModel._model.parameters.values]};
    const cubism = current.internalModel.renderer;
    const draw = cubism.drawMesh;
    const trace = [];
    cubism.drawMesh = function (texture, count, vertexCount, indices, vertices, uv, opacity, ...rest) {
      trace.push([texture, count, vertexCount, opacity, ...indices, ...vertices, ...uv]);
      return draw.call(this, texture, count, vertexCount, indices, vertices, uv, opacity, ...rest);
    };
    let png;
    try {
      renderer.render(app.stage);
      const canvas = document.createElement('canvas');
      canvas.width = crop[2];
      canvas.height = crop[3];
      canvas.getContext('2d').drawImage(app.view, ...crop, 0, 0, canvas.width, canvas.height);
      png = canvas.toDataURL().split(',')[1];
    } finally {
      cubism.drawMesh = draw;
      current.position.set(camera[0], camera[1]);
      current.scale.set(camera[2], camera[3]);
    }
    return {png, state, trace, drawCalls: trace.length, error: renderer.gl.getError()};
  }, detail);
  assert.equal(result.error, 0);
  return result;
}

async function run() {
  assert.ok(['structure-art', 'final-art', 'baseline', 'structure', 'preview', 'final'].includes(mode));
  const browser = await chromium.launch({channel: 'chrome',
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
  try {
    if (mode.endsWith('-art')) await exportPaint(browser, mode === 'structure-art');
    else await captureViewer(browser, mode);
  } finally {
    await browser.close();
  }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
