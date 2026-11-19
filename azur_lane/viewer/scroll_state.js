/* 画廊滚动位置记忆。
 * 返回模型列表前同步恢复坐标：不使用 requestAnimationFrame 延迟，
 * 避免 html 的 scroll-behavior:smooth 造成可见的整页滚动。
 */
(function (global) {
  "use strict";

  const positions = new Map();

  /** 进入模型舞台或立绘详情前，保存当前窗口滚动位置。 */
  function remember(key) {
    if (!key) return;
    positions.set(key, {
      x: Math.max(0, global.scrollX || global.pageXOffset || 0),
      y: Math.max(0, global.scrollY || global.pageYOffset || 0),
    });
  }

  /** 列表恢复显示后在当前事件中立即归位，不等待下一帧，也不触发平滑滚动。 */
  function restore(key) {
    const position = positions.get(key);
    if (!position) return false;

    const root = global.document?.documentElement;
    const originalBehavior = root?.style?.scrollBehavior;
    if (root?.style) root.style.scrollBehavior = "auto";

    try {
      // CSS 根元素即使声明 smooth，也不得把“返回位置”变成滚动动画。
      global.scrollTo(position.x, position.y);
    } finally {
      if (root?.style) root.style.scrollBehavior = originalBehavior;
    }

    return true;
  }

  /** 用户主动清空筛选状态时才需要遗忘旧位置。 */
  function clear(key) {
    positions.delete(key);
  }

  global.AzurGalleryScroll = Object.freeze({ remember, restore, clear });
})(typeof window !== "undefined" ? window : globalThis);
