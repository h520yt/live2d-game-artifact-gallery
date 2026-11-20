"use strict";
// 先安装天命之子全部模型和 Cubism 2 运行时，再从仓库根目录启动 HTTP 服务。
// DC_VIEWER_URL 可覆盖默认地址。运行 node tests/destiny_child-browser.cjs。
const assert = require("node:assert/strict");
const fs = require("node:fs");
const {chromium} = require("playwright");
const {assets} = require("../games/destiny_child/viewer/manifest.json");

const url = process.env.DC_VIEWER_URL || "http://127.0.0.1:8000/games/destiny_child/viewer/";
const viewports = [
  {width:1101,height:761},
  {width:641,height:961},
  {width:1303,height:551},
];

async function loaded(page, id) {
  await page.waitForFunction(id => {
    const model = window.dcTestApp?.stage.children[0];
    return document.getElementById("dc-status").hidden &&
      model?.internalModel.settings.url.includes("/" + id + "/") &&
      model.internalModel.motionManager.playing;
  }, id);
}

function closeTo(actual, expected, tolerance, label) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${label}: ${actual} vs ${expected}`);
}

async function frame(page, motionTime) {
  return page.evaluate(motionTime => {
    const {renderer, screen, stage, view} = window.dcTestApp;
    const model = stage.children[0];
    if (motionTime !== undefined) {
      UtSystem.setUserTimeMSec(motionTime);
      model.update(1);
    }
    renderer.render(stage);
    const gl = renderer.gl;
    const width = gl.drawingBufferWidth, height = gl.drawingBufferHeight;
    const rgba = new Uint8Array(width * height * 4);
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, rgba);
    let left = width, right = -1, top = height, bottom = -1;
    let visible = 0, fingerprint = 0;
    for (let i = 3; i < rgba.length; i += 4) {
      if (rgba[i] < 16) continue;
      const pixel = (i - 3) / 4;
      const x = pixel % width, y = height - 1 - Math.floor(pixel / width);
      left = Math.min(left, x);
      top = Math.min(top, y);
      right = Math.max(right, x);
      bottom = Math.max(bottom, y);
      visible++;
      fingerprint = (Math.imul(fingerprint, 31) + rgba[i - 1] + x + y) | 0;
    }
    const r = renderer.resolution;
    const css = view.getBoundingClientRect();
    return {
      pixels:[width,height], canvas:[view.width,view.height], css:[css.width,css.height],
      viewport:[view.parentElement.clientWidth,view.parentElement.clientHeight],
      screen:[screen.width,screen.height], resolution:r,
      antialias:gl.getContextAttributes().antialias, error:gl.getError(), visible, fingerprint,
      edges:[left / r,top / r,(right + 1) / r,(bottom + 1) / r],
      transform:[model.x,model.y,model.scale.x,model.scale.y,model.pivot.x,model.pivot.y],
    };
  }, motionTime);
}

function checkFit(state, dpr, label) {
  const {pixels, canvas, css, viewport, screen, edges, transform} = state;
  assert.equal(state.resolution, dpr, label);
  assert.equal(state.antialias, true, label);
  assert.equal(state.error, 0, label);
  assert.deepEqual(pixels, canvas, label);
  assert.ok(state.visible > 1000, label);
  for (let axis = 0; axis < 2; axis++) {
    assert.equal(pixels[axis], Math.round(viewport[axis] * dpr), label);
    closeTo(css[axis], screen[axis], .02, label + " CSS size");
    closeTo(screen[axis], viewport[axis], .5, label + " stage size");
    closeTo(transform[axis], screen[axis] / 2, .5, label + " model origin");
    const min = edges[axis], max = edges[axis + 2];
    assert.ok(min > 3 && max < screen[axis] - 3, `${label} cropped: ${edges}`);
    closeTo((min + max) / 2, screen[axis] / 2, 8, label + " visible center");
  }
}

async function checkInteractions(page, initial, card, scrollY) {
  const canvas = page.locator("#dc-canvas");
  const box = await canvas.boundingBox();
  await page.evaluate(() => {
    window.dcTestMotions = [];
    const manager = window.dcTestApp.stage.children[0].internalModel.motionManager;
    manager.on("motionStart", name => window.dcTestMotions.push(name));
  });

  await page.mouse.move(box.x + 80, box.y + 80);
  await page.mouse.down();
  await page.mouse.move(box.x + 133, box.y + 111, {steps:5});
  await page.mouse.up();
  await page.mouse.wheel(0, -100);
  await page.waitForFunction(scale => window.dcTestApp.stage.children[0].scale.x > scale, initial.transform[2]);
  const moved = await frame(page);
  closeTo(moved.transform[0], initial.transform[0] + 53, .01, "drag x");
  closeTo(moved.transform[1], initial.transform[1] + 31, .01, "drag y");
  assert.deepEqual(await page.evaluate(() => window.dcTestMotions), []);

  await page.locator("#dc-tools summary").click();
  await page.locator("#reset-fit").click();
  await page.locator("#dc-tools summary").click();
  assert.deepEqual((await frame(page)).transform, initial.transform);

  for (const [button, motion] of [["left","hit"],["right","attack"]]) {
    await canvas.click({button,position:{x:80,y:80}});
    await page.waitForFunction(motion => window.dcTestMotions.includes(motion), motion);
    assert.deepEqual((await frame(page)).transform, initial.transform);
  }
  await page.locator("#back-to-catalog").click();
  assert.equal(await page.evaluate(() => window.scrollY), scrollY);
  assert.equal(await card.evaluate(node => node === document.activeElement), true);
}

async function checkDpiChange(page, initial) {
  const {width,height} = page.viewportSize();
  const cdp = await page.context().newCDPSession(page);
  try {
    for (const [deviceScaleFactor, expected] of [[1.25,1.25],[2.5,2],[2,2]]) {
      await cdp.send("Emulation.setDeviceMetricsOverride", {width,height,deviceScaleFactor,mobile:false});
      // CDP 只改 DPR 且视口尺寸相同时，Chrome 不会派发 resize 或媒体查询事件。
      await page.evaluate(() => window.dispatchEvent(new Event("resize")));
      await page.waitForFunction(({deviceScaleFactor,expected}) =>
        window.devicePixelRatio === deviceScaleFactor && window.dcTestApp.renderer.resolution === expected,
      {deviceScaleFactor,expected});
      const state = await frame(page);
      checkFit(state, expected, "live DPI change");
      assert.deepEqual(state.transform, initial.transform);
    }
  } finally {
    await cdp.detach();
  }
}

async function main() {
  const channel = process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ||
    (fs.existsSync(chromium.executablePath()) ? undefined : "chrome");
  const browser = await chromium.launch({
    channel,
    args:["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"],
  });
  const reference = new Map();
  let maxDpiCenterDifference = 0;
  try {
    for (const dpr of [1,1.25,1.5,2]) {
      const page = await browser.newPage({viewport:viewports[0],deviceScaleFactor:dpr});
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.goto(url);
      const cards = page.locator("#items .sg-card");
      await cards.last().waitFor();
      assert.equal(await cards.count(), assets.length);
      assert.equal(await page.locator('#items [data-ready="true"]').count(), assets.length,
        "Install all Destiny Child models before running the WebGL test");
      await page.evaluate(() => {
        const Application = PIXI.Application;
        PIXI.Application = class extends Application {
          constructor(options) {
            super(options);
            window.dcTestApp = this;
          }
        };
        // 固定 SDK 动作时钟，避免跨 DPI 比较时采到不同动画阶段。
        UtSystem.setUserTimeMSec(1);
      });

      const card = cards.first();
      await card.click();
      for (const [index, asset] of assets.entries()) {
        await loaded(page, asset.id);
        for (const [size, viewport] of viewports.entries()) {
          await page.setViewportSize(viewport);
          await page.waitForFunction(({width,height}) => {
            const {screen, view} = window.dcTestApp;
            return Math.round(screen.width) === width &&
              Math.round(screen.height) === view.parentElement.clientHeight &&
              window.innerHeight === height;
          }, viewport);
          const label = `${asset.id}, ${viewport.width}×${viewport.height}, DPR ${dpr}`;
          const state = await frame(page);
          checkFit(state, dpr, label);
          const key = `${asset.id}-${size}`;
          if (dpr === 1) reference.set(key, state);
          else {
            const baseline = reference.get(key);
            for (let axis = 0; axis < 2; axis++) {
              const center = (state.edges[axis] + state.edges[axis + 2]) / 2;
              const baselineCenter = (baseline.edges[axis] + baseline.edges[axis + 2]) / 2;
              maxDpiCenterDifference = Math.max(maxDpiCenterDifference, Math.abs(center - baselineCenter));
              // 极细的半透明边缘可能随栅格密度出现或消失，变换本身独立校验。
              closeTo(center, baselineCenter, 8, label + " visible center across DPI");
            }
            for (const [axis, value] of state.transform.entries()) {
              closeTo(value, baseline.transform[axis], .5, label + " transform across DPI");
            }
          }
        }
        if (dpr === 1) {
          const initial = reference.get(`${asset.id}-${viewports.length - 1}`);
          const duration = await page.evaluate(() => window.dcTestApp.stage.children[0]
            .internalModel.motionManager.motionGroups.idle[0].getLoopDurationMSec());
          const times = [601,1201,2001, ...[.17,.35,.53,.71,.89].map(fraction => 1 + duration * fraction)];
          for (const time of times.sort((a, b) => a - b)) {
            const animated = await frame(page, time);
            assert.deepEqual(animated.transform, initial.transform, asset.id + " idle transform");
            const [left,top,right,bottom] = animated.edges;
            assert.ok(animated.visible > 1000 &&
              left > 0 && top > 0 && right < animated.screen[0] && bottom < animated.screen[1],
            `${asset.id} idle at ${time}ms cropped: ${animated.edges}`);
          }
          await page.evaluate(() => UtSystem.setUserTimeMSec(1));
        }
        if (index < assets.length - 1) await page.locator("#next").click();
      }

      const beforeNavigation = await frame(page);
      await page.locator("#prev").click();
      await loaded(page, assets.at(-2).id);
      checkFit(await frame(page), dpr, "previous model");
      await page.locator("#next").click();
      await loaded(page, assets.at(-1).id);
      const reopened = await frame(page);
      checkFit(reopened, dpr, "reopened model");
      assert.deepEqual(reopened.transform, beforeNavigation.transform);
      if (dpr === 2) await checkDpiChange(page, reopened);
      await page.locator("#back-to-catalog").click();
      await cards.last().scrollIntoViewIfNeeded();
      const scrollY = await page.evaluate(() => window.scrollY);
      assert.ok(scrollY > 0);
      await cards.last().click();
      await loaded(page, assets.at(-1).id);
      const initial = await frame(page);
      const animated = await frame(page, 901);
      assert.notEqual(animated.fingerprint, initial.fingerprint, "idle motion changes rendered pixels");
      assert.deepEqual(animated.transform, initial.transform, "idle keeps the fit transform fixed");
      await checkInteractions(page, initial, cards.last(), scrollY);
      assert.deepEqual(errors, []);
      await page.close();
      console.log(`DPR ${dpr}: ${assets.length} models × ${viewports.length} viewports, animation and controls passed`);
    }
    console.log(`Largest visible center difference across DPI: ${maxDpiCenterDifference.toFixed(2)} CSS px`);
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
