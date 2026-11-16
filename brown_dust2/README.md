# 棕色尘埃2 · Prestige Skin 尊爵皮肤首批

本模块接入最高规格的 **Prestige Skin** 外观系列，并非普通五星战斗服装。首批共六款：尤丝缇亚 Hot Summer Dream、泰瑞丝 Milky Bikini、洁尼斯 Stranger Bunny、莉贝尔塔 Hedonist、莎赫拉查德 Deliberate Ace、尤里 Forever Mascot。

资源目录来自 myssal/Brown-Dust-2-Asset；前四款角色、技能、互动模型路径有明确映射，后两款角色和技能路径已确认，互动场景尚未建立对应关系，因此不会虚构对应动作。

## Windows PowerShell 运行

1. 在项目根目录先执行 git pull origin main。
2. 检查资源计划：python brown_dust2/scripts/install_prestige.py --plan（默认 raw 模式，不调用 GitHub API；不估算总字节）
3. 下载本批：python brown_dust2/scripts/install_prestige.py
4. 离线核验：python brown_dust2/scripts/install_prestige.py --verify
5. 启动服务：python -m http.server 8000

打开 http://127.0.0.1:8000/brown_dust2/viewer/index.html 。

支持仅安装某款：python brown_dust2/scripts/install_prestige.py --only justia-hot-summer-dream（其它 ID 见 curated_prestige.json）。下载中断可重跑，文件大小匹配时会跳过。**修复 GitHub API 403 rate limit：** 默认直接从 raw.githubusercontent.com 读取 atlas 并据此获取全部贴图，无需 GitHub API Token；旧脚本报 403 后，更新代码并重跑即可，已存在的非空本地文件会跳过。

确实需要上游子目录内的附加素材时可以选择 `--source api`，但它会调用 GitHub Contents API，需配置环境变量 `GITHUB_TOKEN`（注意保护令牌，勿写入代码）。`--source raw` 仅下载 atlas、skel 与 atlas 引用的贴图，不会自动下载技能演出 `bg/` 中不在 atlas 中的附加背景。

## 展示范围

* Spine 4.1 动态角色、技能演出、已定位的互动动画，支持动作选择、切换和 PNG 当前帧导出。
* 完整性检查要求 skel、atlas、atlas 引用的全部 PNG 均真实存在，缺一不进入网页已安装清单。
* 资源只下载到 brown_dust2/data/，代码仓库不追踪游戏美术文件；版权归游戏权利人所有。
* 技能动画的附加背景、复杂分层、音频、秘密剧情及全部游戏触摸逻辑暂未完整还原。PNG 是当前画布截图，不保证等价于官方静态原画。

测试：python -m unittest discover -s brown_dust2/tests -v

## 黑屏、白块及模型光边排查（2026-11-16）

互动动画并非简单的独立动作：`mixN_*` 通常需要第 0 轨播放 `idleN`，第 1 轨播放对应 `mixN_*`；`idle1`、`idle2` 必须循环。
本模块的 Spine 播放器已修复：
- 优先选择包含完整部件的 Skin，右侧可以手动选择 Skin 并重置取景；
- 在当前展示柜的 WebGL 贴图上传时按混合模式设置 `UNPACK_PREMULTIPLY_ALPHA_WEBGL`，减轻因 Alpha 方式不一致产生的发光边、白边及色彩错误；
- 增加「透明边缘」设置：**预乘 Alpha**（默认）和**普通 Alpha**，可对比不同导出批次，不修改原图；
- 互动 `mixN_*` 使用两轨组合，其它独立动作仍能正常播放；
- 播放错误在状态栏显示，已安装和未安装提示不再混淆。

测试步骤：
1. 运行 `git pull origin main`，然后刷新 `http://127.0.0.1:8000/brown_dust2/viewer/index.html`（Ctrl+Shift+R）。
2. 进入「尤丝缇亚 → 互动动画」并选 `idle1`，从「模型部件」菜单中选择显示内容最完整的一套；再尝试 `mix1_1`。
3. 如仍有白边，将「透明边缘」切换为「普通 Alpha（对比）」以核实两种贴图透明模式；选择项只保存在浏览器本地，**无需重新下载资源**。
4. 点击「重置视图」。如果图片仍存在黑色遮挡或显示不全，请收集 F12 控制台报错和对应 Skin 名称；这时需要进一步核验图集图片本身、插槽、或更复杂的动画轨道组合。

