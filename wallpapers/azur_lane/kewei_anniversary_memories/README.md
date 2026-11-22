# 可畏 · 纪念印记

《碧蓝航线》的可畏换装「纪念印记」（Anniversary Memories），本地 Live2D 模型 `kewei_6`，皮肤 ID `207055`。截图里的动作面板与该模型的 45 个动作一一对应，其中包含 11 个 `idle` 变体、19 个 `touch_idle` 变体和 `effect`。壁纸播放截图所选的 `idle5`，以原速的三分之一静音循环，每轮约 60 秒。

## 导入 Wallpaper Engine

打开「壁纸编辑器」，将本目录的 `index.html` 拖到「创建壁纸」，等待画面加载后保存并应用。导入时 Wallpaper Engine 会复制本目录内的文件。也可以直接双击 `index.html` 在支持 WebGL 的浏览器里离线预览。[Wallpaper Engine 官方网页壁纸导入说明](https://docs.wallpaperengine.io/en/web/first/gettingstarted.html)

## 画面和资源

- 根据参考截图取景，人物居中，画面保留膝部和两侧画框。不同宽高比下等比取景，画布随窗口和显示缩放调整，像素预算为 3840 × 2160。
- 保留原模型的绘制顺序、两张 4096 × 4096 原始贴图、物理效果和 `idle5` 动作。运行库和模型数据都在本目录内，支持 `file://` 离线播放。
- 默认最高 30 FPS，并服从 Wallpaper Engine 中更低的 FPS 设置。`preview.jpg` 是实际渲染的 3840 × 2160 预览。
- 如需重新打包，在仓库根目录运行 `python wallpapers/tools/build-kewei.py`。构建脚本读取本地 `azur_lane/data/models/kewei_6/` 和 `shared/vendor/`，生成 `model.bundle.js` 并复制运行库。

## 验证

本机 Wallpaper Engine 2.8.42 的独立预览已确认画面和动画。Chrome 离线验证通过 4K、高 DPI、超宽构图、两个完整循环、限帧和暂停恢复检查。包内五份模型数据与源文件逐字节一致。验证覆盖独立预览，编辑器保存和桌面挂载未实测。
