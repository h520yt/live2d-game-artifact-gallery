/* 碧蓝航线 Live2D：同一皮肤的普通模型与 _hx 形态只占一张卡片。
 * 纯数据工具，不修改原 manifest，也不删除任何模型文件。 */
(function (global) {
  "use strict";

  /**
   * 只有 _hx 的基础模型真实存在，并且皮肤 ID 与名称一致，才归并为一个皮肤。
   * 缺失基础模型或元数据不一致时保留独立卡片，避免合错角色。
   */
  function groupModels(models) {
    if (!Array.isArray(models)) return [];
    const byName = new Map(models.map((model) => [model.name, model]));
    const groups = [];
    const byKey = new Map();

    for (const model of models) {
      const isHx = typeof model.name === "string" && model.name.endsWith("_hx");
      const baseName = isHx ? model.name.slice(0, -3) : model.name;
      const base = isHx ? byName.get(baseName) : model;
      const paired = isHx && base &&
        model.id === base.id && model.en === base.en;
      const key = paired ? baseName : model.name;

      let group = byKey.get(key);
      if (!group) {
        const primary = paired ? base : model;
        group = {
          name: primary.name,
          en: primary.en,
          id: primary.id,
          rel: primary.rel,
          ver: primary.ver,
          cover: primary.cover,
          variants: [],
        };
        byKey.set(key, group);
        groups.push(group);
      }
      group.variants.push(model);
    }

    for (const group of groups) {
      group.variants.sort((a, b) => {
        if (a.name === group.name) return -1;
        if (b.name === group.name) return 1;
        return a.name.localeCompare(b.name, undefined, { numeric: true });
      });
    }
    return groups;
  }

  /** 筛选 Cubism 版本时优先打开对应形态；默认打开普通版。 */
  function preferredModel(group, version = "") {
    if (!group || !Array.isArray(group.variants) || !group.variants.length) {
      return null;
    }
    if (version !== "") {
      const matching = group.variants.find((model) => String(model.ver) === String(version));
      if (matching) return matching;
    }
    return group.variants[0];
  }

  function groupForModel(groups, modelName) {
    return groups.find((group) => group.variants.some((model) => model.name === modelName)) || null;
  }

  const api = Object.freeze({ groupModels, preferredModel, groupForModel });
  global.AzurModelVariants = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window === "undefined" ? globalThis : window);
