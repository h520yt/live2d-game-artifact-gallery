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
    resetCamera: () => {},
    scheduleAutoFocus: () => {},
    currentRole: role,
    chosenSkin: null,
    manualSkinSelection: false,
    isInteractionRole: role => role === "interaction" || role === "interaction2",
    console: {error: () => {}}
  };
  const run = vm.runInNewContext(helpers + skinHelpers + playback + "\nselectAnimation;", scope);
  const state = {
    data:{skeletonData:{animations: animations.map(name=>({name}))}},
    clearTracks:()=>calls.push(["clearTracks"]),
    setAnimation:(track,name,loop)=>{
      calls.push(["setTrack",track,name,loop]);
      return {mixDuration:0.15};
    },
    addAnimation:(track,name,loop,delay)=>{
      calls.push(["addTrack",track,name,loop,delay]);
      return {mixDuration:0.15};
    },
    addEmptyAnimation:(track,mixDuration,delay)=>{
      calls.push(["clearOverlayAfterSequence",track,mixDuration,delay]);
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
    ["setTrack",0,"idle1",true],["setTrack",1,"mix1_1",true],["play"]
  ]);
});

test("只有 mix2_1 时优先补对应 idle2，而非 idle1",()=>{
  const a = harness(["idle1","idle2","mix2_1"],"interaction");
  a.run(a.player,"mix2_1");
  assert.ok(a.calls.some(x=>x[0]==="setTrack" && x[1]===0 && x[2]==="idle2"));
});

test("独立 mix 片段按官方查看器循环，避免短动画结束后残留黑帧",()=>{
  const a=harness(["idle1","mix1_1","idle2","mix2_1"],"interaction");
  assert.equal(a.run(a.player,"mix2_1"),true);
  assert.ok(a.calls.some(x=>x[0]==="setTrack" && x[1]===0 && x[2]==="idle2"));
  assert.ok(a.calls.some(x=>x[0]==="setTrack" && x[1]===1 && x[2]==="mix2_1" && x[3]===true));
});

test("mix2_1_1 到 mix2_1_end 是数字顺序连播，结束清空上层保留 idle2",()=>{
  const names=["idle2","mix2_1_10","mix2_1_1","mix2_1_end","mix2_1_2",
               "mix2_2_1","mix2_2_2","idle3"];
  const f=vm.runInNewContext(helpers+"\n({getMixSequence,getMixSequences});");
  const group=f.getMixSequence(names,"mix2_1_10");
  assert.equal(group.key,"mix2_1");
  assert.deepEqual(Array.from(group.clips),
    ["mix2_1_1","mix2_1_2","mix2_1_10","mix2_1_end"]);
  assert.equal(f.getMixSequences(names).length,2);
  const a=harness(names,"interaction");
  assert.equal(a.run(a.player,"mix2_1_2"),true);
  assert.deepEqual(a.calls,[
    ["clearTracks"],["setupPose"],["setTrack",0,"idle2",true],
    ["setTrack",1,"mix2_1_1",false],
    ["addTrack",1,"mix2_1_2",false,0],
    ["addTrack",1,"mix2_1_10",false,0],
    ["addTrack",1,"mix2_1_end",false,0],
    ["clearOverlayAfterSequence",1,0,0],
    ["play"]
  ]);
  assert.match(a.status[0],/mix2_1 连续 4 段/);
});

test("带分组前缀但没有足够片段的 mix，仍可作为单个循环动作",()=>{
  const a=harness(["idle3","mix3_7_1"],"interaction");
  assert.equal(a.run(a.player,"mix3_7_1"),true);
  assert.ok(a.calls.some(x=>x[0]==="setTrack" && x[1]===1 &&
    x[2]==="mix3_7_1" && x[3]===true));
});

