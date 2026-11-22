"use strict";

// Run from the repository with the two Azur Lane models installed and Chrome available.
// node azur_lane/tests/test_outfits-browser.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "../..");
const origin = "http://azur-outfits.test";
const viewer = "/azur_lane/viewer/index.html";
const target = "baifeng_3";
const control = "qiye_10";
const outfitIndex = require("../config/outfits/index.json");
const outfitEntry = outfitIndex.models[target].find(entry => entry.id === "outfit_01");
const outfit = require(path.resolve(__dirname, "../config/outfits", outfitEntry.backup));
const viewport = {width: 1440, height: 1000};
const mime = {
  ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".png": "image/png",
};

async function setup(page, query = "?shoe_backup=1") {
  let failAtlas = true;
  await page.route(origin + "/**", async route => {
    const pathname = decodeURIComponent(new URL(route.request().url()).pathname);
    if (pathname.endsWith("/" + outfit.atlas) && failAtlas) {
      failAtlas = false;
      return route.fulfill({status: 404});
    }
    const file = path.join(root, pathname);
    const contentType = mime[path.extname(file)] || "application/octet-stream";
    if (pathname === "/azur_lane/viewer/manifest.json") {
      const original = JSON.parse(await fs.readFile(file, "utf8"));
      const models = original.models.filter(model => [target, control].includes(model.name));
      assert.equal(models.length, 2, "install both models before running the browser test");
      return route.fulfill({json: {...original, models, characters: []}});
    }
    try {
      if (route.request().method() === "HEAD") {
        const stat = await fs.stat(file);
        return route.fulfill({contentType, headers: {"content-length": String(stat.size)}});
      }
      return await route.fulfill({contentType, path: file});
    } catch {
      return route.fulfill({status: 404});
    }
  });
  await page.goto(origin + viewer + query);
  await page.evaluate(({attachments, patches}) => {
    const shoeRegions = attachments.flatMap(({forms, shadow, bridges = []}) => {
      const passes = forms.flatMap(({anchor, grid, layers}) => layers.map(({id, region: [x, y]}) => ({
        anchor, x, y, count: grid[0] * grid[1], kind: id, grid,
      })));
      if (shadow) passes.push({anchor: forms.find(form => form.groundPoint).anchor, x: shadow.region[0],
        y: shadow.region[1], count: 4, kind: "shadow"});
      for (const {from, to, grid, frames} of bridges) {
        for (const frame of frames) {
          for (const side of ["back", "front"]) {
            if (!frame[side]) continue;
            const [x, y] = frame[side];
            passes.push({anchor: "bridge", pair: [from, to], x, y, count: grid[0] * grid[1],
              kind: side, grid, hasBack: Boolean(frame.back)});
          }
        }
      }
      return passes;
    });
    PIXI.live2d.config.sound = false;
    // Observe the renderer entry point before the outfit adapter wraps it.
    // The tests exercise the real renderer and collect the submitted meshes.
    const from = PIXI.live2d.Live2DModel.from.bind(PIXI.live2d.Live2DModel);
    PIXI.live2d.Live2DModel.from = async (...args) => {
      const model = await from(...args);
      const renderer = model.internalModel.renderer;
      const {drawables} = model.internalModel.coreModel._model;
      const feet = new Set(attachments.flatMap(({forms}) => forms.map(form => form.anchor)));
      feet.add("ArtMesh12");
      feet.add("ArtMesh214");
      const footRegions = patches.flatMap(({drawables: ids, source, region, whenForm}) => ids.filter(id => feet.has(id)).map(anchor => {
        const index = drawables.ids.indexOf(anchor);
        if (index < 0) return null;
        const uv = drawables.vertexUvs[index];
        const texture = model.textures[drawables.textureIndices[index]];
        return {anchor, whenForm, count: uv.length / 2,
          x: uv[0] * texture.width - source[0] + region[0],
          y: (1 - uv[1]) * texture.height - source[1] + region[1]};
      })).filter(Boolean);
      const draw = renderer.drawMesh;
      renderer.drawMesh = function (texture, count, vertexCount, indices, vertices, uv, opacity, ...rest) {
        if (texture === 2 && window.outfitDraws) {
          const atlas = model.textures[texture];
          const match = shoeRegions.find(region => region.count === vertexCount &&
            Math.abs(uv[0] * atlas.width - region.x) < 0.01 &&
            Math.abs((1 - uv[1]) * atlas.height - region.y) < 0.01);
          if (match) {
            let valid = vertices.every(Number.isFinite) && indices.length === count;
            let deformation = 0;
            if (match.grid) {
              const [columns, rows] = match.grid;
              const [x, y] = vertices;
              const right = (columns - 1) * 2;
              const bottom = (rows - 1) * columns * 2;
              const dx = vertices[right] - x, dy = vertices[right + 1] - y;
              const ex = vertices[bottom] - x, ey = vertices[bottom + 1] - y;
              for (let i = 0; i < vertexCount; i++) {
                const u = (i % columns) / (columns - 1);
                const v = Math.floor(i / columns) / (rows - 1);
                deformation = Math.max(deformation, Math.hypot(vertices[i * 2] - (x + u * dx + v * ex),
                  vertices[i * 2 + 1] - (y + u * dy + v * ey)) / Math.hypot(dx, dy));
              }
              valid &&= count === (columns - 1) * (rows - 1) * 6;
              for (let i = 0; i < count; i += 3) {
                const a = indices[i] * 2, b = indices[i + 1] * 2, c = indices[i + 2] * 2;
                const area = (vertices[b] - vertices[a]) * (vertices[c + 1] - vertices[a + 1]) -
                  (vertices[b + 1] - vertices[a + 1]) * (vertices[c] - vertices[a]);
                valid &&= area > 0;
              }
            }
            window.outfitDraws.push({
              anchor: match.anchor, kind: match.kind, valid, opacity, deformation,
              vertices: Array.from(vertices), pair: match.pair, hasBack: match.hasBack,
            });
          } else if (opacity > 0) {
            const foot = footRegions.find(region => region.count === vertexCount &&
              Math.abs(uv[0] * atlas.width - region.x) < 0.01 &&
              Math.abs((1 - uv[1]) * atlas.height - region.y) < 0.01);
            if (foot) window.outfitDraws.push({anchor: foot.anchor, whenForm: foot.whenForm, kind: "foot", valid: true, opacity});
          }
        }
        return draw.call(this, texture, count, vertexCount, indices, vertices, uv, opacity, ...rest);
      };
      return model;
    };
  }, outfit);
}

