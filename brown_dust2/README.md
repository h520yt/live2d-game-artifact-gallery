# 棕色尘埃2 · 互动优先展示柜（第三批20款）

## 2026-11-18 · 22 套互动加入非赤脚筛选池

当前全部 22 套独立互动在仓库中已存在来源映射，本轮将原先未分类的 **14 套**作为**脚部待核验候选**加入「非赤脚筛选池」，不复制模型、不删除原有素材。最初 8 套保留原先场景线索和指定 idle；**候选≠已确认符合**。新增「待核验14套」筛选入口，可逐一打开其互动场景判断是否穿鞋、包脚袜子、脚部完全遮挡或出画。

```powershell
cd D:\project_python\live2d-game-artifact-gallery
git pull origin main
python brown_dust2/scripts/install_prestige.py --collection nonbarefoot-pending --list
python brown_dust2/scripts/install_prestige.py --collection nonbarefoot-pending --interaction-only
python brown_dust2/scripts/install_prestige.py --verify --collection all
python -m http.server 8000
```

打开 `http://127.0.0.1:8000/brown_dust2/viewer/index.html`。已分类的原 8 套单独查看：`--collection nonbarefoot-reviewed`；全部 22 套：`--collection nonbarefoot`。只会在本地下载缺失的互动 Spine 素材，不会把素材提交 Git。

## 非赤脚互动 · 场景级筛选（2026-11-18）

展示柜新加 **「非赤脚互动」** 分类。判断依据是互动中的具体画面：有鞋/靴/丝袜/网袜，或脚部被被褥、道具、家具遮挡、位于画面之外，均可收录；同一皮肤只需有部分场景符合，不要求全部动作都符合。

- 最初 8 套已有场景或外观线索；新增 14 套为待核验候选，不等于全部合格。全部复用现有模型，不复制皮肤记录或删除素材。
- 配置在 `curated_nonbarefoot.json`，为每套存储判定原因、场景确认程度、优先角色模型与优先 idle（仅有截图依据时才写具体编号）。
- **Ventana · Onsen Practitioner** 用户明确认可的脚部遮挡场景为 `idle2`，进入该皮肤时优先尝试 `idle2`；**Sylvia · Bikini Agent** 的参考横躺画面优先 `idle1`。
- 其他资源目前只有鞋袜或特定遮挡场景的依据，**已入选但标为「非赤脚·部分场景」**；这些条目不会虚构已验证的动画编号，也不代表任意 `mix` 动作都符合。
- 查看当前筛选结果：页面「非赤脚互动」；使用本地安装器只查看这批：`python brown_dust2/scripts/install_prestige.py --collection nonbarefoot --list`。仅下载其中已入选且缺失的互动资源：`python brown_dust2/scripts/install_prestige.py --collection nonbarefoot --interaction-only`。
- 下载状态仍由本地模型完整性检测控制；14 套新候选尚未完成 WebGL 画面验收，不能视为已符合非赤脚条件。


## 最新：第三批20款（2026-11-17）

本次根据互动优先、成熟御姐、黑丝/网袜、腿部展示及泳装/运动系等偏好新增20款。**20款不是20套独立互动**：只核实到 Aquila · Sealed Desires 的两段新互动场景，另外19款是人物/技能 Spine 动态（其中 Sweet Temptation Liatris 是新 Special Skin）。不把技能动画冒充互动。

累计：原34款 + 第三批20款 = **54款**，有独立互动映射 **22款**。独立互动场景文件合计23组（Aquila 两组计作一款）。

### 第三批名单

