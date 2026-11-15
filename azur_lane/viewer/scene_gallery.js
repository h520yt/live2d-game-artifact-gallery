/* 碧蓝航线静态皮肤场景：使用本地已解包素材，不替换官方原图。 */
(function (root) {
  "use strict";
  const VARIANT = new Set(["n", "rw", "hx", "g", "ex", "hd", "bh", "h", "p", "d"]);
  const BG = new Set(["bj", "bg", "back"]);
  const FRONT = new Set(["front", "middle", "mid", "effect", "light"]);
  const imageCache = new Map();
  let currentCharacter = null;
  let scenes = [];
  let currentScene = null;
  let renderSerial = 0;
  let exportReady = false;
  let bound = false;

  const byId = id => document.getElementById(id);

  function roleOf(tokens) {
    if (tokens.some(t => BG.has(t.replace(/[0-9]+$/, "")))) return "background";
    if (tokens.some(t => FRONT.has(t.replace(/[0-9]+$/, "")))) return "foreground";
    return "";
  }

  function assetBase(c) {
    if (c.asset) return c.asset;
    const parts = String(c.rep || "").split("_");
    while (parts.length > 1 && VARIANT.has(parts[parts.length - 1])) parts.pop();
    return parts.join("_");
  }

  function parseItem(item, base) {
    if (item.name !== base && !item.name.startsWith(base + "_")) return null;
    const rest = item.name === base ? [] : item.name.slice(base.length + 1).split("_");
    return { item, flags: rest.filter(token => VARIANT.has(token)), role: roleOf(rest) };
  }

  function buildScenes(c) {
    const base = assetBase(c);
    const parsed = (c.items || []).map(it => parseItem(it, base)).filter(Boolean);
    const figures = parsed.filter(p => !p.role && p.item.kind !== "part");
    const parts = parsed.filter(p => !!p.role);

    return figures.map(figure => {
      const allowed = new Set(figure.flags);
      const compatible = parts.filter(p => p.flags.every(flag => allowed.has(flag)));
      const bestFor = role => compatible.filter(p => p.role === role)
        .sort((a, b) => b.flags.length - a.flags.length || a.item.name.localeCompare(b.item.name))[0];
      return {
        name: figure.item.name, figure: figure.item,
        background: (bestFor("background") || {}).item || null,
        foreground: (bestFor("foreground") || {}).item || null,
      };
    });
  }

  function preferredScene(c) {
    const list = buildScenes(c);
    return list.find(s => s.name === c.rep && s.background)
      || list.find(s => s.background)
      || list.find(s => s.name === c.rep)
      || list[0] || null;
  }

  function decorateCard(card, c) {
    const chosen = preferredScene(c);
    if (!chosen || !chosen.background) return card;
    const thumb = card.querySelector(".thumb");
    const figure = thumb && thumb.querySelector("img");
    if (!thumb || !figure) return card;
    figure.src = chosen.figure.path;
    figure.classList.add("scene-figure-preview");
    const bg = document.createElement("img");
    bg.className = "scene-background-preview";
    bg.alt = "";
    bg.loading = "lazy";
    bg.src = chosen.background.path;
    bg.onerror = () => { bg.remove(); thumb.classList.remove("has-scene-preview"); };
    thumb.insertBefore(bg, thumb.firstChild);
    thumb.classList.add("has-scene-preview");
    const marker = document.createElement("span");
    marker.className = "scene-ready-mark";
    marker.textContent = "场景预览";
    thumb.appendChild(marker);
    return card;
  }

  function loadImage(path) {
    if (!path) return Promise.resolve(null);
    if (!imageCache.has(path)) {
      imageCache.set(path, new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error("无法加载资源：" + path));
        img.src = path;
      }));
    }
    return imageCache.get(path);
  }

  function goodBounds(bounds) {
    return bounds && ["minX", "minY", "maxX", "maxY"].every(k => Number.isFinite(bounds[k]))
      && bounds.maxX > bounds.minX && bounds.maxY > bounds.minY;
  }

  function positionFor(bounds, union, factor) {
    return {
      x: (bounds.minX - union.minX) * factor,
      y: (union.maxY - bounds.maxY) * factor,
      w: (bounds.maxX - bounds.minX) * factor,
      h: (bounds.maxY - bounds.minY) * factor
    };
  }

  function settings() {
    return {
      scale: Number(byId("scene-scale").value) / 100,
      dx: Number(byId("scene-offset-x").value) / 100,
      dy: Number(byId("scene-offset-y").value) / 100,
      front: byId("scene-show-front").checked
    };
  }

  function drawScene(scene, images) {
    const canvas = byId("scene-canvas");
    const ctx = canvas.getContext("2d");
    const layers = [
      { item: scene.background, img: images[0] },
      { item: scene.figure, img: images[1] },
      { item: scene.foreground, img: images[2] }
    ].filter(layer => layer.item && layer.img);
    const hasBg = Boolean(scene.background && images[0]);
    const useBounds = hasBg && layers.every(layer => goodBounds(layer.item.bounds));
    const opt = settings();
    let width, height, placements;
    if (useBounds) {
      const bb = layers.reduce((u, layer) => ({
        minX: Math.min(u.minX, layer.item.bounds.minX),
        minY: Math.min(u.minY, layer.item.bounds.minY),
        maxX: Math.max(u.maxX, layer.item.bounds.maxX),
        maxY: Math.max(u.maxY, layer.item.bounds.maxY)
      }), { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });
      const worldW = bb.maxX - bb.minX, worldH = bb.maxY - bb.minY;
      const factor = Math.min(1, 2400 / Math.max(worldW, worldH));
      width = Math.max(1, Math.round(worldW * factor));
      height = Math.max(1, Math.round(worldH * factor));
      placements = layers.map(layer => positionFor(layer.item.bounds, bb, factor));
    } else {
      const background = images[0] || images[1];
      const factor = Math.min(1, 2400 / Math.max(background.naturalWidth, background.naturalHeight));
      width = Math.max(1, Math.round(background.naturalWidth * factor));
      height = Math.max(1, Math.round(background.naturalHeight * factor));
      placements = layers.map(layer => {
        if (layer.item === scene.background) return { x: 0, y: 0, w: width, h: height };
        if (layer.item === scene.foreground) return { x: 0, y: 0, w: width, h: height };
        const ratio = Math.min(width * 0.98 / layer.img.naturalWidth, height * 0.94 / layer.img.naturalHeight);
        const w = layer.img.naturalWidth * ratio, h = layer.img.naturalHeight * ratio;
        return { x: (width - w) / 2, y: (height - h) / 2, w, h };
      });
    }
    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);
    layers.forEach((layer, index) => {
      if (layer.item === scene.foreground && !opt.front) return;
      const p = placements[index];
      if (layer.item === scene.figure) {
        const w = p.w * opt.scale, h = p.h * opt.scale;
        const x = p.x + (p.w - w) / 2 + opt.dx * width;
        const y = p.y + (p.h - h) / 2 + opt.dy * height;
        ctx.drawImage(layer.img, x, y, w, h);
      } else {
        ctx.drawImage(layer.img, p.x, p.y, p.w, p.h);
      }
    });
    return { hasBg, useBounds };
  }

  async function render() {
    if (!currentScene) return;
    const serial = ++renderSerial;
    exportReady = false;
    byId("scene-export").disabled = true;
    byId("scene-notice").textContent = "正在组合场景素材…";
    const items = [currentScene.background, currentScene.figure, currentScene.foreground];
    const resolved = await Promise.all(items.map(it => it ? loadImage(it.path).catch(() => null) : Promise.resolve(null)));
    if (serial !== renderSerial) return;
    if (!resolved[1]) {
      byId("scene-canvas").width = 1;
      byId("scene-canvas").height = 1;
      byId("scene-notice").textContent = "人物 PNG 不可用，请重新安装或检查本地文件。";
      return;
    }
    try {
      const outcome = drawScene(currentScene, resolved);
      exportReady = outcome.hasBg;
      byId("scene-export").disabled = !exportReady;
      const message = !currentScene.background
        ? "未发现与该形态匹配的专属背景；当前仅展示人物。可重新运行安装脚本补齐场景素材。"
        : !outcome.hasBg
          ? "已索引背景，但文件加载失败。请重新安装背景并刷新资源清单。"
          : outcome.useBounds
            ? "已组合人物＋背景，按解包 Mesh 坐标初步对齐；请与游戏原场景核对。"
            : "已组合人物＋背景。原始图层缺少共同坐标，当前是自动排版；可调节人物位置和比例后导出。";
      const frontMessage = currentScene.foreground && !resolved[2] ? " 前景文件加载失败。" : "";
      byId("scene-notice").textContent = message + frontMessage;
    } catch (error) {
      byId("scene-notice").textContent = "场景绘制失败：" + error.message;
      byId("scene-export").disabled = true;
    }
  }

  function setMode(mode) {
    const sceneMode = mode === "scene";
    byId("scene-area").hidden = !sceneMode;
    byId("detail-grid").hidden = sceneMode;
    byId("scene-options").hidden = !sceneMode;
    document.querySelectorAll("#detail-modes [data-mode]").forEach(btn => {
      btn.classList.toggle("on", btn.dataset.mode === mode);
    });
    if (sceneMode) render();
  }

  function chooseFigure(name) {
    currentScene = scenes.find(s => s.name === name) || scenes[0] || null;
    byId("scene-scale").value = 100;
    byId("scene-offset-x").value = 0;
    byId("scene-offset-y").value = 0;
    byId("scene-show-front").checked = true;
    if (currentScene) render();
  }

  function init() {
    if (bound) return;
    bound = true;
    document.querySelectorAll("#detail-modes [data-mode]").forEach(btn => {
      btn.onclick = () => setMode(btn.dataset.mode);
    });
    byId("scene-figure-select").onchange = e => chooseFigure(e.target.value);
    ["scene-scale", "scene-offset-x", "scene-offset-y", "scene-show-front"].forEach(id => {
      byId(id).oninput = () => {
        if (currentScene && !byId("scene-area").hidden) render();
      };
    });
    byId("scene-reset").onclick = () => {
      if (currentScene) chooseFigure(currentScene.name);
    };
    byId("scene-export").onclick = () => {
      if (!exportReady || !currentScene) return;
      const filename = currentScene.name.replace(/[^a-zA-Z0-9_-]/g, "_") + "_scene.png";
      byId("scene-canvas").toBlob(blob => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1500);
      }, "image/png");
    };
  }

  function open(c) {
    init();
    currentCharacter = c;
    scenes = buildScenes(c);
    const select = byId("scene-figure-select");
    select.replaceChildren();
    scenes.forEach(scene => {
      const option = document.createElement("option");
      option.value = scene.name;
      option.textContent = scene.name + (scene.background ? " · 有背景" : " · 缺背景");
      select.appendChild(option);
    });
    const preferred = preferredScene(c);
    if (preferred) {
      select.value = preferred.name;
      chooseFigure(preferred.name);
    } else {
      currentScene = null;
      byId("scene-notice").textContent = "没有可合成的角色主立绘，请查看原始素材。";
      byId("scene-export").disabled = true;
    }
    setMode(scenes.length ? "scene" : "raw");
  }

  const api = { buildScenes, preferredScene, decorateCard, open };
  root.AzurSceneGallery = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
