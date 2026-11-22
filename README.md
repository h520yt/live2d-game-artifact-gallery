# live2d-game-artifact-gallery

## 碧蓝航线 · 第九批成熟 Live2D 候选（2026-11-22）

已对照已收录的 2～8 批及 `viewer/manifest.json` 去重，第九批登记 20 条、启用 16 条安装候选、4 条因脚部/造型风险暂缓。仅核实外部 L2D/立绘资源名与皮肤元数据，鞋履与全动作尚未在本机逐项验收。

```powershell
git pull --ff-only origin main
python azur_lane/scripts/install_batch9.py --plan
python azur_lane/scripts/install_batch9.py
python scripts/gallery.py serve --port 8000
```

完整候选和验收规则：[第九批说明](azur_lane/docs/2026-11-22-batch9-mature-live2d.md)。

---


> **统一展示规范**：碧蓝航线、棕色尘埃 2、重返未来 1999 采用封面卡片→大舞台→原位返回；后续游戏脚手架直接复用 `shared/skin_gallery.css` / `shared/skin_gallery.js`，不按版本、价格或导入批次新增分类页。参见 [统一游戏画廊标准](docs/unified-game-gallery-standard.md)。


## 重返未来：1999 · 佩施塔（白雪）角色原画（2026-11-20）

已补初始衣着 `315901` 人物立绘与「童话出逃日」`315902` 的同皮肤
**角色＋原场景插画**。图片存储在本机，不随 Git 同步：

```powershell
git pull origin main
python reverse1999/scripts/sync.py character-art all
python scripts/gallery.py serve --port 8000
```

在「重返未来：1999」搜索白雪或佩施塔，打开后默认显示已安装原画，
可以切换已有的动态模型。具体说明见 [1999 模块](reverse1999/README.md)。

## 重返未来：1999 · 完整场景图（角色＋专属背景，2026-11-19）

