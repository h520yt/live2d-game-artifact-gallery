# 多游戏展示柜 · 第三阶段重构（2026-11-18）

## 核心变化

第三阶段把「统一资源目录 → 指定皮肤」变成实际的深链接，并新增可复用的游戏查看器协议和新游戏插件入口，**不重新实现现有四个游戏的 Cubism / Spine 播放器**。

### 1. 统一查看器桥接协议

公共脚本：`shared/gallery_bridge.js`，四个游戏页面分别注册自己的适配器：

- `open(assetId)`：按原游戏准确资源 ID 打开指定皮肤。
- `listRoles()` / `selectRole(role)`：读取和切换姿态、模型角色或互动场景。
- `listActions()` / `playAction(name)`：读取和执行该引擎真实存在的动作。
- `GalleryViewerBridge.refresh()`：模型或骨骼初始化成功后刷新统一操作条。

统一资源目录点击皮肤时会生成 `?gallery_asset=<编码后的资源 ID>` 参数。游戏查看器解析参数并按准确 ID 定位，优先复用原有点击/加载流程。

各游戏的能力实现：

| 游戏 | 资源定位 | 姿态 / 特殊资源 | 动作播放 |
|---|---|---|---|
| 碧蓝航线 | 模型名或立绘资源名 | 模型与立绘场景保留原入口 | 调用 Cubism motion；同步 ArtMesh 动作状态 |
| NIKKE | 角色/皮肤 ID | 原有 fb / cover / aim 等姿态 | Spine 原有 `playAnim`，保留待机回落 |
| 重返未来1999 | 皮肤 ID + folder/channel/skin | 原有 Spine 姿态和静态原画 | Cubism motion 或 Spine 动画 |
| 棕色尘埃2 | costume ID | character / cutscene / interaction / interaction2 | 保留 `selectAnimation` 的 idle/mix 多段演出 |

可选参数：`gallery_role`、`gallery_motion`。只有当前游戏模型包含相应资源和动作时才执行；加载失败不假装成功。不存在的 ID 明确提示找不到，不能自动选择名称相似的其它资源。

**注：** 这是浏览器同页的统一接口，不是跨域远程控制接口。已加载的动画特效、动作编排和人体位置仍由各游戏旧代码负责；桥接层不更改原素材。

### 2. 新游戏插件注册和脚手架

`gallery/plugins.json` 维护非内置游戏（起初为空）。
`gallery_core/plugins.py` 对插件 ID、路径、重复注册、viewer/manifest 文件做校验；只允许 `games/<slug>/viewer/` 下标准目录，不执行来自 JSON 的 Python 代码。

示例：先预览生成方案：

```powershell
python scripts/new_game.py --id example_game --title "示例游戏" --dry-run
```

创建实际插件：

```powershell
python scripts/new_game.py --id example_game --title "示例游戏"
```

创建后的目录：

```text
games/example_game/
├── README.md
└── viewer/
    ├── index.html
    ├── viewer.js
    └── manifest.json
```

游戏版权资源放在 `games/example_game/data/`，默认由 .gitignore 忽略。

插件 manifest（generic-assets-v1）示例：

```json
{
  "schema_version": 1,
  "assets": [
    {
      "id": "skin_01",
      "title": "Skin 01",
      "renderer": "spine",
      "roles": {
        "character": [
          "../data/skin_01.skel",
          "../data/skin_01.atlas",
          "../data/skin_01.png"
        ]
      },
      "required_files": [
        "../data/skin_01.skel",
        "../data/skin_01.atlas",
        "../data/skin_01.png"
      ],
      "optional_files": [],
      "preview": "../data/skin_01_preview.png",
      "tags": ["待审核"],
      "metadata": {}
    }
  ]
}
```

执行：

```powershell
python scripts/gallery.py serve --port 8000
```

统一目录会自动读取插件注册表，加入该游戏和资产清单。**脚手架只提供真实静态图片预览，不会凭空拥有 Spine/Cubism 动作播放器**。为新游戏实现动态模型时，需要在自己的 viewer.js 替换占位实现，注册统一 Bridge 协议，不必再改动统一目录的游戏列表。

### 3. 测试及安全边界

- 路径必须仍在项目目录内，拒绝插件资源绝对路径、非法跳转。
- 资源 ID 全局采用 `game:source_id`；重复 ID 直接报错。
- 统一 URL 只接受安全长度的资源 ID，不执行用户传入的脚本或下载地址。
- 动作列表来自已加载的真实模型，不凭名字推断不存在的动作。
- 原页面的复杂动画、定位、贴图、前景控制和壁纸相关逻辑不被覆盖。
- 脚手架创建时不覆盖已有游戏；`--dry-run` 不修改文件或注册表。
- 新增 Node 契约测试、四游戏内联脚本语法检查、Python 插件注册与安全测试。

## 本地验收建议

在项目根目录使用：

```powershell
git fetch origin
git switch refactor/gallery-core-20261118
git pull --ff-only origin refactor/gallery-core-20261118
python scripts/gallery.py serve --port 8000
```

打开 `http://127.0.0.1:8000/gallery/`，点击皮肤，应进入对应游戏并自动选中目标。

建议用你本地已经真实安装的四个游戏各一款进行浏览器验收，验证：模型能否出现、动作列表和播放能否使用、切换游戏原有互动模式是否正常。重返未来1999 的部分源 ID 包含中文皮肤名称，已经允许 Unicode，并对路径控制字符做安全限制。

## 合并策略

先在 Draft PR 中完成 CI。使用 Windows 本地原始素材验证通过后，再人工决定是否合并 `main`。
后续继续优化失败恢复、插件下载器抽象、4K Wallpaper 导出工作流；它们不在本阶段冒充已完成功能。
