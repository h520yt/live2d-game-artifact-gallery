# Sylvia · Bikini Agent · 4K 左右镜像动态壁纸

本目录是可独立导入 Wallpaper Engine 的 **Web Wallpaper**。仅制作 **3840 × 2160、16:9** 一个版本，自动循环、无交互、无声音。页面仅显示动态画面，没有展示柜菜单、按钮、标题、提示或调试面板。可以直接双击 `index.html` 离线预览，不需要启动 Python、Node 或 HTTP 服务。

## 实际使用的资源

本地 `brown_dust2/costume_catalog.json` 与 `brown_dust2/viewer/manifest.json` 共同确认：

| 项目 | 实际值 |
| --- | --- |
| 游戏 / 角色 | Brown Dust 2 / Sylvia |
| 服装 / ID | Bikini Agent / `costume-001006` |
| 分类 | Fated Guest，独立互动动画 `interaction` |
| 上游路径标识 | `spine/illust/illust_dating/illust_dating8` |
| 本地来源目录 | `D:\project_python\live2d-game-artifact-gallery\brown_dust2\data\costume-001006\interaction\` |
| 骨骼 | `assets/illust_dating8.skel`，Spine **4.1.11** |
| 图集 | `assets/illust_dating8.atlas` |
| 贴图 | `assets/illust_dating8.png`、`illust_dating8_2.png` 至 `illust_dating8_6.png`，共 **6 张** |
| Skin | **`default`**；该骨骼唯一 Skin，478 个附件 |
| 动画 | **`idle1`**，轨道 0，`loop=true`，原速 1 倍，周期 **2 秒** |
| 其他动作 | 不播放 idle2 / idle3，不播放 mix，不建立动作队列，不随机切换 |

**最终使用 idle1。** 它能够独立稳定循环并显示目标床上横躺场景，无需额外基础轨道。`idle2` 和 `idle3` 虽然存在，但没有启用。

8 个资源文件（骨骼、图集、6 张 PNG）均保留原始字节，SHA-256 和大小见 `assets-manifest.json`。5 张图集为 2048 × 2048，最后一张为 2048 × 1024。原始美术没有重绘、超分或变形；4K 指输出画布与构图尺寸。

## 复用的播放逻辑与离线加载

- `js/spine-player4.1.js` 是本项目 `shared/vendor/spine-player4.1.js` 的完整、字节一致副本，使用完整 SpinePlayer，未另写简化播放器。
- `js/wallpaper.js` 直接保留展示柜的 `idleSceneKey`、`skinForAnimation`、`applySkin` 函数；同名 / 同分组 / default 的匹配规则一致。idle1 按原选择动作流程清除轨道并循环播放。
- 沿用展示柜的 PMA 像素上传和混合设置，保留原始骨骼、插槽顺序、网格、裁剪与图集 UV；本场景没有隐藏背景或人物槽位。
- `js/assets.bundle.js` 将上述原始资源嵌入 Data URI，通过现有 SpinePlayer 的 `rawDataURIs` 加载接口使用。HTML、CSS、脚本全部使用目录内相对路径，资源键与图集页面名一致。
- `assets/` 保留原件供校验；播放只读取 bundle，不会再次加载原件。不依赖展示柜页面、项目根目录、联网资源、CDN 或本地服务。CSP 禁止网络连接。

## 镜像与 4K 构图

最终渲染容器使用 CSS **`transform: scaleX(-1)`**，围绕中心镜像完整画布。**头在右边，腿在左边**。骨骼缩放、骨骼方向、贴图坐标及动画数据均保持原值，避免负骨骼缩放影响蒙皮、裁剪与附件。

相机在加载时对完整 idle1 周期采样 65 个姿态，统计头发、脸、手臂、手和腿部的运动边界，等比适配至画布约 91% 宽度，并保留两端余量。固定镜头中心约 `(-79.3954, -64.4912)`、zoom 约 `1.043061`。不逐帧追踪人物，不会因呼吸反复缩放。

画面保留头部、上半身、双手、腿部与脚趾；裁去外围多余的室内上下空间，床铺与真实室内背景填满 16:9。没有横向拉伸、纯黑边栏、模糊背景层或背景拼接。`preview.png` 是实际 **3840 × 2160** 渲染截图。

## 性能与稳定性

- 一个 WebGL 上下文、一套 SpinePlayer、6 张图集纹理，只初始化和上传一次；加载后释放 Data URI 索引。
- 内部画布固定 3840 × 2160，Windows 200% DPI 下不会扩大到 8K。仅针对 16:9 4K 桌面交付。
- 默认最高 30 FPS，接受 Wallpaper Engine 更低的全局帧率设置；低帧率仍按真实时间推进动画。
- 支持 Wallpaper Engine 的暂停 / 恢复回调；暂停后不继续更新骨骼或绘制 WebGL。
- 不生成 mipmaps，不保留绘图缓冲，不在播放循环中读取像素、重算取景或重新请求资源。
- 原始 RGBA 图集理论容量约 **88 MiB**，单个 4K RGBA 颜色缓冲约 **31.6 MiB**；这不是实测总显存，浏览器与驱动还会占用额外资源。

## 导入 Wallpaper Engine

1. 保持本目录完整。打开 Wallpaper Engine 的「壁纸编辑器」。
2. 将**本目录的 `index.html`** 拖入「创建壁纸 / Create Wallpaper」，按网页类型导入。
3. 检查预览，保存项目并应用到 3840 × 2160 显示器。目录内已有 Web 类型 `project.json` 和 `preview.png`。
4. 导入会复制文件到 Wallpaper Engine 的 `projects/myprojects/`。此后若修改源目录，需要同步或重新导入复制后的项目。

只选择本目录，不要选择整个展示柜仓库。`verification/` 是开发验证记录与脚本，不参与播放。

官方导入说明：<https://docs.wallpaperengine.io/en/web/first/gettingstarted.html>

官方暂停与全局帧率回调：<https://docs.wallpaperengine.io/en/web/api/propertylistener.html>

## 已完成的测试与验证边界

具体结果见 `verification/RESULTS.md`，原始记录见该目录 JSON。测试包括原始资源与 bundle 校验、完整循环姿态采样、离线 file:// 运行、4K 画布、镜像像素对照、无 UI、暂停恢复、帧率限制、持续循环与独立目录搬移。

**尚未在 Wallpaper Engine 内实机验证**：编辑器导入与保存、其 CEF 内核实际播放、桌面挂载、真实宿主暂停策略、多小时播放、休眠唤醒和显卡驱动恢复。浏览器通过与回调模拟不等同于 Wallpaper Engine 实机通过。性能结果也不是目标设备显存或 GPU 占用测量。

如需在原仓库重新验证，可从仓库根目录运行（这些开发命令不参与壁纸运行）：

```powershell
python wallpapers/brown_dust2/sylvia_bikini_agent_4k_mirrored/verification/build.py
python wallpapers/brown_dust2/sylvia_bikini_agent_4k_mirrored/verification/check-package.py
node wallpapers/brown_dust2/sylvia_bikini_agent_4k_mirrored/verification/check-pose.cjs
node wallpapers/brown_dust2/sylvia_bikini_agent_4k_mirrored/verification/verify.cjs
python wallpapers/brown_dust2/sylvia_bikini_agent_4k_mirrored/verification/check-images.py
```

代码仅放在本独立目录，未修改原展示柜，没有自动提交 Git。游戏美术与 Spine 运行库的权利归原权利人。
