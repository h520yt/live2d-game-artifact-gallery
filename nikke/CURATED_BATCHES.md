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


## 展示柜数量仍停留在 16 条？

**原因先分清两层：** `nikke/curated_batches.json` 里的 35 个 ID 是“计划收藏”；网页实际读取的是 `nikke/viewer/nikke_manifest.json`，后者只由本机 `nikke/data/` 里成功下载并经过校验的 Spine 资源生成。`git pull` 只拉代码，不会把 Git 忽略的游戏素材下载到本机。

旧版还有三个问题：PNG 下载失败仍报告成功、只请求主 CDN 而未使用 GitHub 镜像、浏览器可能缓存旧 manifest。本次已修复这三个问题。

在仓库根目录的 PowerShell 依次执行：

```powershell
git pull
python nikke/scripts/install_batches.py --all
python nikke/scripts/install_batches.py --all --verify-only
python -c "import json; p='nikke/viewer/nikke_manifest.json'; d=json.load(open(p,encoding='utf-8')); print('当前清单角色数:',len(d['characters']))"
```

若网络报代理连接失败，默认代理是 `http://127.0.0.1:7897`；没有代理或代理没有运行时改用**直连模式**：

```powershell
python nikke/scripts/install_batches.py --all --direct
```

主 CDN 失败时脚本会尝试 `Nikke-db/Nikke-db.github.io` 的 GitHub 镜像；镜像也失败会明确输出「未找到图集 / 未找到骨骼 / 贴图不完整」。脚本即使返回非零退出码，已成功下载的文件仍会保留，重跑可继续补齐。

确认本地 `nikke_manifest.json` 数量增长后，访问 `http://127.0.0.1:8000/nikke/viewer/` 并刷新页面。查看器会强制重新读取最新 manifest，顶部显示四批计划数、已收录数及缺失 ID。这个“收录数”基于当前 manifest；精确文件级验证以 `nikke/data/_curated_batches_report.json` 为准。

如果仍显示旧数量，检查浏览器访问的项目路径是否就是执行下载命令的那个仓库（不要从另一个旧目录启动静态服务器）。如果 `--verify-only` 报告缺失，请使用正常安装命令补资源，单纯 `gen_nikke_manifest.py` 不会从网络下载新文件。
