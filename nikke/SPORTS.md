# NIKKE 外观风格筛选：运动系

## 筛选原则

风格标签与资源类别（角色 / 活动 / 剧情）独立。运动系包括健身、跑步、啦啦队、拳击、滑板、棒球等与运动直接相关的角色或服装。原有御姐、腿部重点偏好也记录在同一份风格索引中，支持多个标签同时存在。标签属审美整理，不是游戏官方稀有度或题材分类。

角色和皮肤清单：`nikke/style_tags.json`。脚本 `gen_nikke_manifest.py` 会把 ID 匹配到已有本地资源并生成 `tags`；没有下载的皮肤不会因为加入标签而冒出模型。

## 建议安装的运动系资源

| ID | 角色 / 皮肤 | 分类 |
|---|---|---|
| c240 | 鲁玛妮 Rumani | 健身教练、紧身运动裤 |
| c242 | 富克旺 Folkwang | 跑步运动员 |
| c550 | 贝伊 Bay | 啦啦队 |
| c551 | 克雷伊 Clay | 啦啦队 |
| c551_01 | 克雷伊 · 啦啦队训练服 | 训练服 |
| c141 | 米尔克 Milk | 拳击 |
| c141_01 | 米尔克 · 极限战士 | 格斗服 |
| c270_02 | 布兰儿 · 77号击球员 | 棒球 |
| c271_02 | 诺亚尔 · 棒球啦啦队 | 棒球应援 |
| c241 | 艾菲涅尔 Epinel | 滑板；运动属性明确，但不属于优先推荐的御姐风格 |

这里的 ID 已在 Nikke-db 的 `l2d.json` 索引中找到；**索引有记录并不代表 CDN 一定存在完整 fb/cover/aim 文件**。实际下载由 `fetch_nikke.py` 检测资源并跳过失败项。

## Windows 执行方法

在项目根目录执行：

```powershell
git pull
python nikke/scripts/install_style.py 运动系 --dry-run
python nikke/scripts/install_style.py 运动系
```

此命令会复用已存在的 `fetch_nikke.py` 批量下载并执行 `gen_nikke_manifest.py` 更新资源清单。数据下载到 `nikke/data/<ID>`（已被 .gitignore 忽略），不会随 Git 提交。

浏览器刷新 `http://127.0.0.1:8000/nikke/viewer/`，使用顶部「风格筛选 → 运动系」。

已有下载资源也可以单独刷新标签（不需要联网）：

```powershell
python nikke/scripts/gen_nikke_manifest.py
```

其他风格同样可以按需安装：

```powershell
python nikke/scripts/install_style.py 御姐
python nikke/scripts/install_style.py 腿部重点
```

说明：部分换装在游戏里是原角色的服装而不是独立可招募妮姬；这里按展示柜「资源 ID」归档。运动属性不等于御姐属性，尤其是艾菲涅尔属于运动风格扩展，而不是原有成熟御姐的首选。
