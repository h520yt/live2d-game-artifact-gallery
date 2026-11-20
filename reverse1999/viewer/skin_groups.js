/* 1999 画廊的角色级关联：当前仅佩施塔的两个同角色资源合并一张封面。
 * 与原始资源 manifest 分离；其余皮肤维持“一件衣着一张卡片”的既有规则。
 */
(function (global) {
  "use strict";

  function mergePerchta(rows, models) {
    const originalRows = Array.isArray(rows) ? rows : [];
    const inputModels = Array.isArray(models) ? models : [];
    const relevantRows = originalRows.filter(row => ["315901", "315902"].includes(String(row.key)));
    if (!relevantRows.length) return originalRows.slice();

    const perchtas = inputModels.filter(model =>
      ["315901", "315902"].includes(String(model.id)));
    const portrait = perchtas.find(model =>
      String(model.id) === "315901" && model.artwork)?.artwork || null;
    const scene = perchtas.find(model =>
      String(model.id) === "315902" &&
      model.artwork_kind === "character-scene-portrait" && model.artwork)?.artwork || null;
    const playable = perchtas.find(model =>
      String(model.id) === "315902" && model.type !== "artwork" &&
      ["cubism", "scene-live2d", "spine", "showcase", "scene"].includes(model.type)) ||
      perchtas.find(model => String(model.id) === "315901" &&
        ["cubism", "scene-live2d", "spine", "showcase", "scene"].includes(model.type)) || null;
    const fallback = playable || perchtas[0] || null;
    const row = {
      key: "315902", title: "佩施塔", subtitle: "童话出逃日 · 初始皮肤",
      searchText: "佩施塔 白雪 白雪公主 Perchta 315901 315902 童话出逃日 初始皮肤",
      ready: !!fallback,
      preview: scene || portrait || fallback?.full_scene || null,
      status: scene ? "完整场景 · 角色原画 · 动态模型" :
        portrait ? "角色原画 · 动态模型" : "动态模型",
      model: fallback,
      group: { portrait, scene, playable },
    };
    // 不额外创建分类，也不把两个衣着误认成可以随意混搭的角色/背景。
    return originalRows.filter(item =>
      !["315901", "315902"].includes(String(item.key))).concat(row);
  }

  const api = Object.freeze({ mergePerchta });
  global.Reverse1999SkinGroups = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
