# 棕色尘埃2 · 精选动态皮肤展示柜

本展示柜**只展示用户需要的两类皮肤**：高规格特殊皮肤，以及符合「成熟御姐、黑丝/网袜、腿部重点」偏好的其他动态服装。普通无关服装不进入页面，也不进入默认下载任务。

## 精选范围

| 范围 | 数量 | 依据 |
| --- | ---: | --- |
| Prestige Skin（尊爵皮肤） | 6 | 已接入的完整尊爵系列 |
| Special Skin（特殊皮肤） | 8 | 上游特别皮肤目录分类 |
| 视觉风格精选 | 8 | 对照宣传原画检查过的外观；详见 `curated_style.json` |
| **总计** | **22** | 去重后 22 套 |

风格精选包括 Eclipse · Nightmare Bunny、Liatris · Maid Name R、Celia · The Curse、Celia · Masquerade Bunny、Eleaneer · Piercing Magic Bow、Levia · Track and Field Captain、Nebris · New Hire、Morpeah · Daydream Bunny。每条都附有筛选原因与来源链接。**“过膝靴”不会误标成“黑丝”，“运动系”仅在确实突出腿部时保留。** 标签是个人外观筛选，不是游戏官方等级；Spine 动画实际还原度需本机检验。

> 原始 `costume_catalog.json` 仍保存 200 条第三方资源索引，方便以后核对和追加，但该文件只是**后台资料**。展示柜和下载器都会与 `curated_style.json` 白名单相交，只允许 6 款 Prestige、8 款 Special Skin 和 8 套风格精选；不会重新展示或默认下载全部 206 套。

## 本地安装（Windows PowerShell）

```powershell
cd D:\project_python\live2d-game-artifact-gallery
git pull origin main

# 先查看全部精选与本地已安装状态（完全离线）
python brown_dust2/scripts/install_prestige.py --list

# 下载全部22套精选，不会下载其它178套未入选的服装
python brown_dust2/scripts/install_prestige.py --collection all

# 或者分开安装：14款特殊皮肤、8套风格精选
python brown_dust2/scripts/install_prestige.py --collection special
python brown_dust2/scripts/install_prestige.py --collection style

# 可选：只同步已核对的黑丝兔女郎 Eclipse
python brown_dust2/scripts/install_prestige.py --only costume-000706

# 离线检查完整性，刷新网页
python brown_dust2/scripts/install_prestige.py --verify
python -m http.server 8000
```

页面：`http://127.0.0.1:8000/brown_dust2/viewer/index.html`。

筛选项：**全部精选 / 特殊皮肤 / 御姐·腿部 / 成熟御姐 / 黑丝·网袜 / 腿部重点 / 有互动 / 已安装**。支持搜索、角色/技能/互动切换、大屏模式、完整人物适配、PNG 截图。

安装器会在每次下载时检查 .atlas、.skel、atlas 引用贴图。仅完整的本地资源才加入 `manifest.json`。已有资源会跳过，不需要重新下载。当前脚本不会删除此前已下载但不再展示的资源，避免破坏其他收藏。

如果某些上游目录不存在、存在分层背景或 Spine 版本差异，会报告下载或播放失败；**目录选中不等于资源已安装或画面已验证**。

## 管理与扩展

- `curated_prestige.json`：六款尊爵配置，包含补全的互动资源目录。
- `curated_style.json`：只有八套风格精选的 ID、偏好标签、筛选依据和参考链接。
- `costume_catalog.json`：完整原始索引（不直接展示、不自动安装）。
- `scripts/sync_costume_catalog.py`：更新后台原始资源索引，不会自动扩大精选名单。
- `scripts/install_prestige.py`：保留原命令名以兼容旧操作，现默认安装 **全部精选**。支持 `--collection special`、`style`、`prestige`、`interactive`、`--only`、`--character`、`--offset`、`--limit`、`--list` 和 `--verify`。
- `data/`：只在本地保存游戏素材，已在 Git 中忽略；游戏资源版权属于原权利人。

以后如需增加新的御姐/黑丝/腿部重点套装，应先核对外观，再在 `curated_style.json` 添加稳定服装 ID 与外观依据，不能因为角色名字相同就把她的所有服装都混进来。
