# 棕色尘埃2 · 精选动态皮肤展示柜

只展示 Prestige 尊爵、Special Skin 特殊皮肤，以及符合成熟御姐、黑丝/网袜或腿部重点偏好的其它服装。原始 200 套目录仍作为后台资源索引，不会自动安装。

## 独立互动核查结果

| 类型 | 收录 | 找到专属互动 |
| --- | ---: | ---: |
| Prestige Skin | 6 | 6 |
| Special Skin | 8 | 0（官方设计不含独立互动） |
| 外观风格精选 | 12 | 7 |
| **合计** | **26** | **13** |

官方明确：Special Skin 只有新立绘、技能演出和新角色动作，不包括 Fated Guest / Prestige 的独立互动功能。**不能为它们冒用别的衣装的 illust_dating 资源。**

仍未找到独立互动对应目录的五套精选为：Celia · Masquerade Bunny、Celia · The Curse、Eleaneer · Piercing Magic Bow、Levia · Track and Field Captain、Liatris · Maid Name R。它们已有的人物和技能 Spine 动画仍可播放，只是不应该假装有互动场景。

开发者公告：
- https://dotgg.gg/brown-dust-2/45th-developer-notes-1000th-day-update-2/
- https://dotgg.gg/brown-dust-2/%F0%9F%93%A2march-25th-utc-routine-maintenance-and-update/

## 本次真实补齐四套互动索引

| 角色服装 | 互动资源 ID | 外观 |
| --- | --- | --- |
| Sylvia · Bikini Agent | `illust_dating8` | 比基尼、腿部重点 |
| Wilhelmina · Water Park Queen | `illust_dating6` | 成熟御姐、泳装腿部 |
| Dalvi · Bright Moon | `illust_dating20` | 成熟御姐、坐姿腿部 |
| Olivier · Retired Legend | `illust_dating16` | 成熟御姐 |

已分别检查四套上游 atlas 存在，含 6、9、8、8 张贴图页。映射来自同一衣装的模型，不跨角色借用。**这些是资源索引核验，尚未在你的本机下载或渲染。** 每条依据和美术参考链接收录在 `curated_style.json` 中。

## 本地命令（Windows PowerShell）

```powershell
cd D:\project_python\live2d-game-artifact-gallery
git pull origin main

# 离线核对所有精选服装互动状态
python brown_dust2/scripts/install_prestige.py --audit-interactions

# 只下载真正有独立互动索引的13套互动资源（增量跳过已有）
python brown_dust2/scripts/install_prestige.py --collection interactive --role interaction

# 如需把四套新增服装的人物/技能模型也安装完整
python brown_dust2/scripts/install_prestige.py --only costume-001006
python brown_dust2/scripts/install_prestige.py --only costume-067603
python brown_dust2/scripts/install_prestige.py --only costume-061302
python brown_dust2/scripts/install_prestige.py --only costume-003604

# 生成真实安装清单，再启动展示柜
python brown_dust2/scripts/install_prestige.py --verify
python -m http.server 8000
```

访问 `http://127.0.0.1:8000/brown_dust2/viewer/index.html` 后强制刷新浏览器。使用「有互动」筛选可查看 13 套独立互动来源。卡片区分：**独立互动已安装、互动待下载、官方无独立互动、未找到对应互动**。

## 索引与版权

- `curated_prestige.json`：六款尊爵和真实互动映射
- `curated_style.json`：12 套审过造型的风格精选与来源
- `costume_catalog.json`：原始 200 条后台索引（不直接展示、不批量下载）
- `scripts/install_prestige.py`：提供 `--role interaction`、`--audit-interactions`、`--collection interactive`、`--verify`
- `data/`：游戏素材只存本地且 Git 忽略；不删除之前已下载的素材

只有本地的 skel、atlas 和全部所需贴图通过完整性检查后，才标记为已安装。原始美术与动画素材版权归游戏权利人所有。
