/* 棕色尘埃2播放器回归测试：防止只设置动作却忘记调用 play()。 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const page = fs.readFileSync(path.join(__dirname, "../viewer/index.html"), "utf8");
const start = page.indexOf("function selectAnimation(pl, name) {");
const end = page.indexOf("\nasync function loadRole(role) {", start);
assert.ok(start >= 0 && end > start, "找不到播放器动作函数");

function createHarness(animations) {
  const calls = [];
  const states = [];
  const buttons = animations.map(name => ({
    textContent: name,
    classList: {toggle: (cls, selected) => states.push([name, cls, selected])}
  }));
  const status = [];
  const scope = {
    $: id => id === "motions" ? {children: buttons} : null,
    setStatus: message => status.push(message),
    console: {error: () => {}}
  };
  const selectAnimation = vm.runInNewContext(page.slice(start, end) + "\nselectAnimation;", scope);
  const player = {
    animationState: {data: {skeletonData: {animations: animations.map(name => ({name}))}}},
    setAnimation: (name, loop) => calls.push(["setAnimation", name, loop]),
    addAnimation: (name, loop, delay) => calls.push(["addAnimation", name, loop, delay]),
    play: () => calls.push(["play"])
  };
  return {selectAnimation, player, calls, states, status};
}

test("idle 动作启动播放，不是只有 setAnimation", () => {
  const harness = createHarness(["idle", "motion", "_face0"]);
  harness.selectAnimation(harness.player, "idle");
  assert.deepEqual(harness.calls, [
    ["setAnimation", "idle", true],
    ["play"]
  ]);
  assert.ok(harness.states.some(([name, cls, selected]) =>
    name === "idle" && cls === "active" && selected));
});

test("非循环动画结束后回到待机，并实际启动播放器", () => {
  const harness = createHarness(["idle", "motion", "_face0"]);
  harness.selectAnimation(harness.player, "motion");
  assert.deepEqual(harness.calls, [
    ["setAnimation", "motion", false],
    ["addAnimation", "idle", true, 0],
    ["play"]
  ]);
});

test("播放失败时在页面显示错误，而不是假装加载完成", () => {
  const harness = createHarness(["idle"]);
  harness.player.play = () => {throw new Error("WebGL unavailable");};
  harness.selectAnimation(harness.player, "idle");
  assert.match(harness.status[0], /WebGL unavailable/);
});

test("已安装资源不再显示未下载的固定错误提示", () => {
  assert.match(page, /installed\.size\s*\?/);
  assert.match(page, /id="install-hint"/);
  assert.doesNotMatch(page, /<div class="hint">未下载的皮肤/);
});