> 目前已覆盖 WebGL 混合、Skin 选择、双轨播放与摄像机配置的代码及自动测试；由于游戏原始素材不存储在 GitHub，此次提交不能替代你的本机真实模型视觉验收。若源图集本身异常，单纯切换 Alpha 无法完全修复。

### 2026-11-16：修复 `Unable to render skeleton` / `<empty>`

若上版更新后出现黑屏，并报 `Cannot read properties of undefined (reading '<empty>')`，原因是新添加的 `viewport` 配置缺失动画映射。现在撤销了初始化时的 1×1 占位 `viewport` 和重置镜头时对 `player.config.viewport` 的覆盖，继续使用 SpinePlayer 原生动画视口与独立相机取景；不需重新下载资源。


### 2026-11-16：互动场景太小 / 黑边占据画面

原先相机根据整个骨骼测量边界，包括大的黑色背景和遮挡部件；一些互动场景中实际画面只有中央一小块。本次不再用更改 `viewport` 的方式缩放（避免上版 `<empty>` 错误），而是：

- 互动场景启动并播放动画后，从当前画布采样实际非黑内容的范围，按场景短边优先、最大 7 倍的限制做智能放大，画面尽量填充视口；
- 增加 **智能铺满** 按钮，可在动画不同帧重新聚焦；**缩放** 滑块支持 1–8 倍进一步调整；
- 相机状态在 Spine 每帧更新时保持，画布可拖拽平移、鼠标滚轮缩放；
- 重置视图恢复初始取景并重新识别内容，不修改素材、Skin 或底层动画 `viewport`；
- 算法保护空白帧/近黑动画：若没有足够可见像素则保留原相机，不盲目放大。

修改后 `git pull origin main`，刷新浏览器即可；无需重新下载已有素材。


### 尤里「永恒吉祥物」完整资源映射（2026-11-16）

已核对上游 `myssal/Brown-Dust-2-Asset` 与 `Jelosus2/BD2-L2D-Viewer` 的角色目录：

- 人物：`spine/char/char065193`
- 技能骨骼：`spine/cutscenes/cutscene_char065193`
- **互动骨骼**：`spine/illust/illust_dating/illust_dating21`，包含 13 张 atlas 引用贴图，使用互动双轨动画
- 技能附加背景：`spine/cutscenes/cutscene_char065193/bg/` 的 5 张 PNG

执行 `python brown_dust2/scripts/install_prestige.py --only yuri-forever-mascot` 后，安装器会只补缺失文件并重建 manifest。附加背景会下载到 `data/yuri-forever-mascot/cutscene/bg`，当前播放器仍可能需要后续场景合成支持才能展示这些独立背景。原 `char065193` 和 `cutscene_char065193` 编号正确，无需替换。

### 2026-11-16：大屏预览与完整人物适配

针对「预览窗口过小、人物放大后被裁剪」调整：

- 普通页面改为窄角色列表（约 240–300px）和更高的舞台（约 73% 浏览器高度），把空间优先留给画面。
- 点击右上角 **大屏预览 ⛶**，打开占满浏览器窗口的沉浸式展示；按 **Esc** 或「退出大屏」返回。切换时会重建 SpinePlayer，以适应 WebGL 真实画布尺寸，并尽量恢复上次选择的 Skin 和动作。
- **完整适配**：根据骨骼边界适配整个角色。人物动态会尝试排除巨大背景插槽，保持约 12% 安全留白；不再额外运行可能裁掉四肢的像素聚焦。
- **智能铺满**：仍专用于互动动画的黑底缩放。需要完整画面时先点击「完整适配」，而不是反复增大缩放。
- 缩放滑块支持 **50%～500%**，可以缩小并找回被裁掉的部分；仍可拖动平移。
- 本次只修改前端布局与相机计算，不调整 SpinePlayer 的内部 `viewport` 配置，不需要重新下载素材。

自动测试只能验证布局与相机逻辑；实际全身显示效果还需要在浏览器中确认。
