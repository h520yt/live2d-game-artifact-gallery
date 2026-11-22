/* Isolated from the gallery's manifest and outfit registry. */
const canvas = document.querySelector('#view');
const originPath = '../../azur_lane/';
const app = new PIXI.Application({view: canvas, width: 1100, height: 1000,
  backgroundAlpha: 0, antialias: true, autoStart: false, preserveDrawingBuffer: true});
PIXI.live2d.config.sound = false;
let model, name, controller, zoomed = false;

function freeze() {
  const core = model.internalModel.coreModel;
  const parameters = core._model.parameters;
  parameters.values.set(parameters.defaultValues);
  core.saveParameters();
  core.update();
}

function camera(box) {
  model.position.set(0);
  model.scale.set(1);
  const width = model.internalModel.width;
  const height = model.internalModel.height;
  const [x, y, w, h] = box || [0, 0, width, height];
  const scale = Math.min((app.screen.width - 36) / w, (app.screen.height - 32) / h);
  model.scale.set(scale);
  model.position.set((app.screen.width - w * scale) / 2 - x * scale,
    (app.screen.height - h * scale) / 2 - y * scale);
  app.renderer.render(app.stage);
}

async function load(newName, outfit = 'original') {
  if (newName !== name) {
    if (model) model.destroy();
    const url = `${originPath}data/models/${newName}/${newName}.model3.json`;
    model = await PIXI.live2d.Live2DModel.from(url, {autoInteract: false, autoUpdate: false});
    model.autoUpdate = false;
    app.stage.addChild(model);
    name = newName;
    const current = `${originPath}config/outfits/baifeng_3/outfit_01_final_repaint.json`;
    controller = name === 'baifeng_3' ? CubismOutfits.attach(model, [
      {id: 'current', name: '白凤现版换装', file: current},
      {id: 'trial', name: '白凤隔离试验', file: './trial/outfit.json'},
    ], document.baseURI) : null;
  }
  if (controller && !await controller.select(outfit)) throw new Error(`Cannot select ${outfit}`);
  freeze();
  camera();
}

function detail(ids, pad = 1.55) {
  camera();
  const points = geometry().drawables.filter(d => ids.includes(d.id)).flatMap(d => {
    const xy = [];
    for (let i = 0; i < d.screen.length; i += 2) xy.push(d.screen.slice(i, i + 2));
    return xy;
  });
  const xs = points.map(p => (p[0] - model.x) / model.scale.x);
  const ys = points.map(p => (p[1] - model.y) / model.scale.y);
  const [x1, x2, y1, y2] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const w = (x2 - x1) * pad;
  const h = (y2 - y1) * pad;
  camera([(x1 + x2 - w) / 2, (y1 + y2 - h) / 2, w, h]);
}

function geometry() {
  const {coreModel, renderer} = model.internalModel;
  const {drawables: d, parts, parameters: p, canvasinfo} = coreModel._model;
  const m = [...renderer.getMvpMatrix().getArray()];
  const project = vertices => Array.from(vertices, (value, i) => {
    const x = i % 2 ? vertices[i - 1] : value;
    const y = i % 2 ? value : vertices[i + 1];
    return i % 2 ? (1 - (m[1] * x + m[5] * y + m[13])) * canvas.height / 2
      : (1 + m[0] * x + m[4] * y + m[12]) * canvas.width / 2;
  });
  return {
    name, image: [canvas.width, canvas.height], matrix: m, canvasinfo: {...canvasinfo},
    version: Live2DCubismCore.Version.csmGetVersion(),
    textures: model.textures.map(t => [t.width, t.height]),
    parameters: Array.from(p.ids, (id, i) => ({id, min: p.minimumValues[i],
      max: p.maximumValues[i], default: p.defaultValues[i], keys: Array.from(p.keyValues[i])})),
    parts: Array.from(parts.ids, (id, i) => ({id, opacity: parts.opacities[i],
      parent: parts.ids[parts.parentPartIndices?.[i]] ?? null})),
    drawables: Array.from(d.ids, (id, i) => ({id, i, part: parts.ids[d.parentPartIndices?.[i]] ?? null,
      texture: d.textureIndices[i], opacity: d.opacities[i], flags: d.constantFlags[i],
      visible: coreModel.getDrawableDynamicFlagIsVisible(i), drawOrder: d.drawOrders[i], order: d.renderOrders[i],
      masks: Array.from(d.masks[i], index => d.ids[index]), uv: [...d.vertexUvs[i]],
      vertices: [...d.vertexPositions[i]], screen: project(d.vertexPositions[i]), triangles: [...d.indices[i]],
    })),
  };
}

function frame(keep = [], omit = []) {
  const {coreModel, renderer} = model.internalModel;
  const {ids, vertexUvs} = coreModel._model.drawables;
  const wanted = new Set(keep.map(id => vertexUvs[ids.indexOf(id)]));
  const unwanted = new Set(omit.map(id => vertexUvs[ids.indexOf(id)]));
  const original = renderer.drawMesh;
  renderer.drawMesh = function (texture, count, n, indices, positions, uv, ...rest) {
    if (this.getClippingContextBufferForMask() || ((!wanted.size || wanted.has(uv)) && !unwanted.has(uv))) {
      return original.call(this, texture, count, n, indices, positions, uv, ...rest);
    }
  };
  try {
    app.renderer.render(app.stage);
    return {png: canvas.toDataURL().split(',')[1], error: app.renderer.gl.getError()};
  } finally {
    renderer.drawMesh = original;
  }
}

function setMotionSample([, values, partValues]) {
  const core = model.internalModel.coreModel;
  const {parameters, parts} = core._model;
  parameters.values.set(parameters.defaultValues);
  for (const [id, value] of Object.entries(values)) {
    const i = parameters.ids.indexOf(id);
    if (i >= 0) parameters.values[i] = Math.min(parameters.maximumValues[i], Math.max(parameters.minimumValues[i], value));
  }
  for (const [id, value] of Object.entries(partValues)) {
    const i = parts.ids.indexOf(id);
    if (i >= 0) parts.opacities[i] = value;
  }
  core.update();
  app.renderer.render(app.stage);
}

window.proof = {load, geometry, frame, detail, setMotionSample, get model() { return model; }};
if (location.search.includes('capture')) {
  document.body.classList.add('capture');
} else {
  const output = document.querySelector('output');
  const buttons = [...document.querySelectorAll('nav button')];
  const zoom = document.querySelector('#zoom');
  const zoomIDs = () => name === 'baifeng_3' ? ['ArtMesh13', 'ArtMesh18'] : window.dafengShoes;
  const show = async (target, outfit) => {
    buttons.forEach(button => { button.disabled = true; });
    try {
      await load(target, outfit);
      if (zoomed) detail(zoomIDs());
      output.textContent = '';
    } catch (error) {
      output.textContent = error.message;
    } finally {
      buttons.forEach(button => { button.disabled = false; });
    }
  };
  for (const button of document.querySelectorAll('[data-model]')) {
    button.onclick = () => show(button.dataset.model, button.dataset.outfit);
  }
  zoom.onclick = () => {
    if (!model) return;
    zoomed = !zoomed;
    if (zoomed) detail(zoomIDs());
    else camera();
    zoom.textContent = zoomed ? '角色全景' : '足部近景';
  };
  show('baifeng_3', 'trial');
}