async function snapshot(page, pixels = false) {
  return page.evaluate(pixels => {
    const model = current;
    const result = {
      transform: [model.x, model.y, model.scale.x, model.scale.y],
      action: model.internalModel.motionManager.state.currentGroup,
      clock: model.elapsedTime,
    };
    if (pixels) {
      app.renderer.render(app.stage);
      const gl = app.renderer.gl;
      const {drawingBufferWidth: w, drawingBufferHeight: h} = gl;
      const rgba = new Uint8Array(w * h * 4);
      gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, rgba);
      const fingerprints = [2166136261, 2166136261];
      const canvas = app.view.getBoundingClientRect();
      const lowerBody = [565, 483, 965, 800];
      for (let i = 0; i < rgba.length; i += 4) {
        const x = i / 4 % w + canvas.x;
        const y = h - 1 - Math.floor(i / 4 / w) + canvas.y;
        const region = x >= lowerBody[0] && x < lowerBody[2] && y >= lowerBody[1] && y < lowerBody[3] ? 1 : 0;
        for (let c = 0; c < 4; c++) fingerprints[region] = Math.imul(fingerprints[region] ^ rgba[i + c], 16777619);
      }
      result.fingerprints = fingerprints;
      result.glError = gl.getError();
    }
    return result;
  }, pixels);
}

