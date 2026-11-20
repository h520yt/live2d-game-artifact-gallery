#!/usr/bin/env node
"use strict";

// node reverse1999/scripts/test_skin_groups.cjs
const assert = require("node:assert/strict");
const { mergePerchta } = require("../viewer/skin_groups.js");

const initial = {
  id: 315901, name: "佩施塔", skin: "初始皮肤",
  type: "spine", artwork: "../data/character_art/315901/artwork.webp",
  artwork_kind: "character-portrait",
};
const other = {
  id: 315902, name: "佩施塔", skin: "童话出逃日",
  type: "artwork", artwork: "../data/character_art/315902/scene.webp",
  artwork_kind: "character-scene-portrait",
};
const rows = [
  {key:"315902",title:"佩施塔",model:other},
  {key:"315901",title:"佩施塔",model:initial},
  {key:"308603",title:"露西",model:{id:308603}},
];
const result = mergePerchta(rows,[initial,other]);
assert.equal(result.length,2,"两个佩施塔条目必须合并为一张封面");
assert.equal(result.find(x=>x.key==="315901"),undefined,"不得出现第二张初始衣着卡片");
const merged = result.find(x=>x.key==="315902");
assert.equal(merged.group.portrait,initial.artwork);
assert.equal(merged.group.scene,other.artwork);
assert.equal(merged.group.playable,initial);
assert.equal(merged.preview,other.artwork,"封面默认完整场景而非独立人物图");
assert.equal(merged.title,"佩施塔");
assert.ok(merged.searchText.includes("315901"));
assert.ok(result.find(x=>x.key==="308603"),"其它角色不受合并影响");

// 未来若 315902 安装了动态模型，优先用同衣着动态骨骼；315901 立绘继续保留。
const sceneModel = {...other,type:"spine",dir:"../data/spine/v4a1_315902_pst"};
const withSceneModel = mergePerchta(rows,[initial,sceneModel]);
assert.equal(withSceneModel.find(x=>x.key==="315902").group.playable,sceneModel);

// 没有图也不应伪造：只保留真实的背景/人物记录。
const withoutArtwork=mergePerchta([{key:"315901",model:{id:315901,type:"spine"}}],
  [{id:315901,type:"spine"}]);
assert.equal(withoutArtwork.length,1);
assert.equal(withoutArtwork[0].group.scene,null);
assert.equal(withoutArtwork[0].group.portrait,null);

// 纯独立衣着不进入此角色合并。
assert.deepEqual(mergePerchta([{key:"308603"}],[]),[{key:"308603"}]);
console.log("1999 佩施塔合并 / 完整场景 / 角色原画 / 动态模型逻辑测试通过");
