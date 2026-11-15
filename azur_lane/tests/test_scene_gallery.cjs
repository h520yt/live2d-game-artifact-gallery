"use strict";
const assert = require("node:assert/strict");
const gallery = require("../viewer/scene_gallery.js");
function item(name, kind = "variant") { return { name, kind, path: name + ".png" }; }

const c = { asset: "hu_2", rep: "hu_2_n_rw", items: [
  item("hu_2", "main"), item("hu_2_n_rw"), item("hu_2_n_rw_hx"),
  item("hu_2_bj", "part"), item("hu_2_n_bj", "part"),
  item("hu_2_n_bj_hx", "part"), item("hu_2_front", "part")
]};
const scenes = gallery.buildScenes(c);
assert.equal(scenes.length, 3);
assert.equal(scenes[0].background.name, "hu_2_bj");
assert.equal(scenes[1].background.name, "hu_2_n_bj");
assert.equal(scenes[2].background.name, "hu_2_n_bj_hx");
assert.equal(scenes[1].foreground.name, "hu_2_front");
assert.equal(gallery.preferredScene(c).name, "hu_2_n_rw");

const noBackground = { asset: "aersasi_3", rep: "aersasi_3", items: [item("aersasi_3", "main")] };
assert.equal(gallery.preferredScene(noBackground).background, null);
assert.equal(gallery.buildScenes(noBackground).length, 1);

const noCrossMatch = { asset: "hu_2", rep: "hu_2", items: [
  item("hu_2", "main"), item("hu_20_bj", "part")
]};
assert.equal(gallery.preferredScene(noCrossMatch).background, null);
console.log("scene gallery composition tests: OK");
