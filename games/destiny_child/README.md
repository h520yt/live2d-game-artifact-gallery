# 天命之子 · Live2D 皮肤展示柜

按照第四阶段插件接入规范，和其它游戏统一为「卡片 → 全屏独立舞台 → 返回原位置」，不新增游戏内分类页。

来源：[Pelom777/DestinyChildLive2D](https://github.com/Pelom777/DestinyChildLive2D)，上游提交 `63e43d034512946c5eb308754f18a1865382bdf6`。名称参考 [Live2D-DCG](https://github.com/Live2D-DCG/Live2D-DCG.github.io)。

首批20套，模型为 Cubism 2 `model.json` / `.moc` / 纹理 / `.mtn` 动作。没有确认人物＋背景的完整场景时仅使用角色原图标作为封面，绝不将素材碎片伪装成完整原画。

## PowerShell（仓库根目录）

```powershell
python games/destiny_child/scripts/sync.py --plan
python games/destiny_child/scripts/sync.py --id c001_14
python games/destiny_child/scripts/sync.py --all
python scripts/gallery.py sync-index
python scripts/gallery.py verify
python scripts/gallery.py serve
```

在 `http://127.0.0.1:8000/gallery/` 选择「天命之子」。也可访问 `games/destiny_child/viewer/index.html`。

本地模型在 `games/destiny_child/data/`（Git 忽略）。下载成功与入口文件存在不等于浏览器逐套动画已验收。出错可运行 `python games/destiny_child/scripts/sync.py --id c001_14 --force`。原游戏资源版权归权利方所有，仅作个人合法本地欣赏。
