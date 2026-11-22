/* Outfit adapter for the bundled pixi-live2d-display Cubism renderer.
 * Texture patches keep the original UVs, clipping and draw order. Attachments
 * use artwork vertices bound to the current frame's ArtMesh vertices.
 */
(function (global) {
  "use strict";

  const controllers = new WeakMap();

  function enabledOutfits(definitions) {
    if (!Array.isArray(definitions)) return [];
    const ids = new Set(["original"]);
    return definitions.filter(outfit => {
      if (typeof outfit?.id !== "string" || !outfit.id || typeof outfit.name !== "string" ||
        typeof outfit.file !== "string" || !outfit.file || outfit.enabled === false || ids.has(outfit.id)) {
        return false;
      }
      ids.add(outfit.id);
      return true;
    });
  }

  async function loadImage(url) {
    const image = new Image();
    image.src = url;
    await image.decode();
    return image;
  }

  function placeForm(form) {
    const {pins, positions, vertices, reference} = form;
    const target = form.fitPoints || vertices;
    for (let i = 0; i < pins.length; i++) {
      let x = 0, y = 0;
      for (const [vertex, weight] of pins[i]) {
        x += positions[vertex * 2] * weight;
        y += positions[vertex * 2 + 1] * weight;
      }
      target[i * 2] = x;
      target[i * 2 + 1] = y;
    }
    if (!reference) return;

    // Carry the distance beyond the foot mesh with the overall rotation and
    // scale, while each grid point keeps its own local motion from the foot.
    const count = pins.length;
    let centerX = 0, centerY = 0;
    for (let i = 0; i < count; i++) {
      centerX += target[i * 2] / count;
      centerY += target[i * 2 + 1] / count;
    }
    let along = 0, across = 0;
    for (let i = 0; i < count; i++) {
      const [x, y] = reference.points[i];
      const dx = target[i * 2] - centerX, dy = target[i * 2 + 1] - centerY;
      along += x * dx + y * dy;
      across += x * dy - y * dx;
    }
    along /= reference.lengthSquared;
    across /= reference.lengthSquared;
    form.along = along;
    form.across = across;
    for (let i = 0; i < reference.shape.length; i++) {
      const [x, y] = reference.shape[i];
      const baseX = reference.local ? target[i * 2] : centerX;
      const baseY = reference.local ? target[i * 2 + 1] : centerY;
      vertices[i * 2] = baseX + along * x - across * y;
      vertices[i * 2 + 1] = baseY + across * x + along * y;
    }
    if (form.soleSupport) placeSole(form);
  }

  function placeSole({vertices, soleSupport: {supports: [a, b], drop, offsets, weights}}) {
    // Fit the rest profile through the existing forefoot and heel anchors.
    // Blend the rim toward that profile while those two grid points stay put.
    const x = vertices[a * 2], y = vertices[a * 2 + 1];
    const along = (y - vertices[b * 2 + 1]) / drop;
    const across = (vertices[b * 2] - x) / drop;
    for (let i = 0; i < weights.length; i++) {
      const u = offsets[i * 2], v = offsets[i * 2 + 1];
      const targetX = x + along * u - across * v;
      const targetY = y + across * u + along * v;
      vertices[i * 2] += (targetX - vertices[i * 2]) * weights[i];
      vertices[i * 2 + 1] += (targetY - vertices[i * 2 + 1]) * weights[i];
    }
  }

  function gridPoint([u, v], {grid: [columns, rows], vertices}) {
    const x = u * (columns - 1), y = v * (rows - 1);
    const col = Math.max(0, Math.min(columns - 2, Math.floor(x)));
    const row = Math.max(0, Math.min(rows - 2, Math.floor(y)));
    const dx = x - col, dy = y - row;
    const topLeft = (row * columns + col) * 2;
    const bottomRight = topLeft + (columns + 1) * 2;
    const middle = topLeft + (dx >= dy ? 2 : columns * 2);
    const weight = Math.min(dx, dy);
    const length = Math.max(dx, dy);
    return [0, 1].map(axis => vertices[topLeft + axis] * (1 - length) +
      vertices[middle + axis] * (length - weight) + vertices[bottomRight + axis] * weight);
  }

  function contactStrength(foot, floor) {
    const [x, y] = gridPoint(foot.groundPoint, foot);
    const [groundX, groundY] = gridPoint([0.5, 0.5], floor);
    const v = floor.vertices;
    const width = Math.hypot(v[2] - v[0], v[3] - v[1]);
    const travel = Math.hypot(x - groundX, y - groundY) / (width * 0.18);
    const fade = Math.max(0, Math.min(1, 1 - travel));
    return fade * fade * (3 - 2 * fade);
  }

  function placeStiffLayer(layer, form) {
    const {pivot, stiffness, offsets, vertices} = layer;
    const [x, y] = gridPoint(pivot, form);
    for (let i = 0; i < offsets.length; i += 2) {
      const u = offsets[i], v = offsets[i + 1];
      const rigidX = x + form.along * u - form.across * v;
      const rigidY = y + form.across * u + form.along * v;
      vertices[i] = form.vertices[i] + (rigidX - form.vertices[i]) * stiffness;
      vertices[i + 1] = form.vertices[i + 1] + (rigidY - form.vertices[i + 1]) * stiffness;
    }
  }

  function gridTriangles(columns, rows) {
    const triangles = [];
    for (let row = 1; row < rows; row++) {
      for (let col = 1; col < columns; col++) {
        const i = row * columns + col;
        triangles.push(i - columns - 1, i - 1, i, i - columns - 1, i, i - columns);
      }
    }
    return new Uint16Array(triangles);
  }

  function placeBridge(bridge, t) {
    const {from, to, fromUV, toUV, vertices, triangles} = bridge;
    placeForm(from);
    placeForm(to);
    for (let i = 0; i < fromUV.length; i++) {
      const a = gridPoint(fromUV[i], from);
      const b = gridPoint(toUV[i], to);
      vertices[i * 2] = a[0] + (b[0] - a[0]) * t;
      vertices[i * 2 + 1] = a[1] + (b[1] - a[1]) * t;
    }
    for (let i = 0; i < triangles.length; i += 3) {
      const a = triangles[i] * 2, b = triangles[i + 1] * 2, c = triangles[i + 2] * 2;
      const area = (vertices[b] - vertices[a]) * (vertices[c + 1] - vertices[a + 1]) -
        (vertices[b + 1] - vertices[a + 1]) * (vertices[c] - vertices[a]);
      if (!(area > 0)) return false;
    }
    return true;
  }

  function bridgeProgress({from, to}, opacities, orders) {
    let outgoing = opacities[from.index], incoming = opacities[to.index];
    if (orders[to.index] > orders[from.index]) outgoing *= 1 - incoming;
    else incoming *= 1 - outgoing;
    return incoming / (incoming + outgoing);
  }

  function attach(model, definitions, baseURL) {
    if (controllers.has(model)) return controllers.get(model);
    const options = enabledOutfits(definitions);
    const internal = model.internalModel;
    const core = internal?.coreModel;
    const drawables = core?._model?.drawables;
    const renderer = internal?.renderer;
    if (!options.length || !drawables || !renderer?.drawMesh || !renderer?.doDrawModel) return null;

    const indexById = new Map(Array.from(drawables.ids, (id, index) => [id, index]));
    const indexByUV = new Map(drawables.vertexUvs.map((uv, index) => [uv, index]));
    const originals = model.textures;
    const outfitTextureIndex = originals.length;
    const prepared = new Map();
    const textures = new Set();
    let active = null;
    let selection = 0;
    let destroyed = false;

    function drawableIndex(id) {
      const index = indexById.get(id);
      if (index === undefined) throw new Error("Unknown outfit ArtMesh: " + id);
      return index;
    }

    function checkRegion(image, region) {
      const [x, y, width, height] = region;
      if (!region.every(Number.isInteger) || x < 0 || y < 0 || width <= 0 || height <= 0 ||
        x + width > image.width || y + height > image.height) {
        throw new Error("Outfit atlas region is out of bounds: " + region.join(", "));
      }
    }

    async function prepare(option) {
      const url = new URL(option.file, baseURL);
      const response = await fetch(url);
      if (!response.ok) throw new Error("Outfit HTTP " + response.status + ": " + url);
      const definition = await response.json();
      const artwork = await loadImage(new URL(definition.atlas, url));
      const atlas = document.createElement("canvas");
      atlas.width = artwork.width;
      atlas.height = artwork.height;
      const ctx = atlas.getContext("2d");
      ctx.drawImage(artwork, 0, 0);
      const patches = new Map();
      const formPatches = new Map();

      for (const {drawables: ids, source, region, coverage, overlay, whenForm} of definition.patches || []) {
        const [x, y, width, height] = region;
        checkRegion(atlas, region);
        const indices = ids.map(drawableIndex);
        const sourceIndex = drawables.textureIndices[indices[0]];
        const image = originals[sourceIndex].baseTexture.resource.source;
        const sourceRegion = [...source, width, height];
        checkRegion(image, sourceRegion);
        // Keep the original silhouette unless an attachment covers part of it.
        // Apply the optional cutout in the same UV space as the material.
        const patch = document.createElement("canvas");
        patch.width = width;
        patch.height = height;
        const paint = patch.getContext("2d");
        if (overlay) {
          // An ankle overlap may share a drawable with the rest of the leg.
          // Only submit the painted pixels, using the original mesh alpha.
          paint.drawImage(artwork, ...region, 0, 0, width, height);
          paint.globalCompositeOperation = "destination-in";
          paint.drawImage(image, ...sourceRegion, 0, 0, width, height);
        } else {
          paint.drawImage(image, ...sourceRegion, 0, 0, width, height);
          paint.globalCompositeOperation = "source-atop";
          paint.drawImage(artwork, ...region, 0, 0, width, height);
        }
        if (coverage) {
          const coverageRegion = [...coverage, width, height];
          checkRegion(atlas, coverageRegion);
          paint.globalCompositeOperation = "destination-in";
          paint.drawImage(artwork, ...coverageRegion, 0, 0, width, height);
        }
        ctx.clearRect(x, y, width, height);
        ctx.drawImage(patch, x, y);
        let destination = patches;
        if (whenForm) {
          const anchor = drawableIndex(whenForm);
          if (!formPatches.has(anchor)) formPatches.set(anchor, new Map());
          destination = formPatches.get(anchor);
        }
        for (const index of indices) {
          if (drawables.textureIndices[index] !== sourceIndex) {
            throw new Error("Outfit patch spans multiple original textures");
          }
          const originalUV = drawables.vertexUvs[index];
          if (originalUV.some((value, i) => {
            const offset = i % 2 === 0 ? value * image.width - source[0] : (1 - value) * image.height - source[1];
            return offset < -0.01 || offset > (i % 2 === 0 ? width : height) + 0.01;
          })) {
            throw new Error("ArtMesh falls outside outfit patch: " + drawables.ids[index]);
          }
          const uv = originalUV.map((coordinate, i) => i % 2 === 0
            ? (coordinate * image.width - source[0] + x) / atlas.width
            : 1 - ((1 - coordinate) * image.height - source[1] + y) / atlas.height);
          destination.set(index, {uv, overlay});
        }
      }

      function fit({anchor, region, size, grid, bindings, rigid, warpRest, groundPoint, underlay, layers, soleSupport}) {
        const [width, height] = size || region.slice(2);
        const [columns, rows] = grid;
        const index = drawableIndex(anchor);
        const count = columns * rows;
        if (!grid.every(n => Number.isInteger(n) && n >= 2 && n <= 32) ||
          (rigid ? bindings.length !== rigid.length || rigid.length < 2 || count !== 4 : bindings.length !== count) ||
          (warpRest && (rigid || warpRest.length !== count ||
            warpRest.some(point => point.length !== 2 || !point.every(Number.isFinite)))) ||
          (layers && (!layers.length || !Number.isFinite(width) || !Number.isFinite(height) ||
            width <= 0 || height <= 0))) {
          throw new Error("Invalid outfit attachment grid: " + anchor);
        }
        const positions = drawables.vertexPositions[index];
        const textureCoordinates = rect => rectangleUV(rect, grid);
        const uv = region && textureCoordinates(region);
        const underlayUV = underlay && textureCoordinates([...underlay, width, height]);
        const fittedLayers = layers?.map(({region, frame, behind, after, rotation = 0, stiffness = 0, pivot}) => {
          const uv = textureCoordinates(region);
          if (behind && after) throw new Error("Conflicting outfit layer order: " + anchor);
          const afterIndex = after === undefined ? undefined : drawableIndex(after);
          if (stiffness !== 0) {
            if (!warpRest || frame || rotation !== 0 || !Number.isFinite(stiffness) ||
              stiffness < 0 || stiffness > 1 || !Array.isArray(pivot) || pivot.length !== 2 ||
              !pivot.every(value => Number.isFinite(value) && value >= 0 && value <= 1)) {
              throw new Error("Invalid stiff outfit layer: " + anchor);
            }
            const offsets = new Float32Array(count * 2);
            for (let i = 0; i < count; i++) {
              offsets[i * 2] = ((i % columns) / (columns - 1) - pivot[0]) * width;
              offsets[i * 2 + 1] = (pivot[1] - Math.floor(i / columns) / (rows - 1)) * height;
            }
            return {uv, behind, afterIndex, pivot, stiffness, offsets, vertices: new Float32Array(count * 2)};
          }
          if (!frame && rotation === 0) return {uv, behind, afterIndex};
          if (count !== 4 || !frame) throw new Error("Outfit mesh layer must span the form: " + anchor);
          const [x, y, w, h] = frame;
          if (!frame.every(Number.isFinite) || !Number.isFinite(rotation) || w <= 0 || h <= 0) {
            throw new Error("Invalid outfit layer frame: " + anchor);
          }
          const angle = rotation * Math.PI / 180;
          const cos = Math.cos(angle), sin = Math.sin(angle);
          const centerX = x + w / 2, centerY = y + h / 2;
          const corners = [[-w / 2, -h / 2], [w / 2, -h / 2], [-w / 2, h / 2], [w / 2, h / 2]]
            .map(([u, v]) => [(centerX + cos * u - sin * v) / width, (centerY + sin * u + cos * v) / height]);
          return {uv, corners, behind, afterIndex, vertices: new Float32Array(8)};
        });
        const vertices = new Float32Array(count * 2);
        const pins = bindings.map(binding => {
          if (!binding.length || binding.some(([vertex, weight]) => !Number.isInteger(vertex) ||
            vertex < 0 || vertex * 2 >= positions.length || !Number.isFinite(weight)) ||
            Math.abs(binding.reduce((sum, pair) => sum + pair[1], 0) - 1) > 0.001) {
            throw new Error("Invalid outfit attachment binding: " + anchor);
          }
          return binding;
        });
        let reference = null;
        const landmarks = warpRest || rigid;
        if (landmarks) {
          const cx = landmarks.reduce((sum, point) => sum + point[0], 0) / landmarks.length;
          const cy = landmarks.reduce((sum, point) => sum + point[1], 0) / landmarks.length;
          const points = landmarks.map(([px, py]) => [px - cx, cy - py]);
          const lengthSquared = points.reduce((sum, [px, py]) => sum + px * px + py * py, 0);
          if (!(lengthSquared > 0) || !Number.isFinite(lengthSquared)) {
            throw new Error("Invalid outfit attachment landmarks: " + anchor);
          }
          const shape = Array.from({length: count}, (_, i) => {
            const x = (i % columns) * width / (columns - 1);
            const y = Math.floor(i / columns) * height / (rows - 1);
            const [px, py] = warpRest ? warpRest[i] : [cx, cy];
            return [x - px, py - y];
          });
          reference = {points, lengthSquared, shape, local: Boolean(warpRest)};
        }
        let support = null;
        if (soleSupport) {
          const {column, supportRows, rowStiffness} = soleSupport;
          const [front, heel] = supportRows;
          if (!warpRest || supportRows.length !== 2 || !Number.isInteger(column) || column < 0 || column >= columns ||
            !supportRows.every(Number.isInteger) || front < 0 || heel >= rows || front >= heel ||
            rowStiffness.length !== rows || !rowStiffness.every(value => Number.isFinite(value) && value >= 0 && value <= 1)) {
            throw new Error("Invalid outfit sole supports: " + anchor);
          }
          const offsets = new Float32Array(count * 2);
          const weights = new Float32Array(count);
          for (let i = 0; i < count; i++) {
            const row = Math.floor(i / columns);
            offsets[i * 2] = ((i % columns) - column) * width / (columns - 1);
            offsets[i * 2 + 1] = (front - row) * height / (rows - 1);
            weights[i] = rowStiffness[row];
          }
          support = {supports: [front * columns + column, heel * columns + column],
            drop: (heel - front) * height / (rows - 1), offsets, weights};
        }
        return {index, positions, vertices, grid, uv, underlayUV, layers: fittedLayers, soleSupport: support,
          triangles: gridTriangles(columns, rows), pins, groundPoint,
          reference, fitPoints: landmarks ? new Float32Array(landmarks.length * 2) : null};
      }

      function rectangleUV(rect, [columns, rows]) {
        checkRegion(atlas, rect);
        const [x, y, w, h] = rect;
        const result = new Float32Array(columns * rows * 2);
        for (let row = 0; row < rows; row++) {
          for (let col = 0; col < columns; col++) {
            const i = (row * columns + col) * 2;
            result[i] = (x + w * col / (columns - 1)) / atlas.width;
            result[i + 1] = 1 - (y + h * row / (rows - 1)) / atlas.height;
          }
        }
        return result;
      }

      const attachments = (definition.attachments || []).map(({forms, over, hide = [], shadow, mergeViews, bridges = []}) => {
        const hidden = hide.map(drawableIndex);
        const layers = [...new Set([...over.map(drawableIndex), ...hidden])];
        if (!forms.length || !layers.length) throw new Error("Outfit attachment needs a form and a draw layer");
        const fitted = forms.map(fit);
        const byAnchor = new Map(fitted.map(form => [form.index, form]));
        const fittedBridges = bridges.map(({from, to, grid, fromUV, toUV, frames}) => {
          const source = byAnchor.get(drawableIndex(from)), destination = byAnchor.get(drawableIndex(to));
          const [columns, rows] = grid;
          const count = columns * rows;
          const validUV = points => points.length === count && points.every(point =>
            point.length === 2 && point.every(value => Number.isFinite(value) && value >= 0 && value <= 1));
          if (!mergeViews || !source || !destination || source === destination || frames.length < 3 ||
            !grid.every(n => Number.isInteger(n) && n >= 2 && n <= 32) || !validUV(fromUV) || !validUV(toUV)) {
            throw new Error("Invalid outfit transition: " + from + " / " + to);
          }
          return {from: source, to: destination, fromUV, toUV, vertices: new Float32Array(count * 2),
            triangles: gridTriangles(columns, rows),
            frames: frames.map(({front, back}) => ({front: rectangleUV(front, grid), back: back && rectangleUV(back, grid)}))};
        });
        return {hidden, layers, forms: fitted, mergeViews, bridges: fittedBridges,
          shadow: shadow ? {form: fit(shadow), layer: drawableIndex(shadow.over)} : null};
      });
      if (destroyed) return null;
      const texture = global.PIXI.Texture.from(atlas, {
        alphaMode: global.PIXI.ALPHA_MODES.UNPACK,
      });
      textures.add(texture);
      return {texture, patches, formPatches, attachments};
    }

    const triggers = new Map();
    const underlays = new Map();
    const hidden = new Set();
    const viewOpacities = new Map();
    const viewPatches = new Map();
    const drawModel = renderer.doDrawModel;
    const drawMesh = renderer.drawMesh;
    const visible = index => core.getDrawableDynamicFlagIsVisible(index) && drawables.opacities[index] > 0;

    function schedule(passes, trigger, form, opacity, uv = form.uv, vertices = form.vertices) {
      if (!passes.has(trigger)) passes.set(trigger, []);
      passes.get(trigger).push({form, opacity, uv, vertices});
    }

    renderer.doDrawModel = function () {
      triggers.clear();
      underlays.clear();
      hidden.clear();
      viewOpacities.clear();
      viewPatches.clear();
      if (active) {
        const orders = drawables.renderOrders;
        for (const {forms, layers, hidden: covered, shadow, mergeViews, bridges} of active.attachments) {
          const visibleForms = forms.filter(form => visible(form.index))
            .sort((a, b) => orders[b.index] - orders[a.index]);
          if (!visibleForms.length) continue;
          let form = visibleForms[0];
          let remaining = 1;
          if (mergeViews) {
            // Measure each drawing's alpha after the higher views occlude it.
            // Submit a single shoe and suppress the outgoing foot silhouette.
            let strongest = 0;
            for (const candidate of visibleForms) {
              const contribution = remaining * drawables.opacities[candidate.index];
              if (contribution > strongest) {
                form = candidate;
                strongest = contribution;
              }
              remaining -= contribution;
            }
            if (visibleForms.length > 1) {
              for (const candidate of visibleForms) {
                viewOpacities.set(candidate.index, candidate === form ? 1 - remaining : 0);
              }
            }
          } else {
            form = visibleForms.find(candidate => drawables.opacities[candidate.index] >= 0.5) || form;
            for (const candidate of visibleForms) remaining *= 1 - drawables.opacities[candidate.index];
          }
          let trigger = form.index;
          for (const layer of layers) {
            if (visible(layer) && orders[layer] > orders[trigger]) trigger = layer;
          }
          const opacity = 1 - remaining;
          for (const [index, patch] of active.formPatches.get(form.index) || []) {
            viewPatches.set(index, patch);
          }
          const first = mergeViews ? form.index : visibleForms[visibleForms.length - 1].index;
          const bridge = bridges.find(({from, to}) => (from === form || to === form) &&
            visible(from.index) && visible(to.index));
          const t = bridge && bridgeProgress(bridge, drawables.opacities, orders);
          if (bridge && t > 0.025 && t < 0.975 && placeBridge(bridge, t)) {
            const frame = bridge.frames[Math.round(t * (bridge.frames.length - 1))];
            bridge.index = form.index;
            if (frame.back) schedule(underlays, first, bridge, opacity, frame.back);
            schedule(triggers, trigger, bridge, opacity, frame.front);
          } else if (form.layers) {
            placeForm(form);
            // The far rim can sit behind the sock. The near side and the
            // hardware layer stay over the foot in the configured order.
            for (const layer of form.layers) {
              if (layer.stiffness) {
                placeStiffLayer(layer, form);
              } else if (layer.corners) {
                for (let i = 0; i < layer.corners.length; i++) {
                  layer.vertices.set(gridPoint(layer.corners[i], form), i * 2);
                }
              }
              const after = layer.afterIndex;
              const front = after !== undefined && visible(after) && orders[after] > orders[trigger] ? after : trigger;
              schedule(layer.behind ? underlays : triggers, layer.behind ? first : front,
                form, opacity, layer.uv, layer.vertices);
            }
          } else {
            placeForm(form);
            schedule(triggers, trigger, form, opacity);
            if (form.underlayUV) schedule(underlays, first, form, opacity, form.underlayUV);
          }
          if (shadow && form.groundPoint && visible(shadow.layer)) {
            placeForm(shadow.form);
            const contact = contactStrength(form, shadow.form);
            if (contact > 0) schedule(triggers, shadow.layer, shadow.form, contact * opacity);
          }
          for (const index of covered) hidden.add(index);
        }
      }
      return drawModel.call(this);
    };

    function drawAttachments(renderer, passes) {
      if (!passes) return;
      const culling = renderer.isCulling();
      const clip = renderer.getClippingContextBufferForDraw();
      renderer.setIsCulling(false);
      const clipping = renderer._clippingManager?.getClippingContextListForDraw();
      for (const {form, opacity, uv, vertices} of passes) {
        renderer.setClippingContextBufferForDraw(clipping?.[form.index] || null);
        drawMesh.call(renderer, outfitTextureIndex, form.triangles.length, vertices.length / 2, form.triangles,
          vertices, uv, opacity, 0, core.getDrawableInvertedMaskBit(form.index));
      }
      renderer.setClippingContextBufferForDraw(clip);
      renderer.setIsCulling(culling);
    }

    renderer.drawMesh = function (texture, indexCount, vertexCount, indices, vertices, uv, opacity, blend, inverted) {
      const index = active && !this.getClippingContextBufferForMask() ? indexByUV.get(uv) : undefined;
      if (index === undefined) {
        return drawMesh.call(this, texture, indexCount, vertexCount, indices, vertices, uv, opacity, blend, inverted);
      }
      const patch = viewPatches.get(index) || active.patches.get(index);
      const replacement = patch && !patch.overlay;
      const drawOpacity = hidden.has(index) ? 0 : (viewOpacities.get(index) ?? opacity);
      drawAttachments(this, underlays.get(index));
      drawMesh.call(this, replacement ? outfitTextureIndex : texture, indexCount, vertexCount, indices, vertices,
        replacement ? patch.uv : uv, drawOpacity, blend, inverted);
      if (patch?.overlay && drawOpacity > 0) {
        drawMesh.call(this, outfitTextureIndex, indexCount, vertexCount, indices, vertices,
          patch.uv, drawOpacity, blend, inverted);
      }
      drawAttachments(this, triggers.get(index));
    };

    async function select(id) {
      const request = ++selection;
      if (id === "original") {
        active = null;
        model.textures = originals;
        return true;
      }
      const definition = options.find(option => option.id === id);
      if (!definition || destroyed) return false;
      if (!prepared.has(id)) {
        prepared.set(id, prepare(definition).catch(error => {
          prepared.delete(id);
          throw error;
        }));
      }
      const outfit = await prepared.get(id);
      if (!outfit || destroyed || request !== selection) return false;
      active = outfit;
      model.textures = [...originals, outfit.texture];
      return true;
    }

    model.once("destroy", () => {
      destroyed = true;
      model.textures = originals;
      active = null;
      for (const texture of textures) texture.destroy(true);
    });
    const controller = {options, select};
    controllers.set(model, controller);
    return controller;
  }

  global.CubismOutfits = {attach};
})(window);
