"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(
  path.join(root, "azur_lane/viewer/scroll_state.js"), "utf8"
);

function createBrowser() {
  const frameQueue = [];
  const scrollCalls = [];
  const rootStyle = { scrollBehavior: "" };
  const browser = {
    scrollX: 0,
    scrollY: 0,
    document: { documentElement: { style: rootStyle } },
    requestAnimationFrame(callback) {
      frameQueue.push(callback);
    },
    scrollTo(x, y) {
      // 测试页的 html 默认声明 scroll-behavior:smooth。
      // 只有明确临时设置为 auto 时才允许立即回到原位置。
      const behavior = rootStyle.scrollBehavior || "smooth";
      scrollCalls.push({ x, y, behavior });
      if (behavior === "auto") {
        this.scrollX = x;
        this.scrollY = y;
      } else {
        frameQueue.push(() => {
          this.scrollX = x;
          this.scrollY = y;
        });
      }
    },
  };

  vm.runInNewContext(source, { window: browser }, {
    filename: "scroll_state.js",
  });

  return { browser, scrollCalls, rootStyle, frameQueue };
}

test("returning from a deeply scrolled model is instantaneous, with no animation frames", () => {
  const { browser, scrollCalls, rootStyle, frameQueue } = createBrowser();
  browser.scrollY = 4180;
  browser.AzurGalleryScroll.remember("l2d-list");

  browser.scrollY = 0; // 隐藏长列表时，浏览器强制把窗口压到顶部。
  assert.equal(browser.AzurGalleryScroll.restore("l2d-list"), true);
  assert.equal(browser.scrollY, 4180, "must restore synchronously before the next repaint");
  assert.equal(frameQueue.length, 0, "must not queue requestAnimationFrame or smooth animation");
  assert.deepEqual(scrollCalls, [{ x: 0, y: 4180, behavior: "auto" }]);
  assert.equal(rootStyle.scrollBehavior, "", "must preserve normal site scrolling behavior");
});

test("artwork and Live2D positions are remembered independently", () => {
  const { browser, scrollCalls } = createBrowser();
  browser.scrollY = 725;
  browser.AzurGalleryScroll.remember("paint-list");
  browser.scrollY = 5000;
  browser.AzurGalleryScroll.remember("l2d-list");

  assert.equal(browser.AzurGalleryScroll.restore("paint-list"), true);
  assert.equal(browser.scrollY, 725);
  assert.equal(browser.AzurGalleryScroll.restore("l2d-list"), true);
  assert.equal(browser.scrollY, 5000);
  assert.deepEqual(scrollCalls.map((c) => [c.x, c.y]), [[0, 725], [0, 5000]]);
  assert.ok(scrollCalls.every((c) => c.behavior === "auto"));
});

test("repeated opens always use the newest remembered position without scrolling visibly", () => {
  const { browser, scrollCalls, frameQueue } = createBrowser();
  browser.scrollY = 2800;
  browser.AzurGalleryScroll.remember("l2d-list");
  browser.scrollY = 3600;
  browser.AzurGalleryScroll.remember("l2d-list");
  browser.scrollY = 0;

  browser.AzurGalleryScroll.restore("l2d-list");
  assert.equal(browser.scrollY, 3600);
  assert.deepEqual(scrollCalls.map((c) => c.y), [3600]);
  assert.equal(frameQueue.length, 0);
});

test("restore preserves an existing explicit scroll-behavior setting", () => {
  const { browser, rootStyle } = createBrowser();
  rootStyle.scrollBehavior = "smooth";
  browser.scrollY = 1940;
  browser.AzurGalleryScroll.remember("l2d-list");
  browser.scrollY = 0;
  browser.AzurGalleryScroll.restore("l2d-list");
  assert.equal(browser.scrollY, 1940);
  assert.equal(rootStyle.scrollBehavior, "smooth");
});

test("clearing a key removes its saved position", () => {
  const { browser, scrollCalls, frameQueue } = createBrowser();
  browser.scrollY = 1250;
  browser.AzurGalleryScroll.remember("paint-list");
  browser.AzurGalleryScroll.clear("paint-list");
  assert.equal(browser.AzurGalleryScroll.restore("paint-list"), false);
  assert.equal(frameQueue.length, 0);
  assert.equal(scrollCalls.length, 0);
});

test("gallery wires model return and artwork detail close to instant position restoration", () => {
  const page = fs.readFileSync(
    path.join(root, "azur_lane/viewer/index.html"), "utf8"
  );
  assert.ok(page.includes('<script src="scroll_state.js"></script>'));
  assert.ok(page.includes("html{scroll-behavior:smooth}"));
  assert.match(page, /function enterStage\(i\)\{\s*AzurGalleryScroll\.remember\("l2d-list"\)/);
  assert.match(page, /function exitStage\(\)\{[\s\S]*?AzurGalleryScroll\.restore\('l2d-list'\)/);
  assert.match(page, /function openDetail\(c\)\{\s*AzurGalleryScroll\.remember\("paint-list"\)/);
  assert.match(page, /function closeDetail\(\)\{[\s\S]*?AzurGalleryScroll\.restore\('paint-list'\)/);
  assert.ok(page.includes("if(e.target.id === 'detail' || e.target.id === 'detail-close') closeDetail();"));
  assert.ok(!source.includes("requestAnimationFrame"), "scroll state should not delay restoration");
});
