"use strict";

(() => {
  const GAMES = Object.freeze({
    azur_lane: { title: "碧蓝航线", viewer: "../azur_lane/viewer/index.html" },
    nikke: { title: "NIKKE", viewer: "../nikke/viewer/index.html" },
    reverse1999: { title: "重返未来：1999", viewer: "../reverse1999/viewer/index.html" },
    brown_dust2: { title: "棕色尘埃2", viewer: "../brown_dust2/viewer/index.html" },
  });
  const STATUS = Object.freeze({
    entrypoints_present: "入口文件齐全",
    partial: "入口部分缺失",
    missing: "入口文件缺失",
    no_entrypoints: "无核查入口",
    not_checked: "尚未核查",
  });
  const PAGE_SIZE = 48;
  const FAVORITES_KEY = "gallery-favorites-v1";
  const collator = new Intl.Collator("zh-CN", { numeric: true, sensitivity: "base" });
  const byId = (id) => document.getElementById(id);

  const controls = {
    search: byId("search"),
    game: byId("game"),
    renderer: byId("renderer"),
    tag: byId("tag"),
    status: byId("status"),
    favoritesOnly: byId("favorites-only"),
    sort: byId("sort"),
  };
  const state = {
    assets: [],
    statuses: new Map(),
    favorites: loadFavorites(),
    visibleLimit: PAGE_SIZE,
  };

  function loadFavorites() {
    try {
      const value = JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]");
      return new Set(Array.isArray(value) ? value.filter((id) => typeof id === "string") : []);
    } catch {
      return new Set();
    }
  }

  function saveFavorites() {
    try {
      localStorage.setItem(FAVORITES_KEY, JSON.stringify([...state.favorites]));
    } catch {
      showMessage("浏览器禁止保存本地收藏。本次页面打开期间仍可以继续使用收藏筛选。");
    }
  }

  function showMessage(text) {
    const box = byId("message");
    box.hidden = false;
    box.textContent = text;
  }

  function hideMessage() {
    const box = byId("message");
    box.hidden = true;
    box.textContent = "";
  }

  function safePreviewPath(raw) {
    if (typeof raw !== "string" || !raw || raw.startsWith("/") ||
        raw.includes("\\") || raw.includes("..") || raw.includes("://")) {
      return null;
    }
    return "../" + raw.split("/").map(encodeURIComponent).join("/");
  }

  function makeElement(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined && text !== null) el.textContent = String(text);
    return el;
  }

  function fillOptions(select, values) {
    for (const value of values) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.append(option);
    }
  }

  function initializeFilters() {
    for (const [id, info] of Object.entries(GAMES)) {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = info.title;
      controls.game.append(option);
    }
    const tags = new Set();
    for (const asset of state.assets) {
      for (const tag of asset.tags || []) {
        if (typeof tag === "string" && tag.trim()) tags.add(tag);
      }
    }
    fillOptions(controls.tag, [...tags].sort(collator.compare));
  }

  function isFavorite(asset) {
    return state.favorites.has(asset.id);
  }

  function statusFor(asset) {
    return state.statuses.get(asset.id) || "not_checked";
  }

  function selectAssets() {
    const query = controls.search.value.trim().toLocaleLowerCase();
    const filtered = state.assets.filter((asset) => {
      if (controls.game.value && asset.game !== controls.game.value) return false;
      if (controls.renderer.value && asset.renderer !== controls.renderer.value) return false;
      if (controls.tag.value && !(asset.tags || []).includes(controls.tag.value)) return false;
      if (controls.status.value && statusFor(asset) !== controls.status.value) return false;
      if (controls.favoritesOnly.checked && !isFavorite(asset)) return false;
      const metadata = asset.metadata || {};
      const fields = [
        asset.id, asset.source_id, asset.title,
        metadata.character, metadata.skin_id, ...(asset.tags || []),
      ];
      return !query || fields.some((value) => String(value ?? "").toLocaleLowerCase().includes(query));
    });

    filtered.sort((left, right) => {
      if (controls.sort.value === "favorites") {
        const difference = Number(isFavorite(right)) - Number(isFavorite(left));
        if (difference) return difference;
      }
      if (controls.sort.value === "title") {
        return collator.compare(left.title || "", right.title || "");
      }
      return collator.compare(left.game || "", right.game || "") ||
        collator.compare(left.title || "", right.title || "");
    });
    return filtered;
  }

  function makeCard(asset) {
    const info = GAMES[asset.game];
    const card = makeElement("article", "card");
    const media = makeElement("div", "card-media");
    const fallback = makeElement("div", "media-fallback", asset.preview ? "本地预览未就绪" : "暂无独立预览图");
    media.append(fallback);
    const imgPath = safePreviewPath(asset.preview);
    if (imgPath) {
      const picture = document.createElement("img");
      picture.src = imgPath;
      picture.alt = String(asset.title || asset.source_id) + " 的本地预览";
      picture.loading = "lazy";
      picture.decoding = "async";
      picture.hidden = true;
      picture.addEventListener("load", () => {
        picture.hidden = false;
        fallback.hidden = true;
      });
      picture.addEventListener("error", () => {
        picture.remove();
        fallback.hidden = false;
      }, { once: true });
      media.append(picture);
    }
    card.append(media);

    const body = makeElement("div", "card-body");
    const heading = makeElement("div", "card-game");
    heading.append(makeElement("span", "", info.title));
    heading.append(makeElement("span", "status", STATUS[statusFor(asset)] || "尚未核查"));
    body.append(heading);
    body.append(makeElement("h3", "card-title", asset.title));
    body.append(makeElement("div", "card-id", asset.source_id));
    const tags = makeElement("div", "tags");
    const labels = Array.isArray(asset.tags) ? asset.tags : [];
    for (const label of labels.slice(0, 5)) {
      tags.append(makeElement("span", "tag", label));
    }
    if (!labels.length) tags.append(makeElement("span", "tag", asset.renderer || "未知格式"));
    body.append(tags);
    card.append(body);

    const actions = makeElement("div", "card-actions");
    const link = makeElement("a", "open-link", "进入游戏查看器");
    link.href = info.viewer;
    link.title = "进入" + info.title + "专属查看器，按资源 ID 搜索：" + asset.source_id;
    actions.append(link);
    const favorite = makeElement("button", "fav-button", isFavorite(asset) ? "★ 已收藏" : "☆ 收藏");
    favorite.type = "button";
    favorite.setAttribute("aria-pressed", String(isFavorite(asset)));
    favorite.setAttribute("aria-label", (isFavorite(asset) ? "取消收藏 " : "收藏 ") + asset.title);
    favorite.addEventListener("click", () => {
      if (state.favorites.has(asset.id)) state.favorites.delete(asset.id);
      else state.favorites.add(asset.id);
      saveFavorites();
      render();
    });
    actions.append(favorite);
    card.append(actions);
    return card;
  }

  function render() {
    const filtered = selectAssets();
    const cards = byId("cards");
    const page = filtered.slice(0, state.visibleLimit);
    const fragment = document.createDocumentFragment();
    page.forEach((asset) => fragment.append(makeCard(asset)));
    cards.replaceChildren(fragment);
    byId("total-count").textContent = state.assets.length.toLocaleString();
    byId("game-count").textContent = new Set(state.assets.map((item) => item.game)).size;
    byId("visible-count").textContent = filtered.length.toLocaleString();
    byId("favorite-count").textContent = state.favorites.size;
    byId("result-text").textContent = "匹配 " + filtered.length + " 项 · 当前显示 " + page.length + " 项";
    byId("pagination").hidden = page.length >= filtered.length;
    if (!filtered.length) showMessage("没有符合当前条件的资源。可以调整关键词、游戏和标签筛选。");
    else hideMessage();
  }

  function bindEvents() {
    for (const control of Object.values(controls)) {
      const eventType = control === controls.search ? "input" : "change";
      control.addEventListener(eventType, () => {
        state.visibleLimit = PAGE_SIZE;
        render();
      });
    }
    byId("load-more").addEventListener("click", () => {
      state.visibleLimit += PAGE_SIZE;
      render();
    });
    byId("reset-filters").addEventListener("click", () => {
      controls.search.value = "";
      controls.game.value = "";
      controls.renderer.value = "";
      controls.tag.value = "";
      controls.status.value = "";
      controls.favoritesOnly.checked = false;
      controls.sort.value = "game";
      state.visibleLimit = PAGE_SIZE;
      render();
    });
  }

  async function fetchJson(path, optional = false) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (!response.ok) throw new Error("HTTP " + response.status);
      return await response.json();
    } catch (error) {
      if (optional) return null;
      throw error;
    }
  }

  async function initialize() {
    bindEvents();
    try {
      const catalog = await fetchJson("./catalog.json");
      if (catalog.schema_version !== 1 || !Array.isArray(catalog.assets)) {
        throw new Error("统一索引版本不匹配或格式不正确");
      }
      state.assets = catalog.assets.filter((item) => item &&
        typeof item.id === "string" && typeof item.game === "string" &&
        GAMES[item.game] && typeof item.source_id === "string");
      const verification = await fetchJson("./verification-report.json", true);
      if (verification && Array.isArray(verification.items)) {
        for (const item of verification.items) {
          if (item && typeof item.id === "string" && typeof item.status === "string") {
            state.statuses.set(item.id, item.status);
          }
        }
      }
      initializeFilters();
      render();
    } catch (error) {
      byId("result-text").textContent = "尚未加载统一资源目录";
      showMessage("无法读取统一资源索引（" + error.message +
        "）。请在项目根目录执行 python scripts/gallery.py sync-index，再运行 python -m http.server 8000，" +
        "然后访问 http://127.0.0.1:8000/gallery/ 。不要直接双击 HTML 文件。");
    }
  }

  initialize();
})();