test("连续动作分组按钮不会把原始动作去掉，黑屏时仍能查看实际名称",()=>{
  assert.match(page,/function parseMixSegment\(name\)/);
  assert.match(page,/function getMixSequence\(names, name\)/);
  assert.match(page,/function getMixSequences\(names\)/);
  assert.match(page,/button\.dataset\.sequence = group\.key/);
  assert.match(page,/getMixSequence\(anims,name\)/);
  assert.match(page,/完整播放连续动作/);
  assert.match(page,/state\.addAnimation\(1, clip, false, 0\)/);
  assert.match(page,/state\.addEmptyAnimation\?\.\(1, 0, 0\)/);
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

test("初始互动动画必须与 Skin 场景同组，不能单纯挑选部件最多的 Skin",()=>{
  const scope={chosenSkin:null};
  const helpersFn=vm.runInNewContext(helpers + skinHelpers +
    "\n({skinForAnimation,pickInitialScene});",scope);
  const mk=(name,n)=>({name,getAttachments:()=>Array.from({length:n},(_,i)=>i)});
  const skins=[mk("default",900),mk("idle3_1",465)];
  const anims=["idle1","idle2","idle3_1","mix3_1"];
  const first=helpersFn.pickInitialScene(anims,skins);
  assert.equal(first.skin.name,"idle3_1");
  assert.equal(first.animation,"idle3_1");
  assert.equal(helpersFn.skinForAnimation(skins,"mix3_1").name,"idle3_1");
  // 如果上游只提供 idle3 而不是 idle3_1 动画，也必须选择同组 Skin。
  const groupOnly=helpersFn.pickInitialScene(["idle1","idle3"],skins);
  assert.equal(groupOnly.skin.name,"idle3_1");
  assert.equal(groupOnly.animation,"idle3");
});

test("相同编号的 Skin/idle 必须优先于部件数，动画手动切换时自动切换 Skin",()=>{
  const scope={chosenSkin:null};
  const f=vm.runInNewContext(helpers + skinHelpers +
    "\n({skinForAnimation,pickInitialScene});",scope);
  const mk=(name,n)=>({name,getAttachments:()=>Array.from({length:n},(_,i)=>i)});
  const skins=[mk("idle3_1",800),mk("idle1",200),mk("default",30)];
  const first=f.pickInitialScene(["idle1","idle3_1"],skins);
  assert.equal(first.skin.name,"idle1");
  assert.equal(first.animation,"idle1");
  assert.equal(f.skinForAnimation(skins,"idle3_1").name,"idle3_1");
  assert.equal(f.skinForAnimation(skins,"mix3_2").name,"idle3_1");
  assert.match(page,/isInteractionRole\(currentRole\) && !manualSkinSelection/);
  assert.match(page,/const candidate = skinForAnimation\(pl\.skeleton\?\.data\?\.skins \|\| \[\], name\)/);
  assert.match(page,/changedSkin = applySkin\(pl, candidate\.name\)/);
  assert.match(page,/pl\.animationState\.apply\?\.\(pl\.skeleton\)/);
});

test("互动场景下拉菜单可一键更换配对的动画和 Skin，手动 Skin 锁定仍可解除",()=>{
  assert.match(page,/id="scene-choice"/);
  assert.match(page,/scene\.disabled = !isInteractionRole\(currentRole\)/);
  assert.match(page,/const matched = skinForAnimation\(skinOptions,name\)/);
  assert.match(page,/scene\.onchange = \(\) => \{/);
  assert.match(page,/manualSkinSelection = false;/);
  assert.match(page,/selectAnimation\(pl,scene\.value\)/);
  assert.match(page,/manualSkinSelection = true;/);
  assert.match(page,/savedSkinLocked = manualSkinSelection/);
  assert.match(page,/skinLocked:savedSkinLocked/);
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
  assert.match(page,/!isInteractionRole\(currentRole\)/);
  assert.match(page,/0\.86\/content\.width/);
  assert.match(page,/0\.84\/content\.height/);
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
  assert.match(page,/savedAnimation = selectedMotion \? \(selectedMotion\.dataset\.animation \|\| selectedMotion\.textContent\) : null/);
  assert.match(page,/loadRole\(savedRole, \{skin:savedSkin, skinLocked:savedSkinLocked, animation:savedAnimation\}\)/);
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

test("目录索引与本地资源状态分离，所有收藏并不等于已安装",()=>{
  assert.match(page,/function hasInstalledModel\(skin\)/);
  assert.match(page,/Object\.keys\(installed\.get\(skin\.id\)\.roles\)\.length/);
  assert.match(page,/id="install-hint"/);
  assert.doesNotMatch(page,/<div class="hint">未下载的皮肤/);
});

test("前端严格筛选特殊皮肤和风格白名单，不显示200套原始目录",()=>{
  assert.match(page,/fetch\("\.\.\/costume_catalog\.json"/);
  assert.match(page,/fetch\("\.\.\/curated_style\.json"/);
  assert.match(page,/const styleMap = new Map\(styles\.map/);
  assert.match(page,/allRegular\.filter\(skin => skin\.tier === "Special Skin"/);
  assert.match(page,/styleMap\.has\(skin\.id\)/);
  assert.match(page,/catalog = \[\.\.\.interactionBatch,/);
  assert.match(page,/\.\.\.regular\]/);
  for (const value of ["all", "batch", "special", "style", "mature",
                       "stockings", "legs", "interactive", "installed"]) {
    assert.match(page, new RegExp('data-filter="' + value + '"'));
  }
  for (const value of ["guest", "other", "prestige"]) {
    assert.doesNotMatch(page, new RegExp('data-filter="' + value + '"'));
  }
  assert.match(page,/function isSpecial\(skin\)/);
  assert.match(page,/function hasStyleTag\(skin, tag\)/);
  assert.match(page,/const localCount = catalog\.filter\(hasInstalledModel\)\.length/);
});

test("风格偏好标签展示与已安装状态彼此独立",()=>{
  assert.match(page,/skin\.preference_tags \|\| \[\]/);
  assert.match(page,/skin\.tier === "Special Skin"/);
  assert.match(page,/id="collection-info"/);
  assert.match(page,/互动优先/);
  assert.match(page,/互动优先：本批新增/);
});

test("巨大异常黑色遮罩不再主导互动相机边界",()=>{
  const section=extract("function getInteractionBounds(skeleton) {",
                        "\nfunction resetCamera(pl) {");
  const bounds=vm.runInNewContext(section + "\ngetInteractionBounds;", {});
  const region=(name,x1,y1,x2,y2)=>({
    data:{name},bone:{},
    getAttachment:()=>({
      computeWorldVertices:(_bone,vertices)=>{
        vertices.set([x1,y1,x2,y1,x2,y2,x1,y2]);
      }
    })
  });
  const slots=[
    region("background_huge",-120000,-120000,120000,120000),
    region("invisibleBlackMask",-90000,-90000,90000,90000),
    region("hair",20,120,180,300),
    region("torso",30,20,175,170),
    region("leg1",40,-160,85,25),
    region("leg2",90,-155,140,25)
  ];
  const actual=bounds({drawOrder:slots});
  assert.deepEqual({x:actual.x,y:actual.y,width:actual.width,height:actual.height},
                   {x:20,y:-160,width:160,height:460});
  assert.equal(bounds({drawOrder:[slots[0]]}),null);
});

test("互动相机遇到骨骼边界远大于有效内容时会切换，不再失败后禁用缩放",()=>{
  const start=page.indexOf("function resetCamera(pl) {");
  const end=page.indexOf("\nfunction el(tag, cls, text)",start);
  const section=page.slice(start,end);
  assert.match(section,/isInteractionRole\(currentRole\)\s*\?\s*getInteractionBounds\(skeleton\)/);
  assert.match(section,/const limit = isInteractionRole\(currentRole\) \? 4 : 1\.4/);
  assert.match(section,/if \(!fallbackValid \|\| ratio >= limit\)/);
  assert.match(section,/if \(!boundsUsable\(size\.x, size\.y\)\)/);
  assert.match(section,/baseZoom:camera\.zoom, factor:1, token:loadId/);
  assert.match(section,/\$\("auto-focus"\)\.disabled=!isInteractionRole\(currentRole\)/);
  assert.doesNotMatch(section,/pl\.config\.viewport\s*=/);
});

test("极小中心场景允许高倍率自动聚焦但不放大单个闪光像素",()=>{
  assert.match(page,/Math\.min\(20, 0\.86\/content\.width, 0\.84\/content\.height\)/);
  assert.match(page,/content\.width \* content\.height < 0\.002/);
  assert.match(page,/function sampleVisibleContent\(canvas\)/);
});

test("新一批独立互动即使没有人物/技能模型也可单独展示",()=>{
  assert.match(page,/fetch\("\.\.\/curated_interactions\.json"/);
  assert.match(page,/let collectionFilter = "interactive"/);
  assert.match(page,/data-filter="interactive" class="active"/);
  assert.match(page,/data-filter="batch"/);
  assert.match(page,/collectionFilter === "batch"/);
  assert.match(page,/skin\.interaction_only \? "独立互动专辑"/);
  assert.match(page,/仅互动，无需人物\/技能/);
  assert.match(page,/skin\.interaction_only \? " · 互动专辑/);
  assert.match(page,/catalog\.sort\(\(left,right\) => priority\(left\)-priority\(right\)\)/);
  assert.match(page,/const ready = catalog\.find\(skin => installed\.get\(skin\.id\)\?\.roles\.interaction\)/);
  assert.match(page,/loadRole\(item\.roles\.interaction \? "interaction" : item\.roles\.interaction2/);
  assert.match(page,/new Set\(ids\)\.size !== ids\.length/);
});

test("第三批20款目录按需读取，Aquila 双互动场景都遵循相同双轨逻辑",()=>{
  assert.match(page,/fetch\("\.\.\/curated_batch_20\.json"/);
  assert.match(page,/catalog = \[\.\.\.batch20,\.\.\.interactionBatch/);
  assert.match(page,/data-filter="batch20"/);
  assert.match(page,/collectionFilter === "batch20"/);
  assert.match(page,/interaction2:"互动动画②"/);
  assert.match(page,/const isInteractionRole = role => role === "interaction" \|\| role === "interaction2"/);
  assert.match(page,/defaultMix:isInteractionRole\(role\) \? 0 : 0\.18/);
  assert.match(page,/if \(isInteractionRole\(role\)\) return interactionLabel\(skin\)/);
  assert.match(page,/isInteractionRole\(currentRole\) && !manualSkinSelection/);
  assert.match(page,/roles\.some\(isInteractionRole\)/);
});

test("互动状态区分官方没有互动、资源待下载、真实已安装",()=>{
  const section = extract("function interactionLabel(skin) {",
                          "\nfunction roleHint(skin, role, model) {");
  const scope = {installed:new Map()};
  const label = vm.runInNewContext(section + "\ninteractionLabel;",scope);
  const special = {id:"special",tier:"Special Skin",roles:{character:"ch"}};
  const ordinary = {id:"ordinary",tier:"Costume",roles:{character:"ch"}};
  const fated = {id:"fated",tier:"Fated Guest",roles:{interaction:"dating8"}};
  assert.equal(label(special), "官方无独立互动");
  assert.equal(label(ordinary), "未找到对应互动");
  assert.equal(label(fated), "互动待下载");
  scope.installed.set("fated",{roles:{interaction:{skel:"model.skel"}}});
  assert.equal(label(fated), "独立互动已安装");
});

test("没有独立互动的条目不会创建可点击的伪互动按钮",()=>{
  assert.match(page,/button\.disabled = !info/);
  assert.match(page,/button\.title = label/);
  assert.match(page,/const label = roleHint\(skin, role, info\)/);
  assert.match(page,/if \(skin\.roles\.interaction\) return "互动待下载"/);
  assert.match(page,/--role interaction/);
});

test("未下载服装显示可执行的独立安装命令而不是空白播放器",()=>{
  assert.match(page,/install_prestige\.py --only " \+ skin\.id/);
  assert.match(page,/skin\.mapping === "candidate"/);
});
