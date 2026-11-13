# 《重返未来：1999》本地动态资源预览

本模块支持 Cubism Live2D（.moc3）和 Spine（.skel）。在本地按角色 ID 下载后，用网页切换动作、表情、战斗、房间及 UI 动画；无需安装游戏客户端，也不必克隆完整资源仓库。

数据来源：myssal/Reverse-1999-CN-Asset（GitHub），使用它的 mappings/ArcanistMap.json 映射角色及皮肤。

## 快速上手（Windows PowerShell，仓库根目录执行）

    python reverse1999/scripts/sync.py list --search 佩施塔

    # 佩施塔（白雪活动）初始形态：Spine 4.2
    python reverse1999/scripts/sync.py download 315901

    # 佩施塔「童话出逃日」
    python reverse1999/scripts/sync.py download 315902

    python -m http.server 8000

访问 http://localhost:8000/reverse1999/viewer/ ，搜索「佩施塔」，可以切换 ui、room、fight 等姿态和动画。

下载脚本会自动获取官方 Spine Web Player 4.2 JS/CSS 到本地（不提交 Git）。也可单独执行：

    python reverse1999/scripts/sync.py setup-runtime

## 搜索、选择格式及检查全部皮肤

    python reverse1999/scripts/sync.py list --search 槲寄生
    python reverse1999/scripts/sync.py download 300301 --kind cubism
    python reverse1999/scripts/sync.py download 300301 --kind spine
    python reverse1999/scripts/sync.py download 300301 --kind both

    # 更新角色映射与 GitHub 目录快照后，逐项核对
    python reverse1999/scripts/sync.py audit --refresh

    # 输出所有缺少其中一种动画格式的皮肤
    python reverse1999/scripts/sync.py audit --missing

    # 不重新下载，只重建本地预览列表
    python reverse1999/scripts/sync.py manifest

--kind auto 默认优先 Cubism，缺少 Cubism 时自动选 Spine。audit 输出完整明细到 reverse1999/config/audit-report.json，核查的是上游目录存在，不能据此断言每一个文件都可成功渲染。

由于部分 Cubism 目录包含 v1a6_、v4a0_ 等版本前缀，代码会按皮肤 ID 精确匹配实际目录，而不是仅依赖原映射链接。

## 文件结构

- viewer/index.html：同一页面兼容 Live2D 与 Spine
- viewer/manifest.json：只列出本地已下载的资源
- scripts/sync.py：统一命令行
- scripts/spine.py：Spine 下载、目录审计及官方 4.2 播放器安装
- data/models/：Cubism 模型、贴图、动作（忽略 Git）
- data/spine/：Spine .skel/.atlas/.png（忽略 Git）
- vendor/：从官方 CDN 按需安装的 Spine 4.2 JS/CSS（忽略 Git）
- config/：角色映射缓存、目录快照及审计结果（忽略 Git）

## 兼容性限制

已检查佩施塔及部分老角色的骨骼文件头为 Spine 4.2.36。安装官方 @esotericsoftware/spine-player@4.2.87（同主版本）进行播放；对其他版本会提示不兼容。与 Unity 游戏场景有关的特效可能不能完整还原。

Python 3.9+，无需安装第三方 Python 库。GITHUB_TOKEN 环境变量可以提高 GitHub API 请求额度，请勿写入仓库配置。游戏美术资源版权属于原权利方，工具仅供个人本地欣赏、研究，不提交或分发原始游戏资源。


## 商城高级衣着场景（试验性组合预览）

第一套样板：贝丽尔「释命运以弦音」 313403。上游已核实：

- 背景：singlebg/skin2dbg/313403.png
- 商城展示骨骼：roles_bust/v4a0_313403_ble_skinstorecardface/
- 骨骼版本：Spine 4.2.36
- 同 ID 的普通人物骨骼：roles/v4a0_313403_ble（独立于商城展示骨骼）

在项目根目录执行：

    git pull origin main
    python reverse1999/scripts/sync.py scene 313403

313403 样板现在优先使用已核实的静态资源清单，通过 raw.githubusercontent.com 直接下载，不再调用 GitHub API 查询目录，通常无需 GITHUB_TOKEN。若原始资源直链失败，会尝试 jsDelivr 镜像。其他尚未验证的商城皮肤仍可能使用 GitHub API。
    python -m http.server 8000

打开 http://localhost:8000/reverse1999/viewer/，搜索「贝丽尔」，选择「商城场景（组合预览）」。

scene 命令先核查该皮肤的专属 skin2dbg 背景和角色商城 skinstorecardface / skinstore / skinsuit 的自包含骨骼，下载后生成本地记录。场景仅列出完整下载、骨骼版本为 4.2 的资源。材质、前景分层、Unity 后处理和交互脚本尚未还原；明确标注为「原始商城素材组合预览」，绝不宣称游戏内效果 100% 复刻。

原始游戏素材只保存在 reverse1999/data/scenes/<皮肤ID>/，由 .gitignore 忽略，不提交 Git。
