/* 统一展示柜查看器协议 v1。仅提供同页导航/状态控制，永不加载远程脚本。 */
(function (global) {
  "use strict";
  const PARAM = "gallery_asset";
  const ACTION_PARAM = "gallery_motion";
  const ROLE_PARAM = "gallery_role";
  const MAX_ID_LENGTH = 180;
  let adapter = null;
  let request = null;
  let busy = false;
  let playingPending = false;
  let statusElement = null;
  let roleSelect = null;
  let actionSelect = null;

  function parseRequest(search) {
    const params = new URLSearchParams(search || "");
    const id = params.get(PARAM);
    if (!id || id.length > MAX_ID_LENGTH || /[\u0000-\u001f\u007f/\\?#]/.test(id)) return null;
    const role = params.get(ROLE_PARAM);
    const motion = params.get(ACTION_PARAM);
    return {
      id,
      role: role && role.length <= MAX_ID_LENGTH ? role : null,
      motion: motion && motion.length <= MAX_ID_LENGTH ? motion : null,
    };
  }

  function safeNames(items) {
    if (!Array.isArray(items)) return [];
    return [...new Set(items.filter((x) => typeof x === "string" && x.length > 0 && x.length <= MAX_ID_LENGTH))];
  }

  function create(tag, className, label) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (label !== undefined) element.textContent = label;
    return element;
  }

  function setStatus(message) {
    if (statusElement) statusElement.textContent = message;
  }

  function replaceOptions(select, items, placeholder) {
    const value = select.value;
    select.replaceChildren();
    const empty = create("option", "", placeholder);
    empty.value = "";
    select.append(empty);
    items.forEach((item) => {
      const option = create("option", "", item);
      option.value = item;
      select.append(option);
    });
    if (items.includes(value)) select.value = value;
  }

  function getActions() {
    if (!adapter || typeof adapter.listActions !== "function") return [];
    try { return safeNames(adapter.listActions()); }
    catch (error) { console.warn("Gallery bridge action list failed", error); return []; }
  }

  function getRoles() {
    if (!adapter || typeof adapter.listRoles !== "function") return [];
    try { return safeNames(adapter.listRoles()); }
    catch (error) { console.warn("Gallery bridge role list failed", error); return []; }
  }

  async function call(method, value) {
    if (!adapter || typeof adapter[method] !== "function") return false;
    try { return await adapter[method](value) !== false; }
    catch (error) {
      console.warn("Gallery viewer bridge action failed", error);
      setStatus("操作失败：" + (error.message || String(error)));
      return false;
    }
  }

  function refresh() {
    if (!adapter || !roleSelect || !actionSelect) return;
    const roles = getRoles();
    const actions = getActions();
    const oldRole = roleSelect.value;
    const oldAction = actionSelect.value;
    replaceOptions(roleSelect, roles, "选择姿态／资源类型");
    replaceOptions(actionSelect, actions, "选择动作");
    roleSelect.disabled = !roles.length;
    actionSelect.disabled = !actions.length;
    if (roles.includes(oldRole)) roleSelect.value = oldRole;
    if (actions.includes(oldAction)) actionSelect.value = oldAction;
    if (request && request.motion && !playingPending && actions.includes(request.motion)) {
      const name = request.motion;
      request.motion = null;
      playingPending = true;
      call("playAction", name).then((ok) => {
        playingPending = false;
        if (ok) {
          actionSelect.value = name;
          setStatus("已加载资源 · 播放动作 " + name);
        }
      });
    }
  }

  function mountToolbar() {
    if (document.getElementById("gallery-bridge-toolbar")) return;
    const style = create("style");
    style.textContent = "#gallery-bridge-toolbar{position:fixed;bottom:14px;left:14px;z-index:99998;max-width:min(650px,calc(100vw - 28px));box-sizing:border-box;display:flex;align-items:center;flex-wrap:wrap;gap:7px;padding:10px 12px;background:#101924f0;color:#edf3fa;border:1px solid #53677d;border-radius:12px;box-shadow:0 14px 38px #0009;font:12px/1.5 system-ui,'Microsoft YaHei',sans-serif}#gallery-bridge-toolbar button,#gallery-bridge-toolbar select,#gallery-bridge-toolbar a{font:inherit;color:inherit;background:#203046;border:1px solid #546b82;border-radius:6px;padding:6px 9px;max-width:230px}#gallery-bridge-toolbar a{text-decoration:none}#gallery-bridge-toolbar button{cursor:pointer}#gallery-bridge-toolbar .gb-status{flex-basis:100%;color:#b6c9da;overflow-wrap:anywhere}#gallery-bridge-toolbar select:disabled{opacity:.55}";
    document.head.append(style);
    const bar = create("aside");
    bar.id = "gallery-bridge-toolbar";
    bar.setAttribute("aria-label", "统一展示柜操作");
    const home = create("a", "", "← 资源总目录");
    home.href = "../../gallery/";
    bar.append(home);
    roleSelect = create("select");
    roleSelect.setAttribute("aria-label", "姿态或资源类型");
    roleSelect.onchange = async () => {
      const role = roleSelect.value;
      if (!role) return;
      setStatus("正在切换：" + role);
      await call("selectRole", role);
      refresh();
    };
    bar.append(roleSelect);
    actionSelect = create("select");
    actionSelect.setAttribute("aria-label", "播放动作");
    actionSelect.onchange = async () => {
      const name = actionSelect.value;
      if (!name) return;
      const ok = await call("playAction", name);
      if (ok) setStatus("播放动作：" + name);
    };
    bar.append(actionSelect);
    const hide = create("button", "", "收起");
    hide.type = "button";
    const compact = create("button", "", "展开统一控制");
    compact.type = "button";
    compact.hidden = true;
    hide.onclick = () => {
      roleSelect.hidden = true;
      actionSelect.hidden = true;
      statusElement.hidden = true;
      hide.hidden = true;
      compact.hidden = false;
    };
    compact.onclick = () => {
      roleSelect.hidden = false;
      actionSelect.hidden = false;
      statusElement.hidden = false;
      hide.hidden = false;
      compact.hidden = true;
    };
    bar.append(hide, compact);
    statusElement = create("span", "gb-status", request ? "正在定位：" + request.id : "统一资源操作台");
    statusElement.setAttribute("role", "status");
    bar.append(statusElement);
    document.body.append(bar);
    refresh();
  }

  async function openInitial() {
    if (!request || !adapter || busy) return;
    busy = true;
    try {
      const id = request.id;
      const ok = await call("open", id);
      if (!ok) {
        setStatus("未找到资源：" + id + "。可返回目录刷新索引或检查本地安装。");
        return;
      }
      setStatus("已定位：" + id + "。如动作仍在加载，请查看原游戏操作台。");
      if (request.role) {
        const role = request.role;
        const roles = getRoles();
        request.role = null;
        if (roles.includes(role)) await call("selectRole", role);
      }
      refresh();
    } finally {
      busy = false;
    }
  }

  function register(config) {
    if (!config || typeof config.open !== "function" || !/^[a-z0-9_]+$/.test(config.game || "")) {
      throw new Error("Gallery bridge requires a game id and open function");
    }
    if (adapter && adapter.game !== config.game) throw new Error("Gallery bridge already registered");
    adapter = config;
    request = parseRequest(global.location && global.location.search);
    mountToolbar();
    refresh();
    if (request) return openInitial();
    return Promise.resolve();
  }

  global.GalleryViewerBridge = Object.freeze({
    version: 1,
    register,
    refresh,
    parseRequest,
    get game() { return adapter ? adapter.game : null; },
  });
})(window);
