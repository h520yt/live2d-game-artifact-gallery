"use strict";
/* 动画使用仓库已有 PIXI + Cubism 2 运行时，不从资源站加载脚本。 */
(async () => {
  const $ = id => document.getElementById(id);
  const valid = id => /^c\d{3}_\d{2}$/.test(id);
  const stage = $("dc-stage"), canvas = $("dc-canvas");
  const FORCE = globalThis.PIXI?.live2d?.MotionPriority?.FORCE || 3;
  let app = null, model = null, gallery = null, current = null, token = 0;
  let motions = [], expressions = [], drag = null;
  function status(message) { $("dc-status").textContent=message; $("dc-status").hidden=!message; }
  function fit() {
    if (!model || !app) return;
    const bounds=model.getLocalBounds();
    if (!Number.isFinite(bounds.width) || bounds.width < 1 || bounds.height < 1) return;
    const scale=Math.min(app.renderer.width*.84/bounds.width,app.renderer.height*.86/bounds.height,3);
    model.scale.set(scale);
    model.pivot.set(bounds.x+bounds.width/2,bounds.y+bounds.height/2);
    model.position.set(app.renderer.width/2,app.renderer.height/2);
  }
  function clear() {
    token++;drag=null;motions=[];expressions=[];
    $("actions").replaceChildren();$("expressions").replaceChildren();
    if (model) { const old=model;model=null;app.stage.removeChild(old);old.destroy(); }
    window.GalleryViewerBridge?.refresh();
  }
  function play(name) {
    if (!model || !motions.includes(name)) return false;
    try {model.motion(name,0,FORCE);return true;}
    catch(error){status("动作播放失败："+error.message);return false;}
  }
  function expression(name) {
    if (!model || !expressions.includes(name)) return false;
    try {model.expression(name);return true;}
    catch(error){status("切换表情失败："+error.message);return false;}
  }
  function buttons(target,names,action,label) {
    target.replaceChildren();
    if (!names.length) return;
    const heading=document.createElement("p");heading.textContent=label;target.append(heading);
    names.forEach(name=>{
      const button=document.createElement("button");button.type="button";button.textContent=name;
      button.onclick=()=>action(name);target.append(button);
    });
  }
  async function open(row) {
    clear();
    current=row.asset;
    const requestId=token;
    $("selected").textContent=current.title;
    $("detail").textContent="Cubism 2 · "+current.id;
    if (!valid(current.id)) {status("资源编号不合法");return;}
    if (!row.ready) {
      status("本地模型尚未安装。请运行：\npython games/destiny_child/scripts/sync.py --id "+current.id);
      return;
    }
    // 避免缺少 Cubism 2 SDK / 专属适配器时触发难以定位的 undefined.from 异常。
    if (!globalThis.Live2D || typeof globalThis.PIXI?.live2d?.Live2DModel?.from !== "function") {
      status("Cubism 2 播放运行时未就绪。\n请在项目根目录运行：\npython games/destiny_child/scripts/sync.py --runtime-only\n然后刷新页面。");
      return;
    }
    status("正在加载动态模型…");
    try {
      if (!app) {
        app=new PIXI.Application({view:canvas,width:Math.max(1,stage.clientWidth),
          height:Math.max(1,stage.clientHeight),transparent:true,antialias:true});
      }
      const loaded=await PIXI.live2d.Live2DModel.from("../data/"+current.id+"/model.json",
        {autoInteract:false});
      if (requestId!==token) {loaded.destroy();return;}
      model=loaded;app.stage.addChild(model);fit();
      const settings=model.internalModel?.settings||{};
      motions=Object.keys(settings.motions||{});
      expressions=(settings.expressions||[]).map(item=>item.name).filter(Boolean);
      buttons($("actions"),motions,play,"可播放动作");
      buttons($("expressions"),expressions,expression,"可切换表情");
      if (motions.includes("idle")) play("idle");
      status("");
      window.GalleryViewerBridge?.refresh();
    } catch(error) {
      if (requestId===token) {
        console.error(error);
        status("动态模型加载失败："+error.message+"\n可尝试重新安装该资源并检查浏览器控制台。");
      }
    }
  }
  async function ready(id) {
    if (!valid(id)) return false;
    try {
      const results=await Promise.all(["model.json","model.moc","texture_00.png"].map(name=>
        fetch("../data/"+id+"/"+name,{method:"HEAD",cache:"no-store"})));
      return results.every(response=>response.ok);
    }catch{return false;}
  }
  canvas.addEventListener("pointerdown",event=>{
    if (!model || event.button!==0) return;
    drag={id:event.pointerId,x:event.clientX,y:event.clientY,moved:false};
    canvas.setPointerCapture?.(event.pointerId);
  });
  canvas.addEventListener("pointermove",event=>{
    if (!model || !drag || event.pointerId!==drag.id) return;
    const dx=event.clientX-drag.x,dy=event.clientY-drag.y;
    if (Math.abs(dx)+Math.abs(dy)>2) drag.moved=true;
    model.x+=dx;model.y+=dy;drag.x=event.clientX;drag.y=event.clientY;
  });
  canvas.addEventListener("pointerup",event=>{
    if (!drag || event.pointerId!==drag.id) return;
    const moved=drag.moved;drag=null;if (!moved)play("hit");
  });
  canvas.addEventListener("pointercancel",()=>{drag=null});
  canvas.addEventListener("contextmenu",event=>{event.preventDefault();play("attack")});
  canvas.addEventListener("wheel",event=>{
    if (!model) return;
    event.preventDefault();model.scale.set(Math.min(12,Math.max(.03,model.scale.x*(event.deltaY<0?1.12:1/1.12))));
  },{passive:false});
  window.addEventListener("resize",()=>{
    if(app){app.renderer.resize(Math.max(1,stage.clientWidth),Math.max(1,stage.clientHeight));fit();}
  });
  $("reset-fit").onclick=fit;
  try {
    const response=await fetch("manifest.json",{cache:"no-store"});
    if (!response.ok) throw Error("HTTP "+response.status);
    const data=await response.json();
    if (data.schema_version!==1 || !Array.isArray(data.assets)) throw Error("manifest 无效");
    const statuses=await Promise.all(data.assets.map(asset=>ready(asset.id)));
    gallery=SkinGallery.create({grid:$("items"),search:$("search"),sort:$("sort"),count:$("count"),
      detail:$("detail-view"),onOpen:row=>{open(row);return true},
      onClose:()=>{clear();current=null;status("");}});
    gallery.setItems(data.assets.map((asset,index)=>({
      key:asset.id,title:asset.title,subtitle:asset.metadata?.character||asset.id,
      ready:statuses[index],preview:asset.preview,
      status:statuses[index]?"必要模型入口存在":"待安装动态模型",asset
    })));
    $("back-to-catalog").onclick=()=>gallery.close();
    $("prev").onclick=()=>gallery.navigate(-1);
    $("next").onclick=()=>gallery.navigate(1);
    window.GalleryViewerBridge?.register({game:"destiny_child",open:id=>gallery.open(id),
      listRoles:()=>model?["model"]:[],selectRole:name=>name==="model"&&!!model,
      listActions:()=>motions,playAction:play});
  } catch(error){$("catalog-status").textContent="无法读取资源目录："+error.message;}
})();
