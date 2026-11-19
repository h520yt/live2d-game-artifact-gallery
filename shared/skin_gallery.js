/* 统一皮肤画廊：只负责卡片、搜索、排序、详情覆盖层与原位返回。
 * 任何游戏专有的 Live2D / Spine / 互动状态都应由 onOpen 实现。 */
(function (global) {
  "use strict";
  function create(config) {
    const root = config.grid;
    const search = config.search;
    const sort = config.sort;
    const count = config.count;
    const detail = config.detail;
    if (!root || !search || !detail || typeof config.onOpen !== "function") {
      throw new Error("SkinGallery requires grid, search, detail and onOpen");
    }
    let all = [], visible = [], selectedKey = null, returnScroll = 0;
    let lastButton = null;
    const collator = new Intl.Collator("zh-CN", {numeric:true,sensitivity:"base"});

    function itemKey(item) { return String(item.key); }
    function render() {
      const query = search.value.trim().toLocaleLowerCase();
      visible = all.filter(item =>
        !query || [item.title,item.subtitle,item.key,item.searchText].some(
          text => String(text ?? "").toLocaleLowerCase().includes(query)
        ));
      if (sort?.value === "name") {
        visible.sort((a,b) => collator.compare(String(a.title),String(b.title)));
      } else if (sort?.value === "installed") {
        visible.sort((a,b) => Number(!!b.ready) - Number(!!a.ready));
      }
      root.replaceChildren();
      for (const item of visible) {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "sg-card";
        card.dataset.key = itemKey(item);
        card.dataset.ready = String(!!item.ready);
        card.setAttribute("aria-label", String(item.title) + " " + String(item.subtitle || ""));
        const preview = document.createElement("div");
        preview.className = "sg-card-preview";
        const fallback = document.createElement("div");
        fallback.className = "sg-card-placeholder";
        fallback.textContent = item.ready ? "暂无完整场景预览" : "素材待安装";
        const src = item.preview;
        // 只加载当前游戏本地数据。不能把未组合的人物图集、背景当成场景成图。
        if (typeof src === "string" && /^\.\.\/data\/(?!.*(?:\.\.|\\|[?#]))[a-zA-Z0-9_./%-]+$/.test(src)) {
          const img = document.createElement("img");
          img.alt = item.title + " · 场景封面";
          img.loading = "lazy";
          img.decoding = "async";
          img.onerror = () => { img.remove(); preview.append(fallback); };
          img.src = src;
          preview.append(img);
        } else {
          preview.append(fallback);
        }
        const meta = document.createElement("div");
        meta.className = "sg-card-meta";
        const title = document.createElement("div");
        title.className = "sg-card-title";
        title.textContent = item.title || item.key;
        const subtitle = document.createElement("div");
        subtitle.className = "sg-card-sub";
        subtitle.textContent = item.subtitle || "";
        const state = document.createElement("div");
        state.className = "sg-card-state";
        state.textContent = item.status || (item.ready ? "点击查看" : "待安装");
        meta.append(title, subtitle, state);
        card.append(preview, meta);
        card.addEventListener("click", () => open(itemKey(item), card));
        root.append(card);
      }
      if (count) count.textContent = visible.length + " 套 / 共 " + all.length + " 套";
    }
    function setItems(items) {
      const map = new Map();
      for (const row of items || []) {
        if (!row || row.key === undefined || row.key === null) continue;
        map.set(itemKey(row),row);
      }
      all = [...map.values()];
      render();
    }
    function open(key, trigger = null) {
      const row = all.find(item => itemKey(item) === String(key));
      if (!row) return false;
      if (detail.hidden) {
        returnScroll = window.scrollY;
        lastButton = trigger || root.querySelector("[data-key='" + CSS.escape(String(key)) + "']");
      }
      selectedKey = String(key);
      detail.hidden = false;
      document.body.classList.add("sg-detail-open");
      const result = config.onOpen(row, selectedKey);
      if (result === false) {
        detail.hidden = true;
        document.body.classList.remove("sg-detail-open");
        return false;
      }
      return true;
    }
    function close() {
      if (detail.hidden) return;
      detail.hidden = true;
      document.body.classList.remove("sg-detail-open");
      if (typeof config.onClose === "function") config.onClose();
      // 背景目录从未移除 DOM；返回时不会重新渲染卡片或播放滚动动画。
      if (Math.abs(window.scrollY - returnScroll) > 1) {
        window.scrollTo({top:returnScroll,behavior:"instant"});
      }
      if (lastButton?.isConnected) lastButton.focus({preventScroll:true});
    }
    function navigate(offset) {
      const index = visible.findIndex(item => itemKey(item) === selectedKey);
      if (index < 0 || !visible.length) return false;
      const next = visible[(index + offset + visible.length) % visible.length];
      return open(itemKey(next));
    }
    search.addEventListener("input",render);
    if (sort) sort.addEventListener("change",render);
    document.addEventListener("keydown",event => {
      if (event.key === "Escape" && !detail.hidden) {
        if (typeof config.onEscape === "function" && config.onEscape(event) === true) return;
        event.preventDefault();close();
      }
    });
    return {setItems,open,close,navigate,render,get visible(){return visible.slice();},get selectedKey(){return selectedKey;}};
  }
  global.SkinGallery = Object.freeze({create});
})(window);