async function interactions(page) {
  const outfitSelect = page.locator("#outfit-select");
  await page.getByText("Sunshower Fox Bride", {exact: true}).click();
  await outfitSelect.waitFor({state: "visible"});
  assert.deepEqual(await outfitSelect.locator("option").allTextContents(), ["原始装扮", "换装 01 · 黑丝皮鞋"]);
  assert.equal(await outfitSelect.inputValue(), "original");

  await outfitSelect.selectOption("outfit_01");
  await page.getByText("换装加载失败，可重试", {exact: true}).waitFor();
  assert.equal(await outfitSelect.inputValue(), "original");
  await page.evaluate(() => {
    app.stop();
    current.autoUpdate = false;
    current.deltaTime = 0;
    const core = current.internalModel.coreModel;
    core._model.parameters.values.set(core._model.parameters.defaultValues);
    core.saveParameters();
    core.update();
  });
  const original = await snapshot(page, true);
  await outfitSelect.selectOption("outfit_01");
  await page.waitForFunction(() => current?.textures.length === 3);
  await page.evaluate(() => {window.outfitDraws = [];});
  const dressed = await snapshot(page, true);
  const standingShadows = await page.evaluate(() => window.outfitDraws
    .filter(pass => pass.kind === "shadow" && pass.opacity > .9).map(pass => pass.anchor).sort());
  assert.deepEqual(standingShadows, ["ArtMesh13", "ArtMesh18"]);
  assert.equal(dressed.glError, 0);
  assert.deepEqual(dressed.transform, original.transform);
  assert.equal(dressed.clock, original.clock);
  assert.equal(dressed.fingerprints[0], original.fingerprints[0], "background and upper body changed");
  assert.notEqual(dressed.fingerprints[1], original.fingerprints[1], "outfit did not change the lower body");
  await outfitSelect.selectOption("original");
  assert.deepEqual(await snapshot(page, true), original, "restoring the outfit must reproduce the original frame");
  for (let i = 0; i < 2; i++) {
    await outfitSelect.selectOption("outfit_01");
    await page.waitForFunction(() => current?.textures.length === 3);
    assert.deepEqual(await snapshot(page, true), dressed, "reapplying the outfit must reproduce the dressed frame");
    await outfitSelect.selectOption("original");
    assert.deepEqual(await snapshot(page, true), original, "repeated switching must restore the original frame");
  }

  await page.locator("#motion-panel .m-toggle").click();
  await page.locator("#motion-panel .mbtn").filter({hasText: /^idle$/}).click();
  await page.waitForFunction(() => current?.internalModel.motionManager.playing);
  await page.mouse.move(670, 510);
  await page.mouse.wheel(0, -120);
  await page.waitForFunction(scale => current.scale.x > scale, original.transform[2]);
  await page.mouse.wheel(0, 120);
  await page.waitForFunction(scale => current.scale.x < scale, original.transform[2] * 1.06);
  await page.mouse.down();
  await page.mouse.move(713, 541, {steps: 5});
  await page.mouse.up();
  const moved = await snapshot(page);
  assert.equal(moved.action, "idle");
  assert.notDeepEqual(moved.transform, original.transform);
  await outfitSelect.selectOption("outfit_01");
  await page.waitForFunction(() => current?.textures.length === 3);
  assert.deepEqual(await snapshot(page), moved, "outfit selection changed the camera or motion clock");
  await page.locator("#motion-panel .m-toggle").click();
}

