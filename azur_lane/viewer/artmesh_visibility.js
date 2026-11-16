/* Live2D 可逆图层控制：针对 qiye_10 / idle9 等动作的前景遮挡。
 * 不修改模型资源；仅在 Cubism 更新后覆盖选中 ArtMesh 的可见度。
 * 图层 ID 依赖真实模型，不能由截图推断，候选需要用户在本机逐项预览。
 */
(function (global) {
  "use strict";

  const STORAGE_KEY = "azurlane.artmesh.hidden.v1";
  const MAX_LIST = 80;
  const states = new WeakMap();
  let active = null;
  let layerRoot = null;
  let listMode = "likely";
  let query = "";

  function storedRules() {
    try {
      const obj = JSON.parse(global.localStorage.getItem(STORAGE_KEY) || "{}");
      return obj && typeof obj === "object" && !Array.isArray(obj) ? obj : {};
    } catch (_e) {
      return {};
    }
  }

  function ruleKey(name, motion) {
    return name + "::" + (motion || "default");
  }

  function readHidden(name, motion) {
    const ids = storedRules()[ruleKey(name, motion)];
    return new Set(Array.isArray(ids) ? ids.filter(x => typeof x === "string") : []);
  }

  function saveHidden(name, motion, hidden) {
    try {
      const rules = storedRules();
      const key = ruleKey(name, motion);
      if (hidden.size) rules[key] = Array.from(hidden);
      else delete rules[key];
      global.localStorage.setItem(STORAGE_KEY, JSON.stringify(rules));
      return true;
    } catch (_e) {
      return false;
    }
  }

  function rectangle(vertices) {
    if (!vertices || vertices.length < 6) return null;
    let left = Infinity, right = -Infinity, top = Infinity, bottom = -Infinity;
    for (let i = 0; i < vertices.length - 1; i += 2) {
      const x = Number(vertices[i]);
      const y = Number(vertices[i + 1]);
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      left = Math.min(left, x);
      right = Math.max(right, x);
      top = Math.min(top, y);
      bottom = Math.max(bottom, y);
    }
    if (!Number.isFinite(left) || right <= left || bottom <= top) return null;
    return { left, right, top, bottom, area: (right - left) * (bottom - top) };
  }

  function inspect(core) {
    if (!core || typeof core.getDrawableCount !== "function") return [];
    const ids = core.getDrawableIds() || [];
    const orders = core.getDrawableRenderOrders() || [];
    const result = [];
    const n = core.getDrawableCount();
    for (let i = 0; i < n; i++) {
      const rect = rectangle(core.getDrawableVertexPositions(i));
      if (!rect) continue;
      const opacity = Number(core.getDrawableOpacity(i)) || 0;
      const visible = typeof core.getDrawableDynamicFlagIsVisible === "function"
        ? !!core.getDrawableDynamicFlagIsVisible(i) : true;
      result.push({
        index: i,
        id: String(ids[i] || ("ArtMesh#" + i)),
        order: Number(orders[i]) || 0,
        opacity,
        visible,
        rect,
        areaRatio: 0,
        foregroundCandidate: false,
        score: 0,
      });
    }
    if (!result.length) return [];
    // 用可见图层的整体坐标范围归一化面积，不依赖模型实际像素尺寸。
    const visible = result.filter(x => x.visible && x.opacity > 0.05);
    const bounds = visible.length ? visible : result;
    const left = Math.min(...bounds.map(x => x.rect.left));
    const right = Math.max(...bounds.map(x => x.rect.right));
    const top = Math.min(...bounds.map(x => x.rect.top));
    const bottom = Math.max(...bounds.map(x => x.rect.bottom));
    const whole = Math.max((right - left) * (bottom - top), 1);
    const minOrder = Math.min(...bounds.map(x => x.order));
    const maxOrder = Math.max(...bounds.map(x => x.order));
    const range = Math.max(maxOrder - minOrder, 1);
    for (const row of result) {
      row.areaRatio = Math.min(row.rect.area / whole, 1);
      const layerIsFront = (row.order - minOrder) / range >= 0.65;
      const isLarge = row.areaRatio >= 0.035;
      const named = /leaf|leaves|tree|plant|front|foliage|grass|bush|mask|qian|yezi|zhiwu/i.test(row.id);
      row.foregroundCandidate = row.visible && row.opacity > 0.12
        && ((layerIsFront && isLarge) || (named && row.areaRatio >= 0.007));
      row.score = (row.order - minOrder) / range * 2
        + Math.sqrt(row.areaRatio) * 1.5 + (named ? 1 : 0);
    }
    return result;
  }

  function likelyForeground(rows, limit) {
    const n = typeof limit === "number" ? limit : 6;
    return rows.filter(x => x.foregroundCandidate)
      .sort((a, b) => b.score - a.score)
      .slice(0, Math.max(0, n));
  }

  function coreState(model, name) {
    if (states.has(model)) return states.get(model);
    const internal = model && model.internalModel;
    const core = internal && internal.coreModel;
    const raw = core && core._model && core._model.drawables;
    const opacities = raw && raw.opacities;
    if (!core || !opacities || typeof core.getDrawableIds !== "function") return null;
    const ids = Array.from(core.getDrawableIds());
    const indexById = new Map(ids.map((id, i) => [String(id), i]));
    const state = {
      name,
      core,
      opacities,
      indexById,
      motion: null,
      hidden: readHidden(name, null),
      prior: new Map(),
      // 在显示/隐藏切换时恢复先前透明度；常规参数由 Cubism 自己继续计算。
      restore() {
        for (const [index, value] of this.prior) this.opacities[index] = value;
        this.prior.clear();
      },
      apply() {
        for (const [index, value] of Array.from(this.prior)) {
          const id = String(ids[index]);
          if (!this.hidden.has(id)) {
            this.opacities[index] = value;
            this.prior.delete(index);
          }
        }
        for (const id of this.hidden) {
          const index = this.indexById.get(id);
          if (index === undefined || index >= this.opacities.length) continue;
          if (!this.prior.has(index)) this.prior.set(index, this.opacities[index]);
          this.opacities[index] = 0;
        }
      },
      activate(motion) {
        this.restore();
        this.motion = motion || null;
        this.hidden = readHidden(this.name, this.motion);
        this.apply();
      },
      updateHidden(idsToHide) {
        this.hidden = new Set(idsToHide);
        this.apply();
        return saveHidden(this.name, this.motion, this.hidden);
      },
    };
    // 原本的全屏遮罩修复可能已包装过 update；这里继续串接而不替换旧逻辑。
    const previous = internal.update.bind(internal);
    internal.update = function (delta, now) {
      const result = previous(delta, now);
      state.apply();
      return result;
    };
    states.set(model, state);
    return state;
  }

  function escapeText(text) {
    return String(text).replace(/[&<>"']/g, ch => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[ch]));
  }

  function draw() {
    if (!layerRoot) return;
    layerRoot.replaceChildren();
    if (!active) return;
    const toggle = global.document.createElement("button");
    toggle.type = "button";
    toggle.className = "layer-tools-toggle";
    toggle.textContent = "前景图层 · " + active.hidden.size + " 隐藏";
    const panel = global.document.createElement("div");
    panel.className = "layer-tools-panel";
    const opened = layerRoot.dataset.open === "true";
    panel.hidden = !opened;
    toggle.onclick = () => {
      layerRoot.dataset.open = opened ? "false" : "true";
      draw();
    };
    layerRoot.append(toggle, panel);
    if (!opened) return;

    const scope = global.document.createElement("div");
    scope.className = "layer-scope";
    scope.textContent = active.name + " / " + (active.motion || "默认姿态");
    const intro = global.document.createElement("p");
    intro.textContent = "优先检查大片前景叶片。点击图层“隐藏”可实时对比，关闭不会改动模型原文件。";
    panel.append(scope, intro);
    const controls = global.document.createElement("div");
    controls.className = "layer-tools-actions";
    const filter = global.document.createElement("button");
    filter.type = "button";
    filter.textContent = listMode === "likely" ? "显示全部图层" : "只看前景候选";
    filter.onclick = () => { listMode = listMode === "likely" ? "all" : "likely"; query = ""; draw(); };
    const tryHide = global.document.createElement("button");
    tryHide.type = "button";
    tryHide.textContent = "试隐藏前景";
    tryHide.title = "仅隐藏最靠前的大面积候选；可能误伤人物，可立即恢复";
    tryHide.onclick = () => {
      const candidates = likelyForeground(inspect(active.core), 4);
      active.updateHidden([...active.hidden, ...candidates.map(x => x.id)]);
      draw();
    };
    const reset = global.document.createElement("button");
    reset.type = "button";
    reset.textContent = "全部恢复";
    reset.onclick = () => { active.updateHidden([]); draw(); };
    controls.append(filter, tryHide, reset);
    panel.append(controls);
    const input = global.document.createElement("input");
    input.type = "search";
    input.className = "layer-tools-search";
    input.placeholder = "搜索 ArtMesh ID 或序号";
    input.value = query;
    input.oninput = () => { query = input.value; updateList(panel); };
    panel.append(input);
    const notice = global.document.createElement("small");
    notice.className = "layer-tools-note";
    notice.textContent = "建议在 qiye_10 播放 idle9 后操作；自动候选只是辅助，误隐藏请点“恢复”。";
    panel.append(notice);
    const list = global.document.createElement("div");
    list.className = "layer-tools-list";
    panel.append(list);
    updateList(panel);
  }

  function updateList(panel) {
    const list = panel.querySelector(".layer-tools-list");
    if (!list || !active) return;
    list.replaceChildren();
    const all = inspect(active.core);
    // 选中过的层始终可见，方便恢复；不因为当前帧不可见而丢失。
    const candidates = all.filter(x => active.hidden.has(x.id)
      || (listMode === "all" ? x.visible : x.foregroundCandidate));
    candidates.sort((a, b) => {
      if (active.hidden.has(a.id) !== active.hidden.has(b.id)) return active.hidden.has(a.id) ? -1 : 1;
      return b.score - a.score;
    });
    const matched = candidates.filter(x => !query.trim()
      || (x.id + " " + x.index).toLowerCase().includes(query.trim().toLowerCase()));
    const label = global.document.createElement("div");
    label.className = "layer-tools-count";
    label.textContent = "找到 " + matched.length + " 层，显示前 " + MAX_LIST + " 层";
    list.append(label);
    for (const item of matched.slice(0, MAX_LIST)) {
      const line = global.document.createElement("div");
      line.className = "layer-tools-item";
      const isHidden = active.hidden.has(item.id);
      const details = global.document.createElement("span");
      details.title = item.id;
      details.textContent = "#" + item.index + " " + item.id
        + " · 前后序 " + item.order
        + " · 面积 " + (item.areaRatio * 100).toFixed(1) + "%";
      const button = global.document.createElement("button");
      button.type = "button";
      button.textContent = isHidden ? "恢复" : "隐藏";
      button.className = isHidden ? "is-hidden" : "";
      button.onclick = () => {
        const next = new Set(active.hidden);
        if (isHidden) next.delete(item.id); else next.add(item.id);
        active.updateHidden(next);
        updateList(panel);
        const top = layerRoot.querySelector(".layer-tools-toggle");
        if (top) top.textContent = "前景图层 · " + active.hidden.size + " 隐藏";
      };
      line.append(details, button);
      list.append(line);
    }
    if (!matched.length) {
      const empty = global.document.createElement("p");
      empty.textContent = "没有候选；切换“显示全部图层”后，可逐项检查并隐藏。";
      list.append(empty);
    }
  }

  function mount(model, name, rootId) {
    layerRoot = global.document.getElementById(rootId);
    if (!layerRoot) return false;
    layerRoot.dataset.open = "false";
    listMode = "likely";
    query = "";
    active = coreState(model, name);
    if (active) active.activate(null); // 缓存模型再次打开时恢复默认动作作用域
    draw();
    return !!active;
  }

  function setMotion(model, motion) {
    const state = states.get(model);
    if (!state) return;
    state.activate(motion);
    if (state === active) draw();
  }

  function clearPanel() {
    active = null;
    if (layerRoot) layerRoot.replaceChildren();
  }

  global.AzurArtmeshVisibility = {
    mount,
    setMotion,
    clearPanel,
    inspect,
    likelyForeground,
    readHidden,
    ruleKey
  };
})(typeof window !== "undefined" ? window : globalThis);
