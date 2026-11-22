const states = new WeakMap();
const watched = ["ArtMesh12", "ArtMesh13", "ArtMesh17", "ArtMesh18", "ArtMesh156",
  "ArtMesh214", "ArtMesh217", "ArtMesh223", "ArtMesh229"];
const parameters = ["Param71", "Param45", "Param48", "Param51", "Param37", "Param40", "Param43"];
const colors = {
  "far-quarter": "#f1cc00", "throat-wall": "#d5a620", "heel": "#207842", "midsole": "#43c861",
  "vamp": "#266bc9", "near-quarter": "#1992f5", "toe": "#1744b6", "instep": "#55caed",
  "lining-shadow": "#ad8400", "cavity": "#c48b00", "collar": "#fff05c", "strap": "#9260d7", "buckle": "#dc71f1",
  "sole-wall": "#34e18a", "fore-tread": "#187c47", "heel-tread": "#17532f",
  "transition-back": "#edc82c", "transition-front": "#0287aa",
};

function canvas(width, height) {
  const result = document.createElement("canvas");
  result.width = width;
  result.height = height;
  return result;
}

function attach(model, view, definitionURL) {
  if (states.has(model)) {
    const state = states.get(model);
    state.panel.hidden = false;
    return state;
  }
  const {coreModel: core, renderer} = model.internalModel;
  const {drawables, parameters: params} = core._model;
  const watchedIndices = new Set(watched.map(id => drawables.ids.indexOf(id)));
  const byVertices = new Map(drawables.vertexPositions.map((positions, i) => [positions, i]));
  const panel = document.createElement("aside");
  panel.id = "shoe-debug";
  panel.style.cssText = "position:fixed;top:124px;left:14px;z-index:30;padding:10px;background:#121820ed;color:#fff;" +
    "font:12px/1.4 monospace;border:1px solid #798797;max-height:65vh;overflow:auto;max-width:380px";
  panel.append("鞋履调试　");
  const mode = document.createElement("select");
  for (const [value, label] of [["layers", "纯色分层"], ["mesh", "网格与绑点"], ["original", "正式贴图"]]) {
    mode.add(new Option(label, value));
  }
  const isolation = document.createElement("select");
  isolation.add(new Option("全部图层", "all"));
  isolation.add(new Option("仅袜脚", "foot"));
  for (const id of watched) isolation.add(new Option("仅 " + id, "foot:" + id));
  for (const id of Object.keys(colors)) isolation.add(new Option(id, id));
  const trace = document.createElement("pre");
  trace.style.margin = "6px 0 0";
  panel.append(mode, isolation, trace);
  const overlay = canvas(1, 1);
  overlay.style.cssText = "position:fixed;z-index:29;pointer-events:none";
  overlay.hidden = true;
  document.body.append(overlay, panel);
  const pen = overlay.getContext("2d");
  let sourceTexture = null, debugTexture = null;
  const definition = fetch(definitionURL).then(response => {
    if (!response.ok) throw new Error("鞋履调试配置 HTTP " + response.status);
    return response.json();
  });
  let forms = new Map(), regions = new Map();
  let frame = [];
  const state = {
    panel, mode, isolation,
    get frame() { return frame; },
    hide() {
      panel.hidden = overlay.hidden = true;
      if (model.textures[2] === debugTexture) model.textures[2] = sourceTexture;
      debugTexture?.destroy(true);
      debugTexture = null;
    },
    async apply() {
      const config = await definition;
      if (panel.hidden) return;
      const texture = model.textures[2];
      if (!texture) {
        debugTexture?.destroy(true);
        debugTexture = sourceTexture = null;
        trace.textContent = "选择换装 01 查看鞋层";
        overlay.hidden = true;
        return;
      }
      if (texture !== debugTexture) sourceTexture = texture;
      const backup = sourceTexture.baseTexture.resource.source;
      const atlas = canvas(backup.width, backup.height);
      const ctx = atlas.getContext("2d");
      ctx.drawImage(backup, 0, 0);
      forms = new Map(config.attachments.flatMap(a => a.forms.map(f => [f.anchor, f])));
      regions = new Map();
      function recolor(region, color, opacity) {
        const [x, y, w, h] = region;
        const tile = canvas(w, h);
        const paint = tile.getContext("2d");
        paint.drawImage(backup, x, y, w, h, 0, 0, w, h);
        paint.globalCompositeOperation = "source-in";
        paint.fillStyle = color;
        paint.fillRect(0, 0, w, h);
        ctx.clearRect(x, y, w, h);
        ctx.globalAlpha = opacity;
        ctx.drawImage(tile, x, y);
        ctx.globalAlpha = 1;
      }
      for (const form of forms.values()) {
        for (const part of form.layers) {
          const [x, y] = part.region;
          regions.set(x + "," + y, {anchor: form.anchor, id: part.id, grid: form.grid});
          if (mode.value === "original") continue;
          const selected = isolation.value === "all" || isolation.value === part.id;
          recolor(part.region, colors[part.id] || "#ffe170", Number(selected));
        }
      }
      for (const {bridges = []} of config.attachments) {
        for (const {from, to, grid, frames} of bridges) {
          for (const [phase, frame] of frames.entries()) {
            for (const side of ["back", "front"]) {
              const region = frame[side];
              if (!region) continue;
              const id = "transition-" + side;
              regions.set(region.slice(0, 2).join(","), {anchor: from + "↔" + to, id, grid, phase});
              if (mode.value !== "original") {
                recolor(region, colors[id], Number(isolation.value === "all" || isolation.value === id));
              }
            }
          }
        }
      }
      if (mode.value !== "original") {
        const focused = isolation.value.startsWith("foot:") ? isolation.value.slice(5) : null;
        for (const {region, drawables} of config.patches) {
          if (drawables.includes("ArtMesh798")) continue;
          recolor(region, "#bebebe", !focused || drawables.includes(focused) ? 0.67 : 0);
        }
      }
      const previous = debugTexture;
      debugTexture = mode.value === "original" ? null : PIXI.Texture.from(atlas, {
        alphaMode: PIXI.ALPHA_MODES.UNPACK,
      });
      model.textures[2] = debugTexture || sourceTexture;
      previous?.destroy(true);
    },
  };
  const refresh = () => state.apply().catch(error => { trace.textContent = error.message; });
  mode.onchange = isolation.onchange = refresh;
  states.set(model, state);

  const drawMesh = renderer.drawMesh;
  renderer.drawMesh = function (textureIndex, count, vertexCount, triangles, vertices, uv, opacity, ...rest) {
    if (!panel.hidden && model.textures[2] && !this.getClippingContextBufferForMask()) {
      const atlas = model.textures[2];
      const key = Math.round(uv[0] * atlas.width) + "," + Math.round((1 - uv[1]) * atlas.height);
      const layer = textureIndex === 2 && regions.get(key);
      if (layer && vertexCount === layer.grid[0] * layer.grid[1]) {
        frame.push({...layer, opacity, vertices: Array.from(vertices)});
      } else {
        const index = byVertices.get(vertices);
        if (watchedIndices.has(index)) {
          frame.push({anchor: drawables.ids[index], id: "foot", order: drawables.renderOrders[index], opacity});
        }
      }
    }
    return drawMesh.call(this, textureIndex, count, vertexCount, triangles, vertices, uv, opacity, ...rest);
  };

  function drawMeshOverlay(matrix) {
    const rect = view.getBoundingClientRect();
    if (overlay.width !== Math.round(rect.width) || overlay.height !== Math.round(rect.height)) {
      overlay.width = Math.round(rect.width);
      overlay.height = Math.round(rect.height);
    }
    overlay.style.left = rect.left + "px";
    overlay.style.top = rect.top + "px";
    pen.clearRect(0, 0, overlay.width, overlay.height);
    const project = (x, y) => [
      (1 + matrix[0] * x + matrix[4] * y + matrix[12]) * rect.width / 2,
      (1 - matrix[1] * x - matrix[5] * y - matrix[13]) * rect.height / 2,
    ];
    function dot(point, radius, color) {
      pen.beginPath();
      pen.fillStyle = color;
      pen.arc(...point, radius, 0, Math.PI * 2);
      pen.fill();
    }
    function line(a, b) {
      pen.moveTo(...a);
      pen.lineTo(...b);
    }
    for (const index of watchedIndices) {
      if (!core.getDrawableDynamicFlagIsVisible(index) || drawables.opacities[index] <= 0 ||
        (!forms.has(drawables.ids[index]) && drawables.ids[index] !== "ArtMesh156" &&
          isolation.value !== "foot:" + drawables.ids[index])) continue;
      const vertices = drawables.vertexPositions[index];
      const points = [];
      for (let i = 0; i < vertices.length; i += 2) points.push(project(vertices[i], vertices[i + 1]));
      const edgeCounts = new Map();
      const idx = drawables.indices[index];
      for (let i = 0; i < idx.length; i += 3) {
        for (let k = 0; k < 3; k++) {
          const edge = [idx[i + k], idx[i + (k + 1) % 3]].sort((a, b) => a - b).join(",");
          edgeCounts.set(edge, (edgeCounts.get(edge) || 0) + 1);
        }
      }
      pen.strokeStyle = "#ff4058";
      pen.lineWidth = 1.45;
      pen.beginPath();
      for (const [edge, count] of edgeCounts) {
        if (count !== 1) continue;
        const [a, b] = edge.split(",").map(Number);
        line(points[a], points[b]);
      }
      pen.stroke();
      for (const point of points) dot(point, 1.55, "#ff4058");
      pen.fillStyle = "#ff9caa";
      pen.font = "bold 12px monospace";
      const top = points.reduce((a, b) => a[1] < b[1] ? a : b);
      pen.fillText(drawables.ids[index], top[0] + 8, top[1] - 4);
    }
    const drawn = new Map(frame.filter(item => item.vertices).map(item => [item.anchor, item]));
    for (const [anchor, item] of drawn) {
      const form = forms.get(anchor);
      const [columns, rows] = item.grid;
      const grid = item.vertices;
      const points = [];
      for (let i = 0; i < grid.length; i += 2) points.push(project(grid[i], grid[i + 1]));
      pen.strokeStyle = "#00ebff";
      pen.lineWidth = 0.8;
      pen.beginPath();
      points.forEach((point, i) => {
        if (i % columns) line(point, points[i - 1]);
        if (i >= columns) line(point, points[i - columns]);
      });
      pen.stroke();
      const source = form && drawables.vertexPositions[drawables.ids.indexOf(anchor)];
      for (let i = 0; i < columns * rows; i++) {
        dot(points[i], 1.8, "#00ebff");
        if (!source) continue;
        let x = 0, y = 0;
        for (const [index, weight] of form.bindings[i]) {
          x += source[index * 2] * weight;
          y += source[index * 2 + 1] * weight;
        }
        dot(project(x, y), 2.3, "#ffffff");
      }
    }
  }

  const draw = renderer.doDrawModel;
  renderer.doDrawModel = function () {
    frame = [];
    const result = draw.call(this);
    if (panel.hidden || !model.textures[2]) return result;
    overlay.hidden = mode.value !== "mesh";
    const posture = parameters.map(id => id + "=" + params.values[params.ids.indexOf(id)].toFixed(2));
    const legend = "灰：袜脚　黄：鞋口　蓝：鞋面　绿：鞋底　紫：装饰";
    const meshLegend = overlay.hidden ? "" : "\n红：原脚网格　白：加权控制点　青：鞋网格";
    trace.textContent = legend + meshLegend + "\n" + posture.slice(0, 4).join(" ") + "\n" +
      posture.slice(4).join(" ") + "\n" + frame.map(({anchor, id, order, opacity, phase}, i) =>
        String(i + 1).padStart(2) + " " + anchor + " " + id +
        (order === undefined ? "" : " #" + order) +
        (phase === undefined ? "" : " phase=" + phase) + " α=" + opacity.toFixed(2)).join("\n");
    if (!overlay.hidden) drawMeshOverlay(this.getMvpMatrix().getArray());
    return result;
  };
  model.once("destroy", () => { state.hide(); overlay.remove(); panel.remove(); });
  return state;
}

window.AzurShoeDebug = {attach, get: model => states.get(model)};