async function allMotions(page) {
  return page.evaluate(async attachments => {
    const model = current;
    const {coreModel: core, motionManager: manager} = model.internalModel;
    const {drawables} = core._model;
    const forms = ["ArtMesh13", "ArtMesh229", "ArtMesh223"].map(id => drawables.ids.indexOf(id));
    const byAnchor = new Map(attachments.flatMap(({forms, over, hide}) => forms.map(form => [
      form.anchor, {...form, triggers: [...over, ...hide]},
    ])));
    function visibleOrder(id) {
      const i = drawables.ids.indexOf(id);
      return i >= 0 && drawables.opacities[i] > 0 && core.getDrawableDynamicFlagIsVisible(i)
        ? drawables.renderOrders[i] : -1;
    }
    function gridPoint(vertices, [columns, rows], [u, v]) {
      const x = u * (columns - 1), y = v * (rows - 1);
      const col = Math.min(columns - 2, Math.floor(x));
      const row = Math.min(rows - 2, Math.floor(y));
      const dx = x - col, dy = y - row;
      const a = 2 * (row * columns + col);
      const b = a + 2 * (dx >= dy ? 1 : columns);
      const c = a + 2 * (columns + 1);
      return [0, 1].map(axis => (1 - Math.max(dx, dy)) * vertices[a + axis] +
        Math.abs(dx - dy) * vertices[b + axis] + Math.min(dx, dy) * vertices[c + axis]);
    }
    const seen = new Set();
    const deformed = new Set();
    const stableHardware = new Set();
    const separateHeel = new Set();
    let scopedCuts = 0;
    let evaluated = 0;
    let rendered = 0;
    let transitions = 0;
    const bridged = {};
    for (const action of Object.keys(manager.definitions)) {
      const motion = await manager.loadMotion(action, 0);
      if (!motion) throw Error("Missing motion " + action);
      manager.stopAllMotions();
      core._model.parameters.values.set(core._model.parameters.defaultValues);
      core.saveParameters();
      if (!await model.motion(action, 0, 3)) throw Error("Could not start " + action);
      const inspectEveryFrame = action === "touch_drag9" || action === "touch_body";
      const fps = inspectEveryFrame ? 60 : 24;
      const frames = Math.ceil(motion.getLoopDuration() * fps);
      let lastForm = null;
      for (let frame = 0; frame <= frames; frame++) {
        model.internalModel.update(1000 / fps, frame * 1000 / fps);
        evaluated++;
        const form = forms.map(index => drawables.opacities[index] >= 0.5).join(",");
        if (!inspectEveryFrame && frame % Math.max(1, Math.floor(frames / 3)) !== 0 &&
          form === lastForm && frame !== frames) continue;
        lastForm = form;
        window.outfitDraws = [];
        app.renderer.render(app.stage);
        rendered++;
        const passes = window.outfitDraws;
        const byShoe = new Map();
        for (const pass of passes) {
          if (pass.kind === "shadow" || pass.kind === "foot") continue;
          if (!byShoe.has(pass.anchor)) byShoe.set(pass.anchor, []);
          byShoe.get(pass.anchor).push(pass);
        }
        const shadows = passes.filter(pass => pass.kind === "shadow");
        const visible = forms.filter(index => drawables.opacities[index] > 0 && core.getDrawableDynamicFlagIsVisible(index));
        const ranked = visible.sort((a, b) => drawables.renderOrders[b] - drawables.renderOrders[a]);
        const contributions = ranked.map((index, i) => drawables.opacities[index] *
          ranked.slice(0, i).reduce((remaining, higher) => remaining * (1 - drawables.opacities[higher]), 1));
        const expectedFront = drawables.ids[ranked[contributions.indexOf(Math.max(...contributions))]];
        const expectedOpacity = contributions.reduce((sum, alpha) => sum + alpha, 0);
        const bridge = byShoe.get("bridge");
        if (bridge) {
          const {pair, hasBack} = bridge[0];
          const front = bridge.find(pass => pass.kind === "front");
          const back = bridge.find(pass => pass.kind === "back");
          const foot = passes.find(pass => pass.anchor === expectedFront && pass.kind === "foot");
          const sameMesh = !back || back.vertices.every((value, index) => value === front?.vertices[index]);
          if (!front || Boolean(back) !== hasBack || !sameMesh || !foot || !pair.includes(expectedFront) ||
            pair.some(id => visibleOrder(id) < 0) || byShoe.has(expectedFront) ||
            passes.indexOf(foot) > passes.indexOf(front) || (back && passes.indexOf(back) > passes.indexOf(foot))) {
            throw Error(action + " frame " + frame + ": invalid transition passes");
          }
          byShoe.delete("bridge");
          byShoe.set(expectedFront, bridge);
          const key = pair.join(" / ");
          bridged[key] = (bridged[key] || 0) + 1;
        }
        const adjacentFoot = passes.find(pass => pass.anchor === "ArtMesh214");
        if (adjacentFoot?.whenForm) scopedCuts++;
        const wrongCut = adjacentFoot && Boolean(adjacentFoot.whenForm) !== (expectedFront === "ArtMesh13");
        if (visible.length > 1) transitions++;
        const misaligned = [...byShoe].some(([anchor, layers]) => {
          if (layers === bridge) return false;
          const [first] = layers;
          if (first.deformation > 0.001) deformed.add(anchor);
          const form = byAnchor.get(anchor);
          const frontTrigger = Math.max(visibleOrder(anchor), ...form.triggers.map(visibleOrder));
          const frontLayers = form.layers.filter(layer => !layer.behind).sort((a, b) =>
            Math.max(visibleOrder(a.after), frontTrigger) - Math.max(visibleOrder(b.after), frontTrigger));
          const expected = [...form.layers.filter(layer => layer.behind).map(layer => layer.id), "foot",
            ...frontLayers.map(layer => layer.id)];
          const submitted = passes.filter(pass => pass.anchor === anchor && pass.kind !== "shadow");
          if (submitted.map(pass => pass.kind).join(",") !== expected.join(",")) return true;
          if (anchor === "ArtMesh13" && visibleOrder("ArtMesh12") > frontTrigger &&
            passes.findIndex(pass => pass.anchor === anchor && pass.kind === "collar") <=
              passes.findIndex(pass => pass.anchor === "ArtMesh12" && pass.kind === "foot")) return true;
          return layers.some(layer => {
            const {pivot} = form.layers.find(part => part.id === layer.kind);
            const displacement = Math.max(...layer.vertices.map((value, vertex) => Math.abs(value - first.vertices[vertex])));
            if (!pivot) return displacement !== 0;
            const [x, y] = gridPoint(layer.vertices, form.grid, pivot);
            const [baseX, baseY] = gridPoint(first.vertices, form.grid, pivot);
            if (displacement > 1e-5) {
              if (layer.kind === "heel") separateHeel.add(anchor);
              if (layer.kind === "buckle") stableHardware.add(anchor);
            }
            return Math.hypot(x - baseX, y - baseY) > 1e-5;
          });
        });
        if (byShoe.size !== 2 || !byShoe.has("ArtMesh18") || !byShoe.has(expectedFront) || misaligned || wrongCut ||
          byShoe.get(expectedFront).some(pass => Math.abs(pass.opacity - expectedOpacity) > 1e-6) ||
          shadows.some(shadow => !byShoe.has(shadow.anchor)) ||
          passes.some(x => !x.valid || x.opacity <= 0 || x.opacity > 1 + 1e-6) ||
          app.renderer.gl.getError() !== 0) {
          throw Error(action + " frame " + frame + ": " + JSON.stringify(passes.map(({vertices, ...pass}) => pass)));
        }
        for (const anchor of byShoe.keys()) seen.add(anchor);
      }
    }
    window.outfitDraws = null;
    return {motions: Object.keys(manager.definitions).length, evaluated, rendered, transitions,
      anchors: [...seen].sort(), deformedAnchors: [...deformed].sort(), hardwareAnchors: [...stableHardware].sort(),
      heelAnchors: [...separateHeel], scopedCuts, bridged};
  }, outfit.attachments);
}

