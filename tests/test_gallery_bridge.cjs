"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const root = path.resolve(__dirname, "..");
const bridgeSource = fs.readFileSync(path.join(root, "shared/gallery_bridge.js"), "utf8");

function loadBridge() {
  const context = {
    window: { location: { search: "" } },
    URLSearchParams,
    console,
  };
  vm.runInNewContext(bridgeSource, context, { filename: "gallery_bridge.js" });
  return context.window.GalleryViewerBridge;
}

test("bridge contract is available without game engine", () => {
  const bridge = loadBridge();
  assert.equal(bridge.version, 1);
  assert.equal(typeof bridge.register, "function");
  assert.equal(typeof bridge.refresh, "function");
  assert.equal(bridge.game, null);
});

test("deep link parser preserves exact asset id and optional role/action", () => {
  const bridge = loadBridge();
  const request = bridge.parseRequest("?gallery_asset=wuzang_3&gallery_role=interaction&gallery_motion=idle2");
  assert.equal(request.id, "wuzang_3");
  assert.equal(request.role, "interaction");
  assert.equal(request.motion, "idle2");
});

test("Reverse 1999 Unicode skin identifiers can be deep-linked", () => {
  const bridge = loadBridge();
  const asset = "313403:泉眼深处";
  const request = bridge.parseRequest("?" + new URLSearchParams({ gallery_asset: asset }));
  assert.equal(request.id, asset);
});

test("malformed or oversized asset identifiers are rejected", () => {
  const bridge = loadBridge();
  for (const value of ["../secret", "bad/id", "bad\\id", "bad?query", ""]) {
    assert.equal(bridge.parseRequest("?" + new URLSearchParams({ gallery_asset: value })), null);
  }
  assert.equal(bridge.parseRequest("?" + new URLSearchParams({ gallery_asset: "a".repeat(181) })), null);
});

test("four existing viewer pages each register a game-specific bridge", () => {
  const games = ["azur_lane", "nikke", "reverse1999", "brown_dust2"];
  for (const game of games) {
    const page = fs.readFileSync(path.join(root, game, "viewer/index.html"), "utf8");
    assert.ok(page.includes('../../shared/gallery_bridge.js'), "bridge script missing: " + game);
    assert.ok(page.includes('GalleryViewerBridge?.register'), "bridge adapter missing: " + game);
    assert.ok(page.includes('GalleryViewerBridge?.refresh'), "bridge readiness missing: " + game);
  }
});

test("catalog links preserve exact resource id in a URL query", () => {
  const app = fs.readFileSync(path.join(root, "gallery/app.js"), "utf8");
  assert.match(app, /gallery_asset:\s*asset\.source_id/);
  assert.ok(app.includes("registerCatalogGames(catalog.game_info)"));
});

test("viewers retain their existing renderers", () => {
  const azur = fs.readFileSync(path.join(root, "azur_lane/viewer/index.html"), "utf8");
  const nikke = fs.readFileSync(path.join(root, "nikke/viewer/index.html"), "utf8");
  const bd2 = fs.readFileSync(path.join(root, "brown_dust2/viewer/index.html"), "utf8");
  assert.ok(azur.includes("Live2DModel.from"));
  assert.ok(nikke.includes("new runtime.SpinePlayer"));
  assert.ok(bd2.includes("selectAnimation(pl, name)"));
});
