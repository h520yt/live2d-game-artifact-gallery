/* 画廊内页的位置恢复工具。
 * 模型舞台使用 display:none 隐藏长列表，浏览器会压缩 scrollY；
 * 记录入口位置并在列表重新布局后恢复，避免返回时跳到顶部。
 */
(function (global) {
  "use strict";

  const positions = new Map();

  /** 进入模型舞台或图片详情前保存当前页面位置。 */
  function remember(key) {
    if (!key) return;
    positions.set(key, {
      x: Math.max(0, global.scrollX || global.pageXOffset || 0),
      y: Math.max(0, global.scrollY || global.pageYOffset || 0),
    });
  }

  /** 先恢复被隐藏的列表，再等待浏览器完成布局后恢复原始坐标。 */
  function restore(key) {
    const position = positions.get(key);
    if (!position) return false;
    global.requestAnimationFrame(() => {
      global.scrollTo(position.x, position.y);
    });
    return true;
  }

  /** 新筛选或重新开始浏览时可以清除旧的保存状态。 */
  function clear(key) {
    positions.delete(key);
  }

  global.AzurGalleryScroll = Object.freeze({ remember, restore, clear });
})(typeof window !== "undefined" ? window : globalThis);