async function debugMode(browser) {
  const page = await browser.newPage({viewport});
  try {
    await setup(page, "?shoe_debug=1");
    await page.getByText("Sunshower Fox Bride", {exact: true}).click();
    await page.locator("#shoe-debug").waitFor({state: "visible"});
    const select = page.locator("#outfit-select");
    await select.selectOption("outfit_01");
    await page.getByText("换装加载失败，可重试", {exact: true}).waitFor();
    await select.selectOption("outfit_01");
    await page.locator("#outfit-status").waitFor({state: "hidden"});
    await page.evaluate(() => {
      app.stop();
      current.autoUpdate = false;
      const core = current.internalModel.coreModel;
      const params = core._model.parameters;
      params.values.set(params.defaultValues);
      core.saveParameters();
      core.update();
    });
    const drawVariant = (mode, isolation) => page.evaluate(async ({mode, isolation}) => {
      const inspector = AzurShoeDebug.get(current);
      inspector.mode.value = mode;
      inspector.isolation.value = isolation;
      await inspector.apply();
    }, {mode, isolation});
    const colored = await snapshot(page, true);
    await drawVariant("layers", "foot");
    assert.notDeepEqual((await snapshot(page, true)).fingerprints, colored.fingerprints,
      "isolating the foot must hide the attachments in the framebuffer");
    await drawVariant("original", "all");
    const material = await snapshot(page, true);
    assert.notDeepEqual(material.fingerprints, colored.fingerprints);
    await drawVariant("mesh", "all");
    assert.deepEqual((await snapshot(page, true)).fingerprints, colored.fingerprints);
    await drawVariant("original", "all");
    assert.deepEqual(await snapshot(page, true), material);
    await page.locator("#l2d-back").click();
    await page.locator("#shoe-debug").waitFor({state: "hidden"});
    await page.locator('#l2d-grid .card .name').filter({hasText: /^qiye_10$/}).click();
    await page.waitForFunction(() => current?.internalModel.settings.url.includes("/qiye_10/"));
    assert.equal(await page.locator("#shoe-debug").isVisible(), false);
  } finally {
    await page.close();
  }
}

