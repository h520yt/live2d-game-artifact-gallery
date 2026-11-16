/* BD2 Spine 播放器回归：Skin、互动双轨、预乘 Alpha、动画循环。 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const page = fs.readFileSync(path.join(__dirname, "../viewer/index.html"), "utf8");
const inline = page.match(/<script>([\s\S]*?)<\/script>\s*<\/body>/);
assert.ok(inline, "找不到展柜的内联脚本");
assert.doesNotThrow(() => new vm.Script(inline[1]), "前端源码存在语法错误");

function extract(startLabel, endLabel) {
  const start = page.indexOf(startLabel);
  const end = page.indexOf(endLabel, start);
  assert.ok(start >= 0 && end > start, "找不到 JS 代码: " + startLabel);
  return page.slice(start, end);
}

const helpers = extract("function isIdleAnimation(name) {", "\nfunction countSkinAttachments(skin) {");
const skinHelpers = extract("function countSkinAttachments(skin) {", "\nfunction applySkin(pl, name) {");
const playback = extract("function selectAnimation(pl, name) {", "\nasync function loadRole(");

function harness(animations, role="character") {
  const calls = [];
  const states = [];
  const buttons = animations.map(name => ({
    textContent: name,
    classList: {toggle: (cls, checked) => states.push([name,cls,checked])}
  }));
  const status = [];
  const scope = {
    $: id => id === "motions" ? {children:buttons} : null,
    setStatus: message => status.push(message),
    currentRole: role,
    console: {error: () => {}}
  };
  const run = vm.runInNewContext(helpers + skinHelpers + playback + "\nselectAnimation;", scope);
  const state = {
    data:{skeletonData:{animations: animations.map(name=>({name}))}},
    clearTracks:()=>calls.push(["clearTracks"]),
    setAnimation:(track,name,loop)=>{
      calls.push(["setTrack",track,name,loop]);
      return {mixDuration:0.15};
    }
  };
  const player = {
    animationState:state,
    skeleton:{setToSetupPose:()=>calls.push(["setupPose"])},
    setAnimation:(name,loop)=>calls.push(["setAnimation",name,loop]),
    addAnimation:(name,loop,delay)=>calls.push(["addAnimation",name,loop,delay]),
    play:()=>calls.push(["play"])
  };
  return {run,player,calls,states,status,helpers:scope};
}

test("idle1 被识别为循环动画", ()=>{
  const a = harness(["idle1","idle2","mix1_1"],"interaction");
  assert.equal(a.run(a.player,"idle1"),true);
  assert.deepEqual(a.calls,[
    ["clearTracks"],["setAnimation","idle1",true],["play"]
  ]);
});

test("mix1_1 叠加 idle1 后再播放", ()=>{
  const a = harness(["idle1","mix1_1","idle2","mix2_1"],"interaction");
  assert.equal(a.run(a.player,"mix1_1"),true);
  assert.deepEqual(a.calls,[
    ["clearTracks"],["setupPose"],
    ["setTrack",0,"idle1",true],["setTrack",1,"mix1_1",false],["play"]
  ]);
});

test("只有 mix2_1 时优先补对应 idle2，而非 idle1",()=>{
  const a = harness(["idle1","idle2","mix2_1"],"interaction");
  a.run(a.player,"mix2_1");
  assert.ok(a.calls.some(x=>x[0]==="setTrack" && x[1]===0 && x[2]==="idle2"));
});

test("没有对应 idle 的 mix 动作按普通单轨处理",()=>{
  const a = harness(["idle1","mix7_1"],"interaction");
  a.run(a.player,"mix7_1");
  assert.ok(a.calls.some(x=>x[0]==="setAnimation" && x[1]==="mix7_1"));
  assert.ok(!a.calls.some(x=>x[0]==="setTrack"));
});

test("非循环动作结束后回待机",()=>{
  const a = harness(["idle","motion"]);
  a.run(a.player,"motion");
  assert.deepEqual(a.calls,[
    ["clearTracks"],["setAnimation","motion",false],
    ["addAnimation","idle",true,0],["play"]
  ]);
});

test("失败时展示具体原因",()=>{
  const a = harness(["idle"]);
  a.player.play=()=>{throw new Error("WebGL unavailable");};
  assert.equal(a.run(a.player,"idle"),false);
  assert.match(a.status[0],/WebGL unavailable/);
});

test("选择实际部件最多的 Skin 而不是固定 default",()=>{
  const a = harness(["idle"]);
  const mk=(name,n)=>({name,getAttachments:()=>Array.from({length:n},(_,i)=>i)});
  const chosen=a.helpers.bestSkin([mk("default",1),mk("prestige",128),mk("blink",12)]);
  assert.equal(chosen.name,"prestige");
});

test("预乘 Alpha 的纹理上传和播放器混合开关联动",()=>{
  assert.match(page,/UNPACK_PREMULTIPLY_ALPHA_WEBGL/);
  assert.match(page,/premultipliedAlpha:alphaMode === "pma"/);
  assert.match(page,/alphaMode === "pma"/);
  assert.match(page,/id="alpha-mode"/);
});

test("不覆盖 SpinePlayer viewport.animations 导致 <empty> 过渡崩溃",()=>{
  // SpinePlayer 在空动画混合阶段会查询 viewport.animations['<empty>']。
  // 未配置 viewport 比注入缺少 animations 字典的 1x1 viewport 更安全。
  assert.doesNotMatch(page,/\bviewport\s*:\s*\{\s*x\s*:\s*0\s*,\s*y\s*:\s*0\s*,\s*width\s*:\s*1/);
  assert.doesNotMatch(page,/pl\.config\.viewport\s*=\s*\{/);
  assert.match(page,/function resetCamera\(pl\)/);
});

test("相机按骨骼边界取景，并在每一帧维持用户缩放",()=>{
  assert.match(page,/skeleton\.getBounds\(offset, size\)/);
  assert.match(page,/baseZoom:Math\.max\(/);
  assert.match(page,/camera\.zoom = cameraView\.baseZoom \/ cameraView\.factor/);
  assert.match(page,/update:\(\) => \{/);
  assert.match(page,/id="reset-camera"/);
});

test("互动动画自动识别实际可见内容并忽略黑色像素",()=>{
  const section = extract("function findContentBounds(width, height, pixels) {",
                          "\nfunction sampleVisibleContent(canvas) {");
  const detect = vm.runInNewContext(section + "\nfindContentBounds;");
  const w = 64, h = 40;
  const rgba = new Uint8ClampedArray(w*h*4);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const i=(y*w+x)*4;
    rgba[i+3]=255; // 黑色帧全部不计入边界
    if(x>=22&&x<42&&y>=10&&y<27){
      rgba[i]=130; rgba[i+1]=170; rgba[i+2]=210;
    }
  }
  const box=detect(w,h,rgba);
  assert.deepEqual({x:box.left,y:box.top,w:box.width,h:box.height},
                   {x:22,y:10,w:20,h:17});
  assert.equal(detect(w,h,new Uint8ClampedArray(w*h*4)),null);
});

test("智能取景只对互动动画生效，支持手动放大和重试",()=>{
  assert.match(page,/currentRole !== "interaction"/);
  assert.match(page,/0\.82\/content\.width/);
  assert.match(page,/0\.78\/content\.height/);
  assert.match(page,/id="auto-focus"/);
  assert.match(page,/id="zoom"/);
  assert.match(page,/scheduleAutoFocus\(pl\)/);
  assert.match(page,/setZoomFactor\(pl,/);
});

test("预览舞台默认随屏幕增高，沉浸式预览可占满可视窗口",()=>{
  assert.match(page,/height:clamp\(560px,73dvh,1300px\)/);
  assert.match(page,/grid-template-columns:clamp\(240px,19vw,300px\)/);
  assert.match(page,/\.viewer\.theater\{position:fixed;inset:0;z-index:1000/);
  assert.match(page,/height:100dvh/);
  assert.match(page,/\.viewer\.theater \.stage\{height:auto;flex:1 1 auto/);
  assert.match(page,/id="theater-toggle"/);
  assert.match(page,/event\.key === "Escape"/);
});

test("切换大屏保留当前资源分类、Skin 和动画，重建播放器以匹配新尺寸",()=>{
  assert.match(page,/function setTheaterMode\(enabled\)/);
  assert.match(page,/const savedRole = currentRole/);
  assert.match(page,/const savedSkin = chosenSkin/);
  assert.match(page,/savedAnimation = selectedMotion \? selectedMotion\.textContent : null/);
  assert.match(page,/loadRole\(savedRole, \{skin:savedSkin, animation:savedAnimation\}\)/);
  assert.match(page,/async function loadRole\(role, restore=null\)/);
  assert.match(page,/restore\?\.skin && skinOptions\.find/);
  assert.match(page,/restore\?\.animation && anims\.includes/);
});

test("完整适配与智能铺满独立，手动缩放允许缩小到50%",()=>{
  assert.match(page,/id="zoom"[^>]*min="50" max="500"/);
  assert.match(page,/Math\.min\(5, Math\.max\(0\.5, factor\)\)/);
  const wholeFit = page.slice(page.indexOf('$("reset-camera").onclick ='),
                             page.indexOf('$("auto-focus").onclick ='));
  assert.match(wholeFit,/resetCamera\(pl\)/);
  assert.doesNotMatch(wholeFit,/scheduleAutoFocus/);
  const focus = page.slice(page.indexOf('$("auto-focus").onclick ='),
                           page.indexOf('$("zoom").oninput ='));
  assert.match(focus,/scheduleAutoFocus\(pl, 160\)/);
});

test("完整人物优先根据可见部件计算世界边界，忽略巨型背景槽位",()=>{
  const source = extract("function getCharacterBounds(skeleton) {",
                         "\nfunction resetCamera(pl) {");
  const bounds = vm.runInNewContext(source + "\ngetCharacterBounds;");
  const region = (name, left, bottom, right, top) => ({
    data:{name}, bone:{},
    getAttachment:() => ({
      computeWorldVertices:(_bone,vertices) => {
        vertices.set([left,bottom,right,bottom,right,top,left,top]);
      }
    })
  });
  const skeleton = {drawOrder:[
    region("bg_large", -5000,-5000,5000,5000),
    region("body", 10,20,100,200),
    region("hair", 20,180,90,240)
  ]};
  const value = bounds(skeleton);
  assert.deepEqual({x:value.x,y:value.y,width:value.width,height:value.height},
                   {x:10,y:20,width:90,height:220});
  assert.equal(bounds({drawOrder:[region("background",0,0,5000,5000)]}), null);
  assert.match(page,/const paddedWidth = size\.x \* 1\.12/);
  assert.match(page,/Math\.max\(paddedWidth \/ Math\.max\(canvas\.width,1\)/);
  assert.doesNotMatch(page,/pl\.config\.viewport\s*=/);
});

test("索引与本地安装状态仍分离",()=>{
  assert.match(page,/installed\.size\s*\?/);
  assert.match(page,/id="install-hint"/);
  assert.doesNotMatch(page,/<div class="hint">未下载的皮肤/);
});
