# 温塔娜 · 温泉修行者 · 4K 动态壁纸

本目录是独立的 Wallpaper Engine **Web Wallpaper**，直接播放本地原始 Spine 骨骼，不是视频，也不需要 Python、Node、HTTP 服务或互联网。可先双击 `index.html` 查看离线画面。

## 导入 Wallpaper Engine

1. 保持本目录完整，不要只复制 HTML，也不要选择整个展示柜项目。
2. 打开 Wallpaper Engine，点击左下角「壁纸编辑器」。
3. 在编辑器首页，把本目录的 `index.html` 拖入「创建壁纸」，选择 Web / 网页类型并填写名称。
4. Wallpaper Engine 会把目录复制到自己的 `projects/myprojects/`。等待贴图加载后，保存项目，再选择「应用壁纸」。
5. 在 **3840 × 2160、16:9** 显示器上查看。壁纸内部始终使用 3840 × 2160 WebGL 画布；Windows 的 150% / 200% 缩放不会让它重复渲染成 8K。

若只希望临时播放，也可从 Wallpaper Engine 的「打开壁纸 → 打开离线壁纸」选择 `index.html`。编辑器导入会创建独立副本；今后更新源目录后需同步到该副本。

官方导入说明：https://docs.wallpaperengine.io/en/web/first/gettingstarted.html

## 固定场景配置

| 项目 | 配置 |
| --- | --- |
| 游戏 / 角色 | Brown Dust 2 / Ventana |
| 服装 / ID | Onsen Practitioner / `costume-067004` |
| 原始路径 | `spine/illust/illust_dating/illust_dating15` |
| 骨骼版本 / 运行库 | Spine 4.1.11 / 原项目 `shared/vendor/spine-player4.1.js` 的完整副本 |
| Skin | **`default`**（该骨骼唯一 Skin，共 458 个附件；不存在名为 idle2 的 Skin） |
| 基础轨道 0 | **`idle2`，loop=true**，原始时长约 5.333333 秒 |
| 播放速度 | **4/9 倍速**，在上次 2/3 倍速基础上再慢三分之一，实际约 **12 秒 / 周期** |
| 其它轨道 | 空；无 mix 动作、随机切换或动作队列 |
| WebGL 画布 | **3840 × 2160**，人物 X/Y 等比缩放 |
| 帧率 | 默认最多 30 FPS；服从 Wallpaper Engine 更低的全局 FPS 设置 |
| Alpha | PMA 混合 + `UNPACK_PREMULTIPLY_ALPHA_WEBGL=true`，两者一致 |
| 操作 / 声音 | 无鼠标互动、触摸、菜单、音频或调试界面 |

默认采用 **单幅画面等比铺满（cover）**，真实场景填满 3840 × 2160，不显示左右模糊边栏，也不横向拉伸人物。通过上移镜头，保留人物头部、手部、腿部、被褥主体、房间与窗外月夜；裁去上下多余的天花板、地面和前景被褥。原始近竖幅场景无法同时完整保留所有边缘并填满 16:9，因此默认优先铺满。

需要查看原先的完整边缘构图时，可打开 `index.html?framing=contain`；这个备用模式保留全部场景边界并在左右模糊延展。默认 cover 不加载或合成延展图片，只有一个 WebGL 上下文和一套 Spine。

相机在 Skin 和 idle2 正确应用后，对完整循环采样 65 个姿态，固定边界，避免呼吸时镜头反复缩放。默认铺满镜头中心约 `(1.6121, 150)`，zoom 约 `0.829617`，相对原完整适配放大约 1.46 倍；完整边界及实际参数见 `verification/browser-cover-test.json`。

原模型 `FR` 附件的几何尺寸约 **22687 × 18434**，明显大于房间的约 3205 × 2605。本壁纸只在「槽名为 FR 且实测尺寸超过 10000」时将其运行时透明度置零，并排除在相机边界之外，防止异常前景遮挡和缩成小图。其它背景、人物和被褥保持原样；原始骨骼与贴图文件没有修改。边缘使用正确 PMA 上传，避免黑边和错误发亮。

## 离线资源与性能

- `assets/`：原始 `.skel`、`.atlas` 和 **7 张 2048 × 2048 PNG 图集**，全部与展示柜已下载文件 SHA-256 一致。
- `assets.bundle.js`：上述资源的 Data URI 包，使用原播放器 `rawDataURIs` 加载机制。它使严格的 `file://` 浏览器也不需要 XHR、网络服务或额外启动参数。
- 原始文件和 bundle 在磁盘上有意各保留一份，供完整交付与校验；**运行时只读取 bundle，不再请求 assets/ 文件**。每页只上传一次，共 7 个 Spine 图集纹理。加载后释放 Data URI 索引，不持续保留多套加载器或播放器。
- 七张原始 RGBA 图集的理论 GPU 纹理容量约 **112 MiB**；单张 4K RGBA 颜色缓冲约 **31.6 MiB**。驱动、抗锯齿、浏览器合成缓冲和静态延展背景另占内存；这些数值不是实测总显存。
- 不生成 mipmaps，不保留绘图缓冲，不在循环中读取像素或重新计算场景边界。暂停时停止骨骼更新及 WebGL 绘制，并支持恢复。
- `preview.png` / `preview.jpg`：**3840 × 2160 实际渲染截图**；`scene-backdrop.jpg` 只用于模糊背景延展。

**4K 是输出画布与构图尺寸，不代表原始游戏画作具有原生 4K 清晰度。** 原始 2048 图集未进行 AI 超分、重绘或纹理拉伸替换。

## 验证范围

最终结果见 `verification/RESULTS.md`。浏览器离线与持续循环检查、Wallpaper Engine 原生预览检查、编辑器导入/保存、桌面实际挂载分别记录，不把普通浏览器测试作为编辑器验收。

验证脚本在仓库的 `wallpapers/tools/`，不参与壁纸播放：

```powershell
python wallpapers/tools/build-ventana.py
node wallpapers/tools/inspect-ventana.cjs
node wallpapers/tools/verify-ventana.cjs
```

构建器只使用现有本地素材，网络请求为零。浏览器验证使用项目现有 Playwright 和系统 Chrome。不要在 Wallpaper Engine 中选中 `wallpapers/tools/` 或仓库根目录进行导入。

## 文件与来源

`index.html`、`wallpaper.css`、`wallpaper.js` 是独立壁纸代码；没有修改原展示柜。`assets-manifest.json` 记录 9 个原始文件的大小与 SHA-256。`vendor/spine-player4.1.js` 保留现有运行库原文件，来源为 Esoteric Software Spine；游戏美术来源为本机已下载的 Brown Dust 2 资源，权利归各原权利人。

仅在本地交付，不自动提交 Git。目录内 `.gitignore` 排除了游戏素材、嵌入包和场景图像，避免误把美术资源加入源码仓库。