| # | 角色 | 服装 | 收录理由 | 模型类型 |
|---:|---|---|---|---|
| 1 | Aquila | Sealed Desires | 新 Fated Guest；独立互动分为两个场景 | 独立互动×2＋人物＋技能 |
| 2 | Liatris | Sweet Temptation | 11月5日新 Special Skin，甜点制作主题 | 人物＋技能 |
| 3 | Eleaneer | Shadow Bunny | 黑色兔女郎造型，深色服饰与腿部视觉 | 人物＋技能 |
| 4 | Darian | Bittersweet Bunny | 兔女郎主题，腿部视觉优先 | 人物＋技能 |
| 5 | Eclipse | Beach Vacation | 成熟角色的夏日海滩造型 | 人物＋技能 |
| 6 | Dalvi | Summer Vacation | 狐系角色夏日清凉造型 | 人物＋技能 |
| 7 | Liberta | Onsen Manager | 温泉经营者和式造型 | 人物＋技能 |
| 8 | Morpeah | Beach Vacation | 海滩假日泳装风格 | 人物＋技能 |
| 9 | Nebris | Laid-back Lifeguard | 救生员运动系泳装 | 人物＋技能 |
| 10 | Angelica | Pool Party | 成人角色泳池派对服装 | 人物＋技能 |
| 11 | Scheherazade | Pool Party | 泳池派对夏装 | 人物＋技能 |
| 12 | Rubia | Maid Bikini | 女仆+比基尼主题 | 人物＋技能 |
| 13 | Luvencia | Ocean Vanguard | 夏日先锋轻装与腿部视觉 | 人物＋技能 |
| 14 | Loen | Track and Field Team | 田径队主题 | 人物＋技能 |
| 15 | Levia | Overheat | Levia 高热战斗造型，建议预览动作 | 人物＋技能 |
| 16 | Michaela | Beachside Justice | 海滨主题成人女性角色 | 人物＋技能 |
| 17 | Mamonir | Miracle Marine | 海军夏日造型 | 人物＋技能 |
| 18 | Venaka | Wind Dancer | 舞蹈主题，动作表现优先 | 人物＋技能 |
| 19 | Valze | Night of Betrayal | 2026-11-05 新吸血鬼女王角色 | 人物＋技能 |
| 20 | Wilhelmina | Frozen Queen | 冰霜女王造型，重点成熟气质 | 人物＋技能 |

### Windows 本地命令

```powershell
cd D:\project_python\live2d-game-artifact-gallery
git pull origin main

# 只查看第三批名单，不联网下载
python brown_dust2/scripts/install_prestige.py --collection batch-20 --list

# 优先安装 Aquila 的两部分独立互动
python brown_dust2/scripts/install_prestige.py --only costume-067902 --interaction-only

# 分批安装20款人物及技能资源（可能较大，可加 --limit 5 --offset 0）
python brown_dust2/scripts/install_prestige.py --collection batch-20

# 离线重建已有安装清单
python brown_dust2/scripts/install_prestige.py --verify --collection all
python -m http.server 8000
```

浏览器地址：`http://127.0.0.1:8000/brown_dust2/viewer/index.html`。使用「第三批20套」筛选；Aquila 将显示「互动动画① / 互动动画②」两个入口。其它19款尚无同服装独立互动映射，人物动态和技能演出可用性以本地下载后的完整性检测为准。

**来源与限制：** 新增列表和角色/技能目录来自 `myssal/Brown-Dust-2-Asset` 与 `Jelosus2/BD2-L2D-Viewer`；两组 Aquila 互动还与另一资源库的 Aquila/Sealed_Desires 目录交叉核对。官方 2026-11-05 更新证实 Sweet Temptation Liatris 是 Special Skin。下载或播放完整度需用户本地验证；游戏美术版权归原权利人。

---

**最新收藏规则：独立互动动画优先。** 只要能匹配真实、独立的 Spine 互动场景，即便没有普通人物动态或技能演出，也可以单独加入展示柜。其余继续保留已选的 Prestige、Special Skin、御姐/黑丝/腿部重点服装，但默认「有互动」筛选。

## 数量与完整性

| 来源 | 数量 | 独立互动来源映射 |
| --- | ---: | ---: |
| Prestige Skin（尊爵） | 6 | 6 |
| Special Skin（特殊皮肤） | 8 | 0（官方设计无独立互动） |
| 风格精选 | 12 | 7 |
| **第二批互动专辑（新）** | **8** | **8** |
| **总计** | **34** | **21** |

以上是来源目录核实情况，不是本机已经全部下载或能正常渲染的保证。安装时下载 atlas、skel 和图集中全部引用的 PNG，并通过本地完整性检查后才会在网页显示「独立互动已安装」。

### 第二批：8 套只装互动的真实映射

