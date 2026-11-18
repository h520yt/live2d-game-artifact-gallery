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
  const browser = {
    scrollX: 0,
    scrollY: 0,
    requestAnimationFrame(callback) {
      frameQueue.push(callback);
    },
    scrollTo(x, y) {
      scrollCalls.push([x, y]);
      this.scrollX = x;
      this.scrollY = y;
    },
  };

  vm.runInNewContext(source, { window: browser }, {
    filename: "scroll_state.js",
  });

  return {
    browser,
    scrollCalls,
    flushFrames() {
      while (frameQueue.length) frameQueue.shift()();
    },
  };
}

test("returning from a model restores the original deep grid position", () => {
  const { browser, scrollCalls, flushFrames } = createBrowser();
  browser.scrollX = 0;
  browser.scrollY = 4180;

  browser.AzurGalleryScroll.remember("l2d-list");
  browser.scrollY = 0; // 隐藏长列表，视口被浏览器压回顶部
  assert.equal(browser.AzurGalleryScroll.restore("l2d-list"), true);
  assert.equal(scrollCalls.length, 0, "must wait until the list has been shown and laid out");

  flushFrames();
  assert.deepEqual(scrollCalls, [[0, 4180]]);
  assert.equal(browser.scrollY, 4180);
});

test("artwork and Live2D positions are independently remembered", () => {
  const { browser, scrollCalls, flushFrames } = createBrowser();
  browser.scrollY = 725;
  browser.AzurGalleryScroll.remember("paint-list");
  browser.scrollY = 5000;
  browser.AzurGalleryScroll.remember("l2d-list");

  browser.AzurGalleryScroll.restore("paint-list");
  flushFrames();
  browser.AzurGalleryScroll.restore("l2d-list");
  flushFrames();

  assert.deepEqual(scrollCalls, [[0, 725], [0, 5000]]);
});

test("repeated opens replace the saved position rather than jumping to an old one", () => {
  const { browser, scrollCalls, flushFrames } = createBrowser();
  browser.scrollY = 2800;
  browser.AzurGalleryScroll.remember("l2d-list");
  browser.scrollY = 3600;
  browser.AzurGalleryScroll.remember("l2d-list");
  browser.AzurGalleryScroll.restore("l2d-list");
  flushFrames();
  assert.deepEqual(scrollCalls, [[0, 3600]]);
});

test("clearing a key removes its saved position", () => {
  const { browser, flushFrames, scrollCalls } = createBrowser();
  browser.scrollY = 1250;
  browser.AzurGalleryScroll.remember("paint-list");
  browser.AzurGalleryScroll.clear("paint-list");
  assert.equal(browser.AzurGalleryScroll.restore("paint-list"), false);
  flushFrames();
  assert.equal(scrollCalls.length, 0);
});

test("gallery wires both model return and artwork detail close to scroll restoration", () => {
  const page = fs.readFileSync(
    path.join(root, "azur_lane/viewer/index.html"), "utf8"
  );
  assert.ok(page.includes('<script src="scroll_state.js"></script>'));
  assert.match(page, /function enterStage\(i\)\{\s*AzurGalleryScroll\.remember\("l2d-list"\)/);
  assert.match(page, /function exitStage\(\)\{[\s\S]*?AzurGalleryScroll\.restore\('l2d-list'\)/);
  assert.match(page, /function openDetail\(c\)\{\s*AzurGalleryScroll\.remember\("paint-list"\)/);
  assert.match(page, /function closeDetail\(\)\{[\s\S]*?AzurGalleryScroll\.restore\('paint-list'\)/);
  assert.ok(page.includes("if(e.target.id === 'detail' || e.target.id === 'detail-close') closeDetail();"));
});
