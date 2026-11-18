# 第七批：穿鞋 / 脚部遮挡 Live2D 候选（并入统一展示柜）

> **成熟画风筛选补充（2026-11-18）：** 第七批原始 20 条记录保留用于溯源，但 `kubo_2`、`weiyan_2` 已排除，`ailunsamuna_2`、`linuo_3` 暂缓复核。现在仅 **16 条**参与第七批精选安装；既有本地模型不删除。筛选规则见 [成熟画风优先规范](mature-style-curation-policy.md)。


本批只接入候选配置及安装脚本，**不新增专题展示页，不新增主导航按钮**。
主查看器始终为 `azur_lane/viewer/index.html`，跨游戏资源目录仍位于 `gallery/`。

## 筛选原则与证据边界

- 偏向成熟画风、腿部表现、丝袜、运动装、赛车装、兔女郎与暗色礼装；运动鞋、长/短靴及包脚鞋优先，脚部被服装或构图遮挡的场景也可进一步观察。
- 根据公开的 L2D bundle 清单、painting bundle 清单及换装目录**三方交叉核对资源名**，排除了前六批已列皮肤和仓库当前 manifest 记录的模型名。
- 仅证明**候选的同名资源在外部清单中存在**，并不保证你本地 EN 服的 CDN 与 CSV 已同步、UnityPy 一定能解包、完整画面中没有赤脚或露趾，也不代表互动动作合格。
- `review_status` 初始全部为「待视觉与动作核验」。正式是否保留取决于你本地全身立绘和每一个触摸 / idle / 换装动作，任意明确露脚场景都按你的标准重新判断，不预设通过。
- `source_skin_id` 为外部皮肤目录的**交叉参考值**；安装时仍优先以本地 `ship_skin_template.json` 的 ID 解析结果为准，不硬编码外部数字覆盖本地元数据。

交叉验证数据源：