| 角色服装 | 上游互动 ID | 贴图页 |
| --- | --- | ---: |
| Loen · Celebrity Bunny | `illust_dating3` | 8 |
| Ventana · Onsen Practitioner | `illust_dating15` | 7 |
| Angelica · Neon Savior | `illust_dating10` | 8 |
| Elise · Code Name O | `illust_dating5` | 7 |
| Granhildr · Combat Medic | `illust_dating19` | 8 |
| Teresse · Medical Club | `illust_dating4` | 6 |
| Palette · Miracle Violet | `illust_dating17` | 8 |
| Tyr · Innocent Bunny | `illust_dating13` | 6 |

以上八套都通过双方交叉核对：上游角色/服装索引的对应关系，以及原始资源库中该互动文件夹存在 .skel、.atlas、所有 PNG 贴图。**新批不添加未经核验的人物/技能映射**，所以人物和技能入口不可用是预期行为，并非缺失。

Aquila · Sealed Desires 在其它资源库里有互动条目，但本项目当前使用的原始素材源没有找到对应的 `illust_dating22.atlas`，暂时不加入可下载名单。

## Windows PowerShell 安装

```powershell
cd D:\project_python\live2d-game-artifact-gallery
git pull origin main

# 默认：只下载本批8套互动模型
python brown_dust2/scripts/install_prestige.py

# 或显式指定
python brown_dust2/scripts/install_prestige.py --collection interaction-batch

# 按来源补齐所有21套独立互动（不会重下人物或技能）
python brown_dust2/scripts/install_prestige.py --collection interactive --role interaction

# 离线核实每套互动映射和本地安装状态
python brown_dust2/scripts/install_prestige.py --collection all --audit-interactions

# 只安装某一套互动
python brown_dust2/scripts/install_prestige.py --only costume-067004 --role interaction

# 验证并重建manifest
python brown_dust2/scripts/install_prestige.py --verify --collection all
python -m http.server 8000
```

打开 `http://127.0.0.1:8000/brown_dust2/viewer/index.html`，按 Ctrl+Shift+R 刷新。左侧默认「有互动」，可切换到「本批新增8套」「全部精选」「特殊皮肤」或按个人喜好筛选。

展示柜首选已经安装的独立互动；如果某套只有互动一类资源，打开后会直接进入「互动动画」，人物和技能按钮不会伪装为可用。支持动画动作、组合轨道、智能铺满、缩放、大屏显示和 PNG 导出。

## 分类说明

Special Skin 官方目前不包含 Prestige/Fated Guest 那种独立互动。没有互动目录的其它精选服装也不自动借用别人的互动资源。

参考：
- 第三方角色动画索引：https://github.com/Jelosus2/BD2-L2D-Viewer/blob/main/src/utils/character_list.ts
- 上游原始资源目录：https://github.com/myssal/Brown-Dust-2-Asset
- Special Skin 官方开发说明：https://dotgg.gg/brown-dust-2/45th-developer-notes-1000th-day-update-2/

## 维护

- `curated_interactions.json`：当前最新互动专辑 8 套，只含独立互动目录
- `curated_prestige.json`：六款尊爵
- `curated_style.json`：12 套风格精选与来源
- `costume_catalog.json`：200 套原始来源记录，仅作为后台索引
- `scripts/install_prestige.py`：默认只处理互动新批，--collection all 才处理所有精选，资源增量缓存
- `viewer/manifest.json`：真实本地文件检查结果
- `data/`：用户本地的游戏美术素材，Git 忽略，不会清理旧资源

角色动画属于原游戏权利人。本项目只维护元数据、同步/预览代码；不会把美术素材提交到 Git 仓库。

## 互动场景黑色 X 形遮罩 / 中心缩成小图（2026-11-16）

部分 Fated Guest 互动 Spine 场景会包含异常巨大的背景网格/遮罩附件。原播放器直接用整个骨骼边界计算相机，把真正的互动场景挤到中心小点，四周显示黑色三角形。这不是把图片文件缩放为 1.0 倍能解决的问题。

本次从场景可见 mesh/region 里剔除背景类插槽和极端尺寸的几何离群值；只有在完整骨骼的长宽比有效内容夸张地大（4 倍以上）时，才自动切换为主体边界取景，尽量保留原有完整画面。若骨骼边界失效，会保留原生相机并启用像素自动取景，不会同时禁用缩放按钮。

自动聚焦最大倍率由 7 倍增加到 20 倍，并为极小的闪光像素增加下限保护。普通皮肤和已经显示完整的场景仍按原边界适配，原始 skel、atlas、mesh、Skin、动作轨道均不修改。

