"use strict";
/* 动画使用仓库已有 PIXI + Cubism 2 运行时，不从资源站加载脚本。 */
(async () => {
  const $ = id => document.getElementById(id);
  const valid = id => /^c\d{3}_\d{2}$/.test(id);
  const stage = $("dc-stage"), canvas = $("dc-canvas");
  const FORCE = globalThis.PIXI?.live2d?.MotionPriority?.FORCE || 3;
  const boundsById = new Map();
  let app = null, model = null, gallery = null, current = null, token = 0;
  let motions = [], expressions = [], drag = null, modelBounds = null;
  function status(message) { $("dc-status").textContent=message; $("dc-status").hidden=!message; }
  function getPixelRatio() {
    return Math.min(2, Math.max(1, window.devicePixelRatio || 1));
  }
  function captureModelBounds(loaded, sample, sampleSize) {
    const bounds = loaded.getLocalBounds().clone();
    const {coreModel, localTransform, drawDataCount} = loaded.internalModel;
    const renderer = app.renderer;
    // 先让 Cubism 更新当前姿态，才能知道网格在模型坐标中的范围。
    sample.resize(1, 1);
    loaded.update(1);
    renderer.render(loaded, {renderTexture:sample});

    // 适配器的 getLocalBounds 返回名义画布尺寸，实际网格可以超出画布。
    let left = bounds.left, top = bounds.top, right = bounds.right, bottom = bounds.bottom;
    const point = new PIXI.Point();
    for (let i = 0; i < drawDataCount; i++) {
      const vertices = coreModel.getTransformedPoints(i);
      for (let j = 0; vertices && j < vertices.length; j += 2) {
        point.set(vertices[j], vertices[j + 1]);
        localTransform.apply(point, point);
        if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) continue;
        left = Math.min(left, point.x);
        top = Math.min(top, point.y);
        right = Math.max(right, point.x);
        bottom = Math.max(bottom, point.y);
      }
    }
    const scale = sampleSize / Math.max(right - left, bottom - top);
    if (!Number.isFinite(scale) || scale <= 0) return bounds;
    const padding = 2;
    const width = Math.ceil((right - left) * scale) + 2 * padding;
    const height = Math.ceil((bottom - top) * scale) + 2 * padding;
    sample.resize(width, height);
    const transform = new PIXI.Matrix(scale, 0, 0, scale, padding - left * scale, padding - top * scale);
    renderer.render(loaded, {renderTexture:sample, transform});

    // 从实际合成的透明度取轮廓，排除隐藏部件、遮罩外网格和透明纹理边缘。
    const pixels = renderer.plugins.extract.pixels(sample);
    let xMin = width, yMin = height, xMax = -1, yMax = -1;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (pixels[(y * width + x) * 4 + 3] < 16) continue;
        xMin = Math.min(xMin, x);
        yMin = Math.min(yMin, y);
        xMax = Math.max(xMax, x);
        yMax = Math.max(yMax, y);
      }
    }
    if (xMax < xMin) return bounds;
    return new PIXI.Rectangle(
      left + (xMin - padding) / scale, top + (yMin - padding) / scale,
      (xMax - xMin + 1) / scale, (yMax - yMin + 1) / scale
    );
  }
  function measureModelBounds(loaded, idleMotion) {
    const sample = PIXI.RenderTexture.create({width:1,height:1,resolution:1});
    const elapsedTime = loaded.elapsedTime;
    loaded.elapsedTime = 0;
    try {
      const rest = captureModelBounds(loaded, sample, 1024);
      const idle = rest.clone();
      const duration = idleMotion?.getLoopDurationMSec();
      if (duration > 0) {
        // 用独立队列取样整个待机动作。适配器每帧会恢复保存的模型参数，
        // 取样时钟只在这段同步离屏计算中生效。
        const internal = loaded.internalModel;
        const queue = new MotionQueueManager();
        queue.startMotion(idleMotion);
        const updatePose = () => queue.updateParam(internal.coreModel);
        const savedClock = UtSystem.getUserTimeMSec;
        let time = 0;
        internal.on("beforeModelUpdate", updatePose);
        UtSystem.getUserTimeMSec = () => time;
        try {
          const steps = Math.min(32, Math.ceil(duration / 200));
          for (let i = 0; i <= steps; i++) {
            time = duration * i / steps;
            idle.enlarge(captureModelBounds(loaded, sample, 320));
          }
        } finally {
          UtSystem.getUserTimeMSec = savedClock;
          internal.off("beforeModelUpdate", updatePose);
        }
      }
      return {rest, idle};
    } finally {
      loaded.elapsedTime = elapsedTime;
      sample.destroy(true);
    }
  }
  function fit() {
    if (!model || !modelBounds) return;
    const {width, height} = app.screen;
    const {rest, idle} = modelBounds;
    const centerX = rest.x + rest.width / 2, centerY = rest.y + rest.height / 2;
    const idleWidth = 2 * Math.max(centerX - idle.left, idle.right - centerX);
    const idleHeight = 2 * Math.max(centerY - idle.top, idle.bottom - centerY);
    const scale = Math.min(width * .84 / rest.width, height * .86 / rest.height,
      width * .94 / idleWidth, height * .94 / idleHeight, 3);
    if (!Number.isFinite(scale) || scale <= 0) return;
    model.scale.set(scale);
    model.pivot.set(centerX, centerY);
    model.position.set(width / 2, height / 2);
  }
  function resize() {
    if (!app) return;
    const width = stage.clientWidth, height = stage.clientHeight;
    if (!width || !height) return; // 返回列表时舞台隐藏，保留上次的缓冲区尺寸。
    const sizeChanged = width !== Math.round(app.screen.width) || height !== Math.round(app.screen.height);
    const pixelRatio = getPixelRatio();
    if (sizeChanged || app.renderer.resolution !== pixelRatio) {
      app.renderer.resolution = pixelRatio;
      app.renderer.resize(width, height);
      if (sizeChanged) fit();
    }
  }
  function watchPixelRatio() {
    window.matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`).addEventListener("change", () => {
      resize();
      watchPixelRatio();
    }, {once:true});
  }
  function clear() {
    token++;drag=null;motions=[];expressions=[];modelBounds=null;
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
    const id = current.id;
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
    let loaded;
    try {
      if (!app) {
        // Canvas 之前固定为 1x 缓冲区，浏览器/系统缩放后被拉伸会进一步模糊。
        // 使用物理像素密度匹配视口，2x 上限防止 4K 屏显存开销失控；
        // WebGL 坐标仍使用 CSS 逻辑像素，不改变动画骨骼的构图比例。
        const pixelRatio = getPixelRatio();
        app=new PIXI.Application({
          view:canvas,
          width:Math.max(1,stage.clientWidth),
          height:Math.max(1,stage.clientHeight),
          resolution:pixelRatio,
          autoDensity:true,
          transparent:true,
          antialias:true
        });
        watchPixelRatio();
      }
      loaded = await PIXI.live2d.Live2DModel.from("../data/" + id + "/model.json",
        {autoInteract:false,autoUpdate:false});
      if (requestId!==token) {loaded.destroy();return;}
      let bounds = boundsById.get(id);
      if (!bounds) {
        const manager = loaded.internalModel.motionManager;
        const idle = manager.settings.motions?.idle?.length ? await manager.loadMotion("idle", 0) : null;
        if (requestId!==token) {loaded.destroy();return;}
        bounds = measureModelBounds(loaded, idle);
        boundsById.set(id, bounds);
      }
      model = loaded;
      modelBounds = bounds;
      resize();
      fit();
      model.update(1);
      model.autoUpdate = true;
      app.stage.addChild(model);
      const settings=model.internalModel?.settings||{};
      motions=Object.keys(settings.motions||{});
      expressions=(settings.expressions||[]).map(item=>item.name).filter(Boolean);
      buttons($("actions"),motions,play,"可播放动作");
      buttons($("expressions"),expressions,expression,"可切换表情");
      if (motions.includes("idle")) play("idle");
      status("");
      window.GalleryViewerBridge?.refresh();
    } catch(error) {
      if (loaded && loaded !== model) loaded.destroy();
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
  new ResizeObserver(resize).observe(stage);
  window.addEventListener("resize",resize);
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
