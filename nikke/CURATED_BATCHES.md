# NIKKE 四批黑丝 / 御姐收藏计划

基于 NIKKE-db 社区动态角色索引（2026-11-16 核对）。**35 个不同资源 ID 已匹配索引；不代表全部 CDN 文件齐全，也不代表全部已在本机安装。**

## 四批内容

| 批次 | 主题 | ID 数 | 说明 |
|---|---|---:|---|
| 1 | 黑丝核心 | 6 | 玛娜、艾达、普丽瓦蒂·严厉教诲、爱德·特工兔女郎、梅登·冰玫瑰、艾玛原装 |
| 2 | 黑丝与网袜扩展 | 9 | 梅登·秘密护士、银华战术升级、诺亚尔、普丽瓦蒂行政正装、诺伊斯、阿莉亚、露菲奢侈兔等 |
| 3 | 成熟御姐扩展 | 14 | 樱花黑夜潜行、朵拉、罗珊娜、牡丹、布丽德、尤尔夏、D、2B、伊芙等 |
| 4 | 新皮肤待复核 | 6 | 玛娜醉酒兔、舒格杀手兔、米尔克花漾兔、薇尔维特魅惑兔、吉尔提神力兔、森疾速兔 |

详细 ID、中文名称和描述以 **`nikke/curated_batches.json`** 为准，不依赖前端手写的 ID 列表。
风格标签集中在 **`nikke/style_tags.json`**，保留此前「御姐、腿部重点、运动系」，新增加「黑丝、网袜、长筒袜、紧身裤、紧身衣、长靴、兔女郎、待复核」。

> **标签边界：** 黑丝与网袜、深色长筒袜、黑色紧身裤分别记录。第四批标记「待复核」，避免未经验证就判定有黑丝。标签是人工整理，不属于官方游戏数据。

## Windows 下载（仓库根目录）

```powershell
git pull
# 先预览 35 个目标
python nikke/scripts/install_batches.py --all --dry-run

# 一键安装四批，已完整下载的会复用（fetch_nikke.py 负责断点续传）
python nikke/scripts/install_batches.py --all

# 只重试某一批
python nikke/scripts/install_batches.py 4

# 下载后核验，跳过 CDN
python nikke/scripts/install_batches.py --all --verify-only
```

下载的 `.skel` / `.atlas` / `.png` 进入 `nikke/data/<ID>/`，该目录被 `.gitignore` 忽略，不将游戏素材提交 Git。

安装器会复用现有 `fetch_nikke.py` 与 `gen_nikke_manifest.py`；生成清单后检查 **skel + atlas + 全部贴图页**，分四种状态：

- `ready`：文件层面存在完整 `fb` 姿态（尚需打开浏览器检查动作渲染）
- `partial`：没有完整 `fb`，但有完整 `cover` / `aim` / 其他姿态
- `incomplete`：有条目，但缺少必要文件
- `missing`：没有生成该资源条目

结果记录在 `nikke/data/_curated_batches_report.json`。只要并非全部 `ready`，脚本就返回非零退出码；这是提醒你检查缺失，不表示此前成功下载的资源被回滚。

## 查看与导出

```powershell
python -m http.server 8000
```

浏览器访问 `http://127.0.0.1:8000/nikke/viewer/`。在收藏批次下拉框选择「第一批」到「第四批」；风格下拉框可单独选择「黑丝」「网袜」等。组合筛选仅显示**实际已安装**且已生成 manifest 的资源。

静态 PNG：沿用已有 `render_art.mjs`，在另一个终端启动 HTTP 服务后，可批量导出已安装的 fb 姿态（`--all` 可能包含其他已安装角色）：

```powershell
node nikke/scripts/render_art.mjs --all
python nikke/scripts/gen_nikke_manifest.py
```

**注意：** Spine 渲染帧不是游戏独立发布的完整原画；背景和原画素材需另外取得。导出静态图需要本机具备 Playwright / Chromium，安装方法见 `nikke/ART_SCENE.md`。

## 回归测试

不需要下载游戏素材：

```powershell
python -m unittest discover -s nikke/tests -v
```

验证四批数据无重复、选批次行为、缺少贴图不算完整等。
