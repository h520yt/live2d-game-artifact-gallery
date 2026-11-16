# 棕色尘埃2 · 互动动画优先展示柜

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
