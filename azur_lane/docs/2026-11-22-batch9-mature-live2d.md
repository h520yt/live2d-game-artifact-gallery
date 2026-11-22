# 碧蓝航线第九批：同级 Live2D · 成熟与鞋履优先（2026-11-22）

以「大凤 · Fun on the Baize」(`dafeng_7`) 为质量对照；本批要求 **L2D 资源存在**，部分为 L2D+。L2D+ 和 L2D 的官方分级以公告/游戏实际页面为准，不能只靠文件名推断。

## 去重与核验

- 已检查 main 分支 `azur_lane/config/curated_collections.json`（第2～8批）及 `azur_lane/viewer/manifest.json`，本批 20 个 asset 与它们均不重合。
- 使用 `Fernando2603/AzurLaneData/sharecfgdata/ship_skin_template.json` 的 painting、英文名称、skin id 和 `AXiX-official/AzurLaneHashFiles` 的 `hashes-live2d.csv`、`hashes-painting.csv` 交叉核验资源名，2026-11-22 查询均存在。
- **已核实资源名 ≠ 已经安装本地模型 ≠ 成熟风格与鞋履通过。** 未连接用户 Windows 本机，也未逐个运行 idle/触摸/切换/特殊动作。
- 筛选标准：成熟御姐整体画风优先，腿部/丝袜及包脚鞋（长靴、短靴、皮鞋、高跟鞋、运动鞋）优先；有裸足、露趾场景需剔除。对于无法确认足部状态的 4 款保守设为 hold。
- 仅 **16 款 candidate** 纳入这次安装器，另外 **4 款 hold** 暂缓；保留 20 条候选记录以便后续复核。
- 不新增批次分类页面；下载的模型和立绘自动进入同一个碧蓝航线展示柜，首页现有入口不变。
- 皮肤专属背景只能匹配官方对应层，不能拿别的资源背景拼接。

## 20 款候选

| # | 角色 | 资源名 | 皮肤英文名 | 分级核验 | 安装状态 | 鞋履审查 |
|---:|---|---|---|---|---|---|
| 1 | 那不勒斯 | `nabulesi_3` | Lost White Bird | L2D+ 官方修正 | 进入安装候选 | 病患场景脚部与特殊姿势待核 |
| 2 | 柴郡 | `chaijun_6` | Cheshire Cat's Fairytale Maze | L2D+ 官方目录 | 进入安装候选 | 高跟鞋、丝袜与触摸变化待核 |
| 3 | 普利茅斯 | `pulimaosi_3` | An Angelic Physical | L2D+ 官方目录 | 暂缓 | 鞋履及姿态不明，暂缓 |
| 4 | 金狮（Gouden Leeuw） | `jinshi_2` | An Intimate Cleaning | L2D+ 官方目录 | 进入安装候选 | 脚部在全部动作中的遮挡待核 |
| 5 | 云仙 | `yunxian_3` | Arcane Ninja Knowledge | L2D 官方目录 | 进入安装候选 | 忍者鞋、足部遮挡待核 |
| 6 | 莫加多尔 | `mojiaduoer_3` | Olfactory Nursery Call | L2D 资源存在 | 暂缓 | 袜鞋未知，暂缓 |
| 7 | 美因茨 | `meiyinci_3` | A Blend of Serenity | L2D 资源存在 | 进入安装候选 | 裙装鞋履及长袜待核 |
| 8 | 那不勒斯 | `nabulesi_2` | Dreamy Night | L2D 官方记录 | 进入安装候选 | 丝袜、鞋履与切换动作待核 |
| 9 | 尾张 | `weizhang_3` | My Wish is For Love | L2D 资源存在 | 进入安装候选 | 鞋履与腿部构图待核 |
| 10 | 渡良濑 | `dulianglai_2` | Garments of Everlasting Magic | L2D 官方目录 | 进入安装候选 | 包脚鞋或靴子待核 |
| 11 | 潘勒韦 | `banerwei_3` | Fresh and Fortunate | L2D 官方目录 | 进入安装候选 | 丝袜、鞋尖与动作待核 |
| 12 | 可畏 | `kewei_4` | The Lover's Heart Flutters On Duty | L2D 资源存在 | 进入安装候选 | 服装与鞋履待核 |
| 13 | 龙武 | `longwu_2` | Ascendant Dragon's Spring Feast | L2D 官方目录 | 暂缓 | 传统服装足部不明，暂缓 |
| 14 | 白龙 | `bailong_3` | Flash of Silk and Strings | L2D 资源存在 | 进入安装候选 | 鞋履、袜装与特殊动作待核 |
| 15 | 克莱蒙梭 | `kelaimengsuo_2` | Splendid Breeze | L2D 官方目录 | 进入安装候选 | 长裙遮挡及鞋跟待核 |
| 16 | 海因里希亲王 | `haiyinlixi_2` | Rabbit on Watch | L2D 资源存在 | 进入安装候选 | 丝袜、包脚鞋待核 |
| 17 | 大凤 | `dafeng_3` | Sweet Time After School | L2D 资源存在 | 进入安装候选 | 制服鞋与腿部角度待核 |
| 18 | 阿达尔伯特亲王 | `adaerbote_2` | After-Hours Service | L2D 资源存在 | 进入安装候选 | 制服鞋及特殊动作待核 |
| 19 | 布雷默顿 | `bulaimodun_2` | Day-Off Date | L2D 资源存在 | 进入安装候选 | 运动鞋或脚部遮挡待核 |
| 20 | 赤城 | `chicheng_5` | Dawn-Phoenix's Summons | L2D 资源存在 | 暂缓 | 和风造型足部不明，暂缓 |

**L2D+ 可查证例子：** 那不勒斯 Lost White Bird（官方公告将最初的 L2D 改判为 L2D+）、金狮 An Intimate Cleaning、柴郡 Cheshire Cat's Fairytale Maze、普利茅斯 An Angelic Physical。其它条目先以 L2D bundle 存在作为技术筛选依据，具体互动等级待逐项复核。

## 本地安装和验收

```powershell
git switch main
git pull --ff-only origin main

# 第九批 16 个启用候选预检：检查本地 L2D / PAINTING 清单
python azur_lane/scripts/install_batch9.py --plan

# 如果本地 CDN 清单缺新资源，先刷新
python azur_lane/scripts/install_batch9.py --refresh

# 安装启用候选，复用既有下载、解包、索引刷新流程
python azur_lane/scripts/install_batch9.py

# 不额外开专题页
python scripts/gallery.py serve --port 8000
```

浏览器打开 `http://127.0.0.1:8000/azur_lane/viewer/index.html` 或统一画廊 `http://127.0.0.1:8000/gallery/`。

只安装两款验证：

```powershell
python azur_lane/scripts/install_batch9.py --only nabulesi_3 jinshi_2
```

本地报告：`azur_lane/data/batch9-install-report.json`。只把 `models_expected/models_built` 和 `paintings_expected/paintings_built` 视为文件完整性，不能当作外观通过。

全动作检查顺序：**完整人体比例和成熟感 → 鞋尖/脚背/鞋底 → idle/触摸/姿态切换 → 模型贴图和专属背景**。若发现任何赤脚或露趾场景，更新候选为 hold/excluded；不要直接删除已经下载的原始模型。

数据来源：
- https://github.com/Fernando2603/AzurLaneData/blob/main/sharecfgdata/ship_skin_template.json
- https://github.com/AXiX-official/AzurLaneHashFiles/blob/master/hashes-live2d.csv
- https://github.com/AXiX-official/AzurLaneHashFiles/blob/master/hashes-painting.csv
- https://azurlane.yo-star.com/news/