已核对个人 fork [h520yt/Reverse-1999-CN-Asset](https://github.com/h520yt/Reverse-1999-CN-Asset)
中 `singlebg/skin2dbg` 的 **12 个皮肤 ID**，以及相同 ID 的 `live2d/roles`
模型目录。这些背景文件本身**没有人物**，因此不能直接当作完整场景图。
现有 UNIQUE 模型继续正常播放；新增本机浏览器合成截图流程，导出真正包含人物＋背景的静态 PNG。

```powershell
git pull origin main
# 一条命令：从个人 fork 补齐缺失模型，导出 12 张完整场景 PNG，并刷新索引
node reverse1999/scripts/export_full_scenes.cjs all --download --force

# 已经装好 12 套 UNIQUE 时，可省略 --download
node reverse1999/scripts/export_full_scenes.cjs all

# 当前默认导出真实 4K 3840×2160；--force 重做此前可能模糊的缓存
node reverse1999/scripts/export_full_scenes.cjs 308603 --force

# 扫描每一套的场景分辨率、背景对应关系和动态模型贴图
node reverse1999/scripts/audit_scene_quality.cjs

python scripts/gallery.py serve --port 8000
```

浏览器打开 <http://127.0.0.1:8000/gallery/>，找到“重返未来：1999”。
仅当 PNG 已实际生成且通过文件签名／尺寸校验时，卡片才显示「完整场景图」
封面；进入对应皮肤，默认显示完整场景图，可切换「Live2D 动态展示」。
没有成功合成的皮肤仍以原有模型显示，不把单独的背景冒充完整原画。
静态 PNG 保存在 `reverse1999/data/full_scenes/<皮肤ID>.png`，被 Git 忽略。

**清晰度修复**：旧版默认生成 1920×1080，现在默认使用 3840×2160 浏览器画布，且必须验证角色真实绘制像素，防止只导出背景。浏览器遇到旧版低清图会自动切到实时动态展示；重新执行 `--force` 后恢复完整场景图片。`audit_scene_quality.cjs` 只读取本机文件，不伪造任何背景。点唱机的独立角色原画不能直接当作动态模型背景；目前核实匹配的专属背景主要对应 12 套 UNIQUE。


**环境**：需 Python 以及仓库已有的 Node/Playwright 依赖，浏览器缺失可执行
`npx playwright install chromium`。首次使用 `--download` 会下载模型和背景；
图片不会随 Git 提交，不能仅靠 `git pull` 在另一台电脑获得图片。
导出使用浏览器的实际 WebGL 绘制结果；**它是本地渲染的场景组合图，不是官方直接提供的完整原画**，
也不能保证与游戏内 Unity 粒子、遮挡和镜头完全一致。未在本会话中运行本机的 12 套素材实图验收。

---


## 成熟画风筛选补充（2026-11-18）

按实际画廊反馈，今后**先筛人物整体成熟感，再筛鞋履、服装与 Live2D 动作**，
明显偏幼态的角色不进入成熟精选。第七批 `kubo_2`、`weiyan_2`，
第八批 `weiyan_4` 已排除；`ailunsamuna_2`、`linuo_3` 因
完整画风尚未复核暂缓。原始名单保留、不删除已下载模型。

当前第七批可安装精选候选 **16 款**、第八批 **19 款**；
未核实成熟感的后续新批次必须先填写 `maturity_screen` 才可进入安装流程。
详见 [成熟画风筛选规范](azur_lane/docs/mature-style-curation-policy.md)。

---

## 碧蓝航线：第八批 20 款成熟礼装与鞋履候选（2026-11-18）

已直接在 `main` 增加 [第八批 20 款候选](azur_lane/docs/2026-11-18-batch8-unified-gallery.md)：
优先成熟军装、夜间礼装、舞台/丝袜及靴类造型，排除前七批名单及当前已登记模型。
候选的 Live2D 和 painting 资源名已经过公开清单交叉核对；**鞋履外观及全部动作均尚未审核**。

```powershell
python azur_lane/scripts/install_batch8.py --plan
python azur_lane/scripts/install_batch8.py
python scripts/gallery.py serve --port 8000
```

安装后只进入原有 Live2D 模型及立绘画廊，不新增批次页面或主导航。
本地报告在 `azur_lane/data/batch8-install-report.json`，不会把“模型齐全”标为“鞋履已通过”。

---

## 碧蓝航线：统一展示与第七批候选（2026-11-18）

碧蓝航线原 Live2D 查看器顶部已移除第五、第六批的专题入口。
今后所有新批次都进入已有 **Live2D 模型 / 立绘画廊**，不再为每批创建单独的展示页。

第七批初步筛选 20 个不与前六批及仓库当前 manifest 重复的皮肤资源名，
覆盖运动系、丝袜、兔女郎、夜间礼装、制服等方向。
公开 L2D 和 painting 哈希清单均能检索到对应资源，
但**鞋履是否包脚、各触摸动作是否露脚仍待本地人工验收**。

```powershell
python azur_lane/scripts/install_batch7.py --plan
python azur_lane/scripts/install_batch7.py
python scripts/gallery.py serve --port 8000
```

安装过程复用既有下载/解包/校验流程，`batch7-install-report.json`
仅确认模型及立绘文件完整度，绝不自动设置鞋履审核通过。
完整名单见[第七批 20 款候选与验收说明](azur_lane/docs/2026-11-18-batch7-unified-gallery.md)。

---

## 多游戏统一浏览（main 分支）

支持碧蓝航线、NIKKE、重返未来：1999、棕色尘埃2 的**跨游戏索引、搜索、标签和收藏**，
同时保留所有游戏现有的独立预览器（动画、互动、场景合成没有被替换）。

```powershell
python scripts/gallery.py serve --port 8000
```

然后访问 <http://127.0.0.1:8000/gallery/>。该命令在本地生成统一索引及文件核查报告、
启动仅监听 127.0.0.1 的静态服务器，不下载或覆盖游戏素材。
游戏资源更新后重启该命令即可刷新索引。四套原始 manifest 仍由各游戏脚本维护。

碧蓝航线第二至第八批共 114 个**批次候选条目**已迁入
`azur_lane/config/curated_collections.json`，原来各批次安装命令不变。
统一缓存完整性及原子写入模块位于 `gallery_core/storage.py`；
当前只抽出跨游戏共通的文件处理，不替换各游戏特有的 CDN/鉴权/解包逻辑。

详见 [第二阶段重构记录](docs/2026-11-18-gallery-core-phase2.md)。


### 第三阶段：皮肤直达、统一动作接口、新游戏脚手架

从统一目录点选一个资源后，浏览器会将精确资源 ID 传给原游戏查看器并尝试自动加载。
查看器页面底部提供统一姿态与动作控制条；实际动画仍由各游戏原有 Cubism/Spine 运行时执行。
某个皮肤没有对应文件、动作或模型加载失败时，查看器会明确提示，不能把索引存在视为已加载成功。

新增游戏时，无须再为统一目录硬编码一个入口：

```powershell
python scripts/new_game.py --id example_game --title "示例游戏" --dry-run
python scripts/new_game.py --id example_game --title "示例游戏"
python scripts/gallery.py serve --port 8000
```

脚手架会创建插件 manifest、静态预览模板、游戏 README 并注册到 `gallery/plugins.json`。
**静态模板不是通用 Live2D/Spine 播放器**；动态模型仍需游戏特有的素材提取器和渲染适配器。
实际游戏资源应放在相应的 `games/<id>/data/` 下（Git 默认忽略）。

第三阶段说明详见 [统一查看器与插件架构](docs/2026-11-18-gallery-core-phase3.md)。

### 碧蓝航线 Live2D 卡片去重（2026-11-18）

碧蓝航线查看器现在把同一皮肤的普通模型和 `_hx` 形态合并显示，
当前 60 个模型文件展示为 **54 张皮肤卡片**。其中 6 套双形态皮肤
在舞台左侧「模型形态」下拉菜单切换原版/HX；各模型的下载、动作、ArtMesh
等功能保持独立，不删除任何素材，也不修改原始 manifest。

按 Cubism 版本筛选时，只要该皮肤的任意形态符合条件就会显示；
打开后优先进入符合所选版本的模型。统一目录中指向 `_hx` 的精确
模型链接继续可用。进入皮肤后可在底部统一控制条中切换形态。

### 第四阶段：集成诊断与发布前验收

第四阶段不扩充新的游戏类型，重点是稳定性与回归验收。资源索引和文件核验报告现在通过稳定摘要对应；
在浏览器中会显示**文件状态最近核验时间**，避免把旧索引核验结果当成实时状态。
注册的新游戏也可被 `python scripts/gallery.py list --game <game_id>` 查询。

```powershell
# 检查四游戏和新插件入口、桥接协议（不检查真实动画画面）
python scripts/gallery.py doctor

# 文件入口存在性报告
python scripts/gallery.py verify

# 在安装 Chrome/Chromium 的电脑上执行真正的浏览器静态目录烟测
python scripts/gallery.py sync-index
python scripts/smoke_browser.py
```

仓库的自动检查涵盖了本地 HTTP 路由和浏览器资源卡片/直达链接，但**不会下载游戏版权素材**，
也不能判断画面、触摸动作、BD2 连续互动和场景合成是否真正正确。
最终合并主分支前必须先用 Windows 本地已安装的皮肤完成实机验收。

验收清单、手工测试步骤与合并门槛见
[第四阶段重构验收报告](docs/2026-11-18-gallery-core-phase4.md)。


---

游戏资源解包 & 展示平台。从游戏客户端提取**立绘、Live2D 模型、音频**等美术制品，
还原成网页可直接查看的格式，并提供带搜索/分组/排序/动作播放的查看器。

> 当前已完整支持 **碧蓝航线（Azur Lane）**；架构设计为可扩展到其他游戏，
> 每个游戏的资源定位/解密/重建逻辑以插件式脚本接入。

**碧蓝航线现状**：
- **立绘**：6129 张（按皮肤分组，3185 个皮肤组）
- **完整静态场景画廊**：已加入人物＋皮肤专属背景/前景组合预览、形态切换、微调与 PNG 导出；分层资源须在本地补齐
- **Live2D**：271 个模型，每个含 14 个动作（idle / home / 触摸 / 任务 / 结婚 等）
- 支持**本地一键自动更新**：拉取最新版本 → 增量下载 → 还原 → 刷新查看器

**NIKKE（胜利女神）现状**：
- **立绘 / 模型**：49 套 Spine 骨骼动画（其中角色 49 套），支持 **立绘(fb) / 半身(cover) / 瞄准(aim)** 三种姿态
- 查看器自动识别 **Spine 4.0 / 4.1** 版本并加载对应 runtime（EsotericSoftware 官方 spine-player），
  正确处理预乘 alpha（premultipliedAlpha），透明背景，自带动作切换/播放控件
- 数据来源：社区 [`Nikke-db`](https://github.com/Nikke-db/Nikke-db.github.io) 已解包的 Spine 资源
- **新：原画/静态、动态模型、场景合成三模式**：可从 Spine 透明渲染批量导出 PNG；读取独立静态图和本地背景图库；切换背景并导出合成图。官方独立原画及背景图片需另行提供，不随代码提交。详见 [`nikke/ART_SCENE.md`](nikke/ART_SCENE.md)。
- **外观风格筛选**：新增「御姐 / 腿部重点 / 运动系」标签与一键安装脚本 `python nikke/scripts/install_style.py 运动系`，自动识别并下载选中风格的 NIKKE 角色、皮肤。详见 [`nikke/SPORTS.md`](nikke/SPORTS.md)。
- **四批收藏一键补齐**：新增 35 个黑丝、网袜、长筒袜、成熟御姐与兔女郎候选 ID，并提供分批下载、文件完整性核验、缺失资源报告。`python nikke/scripts/install_batches.py --all`，详见 [`nikke/CURATED_BATCHES.md`](nikke/CURATED_BATCHES.md)。

## 棕色尘埃2 · 动态皮肤第三批20款（累计54款）

- **第三批新增20款**，均在原始素材库中确认有角色模型和技能演出目录；其中 **Aquila · Sealed Desires** 同时有 `illust_dating22_1` 和 `illust_dating22_2` 两个独立互动场景，其余19款不虚报独立互动。
- **Liatris · Sweet Temptation** 根据 2026-11-05 官方更新归入 Special Skin，其他以成熟御姐、兔女郎、泳装、腿部或运动系造型为主，风格标签需结合本地预览进一步审核。
- 展柜累计 **54 款精选、22 款有独立互动**。第三批筛选按钮「第三批20套」；打开有互动的衣装时优先进入独立互动。
- `python brown_dust2/scripts/install_prestige.py --collection batch-20 --list` 查看第三批，直接运行安装器默认安装这一批。
- 推荐先执行 `python brown_dust2/scripts/install_prestige.py --only costume-067902 --interaction-only` 单独下载 Aquila 的两组互动场景。其余批次见 [详细说明](brown_dust2/README.md)。
- 所有素材仅在用户本地 `brown_dust2/data/` 下载，Git 仓库不包含游戏美术资产。

---

## 目录结构

```
live2d-game-artifact-gallery/
├── viewer/                  # 网页查看器（纯静态，浏览器打开即用）
│   ├── index.html           #   主页面
│   ├── manifest.json        #   资源清单（分组/排序信息，由脚本生成）
│   └── vendor/              #   pixi.js / pixi-live2d-display / Cubism Core
├── data/                    # 还原产物（查看器直接读取）
│   ├── models/<name>/       #   Live2D：moc3 + 贴图 + physics3 + motions/ + model3.json
│   └── paintings/<name>.png #   立绘 PNG
├── cache/AssetBundles/      # 下载的原始 Unity bundle（增量更新对比用，~10GB）
│   ├── painting/  live2d/  paintingface/ ...
├── config/
│   ├── hashes/*.csv         #   各资源类型的版本清单（path,size,md5）
│   └── cfg_json/            #   角色配置（皮肤分组/发布顺序，来自社区数据库）
├── scripts/                 # 所有处理脚本
│   ├── config.py            #   路径与配置中心（改结构只改这里）
│   ├── update.py            #   ★ 一键自动更新入口
│   ├── fetch_manifests.py   #   握手拿版本 + 下载 hash 清单
│   ├── dl_from_csv.py       #   按清单下载 bundle（多线程 + 断点续传）
│   ├── build.py             #   从 bundle 还原立绘 + Live2D（含动作）
│   ├── rebuild_painting.py  #   立绘重建（Mesh+图集碎片 → 完整 PNG）
│   ├── extract_live2d.py    #   Live2D 提取（moc3/贴图/physics/model3.json）
│   ├── motion_convert.py    #   AnimationClip → motion3.json（动作）
│   └── gen_manifest.py      #   生成查看器 manifest（分组/代表图/排序）
├── requirements.txt
└── README.md
```

---

## 快速开始（查看已有资源）

无需任何依赖，直接起个静态服务器：

```bash
cd live2d-game-artifact-gallery
python -m http.server 8000
# 浏览器打开 http://127.0.0.1:8000/viewer/
```

- **Live2D 模型** 页：左侧搜索/排序舰装，点击加载，右侧动作按钮播放动作。
  拖拽平移、滚轮缩放、移动鼠标视线跟随，物理与呼吸已还原。
- **立绘画廊** 页：按皮肤分组；已安装对应背景时，卡片显示人物＋背景预览。
  点开默认是「完整场景」，支持形态、位置、缩放、前景开关和 PNG 导出；切换「原始素材」可查看所有 PNG。
  相关效果是静态组合预览，不保证 100% 还原游戏内摄像机与动态效果。

---

## 碧蓝航线：补齐已安装皮肤的完整场景

新增专门的背景/前景补齐脚本，**只对你本地已经装好的角色立绘处理场景分层**，不会重新下载整套 Live2D：

```powershell
git pull origin main
python azur_lane/scripts/install_scene_layers.py --plan
python azur_lane/scripts/install_scene_layers.py
python -m http.server 8000
```

Windows 也可以直接双击项目根目录的 `补齐碧蓝航线场景素材.bat`。

打开 `http://127.0.0.1:8000/azur_lane/viewer/index.html`，点击「立绘画廊」即可查看。
需要补充人物与背景的 Mesh 坐标时可运行 `python azur_lane/scripts/install_scene_layers.py --geometry`。
尚未下载到本地的版权素材不会随着 Git 更新自动出现；找不到专属背景时继续显示人物并明确提示。

详细操作与限制见 [完整场景画廊说明](azur_lane/docs/2026-11-15-完整场景画廊.md)。

---

## 碧蓝航线第三批：12 款 Live2D 定向安装

新增第三批 12 款御姐 / 腿部构图候选，不需要重新下载全部资源库。运行前确保本地项目同步到最新代码：

```powershell
git pull origin main
python azur_lane/scripts/install_batch3.py --plan
python azur_lane/scripts/install_batch3.py
python -m http.server 8000
```

打开 [第三批专属画廊](azur_lane/viewer/batch3.html)（本地服务地址：`http://127.0.0.1:8000/azur_lane/viewer/batch3.html`）。
支持按角色名、资源名搜索和立绘变体切换。已缓存文件验证后跳过，模型需要具备有效 moc3 与贴图才视作文件就绪；**文件就绪不代表游戏内全部动态交互和双形态已经还原**。

指定某款：`python azur_lane/scripts/install_batch3.py --only gaoxiong_7`。
详细皮肤清单、验收范围及修复说明见 [第三批安装记录](azur_lane/docs/2026-11-15-第三批安装说明.md)。

---

## 碧蓝航线第六批：包脚鞋履 Live2D 候选20款

新增闭合鞋头且遮住脚背的主题初筛池。20个模型已在现有资源 hash 清单找到对应 L2D 与立绘包，其中 2 款赛车长靴已做外观初筛，其余 18 款必须浏览器审核，不保证全部合格。按需安装，审核后标记通过/排除：

```powershell
git pull origin main
python azur_lane/scripts/install_batch6.py --plan
python azur_lane/scripts/install_batch6.py
python -m http.server 8000
```

展示页：<http://127.0.0.1:8000/azur_lane/viewer/batch6.html>；[安装和审核明细](azur_lane/docs/2026-11-17-第六批包脚鞋履筛选.md)。

---

## 碧蓝航线第五批：鞋履主题 Live2D 20 款

新增 20 款鞋履主题候选（黑靴、长靴、兔女郎高跟鞋、女仆鞋等），独立入口不覆盖旧批次。本批在资源 hash 清单中可定位到 Live2D 包；需你本地下载并人工验收鞋履、动作与交互。运行：

```powershell
git pull origin main
python azur_lane/scripts/install_batch5.py --plan
python azur_lane/scripts/install_batch5.py
python -m http.server 8000
```

浏览 <http://127.0.0.1:8000/azur_lane/viewer/batch5.html>，查看 [完整20款清单与安装说明](azur_lane/docs/2026-11-17-第五批鞋履Live2D.md)。

---

## 碧蓝航线第四批：12 款 Live2D 定向安装

第四批包含腓特烈大帝、金鹿号、斯特拉斯堡、天狼星等 **12 款皮肤、13 个模型资源包**（斯特拉斯堡额外含 `_hx` 模型变体），并安装 50 个立绘/背景分层包，按 hash 清单估算约 289.5 MiB。

```powershell
git pull origin main
python azur_lane/scripts/install_batch4.py --plan
python azur_lane/scripts/install_batch4.py
python -m http.server 8000
```

第三批和第二批的入口不变。第四批独立预览：<http://127.0.0.1:8000/azur_lane/viewer/batch4.html>；完成情况：`azur_lane/data/batch4-install-report.json`。
已缓存文件按 MD5 校验后跳过；缺失任何预期模型变体会标记 `incomplete` 并返回失败。文件完整不代表双形态/特效完整复现。

完整名单、分层资源及测试说明见 [第四批安装文档](azur_lane/docs/2026-11-16-第四批安装说明.md)。

---

## Live2D 前景遮挡物控制（企业 qiye_10 / idle9）

部分模型播放特定动作时会出现巨大的前景树叶、全屏特效或过场遮挡。完整 Live2D 操作台现在有左下角的 **「前景图层」** 控制器，可在不改动资源文件的情况下检查并隐藏独立 ArtMesh：

1. 打开完整展厅中的 `qiye_10`，播放动作 `idle9`；
2. 展开左下角「前景图层」，先点「试隐藏前景」查看大面积前景候选是否匹配绿色叶片；
3. 如果误隐藏了人物，点击「全部恢复」；也能在列表逐层按「隐藏 / 恢复」精细调整；
4. 按 `模型 + 动作` 自动存储隐藏图层 ID 到浏览器本地存储，第二次播放相同动作自动恢复设置。

只能隐藏原模型已经分开的图层，遮挡后方如果没有绘制内容，无法凭空补全。
具体操作、技术实现与适用范围请阅读 [Live2D 前景图层控制说明](azur_lane/docs/2026-11-16-Live2D前景图层控制.md)。

---

## 安装依赖（需要更新资源时）

```bash
pip install -r requirements.txt
```

依赖说明：
- `azlassets` —— 碧蓝航线资源工具（用于版本握手 + 拉取 hash 清单）
- `UnityPy` —— 解析 Unity AssetBundle
- `Pillow` / `numpy` —— 立绘 Mesh 重建
- `requests` / `PySocks` —— 下载 + 代理

---

## 数据来源

| 内容 | 来源 |
|------|------|
| 资源 CDN（EN 国际服） | `https://blhxusstatic.yo-star.com/android`（Yostar） |
| 版本网关 | `blhxusgate.yo-star.com:80`（raw TCP + protobuf 握手） |
| 角色分组/发布顺序 | 社区数据库 [`Fernando2603/AzurLaneData`](https://github.com/Fernando2603/AzurLaneData) 的 `ship_skin_template.json` |

> **CN（bilibili）服**：CDN `https://line3-patch-blhx.bilibiligame.net`，
> 网关 `line1-login-bili-blhx.bilibiligame.net`。改 `scripts/config.py` 的 `CDN`/`GATE` 即可切换。

### 资源下载 URL 规则
- hash 清单：`{CDN}/hash/{versionhash}`（版本握手后获得 versionhash）
- 资源文件：`{CDN}/resource/{md5}`（md5 来自清单第 3 列）

---

## 自动更新

```bash
cd live2d-game-artifact-gallery/azur_lane/scripts
python update.py             # 增量更新：只处理相比上次有变化的资源
python update.py --full      # 全量重建（忽略缓存）
python update.py --skip-meta # 跳过社区元数据更新
```

流程：
1. **拉社区元数据** → 皮肤名/分组/发布次序（多源回落，失败不阻断）
2. **握手拿版本** → 下载最新 hash 清单到 `config/hashes/`
3. **增量对比** → 与 `config/hashes_prev/` 比对，找出新增/变更的资源
4. **下载 + 还原** → 只下变化的 bundle（对变化项强制 md5 校验），重建对应立绘/模型/动作
5. **刷新 manifest** → 更新查看器分组数据，回写首页/README 计数，保存本次清单供下次对比

### 元数据说明
角色名 / 分组 / 发布次序来自社区仓库（官方那份配置表是自定义加密二进制，
需逆向 il2cpp 才能解，详见 `azur_lane/DATASOURCE.md`）。
`fetch_metadata.py` 按序尝试三个源（主源 JSON → jsDelivr 镜像 → AzurLaneTools 的 Lua），
带完整性校验（条目数下限，挡掉上游的残缺文件）、防回退、原子写入；
全部源失败时保留现有文件继续，只是新皮肤可能暂时未分组。

### 网络说明
- 脚本默认走本地代理 `127.0.0.1:7897`（海外 CDN，国内需要）。
  在海外服务器 / GitHub Actions 上运行时，把 `azur_lane/scripts/config.py` 的 `USE_PROXY = False`。
- gate 握手是 **raw TCP socket**（不走 HTTP 代理），代理时用 SOCKS5；
  资源下载走 HTTPS（HTTP 代理）。
- 官方 CDN 有限流，偶发连接重置；脚本已内置重试，必要时隔几十秒重跑。

---

## 单步执行（调试用）

```bash
cd live2d-game-artifact-gallery/azur_lane/scripts
python fetch_metadata.py             # 只更新社区元数据（--force 强制）
python fetch_manifests.py            # 只拉最新清单
python dl_from_csv.py L2D            # 只下 Live2D 的 bundle（PAINTING/PIC/L2D）
python dl_from_csv.py --verify L2D   # 同上 + md5 校验（可发现同尺寸的内容改动）
python build.py live2d               # 只还原 Live2D（含动作）
python build.py painting             # 只还原立绘
python gen_manifest.py               # 只重新生成查看器 manifest
```

---

## 技术要点

- **立绘重建**：碧蓝航线立绘贴图是打乱的碎片图集，需用 Mesh 的顶点 + UV
  做三角形仿射变换重排回完整图（`rebuild_painting.py`）。已处理多贴图合成、
  透明区垃圾像素剔除等边缘情况。
- **Live2D 动作**：AnimationClip 的动画数据是 Unity StreamedClip 二进制曲线，
  用 binding path 的 CRC32 反查 Live2D 参数名（`Parameters/ParamXxx`），
  转成标准 `motion3.json`（`motion_convert.py`）。
- **分组**：以皮肤 id（`ship_skin_template.json` 的 `id`）为分组键，
  id 递增对应发布顺序；代表图优先级 `_n_rw > _rw > _n > main`。

---

## NIKKE 管线

NIKKE 的立绘/模型是 **Spine 骨骼动画**（`.skel` + `.atlas` + `.png`），非 Live2D。
支持两种数据源：**(A)** 社区 [`Nikke-db`](https://github.com/Nikke-db/Nikke-db.github.io)
已解包托管的资源；**(B)** 从本地游戏客户端缓存直接解包（数据最全最新）。

### A. 从 Nikke-db 拉取（快速、无需游戏本体）

```bash
cd nikke/scripts

# 1. 拉取资源（读取 Nikke-db 索引 l2d.json，按角色下载 fb/cover/aim + 头像图标）
python fetch_nikke.py                 # 全部角色
python fetch_nikke.py c010 c470       # 指定角色
python fetch_nikke.py --limit 60      # 前 60 个（快速验证）

# 2. 生成查看器 manifest（识别姿态 + Spine 版本 + 封面）
python gen_nikke_manifest.py

# 3.（可选）为缺少现成头像图标的角色，用无头浏览器渲染 Spine 生成缩略图
#    需先在仓库根启动 http server，并安装 playwright
CHROMIUM_PATH=<chrome.exe> node gen_thumbs.mjs http://127.0.0.1:8000 ../data
```

- 数据源索引：`https://nikke-db-legacy.pages.dev/js/json/l2d.json`
- 资源规律：`.../l2d/{id}/{id}_00.skel|.atlas|.png`（+ `/cover/`、`/aim/` 变体）
- 头像图标：`.../images/sprite/si_{id}_00_s.png`

### B. 从本地客户端缓存直接解包（数据最全）

游戏客户端把资源以 **content-addressed** 方式缓存在
`<客户端资源目录>/naps/<hash前2位>/<md5>`（无扩展名）。文件头分两种：
- `UnityFS` —— 明文 Unity 包，**约 76%**，UnityPy 可直接解；
- `NKAB`   —— NIKKE 私有加密包，约 24%，暂不支持。

```bash
cd nikke/scripts
# 指定客户端资源目录（默认 Q:/NIKKE_Assets）
export NIKKE_LOCAL_ASSETS=Q:/NIKKE_Assets

python extract_local.py               # 扫全部 256 个桶
python extract_local.py --buckets 00 01   # 只扫指定桶
python extract_local.py --limit 30    # 前 N 个桶（快速验证）

python gen_nikke_manifest.py          # 再生成 manifest
```

- 解包内容：角色技能演出立绘 `c###_00_skillcut`（归为 **skillcut** 姿态）、
  活动剧情 `EventScene_*`、过场 `liberation/MVG/Glass` 等。
- 实测一次全盘：扫 25266 个明文包 → 提取 **345 套 Spine / 344 个角色场景**，缺贴图 0。
- 支持断点续跑（已提取的 skel 存在则跳过）。

**关键技术点**
- **版本自适应**：读 `.skel` 头部 16 字节的版本串（`4.0.x` / `4.1.x`），
  前端选择 `spine-player4.0.js` / `spine-player4.1.js`（`shared/vendor/`）。
- **正确渲染**：`premultipliedAlpha: true` + 透明背景。此前用 pixi-spine 未处理预乘
  alpha 导致立绘发灰/发黑；换用 EsotericSoftware 官方 spine-player 后还原正确。
- **动画回退**：部分 skillcut/场景模型默认动画名不是 `idle`，查看器在 `success`
  回调里按实际可用动画智能选择（默认名 → 含 idle 的 → 第一个），避免报错。
- **封面缩略图**：优先用 Nikke-db 渲染好的头像图标；缺失时用无头浏览器渲染
  Spine、自动裁剪透明边生成缩略图，避免直接显示打乱的图集碎片。

---

## 说明

本工具仅用于个人学习与研究。提取的立绘、Live2D / Spine 模型版权归属各游戏方
（碧蓝航线：Manjuu / Yongshi / Yostar；NIKKE：SHIFT UP / Level Infinite），
请勿商用或公开再分发。
