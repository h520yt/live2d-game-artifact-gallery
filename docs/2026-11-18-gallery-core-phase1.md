# 皮肤展示柜多游戏重构 · 第一阶段（2026-11-18）

## 目标与边界

在**不修改原有四款游戏的素材路径、页面入口、下载器与 manifest** 的前提下，
建立统一资源索引、本地文件核查方式，以及可复用的碧蓝航线皮肤 ID 消歧规则。

本阶段**不迁移到其他查看器**，不引入 Vue 或后台数据库，不重新下载已安装素材，
也不承诺 Cubism / Spine 的所有动作、互动与动态特效都已还原。

## 新增模块

- `gallery_core/catalog.py`：将四套原始 manifest 转为统一 v1 数据结构。
- `gallery_core/azur_metadata.py`：统一处理资源名、皮肤 ID、NPC 重名与显式覆盖。
- `scripts/gallery.py`：统一索引生成、跨游戏查询和本地入口文件检查。
- `tests/test_gallery_core.py`：无需下载游戏素材的单元测试。
- `gallery/catalog.json`、`gallery/verification-report.json`：本地生成产物，不进入 Git。

现阶段采用只读 manifest 适配，未来新游戏可以添加适配函数，
注册到 `GAME_MANIFESTS` 和 `ADAPTERS`。下载、重建与渲染层将在后续逐步适配。

## 使用方法（仓库根目录）

```powershell
git switch refactor/gallery-core-20261118
python -m unittest discover -s tests -p test_gallery_core.py -v
python scripts/gallery.py sync-index
python scripts/gallery.py list --game nikke --tag 运动系
python scripts/gallery.py list --game brown_dust2
python scripts/gallery.py verify
```

`sync-index` 仅读取已有 manifest 并生成统一目录，没有网络请求或素材写入。
`list` 当前直接读取游戏 manifest 重新构造索引，便于看到新安装的资源。
`verify` 生成 `gallery/verification-report.json`，默认仅生成报告。
要把缺失文件视为失败，执行 `python scripts/gallery.py verify --strict`。

注意：仓库本身不包含版权素材。刚克隆的环境出现 missing 是预期现象，
不代表统一索引逻辑错误。

## 统一索引 v1

资源字段包括：

- `id`：例如 `nikke:c043`，由游戏名和游戏内资源 ID 组合而成。
- `game` / `source_id` / `title` / `renderer`：通用信息。
- `roles`：模型、姿态、立绘、背景或互动场景等资源路径数组。
- `preview` / `tags` / `metadata`：预览、已确认或待审核风格标签、游戏扩展字段。
- `required_files` / `optional_files`：必要入口、可选变体。
- `verification`：生成时一律 `not_checked`，索引存在不代表素材已验收。

碧蓝航线：立绘与 Live2D 按同一资源名合并，同一款皮肤的 `_hx` 变体保留为多个模型入口。
NIKKE：`fb` / `cover` / `aim` 姿态保留在同一角色下。
重返未来1999：`unique` / `jukebox` 是筛选视图，不当成重复模型计数。
棕色尘埃2：保留 `character` / `cutscene` / `interaction` / `interaction2` 的资源角色。

## 文件状态

| 状态 | 含义 |
|---|---|
| `entrypoints_present` | 已声明的必要入口文件存在，不等于动画和互动已验证 |
| `partial` | 部分必要入口存在，部分缺失 |
| `missing` | 全部必要入口缺失 |
| `no_entrypoints` | 清单没有可检查的必要入口 |

Cubism 模型内部贴图/动作依赖与 Spine 动作可用性仍需深度校验；
本阶段只是跨游戏的入口核查，不能用作完整画面验收。

## 皮肤 ID 消歧规则

第五批和第六批都调用 `gallery_core.azur_metadata`：

1. 显式覆盖的 ID 必须出现在当前元数据中，否则主动报错。
2. 如果只有一个候选，采用该候选。
3. 如果非 NPC 区间（900000 至 999999）恰好只有一个候选，采用该候选。
4. 其余情况第五批报错；第六批可保留 `-1`，继续按资源名下载。
5. 不会默认选第一个候选或伪造不存在的皮肤 ID。

原命令不变：

```powershell
python azur_lane/scripts/install_batch5.py --plan
python azur_lane/scripts/install_batch6.py --plan
```

## 兼容与下一阶段

改动仅在 `refactor/gallery-core-20261118` 分支，原 `main` 未修改。
本地素材目录继续保持原样，切回 `main` 即可回滚代码。

第五、六批共 40 项候选已迁入 `azur_lane/config/curated_collections.json`。
下一步将第 2 至 4 批迁入声明式配置，并抽取通用下载/校验流程；
再整合前端列表、搜索、收藏和标签。特殊 Cubism / Spine 互动依然由各引擎单独实现。
