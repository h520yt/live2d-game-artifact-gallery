"use strict";

/* 浏览器前景图层工具的逻辑与页面集成回归测试：无需游戏资源或 node 包。 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const viewerDir = path.resolve(__dirname, "../viewer");
const source = fs.readFileSync(path.join(viewerDir, "artmesh_visibility.js"), "utf8");
const index = fs.readFileSync(path.join(viewerDir, "index.html"), "utf8");
const saved = new Map();
const mockWindow = {
  localStorage: {
    getItem(key) { return saved.get(key) ?? null; },
    setItem(key, value) { saved.set(key, value); }
  }
};
vm.runInNewContext(source, { window: mockWindow, console });
const tools = mockWindow.AzurArtmeshVisibility;
assert(tools, "图层管理器必须导出");

function rect(left, top, right, bottom) {
  return new Float32Array([
    left, top, right, top, right, bottom,
    left, top, right, bottom, left, bottom,
  ]);
}

const drawables = [
  { id: "Body", order: 10, rect: rect(20, 20, 90, 95) },
  { id: "ArtMeshLeaf_A", order: 200, rect: rect(0, 0, 80, 70) },
  { id: "ArtMeshLeaf_B", order: 201, rect: rect(40, 30, 110, 110) },
  { id: "Eye", order: 210, rect: rect(50, 40, 56, 45) },
  { id: "HiddenFront", order: 240, rect: rect(10, 10, 90, 90), opacity: 0 },
];
const core = {
  getDrawableCount() { return drawables.length; },
  getDrawableIds() { return drawables.map(x => x.id); },
  getDrawableRenderOrders() { return drawables.map(x => x.order); },
  getDrawableOpacity(i) { return drawables[i].opacity ?? 1; },
  getDrawableDynamicFlagIsVisible() { return true; },
  getDrawableVertexPositions(i) { return drawables[i].rect; },
};
const rows = tools.inspect(core);
assert.equal(rows.length, 5);
assert.equal(rows.filter(x => x.foregroundCandidate).length, 2,
  "候选必须是面积较大且位于前景的叶片，而非眼睛或主体");
const guessed = Array.from(tools.likelyForeground(rows, 4), x => x.id);
assert.deepEqual(guessed.sort(), ["ArtMeshLeaf_A", "ArtMeshLeaf_B"]);
assert.equal(tools.likelyForeground(rows, 1).length, 1);
assert.equal(tools.inspect(null).length, 0);

assert.equal(tools.ruleKey("qiye_10", "idle9"), "qiye_10::idle9");
assert.equal(tools.ruleKey("qiye_10", null), "qiye_10::default");
saved.set("azurlane.artmesh.hidden.v1", JSON.stringify({
  "qiye_10::idle9": ["ArtMeshLeaf_A", "ArtMeshLeaf_B"],
  "qiye_10::default": ["Body"],
}));
assert.equal(tools.readHidden("qiye_10", "idle9").has("ArtMeshLeaf_B"), true);
assert.equal(tools.readHidden("qiye_10", "touch_special").size, 0,
  "不同动作的隐藏配置不能串用");
assert.equal(tools.readHidden("qiye_10", null).has("Body"), true);
saved.set("azurlane.artmesh.hidden.v1", "{bad json");
assert.equal(tools.readHidden("qiye_10", "idle9").size, 0, "坏数据不能导致页面崩溃");

assert.match(index, /src="artmesh_visibility\.js"/);
assert.match(index, /id="artmesh-tools"/);
assert.match(index, /AzurArtmeshVisibility\.setMotion\(model, g\)/);
assert.match(index, /AzurArtmeshVisibility\.mount\(cached,/);
assert.match(index, /AzurArtmeshVisibility\.mount\(model,/);
assert.match(index, /AzurArtmeshVisibility\.clearPanel\(\)/);
// 验证播放 idle9 后每帧隐藏叶片，切到别的动作时恢复原透明度。
saved.set("azurlane.artmesh.hidden.v1", JSON.stringify({
  "qiye_10::idle9": ["ArtMeshLeaf_A"]
}));
const layerRoot = { dataset: {}, replaceChildren() {}, append() {} };
mockWindow.document = {
  getElementById(id) { return id === "artmesh-tools" ? layerRoot : null; },
  createElement(tag) { return { tag, append() {} }; },
};
const opacity = new Float32Array([1, 0.85]);
const liveCore = {
  _model: { drawables: { opacities: opacity } },
  getDrawableCount() { return 2; },
  getDrawableIds() { return ["Body", "ArtMeshLeaf_A"]; },
  getDrawableRenderOrders() { return [10, 200]; },
  getDrawableOpacity(i) { return opacity[i]; },
  getDrawableDynamicFlagIsVisible() { return true; },
  getDrawableVertexPositions() { return rect(0, 0, 100, 100); },
};
const internalModel = {
  coreModel: liveCore,
  update() { opacity[0] = 1; opacity[1] = 0.85; },
};
const model = { internalModel };
assert.equal(tools.mount(model, "qiye_10", "artmesh-tools"), true);
tools.setMotion(model, "idle9");
assert.equal(opacity[1], 0, "应用指定动作隐藏配置");
internalModel.update(1, 1);
assert.equal(opacity[1], 0, "动画下一帧不应将叶片显示回来");
assert.equal(opacity[0], 1, "隐藏叶片不能影响主体");
tools.setMotion(model, "touch_special");
assert(opacity[1] > 0.8, "切换动作后应恢复前景");
internalModel.update(1, 1);
assert(opacity[1] > 0.8, "恢复结果必须跨帧保持");

console.log("PASS: Live2D ArtMesh foreground controls and idle9 action scoping");