- [公开 L2D 哈希清单](https://github.com/AXiX-official/AzurLaneHashFiles/blob/master/hashes-live2d.csv)
- [公开 painting 哈希清单](https://github.com/AXiX-official/AzurLaneHashFiles/blob/master/hashes-painting.csv)
- [换装资源名与皮肤 ID 目录](https://github.com/Takamiya-reborn/L2Dviewer/blob/main/public/catalog.json)

上述资源索引按 **2026-11-18** 检查，后续 CDN/客户端更新仍需本地 `--plan` 重新验证。

## 20 款候选

| # | 舰娘 | 资源名 | 外部换装名称 | 主题 | 鞋履初筛方向 | 结果 |
|---:|---|---|---|---|---|---|
| 1 | 库珀 | `kubo_2` | 烈日的网球场 | 运动系·网球 | 网球鞋/脚部遮挡候选 | 待审核 |
| 2 | 巴尔的摩 | `baerdimo_6` | 迅疾的蓝星 | 运动系·赛车 | 赛车靴/运动鞋候选 | 待审核 |
| 3 | 霞飞 | `xiafei_4` | 祝福的起步冲刺 | 运动系·竞速 | 运动鞋/包脚鞋候选 | 待审核 |
| 4 | 艾伦·萨姆纳 | `ailunsamuna_2` | Charming Rabbit | 兔女郎·丝袜 | 包脚鞋/脚部遮挡候选 | 待审核 |
| 5 | 里诺 | `linuo_3` | bunny·reno！ | 兔女郎·丝袜 | 包脚鞋/脚部遮挡候选 | 待审核 |
| 6 | 柴郡 | `chaijun_5` | 绚烂夜梦 | 礼装·丝袜 | 礼装鞋/脚部遮挡候选 | 待审核 |
| 7 | 威严 | `weiyan_2` | 囚牢里的危险兔 | 兔女郎·腿部展示 | 包脚鞋/脚部遮挡候选 | 待审核 |
| 8 | 狮 | `shi_3` | 夜巷中的诱引者 | 夜景·成熟 | 高跟鞋/脚部遮挡候选 | 待审核 |
| 9 | 戈里齐亚 | `geliqiya_2` | 办公室的“隔阂” | 职场·丝袜 | 包脚鞋/脚部遮挡候选 | 待审核 |
| 10 | 腓德雷卡·卡尔 | `feiteliekaer_4` | 午夜频道 | 夜景·成熟 | 高跟鞋/脚部遮挡候选 | 待审核 |
| 11 | 埃姆登 | `aimudeng_2` | 黑白的夜之主 | 暗色礼装 | 礼装鞋/脚部遮挡候选 | 待审核 |
| 12 | 关岛 | `guandao_3` | 女忍者的危险综艺秀 | 忍者·腿部展示 | 忍者鞋/足部遮挡候选 | 待审核 |
| 13 | 路易九世 | `luyijiushi_2` | 华服的圣骑士 | 骑士·礼装 | 长靴/礼装鞋候选 | 待审核 |
| 14 | 喀琅施塔得 | `kalangshitade_2` | 突击行动开始！ | 制服·战术 | 军靴/包脚鞋候选 | 待审核 |
| 15 | 曾克海军上将 | `zengkehaijunshangjiang_2` | 心动审讯练习中 | 职场·审讯 | 高跟鞋/包脚鞋候选 | 待审核 |
| 16 | 前卫 | `qianwei_2` | 摇摆不定的伪装 | 角色扮演·成熟 | 靴子/包脚鞋候选 | 待审核 |
| 17 | 可畏 | `kewei_6` | 纪念印记 | 纪念礼装 | 礼装鞋/脚部遮挡候选 | 待审核 |
| 18 | 吾妻 | `wuqi_3` | 心向何方的指导课 | 制服·腿部展示 | 包脚鞋/脚部遮挡候选 | 待审核 |
| 19 | 武藏 | `wuzang_4` | 只为你献上的应援 | 运动系·应援 | 运动鞋/包脚鞋候选 | 待审核 |
| 20 | 浅间 | `qianjian_2` | 绽放于至深之夜 | 夜景·礼装 | 高跟鞋/脚部遮挡候选 | 待审核 |

## Windows 安装与体验

在项目根目录执行：

```powershell
git fetch origin
git switch feature/azur-batch7-unified-gallery-20261118
git pull --ff-only origin feature/azur-batch7-unified-gallery-20261118

# 核对本地 L2D.csv、PAINTING.csv 可否找到这些资源及下载规模
python azur_lane/scripts/install_batch7.py --plan

# 只安装本批 20 款，已验证缓存自动复用
python azur_lane/scripts/install_batch7.py

# 检查安装报告：需要 models/paintings expected 和 built 均一致
# azur_lane/data/batch7-install-report.json

# 更新统一索引并启动模型工作台
python scripts/gallery.py serve --port 8000
```

打开 `http://127.0.0.1:8000/azur_lane/viewer/index.html` 搜索资源名即可。
无需打开新的批次专题网页；统一资源目录会在扫描到本地模型后显示新增皮肤和风格候选标签。

如首次 `--plan` 显示某些资源模型包或立绘包为 0，可以检查本地版本或运行：

```powershell
python azur_lane/scripts/install_batch7.py --refresh
```

注意：`--refresh` 会联网更新元数据和官方文件清单，实际安装素材仍发生在本地。
如只需要少量皮肤先验证：

```powershell
python azur_lane/scripts/install_batch7.py --only kubo_2 baerdimo_6
```

## 验收及后续处理

`batch7-install-report.json` 为运行时报告（位于被 Git 忽略的 data/），只反映**文件是否齐全**。
`footwear_verified` 和 `all_motions_verified` 默认均为 false。视觉不符合的候选可后续从精选集合移除，但**不应删除原始模型/立绘文件**，以免破坏其他收藏或动作测试。

本次仅移除主 Live2D 查看器头部的第五批、第六批专题入口；原来的 `batch5.html` 与 `batch6.html` 文件保留，防止旧链接失效，但不再作为扩展路线。
