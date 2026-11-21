# 天命之子 · Live2D 皮肤展示柜

按照第四阶段插件接入规范，和其它游戏统一为「卡片 → 全屏独立舞台 → 返回原位置」，不新增游戏内分类页。

来源：[Pelom777/DestinyChildLive2D](https://github.com/Pelom777/DestinyChildLive2D)，上游提交 `63e43d034512946c5eb308754f18a1865382bdf6`。名称参考 [Live2D-DCG](https://github.com/Live2D-DCG/Live2D-DCG.github.io)。

目录共有 40 套 Cubism 2 Live2D，包含首批 20 套和 2026-11-21 新增的 20 套。卡片使用与模型 ID 对应的上游角色图标；点开卡片可看完整动态模型。

## PowerShell（仓库根目录）

```powershell
python games/destiny_child/scripts/sync.py --plan
python games/destiny_child/scripts/sync.py --runtime-only
python games/destiny_child/scripts/sync.py --id c001_14
python games/destiny_child/scripts/sync.py --all
python scripts/gallery.py sync-index
python scripts/gallery.py verify
python scripts/gallery.py serve
```

在 `http://127.0.0.1:8000/gallery/` 选择「天命之子」。也可访问 `games/destiny_child/viewer/index.html`。

播放器必须按 Cubism 2 SDK → PIXI 6 → `pixi-live2d-display-cubism2` 的顺序加载。首次运行 `sync.py` 会下载两个 Cubism 2 运行时到 `games/destiny_child/vendor/`。单独补齐运行时可执行 `--runtime-only`。Cubism 2 SDK 为 Live2D Inc. 专有软件，请遵循其授权要求。运行时存放在 Git 忽略目录。

本地模型在 `games/destiny_child/data/`（Git 忽略）。重复执行 `--all` 或任意数量的 `--id` 可以续装缺失或校验失败的文件。新版清单记录新增资源全部依赖的 SHA-256，可校验 MOC 和动作文件是否完整。需要整套重装时可使用 `python games/destiny_child/scripts/sync.py --id c447_11 --force`。原游戏资源版权归权利方所有，仅作个人合法本地欣赏。

安装器使用根目录 `requirements.txt` 中的 Pillow 核验 PNG。

## 清晰度与显示说明

本资源库部分角色的主纹理图集为 1024×1024（例如 `c001_14`），同一人物的部件共同占用该图集；这是源资源的细节上限，不能靠放大画布补出细节。展示柜使用 PIXI 的 `resolution = min(devicePixelRatio, 2)` 与 `autoDensity = true`，防止画布在高 DPI 显示器上被浏览器二次拉伸模糊。对资源本身的清晰度，建议按原生展示尺寸比较，并避免过度滚轮放大；与 NIKKE Spine 项目素材的像素密度不可直接等同。

## 2026-11-21 新增资源

扫描 Pelom777 的 2,188 个模型记录，其中 `c` 系列有 1,368 个角色与衣着记录。对照 Live2D-DCG 的 2,516 项名称与区域索引后，试装 218 套，216 套成功进入实际舞台预览。最终收录下表 20 套。逐套核对了待机循环、25 张必需纹理、45 个其他动作和 16 个可用表情。

| 原始 ID | 角色与衣着 | 筛选依据 |
| --- | --- | --- |
| `c447_11` | Miriam · Original | 黑色连裤袜、窄裙、衬衫与领带 |
| `c474_10` | Hephaestus · Teacher | 半透明深色连裤袜、白色职业外套、高跟鞋 |
| `c534_10` | Legend · Original | 半透明黑色过膝袜、交叉绑带高跟鞋 |
| `c064_02` | Medusa · Conquering | 深色半透明蕾丝长袜、高跟鞋 |
| `c198_02` | Zelos · Turncoat | 深色丝袜、细跟鞋、坐姿 |
| `c244_02` | Chun Li · Dress | 棕色连裤袜、开衩旗袍、系带靴 |
| `c452_02` | Leifang · Vermilion Bird | 深酒红蕾丝过膝袜、红色高跟鞋 |
| `c334_02` | Lisa · Disillusioned | 半透明黑色连裤袜、黑裙、高跟鞋 |
| `c335_02` | Hathor · Extinction | 深灰长袜、细跟绑带鞋 |
| `c482_02` | Theophano · Quirky | 黑色花纹长袜、交叉绑带高跟鞋 |
| `c043_10` | Hera · Shooting Star | 酒红过膝袜、尖头鞋、礼帽 |
| `c539_10` | Belial · Executioner | 紫色长袜、金边高跟鞋、王座礼服 |
| `c447_10` | Miriam · Punishing | 系带过膝靴、哥特长外套 |
| `c227_02` | Mafdet · Dogmatic | 深蓝制服、军靴、完整站姿 |
| `c308_02` | Kubaba · Revenge | 黑皮夹克、长靴与机车 |
| `c354_10` | Demeter · Mad Nurse | 红白护士装、红色过膝靴 |
| `c467_02` | Ziva · Burning | 黑色尖头过膝靴、冰火动效 |
| `c520_02` | Ishimi · False | 黑色系带高跟过膝靴 |
| `c510_10` | Krsnik · Smoker | 红皮外套、窄裙、细跟鞋 |
| `c420_10` | Katherine · Wild Crimson | 红色开衩晚礼服、细跟鞋、烛台舞台 |

新增资源的主图集均为原生 1024×1024，其中 5 套另有一张 512×512 图集。对照 Live2D-DCG 同 ID 的韩服和国际服资源，未发现更高分辨率的同款图集。实际宽高和来源提交见 `viewer/manifest.json`。联动角色设定可参考 [Capcom 春丽角色故事](https://www.streetfighter.com/6/fr/column/detail/wtstory20) 和 [Team Ninja 丽凤角色档案](https://www.teamninja-studio.com/doa6/uk/chara_leifang.html)。

Chrome WebGL 回归测试覆盖全部 40 套、3 种视口和 DPR 1、1.25、1.5、2。默认边界、待机、拖动缩放、动作切换及返回列表的滚动恢复均通过。首页入口、统一目录的模型深链和 20 张新增卡片图标另行通过浏览器检查。

排除示例包括 Zelos 的相近换色 `c198_10`、首批婚纱的进化变体 `c374_01`、首张图集只有 512×512 且呈现细节较弱的 Lisa · Battlesuit `c002_02`，以及外观偏幼的 Aria 造型。Brigid · Scarlet `c290_02` 的可见轮廓在 1303×551 视口中超出现有居中测试容差。Kalaratri 的 `c445_10` 和 `c445_11` 在 Pelom777 的表情文件含非法 JSON 数字，未进入正式目录。