async function test() {
  const browser = await chromium.launch({
    channel: "chrome",
    args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
  });
  try {
    const page = await browser.newPage({viewport});
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await setup(page);
    assert.equal(await page.evaluate(() => typeof window.AzurShoeDebug), "undefined");
    await interactions(page);
    const results = await allMotions(page);
    assert.equal(results.motions, 83);
    assert.ok(results.transitions > 100, "front shoe did not exercise enough overlapping foot views");
    assert.deepEqual(results.anchors, ["ArtMesh13", "ArtMesh18", "ArtMesh223", "ArtMesh229"]);
    assert.deepEqual(results.deformedAnchors, results.anchors);
    assert.deepEqual(results.hardwareAnchors, ["ArtMesh13", "ArtMesh18", "ArtMesh229"]);
    assert.deepEqual(results.heelAnchors, ["ArtMesh13"]);
    assert.ok(results.scopedCuts > 100);
    assert.ok(results.bridged["ArtMesh13 / ArtMesh229"] > 20);
    assert.ok(results.bridged["ArtMesh229 / ArtMesh223"] > 20);

    await page.locator("#l2d-back").click();
    await page.locator('#l2d-grid .card .name').filter({hasText: /^qiye_10$/}).click();
    await page.waitForFunction(() => current?.internalModel.settings.url.includes("/qiye_10/"));
    assert.equal(await page.locator("#outfit-panel").isVisible(), false);
    await page.locator("#l2d-back").click();
    await page.getByText("Sunshower Fox Bride", {exact: true}).click();
    const select = page.locator("#outfit-select");
    await select.waitFor({state: "visible"});
    assert.equal(await select.inputValue(), "original");

    for (const width of [390, 320]) {
      await page.setViewportSize({width, height: 844});
      const boxes = await page.evaluate(() => {
        const rect = selector => document.querySelector(selector).getBoundingClientRect().toJSON();
        return {outfit: rect("#outfit-panel"), motion: rect("#motion-panel .m-toggle"), back: rect("#l2d-back")};
      });
      assert.ok(boxes.motion.left >= 0 && boxes.outfit.right <= width);
      assert.ok(boxes.motion.right < boxes.outfit.left && boxes.motion.top >= boxes.back.bottom);
    }
    assert.deepEqual(errors, []);
    await debugMode(browser);
    console.log(JSON.stringify(results));
  } finally {
    await browser.close();
  }
}

test().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
