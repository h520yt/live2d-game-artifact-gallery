# 《重返未来：1999》本地 Live2D 资源预览

这是 live2d-game-artifact-gallery 的第三个游戏入口。只使用已公开的社区资源库 myssal/Reverse-1999-CN-Asset，不要求安装游戏本体，也不会下载完整仓库。

## 快速体验（Windows PowerShell）

在整个项目的根目录执行：

    python reverse1999/scripts/sync.py list --search 槲寄生
    python reverse1999/scripts/sync.py download 300301
    python -m http.server 8000

打开 http://127.0.0.1:8000/reverse1999/viewer/ ，选择模型，播放动作、表情，滚轮缩放和拖动。

按皮肤名查找：python reverse1999/scripts/sync.py list --search 永不迟到

重建本地索引：python reverse1999/scripts/sync.py manifest

刷新角色名映射：python reverse1999/scripts/sync.py list --refresh

要求 Python 3.9+，无需额外 Python 第三方依赖。GITHUB_TOKEN 为可选环境变量，可提高 GitHub API 请求额度；**不要将 token 写入项目文件**。

## 文件说明

- viewer/index.html：独立 Live2D 展示页面，复用 shared/vendor 内的 Cubism/PixiJS runtime
- viewer/manifest.json：本地模型索引（由脚本生成）
- scripts/sync.py：读取角色映射、按指定皮肤 ID 下载完整模型文件、生成索引
- data/models/：下载的 moc3、model3.json、textures、motions、expressions，已被 Git 忽略
- config/ArcanistMap.json：社区角色映射本地缓存，已被 Git 忽略

## 范围与限制

首批支持 live2d/roles 中带 model3.json 的 Cubism 模型，不处理 roles 下的 Spine 战斗动画。
资源下载取决于上游公开仓库的可访问性、GitHub API 速率限制及模型兼容性。
特殊材质、Unity 场景和部分互动效果不一定能由通用 Cubism runtime 还原。
只供个人本地研究、欣赏；不向 GitHub 提交原始游戏资源。