更新操作：运行 `git pull origin main`，浏览器 `Ctrl+Shift+R`；切换到 Tyr · Innocent Bunny 或之前异常的互动皮肤，点击「完整适配」，需要时点击「智能铺满」。如黑色 X 形仍然覆盖画面，提供当前动作名称、Skin、缩放数字及浏览器控制台错误，以判断是否是源图集本身的异常网格，而非仅取景问题。

本次已有自动化几何边界与聚焦规则测试；无法从 GitHub 自动测试替代本地 WebGL 素材的肉眼验收。


## 互动出现背景却没有人物：Skin / 动画场景错配（2026-11-16）

针对 Angelica · Neon Savior 等多场景互动模型，之前播放器默认选择“部件数最多”的 Skin（例如 `idle3_1`），却另行播放第一条 `idle1` 待机动画。二者属于不同场景时，可能出现房间背景正常而人物不显示的现象。

改动如下：

- 为互动模型优先匹配 **同名 Skin 与 idle 动画**，其次匹配同编号场景，再回退到 `default`；不再按 Skin 部件数量挑首个互动场景；
- 点击 `mixN_*` 时优先维持同组 `idleN` 的基础轨道，自动选择对应场景 Skin，避免不同互动阶段互相串画面；
- 新增 `互动场景` 下拉菜单，列出模型全部 `idle*` 待机场景；选择某场景时会解除手动 Skin 锁定并自动配对；
- 仍可通过 `模型部件` 手动指定 Skin；手动指定后不会被动画切换自动覆盖，切换大屏也能保留该选择；
- 在 Skin 与动画均已应用后再计算相机边界，不再用尚未设置完整姿态的骨骼取景。

本次是播放器状态配对修复，未改游戏文件、未删除素材。执行 `git pull origin main`，用 Ctrl+Shift+R 强制刷新；打开 Angelica → 互动动画，检查「互动场景」及「模型部件」是否对应。若某个组合仍只有背景，可切换另一条 `idle*` 场景或相关 `mix*` 动作，并查看页面状态提示的 Skin / 动作名称。

GitHub 自动测试只能证明配对逻辑和动画轨道设置正确，不能替代用户本地真正的 Spine/WebGL 画面验收。

## 修复 mix2_1_1、mix2_1_2 等连续动作点击黑屏（2026-11-16）

这类编号通常表示连续互动的独立片段。原来的查看器直接把每个 `mix` 当成非循环动画播放一次，片段结束后可能停留在黑场／隐藏角色的过渡帧；而上游 BD2-L2D-Viewer 在用户点选 `mix` 动作时会循环播放。

改进：
- 对非连续的独立 `mixN_*` 使用循环播放，与上游动作浏览模式保持一致；
- 对 `mix2_1_1`、`mix2_1_2` ... `mix2_1_end` 这种连续组，自动按 **数字顺序** 播放整组（而非词典排序，也不再只播放某一帧）；
- 先在轨道 0 播放对应的 `idle2`，连续动画在轨道 1 播放；结束后通过 `addEmptyAnimation(1, 0, 0)` 清除上层轨道，保留 `idle2` 防止永久黑屏；
- 新增金色 **「▶ mix2_1 连播（N段）」** 按钮，并保留底下每个原始编号供检查；点击同组任一原始片段也会连播完整组；
- 大屏切换正确恢复选中的动作 ID，而非用「连播」按钮上的中文文案当作动作名；
- 如果缺失对应 `idleN`，页面显示警告而不是假称成功复现动画。

更新：`git pull origin main` 后 Ctrl+Shift+R 强制刷新，进入对应人物的「互动动画」，优先选择带 ▶ 的完整连播按钮。

本次验证了动画组合、数字排序和轨道清理的代码行为；未在你的本机执行原始 Spine 动画渲染，某些上游片段可能有额外剧情触发依赖，不能保证所有动作都视觉正常。


## 2026-11-17 展柜布局重做（参考碧蓝航线）

为了避免旧版「左侧长列表 + 右侧预览 + 底部海量动作按钮」同时占用屏幕，棕色尘埃2展示柜按碧蓝航线 \`azur_lane/viewer/index.html\` 的使用逻辑进行了分层：

1. **卡片收藏画廊**：首页是全宽的网格收藏，不再固定左侧边栏。上方可搜索角色/服装/编号，按「独立互动、批次、御姐、黑丝/网袜、腿部重点、已安装」筛选；支持排序和 3–6 列卡片密度（手机自动降列数）。
2. **独立动画预览台**：点击卡片才进入预览，不会同时挤显示收藏列表。顶部返回、上一套/下一套；舞台自动填充视口剩余高度。首次打开不再自动进入某位角色。
3. **右上角动作抽屉**：动作列表默认折叠，点「动作 N」展开，可按 \`idle\`、\`mix\`、编号搜索；保留全部原始动作和「▶ mix 连播」按钮，不再让上百个动作按键挤在舞台下方。
4. **高级选项折叠**：Skin、互动场景和预乘/普通 Alpha 放进「场景 / Skin / 透明设置」，智能铺满、缩放、完整适配仍放在主工具栏。
5. **返回与导航**：返回画廊保留搜索/分类/滚动位置；上一套/下一套直接切换当前筛选结果。退出舞台前会尝试从当前 WebGL 画面生成一张轻量卡片预览图，仅在当前网页会话中使用，不上传也不覆盖游戏素材。若不支持截图仍可正常浏览。
6. **快捷键**：\`Esc\` 依次关闭动作抽屉/高级设置/沉浸大屏，最后返回画廊；\`M\` 展开/收起动作抽屉；左右方向键切换上/下一套（输入框聚焦时不会触发）。

实现文件为 \`brown_dust2/viewer/index.html\` 和新增 \`brown_dust2/viewer/layout.css\`，独立样式负责布局与配色，Spine 骨骼播放逻辑、双互动模型、连续 mix、智能取景和本地下载器均继续沿用现有版本。若本地浏览器仍显示旧版，请执行：

\`\`\`powershell
cd D:\project_python\live2d-game-artifact-gallery
git pull origin main
python -m http.server 8000
\`\`\`

打开 \`http://127.0.0.1:8000/brown_dust2/viewer/index.html\`，按 \`Ctrl+Shift+R\` 强制更新样式。**只修改前端页面，无需重新下载已有皮肤资源。**


## 2026-11-17 修复：54 套真实封面、动作列表溢出

### 真实皮肤卡片

上一版网格首次加载只显示 A/L/T 等英文首字母，因为缩略图仅在「从舞台返回列表」时尝试从 WebGL 画布截图，尚未打开的皮肤没有预览来源。

现改为从上游 `myssal/Brown-Dust-2-Asset/ui/illust/illust_inven_char` 读取各套皮肤真实的库存立绘 PNG，通过 `thumbnail_catalog.json` 建立 **54 套精选皮肤一对一的准确资源映射**。这是一张静态立绘小封面，不是完整互动动画截图；卡片打开后仍播放本地 Spine 模型。

- 联网时使用 GitHub Raw CDN 加载缩略图，**更新代码并刷新即可看到，不需要重新下载 Spine 素材**。
- 如果访问 Raw 失败，自动回退到本地 `brown_dust2/data/_thumbnails/{skin_id}.png`；两者都不可用时显示「封面暂不可用」，不再用单个字母冒充立绘。
- 想离线浏览或减少远端请求，可提前缓存 54 张角色封面：

```powershell
cd D:\project_python\live2d-game-artifact-gallery
git pull origin main
python brown_dust2/scripts/download_thumbnails.py
# 本地检查缓存情况（不联网）
python brown_dust2/scripts/download_thumbnails.py --list
# 单独更新一款
python brown_dust2/scripts/download_thumbnails.py --only costume-067902 --force
```

缓存脚本直接使用原始图片 URL，不消耗 GitHub Contents API 额度；校验 PNG 签名及尺寸后原子写入。图片不提交 Git，已有 Spine 模型文件不会更改。

### 动作抽屉布局

动作抽屉改为与舞台高度绑定的浮层，最多约 535px；输入框高度固定为 40px，按钮统一 36px 行高，连续动作按钮横跨两列，**动作列表自己滚动**，不会把上百个按钮挤出抽屉或导致文字堆叠。

仍可在抽屉搜索 `mix`、`idle` 和具体动作编号，按 Esc 或再次点击「动作」收起。

如果仍看到旧版，请从项目根目录启动 `python -m http.server 8000` 并按 `Ctrl+Shift+R` 强制刷新页面与 CSS。

