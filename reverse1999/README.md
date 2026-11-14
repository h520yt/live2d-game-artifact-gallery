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

    python -m http.server 8000

313403 样板优先使用已核实的静态资源清单，通过 raw.githubusercontent.com 直接下载，不再调用 GitHub API 查询目录，通常无需 GITHUB_TOKEN。若原始资源直链失败，会尝试 jsDelivr 镜像。其他尚未验证的商城皮肤仍可能使用 GitHub API。

打开 http://localhost:8000/reverse1999/viewer/，搜索「贝丽尔」，选择「商城场景（组合预览）」。

scene 命令先核查该皮肤的专属 skin2dbg 背景和角色商城 skinstorecardface / skinstore / skinsuit 的自包含骨骼，下载后生成本地记录。场景仅列出完整下载、骨骼版本为 4.2 的资源。材质、前景分层、Unity 后处理和交互脚本尚未还原；明确标注为「原始商城素材组合预览」，绝不宣称游戏内效果 100% 复刻。

原始游戏素材只保存在 reverse1999/data/scenes/<皮肤ID>/，由 .gitignore 忽略，不提交 Git。

## 另一套实测通过浏览器的完整展示：露西「生如行棋」

本项目另加入同 ID 的露西衣着 **308603**，可直接运行：

    python reverse1999/scripts/sync.py showcase 308603

组合资源：背景 singlebg/skin2dbg/308603.png，人物商城动画 roles_bust/v2a8_308603_lxxx_skinstore/。 308603 已核实每个文件的体积并使用原始素材直链下载，通常无需 GitHub API 配额。页面右侧能切换背景可见性、背景覆盖/适配及人物位置和缩放。已通过 GitHub Actions 从上游实际下载素材、用 Chromium 加载并对背景/人物合成画面进行像素对比。预览与真正 Unity 游戏展示仍可能存在视觉差异。技术说明见 docs/2026-11-13-完整皮肤展示.md。

已有的 `scene 313403` 命令与贝丽尔样板保持不变；`showcase 308603` 是另一套独立可测试的场景下载入口。

### 贝丽尔 313403：Cubism 原始动态衣着展示

上游另外存在 live2d/roles/v4a0_313403_ble/v4a0_313403_ble.model3.json，包含 34 个动作组、14 条表情配置（7 个不同表情文件）、57 张贴图和 9.37MB 的 moc3 骨骼模型。其中有 b_idle、b_ruchang（入场）、b_yanzou（演奏）和 b_jiaohu01～04（交互）。

从本次更新开始，重新执行下面的命令，会在原有商城 Spine+背景素材之外继续下载这套 Cubism 动态衣着及 model3.json 声明的全部依赖：

    git pull origin main
    python reverse1999/scripts/sync.py scene 313403

浏览器进入 http://localhost:8000/reverse1999/viewer/，搜索「贝丽尔」后会出现「Live2D 动态衣着+专属背景」和「商城卡面 Spine+背景」两种展示形式，前者支持选择 34 组动作及表情。固定的 313403 资源从 GitHub 原始文件直链下载，不调用 api.github.com，因此通常不需要 GITHUB_TOKEN。

注意：网页中的 Live2D 动作、同皮肤背景已使用上游真实资源；但主界面入场特效的调用时机、前景遮挡、Unity 粒子及完整交互剧本尚未复刻，不能宣称 100% 还原商城效果。


## 女性角色 UNIQUE 最高档衣着完整展示柜（国服 4.1，2026-11-14）

已收录 **12 套 UNIQUE**（最高品质、通常 ¥98/1680 粹雨滴）。皮肤档次与动画引擎类型不同：即使是 UNIQUE，也不保证所有 Unity 粒子、场景脚本能在网页中原样复刻。资源列表已同时加入 viewer/unique-catalog.json，即使尚未下载也能在左侧「Unique 最高档」中看到 12 套和下载状态。

| 角色 | UNIQUE 衣着 | 皮肤 ID | 实装版本 |
|---|---|---|---|
| 星锑 | 启航！向明日 | 302504 | 1.9 |
| 37 | 泉眼深处 | 306604 | 2.2 |
| 曲娘 | 壁上桃源 | 308303 | 2.5 |
| 露西 | 生如行棋 | 308603 | 2.8 |
| 天使娜娜 | 恶之果 | 310003 | 3.2 |
| 梁月 | 照雪明 | 311003 | 3.4 |
| 牙仙 | 彩衣曲 | 305305 | 3.4 |
| 珐琅眼 | 醒时声 | 314403 | 3.7 |
| 诺谛卡 | 名以光辉 | 312003 | 3.7 |
| 纸信圈儿 | 原子时报晓 | 310504 | S02 联动 |
| 狩勋女巫红弩箭 | 虹色冠冕 | 315503 | 4.0 |
| 贝丽尔 | 释命运以弦音 | 313403 | 4.0 |

这 12 个 ID 恰好对应上游 singlebg/skin2dbg 中 12 张完整专属背景，同时在 live2d/roles 中都有已核实的版本前缀 Cubism 模型目录。数据源：myssal/Reverse-1999-CN-Asset；皮肤等级可核查 [灰机中文维基](https://res1999.huijiwiki.com/wiki/%E5%88%86%E7%B1%BB%3A%E8%A1%A3%E7%9D%80)。

在 **VS Code 项目根目录**执行：

    git pull origin main

    # 只显示 12 套的名字、皮肤 ID、本地下载状态
    python reverse1999/scripts/sync.py unique list

    # 一次性下载全部 12 套背景 + Live2D 模型 + 动作 + 表情
    python reverse1999/scripts/sync.py unique all

    # 或者单独下载某一套，例如 37「泉眼深处」
    python reverse1999/scripts/sync.py unique 306604

    # 如果已有本地 HTTP 服务不用重启
    python -m http.server 8000

打开 http://localhost:8000/reverse1999/viewer/ ，切换「Unique 最高档」。每套支持专属背景 + Cubism 原生角色动画，右侧可切换动作、表情；默认播放 b_idle（若该衣着存在）。

下载器不依赖 GitHub 目录 API，直接从已核实的 raw.githubusercontent.com 文件地址按需要下载，原始直链失败会按本项目现有策略尝试 jsDelivr 镜像。分皮肤下载，最多并发 5 个文件，失败可重新执行，已下载完整的文件会复用。即使下载部分失败，也会保留已完整下载的皮肤进入资源索引，缺失的皮肤显示为「待下载」。

游戏素材下载在本机的 reverse1999/data/unique/<皮肤ID> 中（被 Git 忽略），不上传版权美术资源到公开 GitHub 仓库。此功能为展示柜、Wallpaper Engine 网页壁纸的素材验证基础；Wallpaper Engine 导出和 Unity 全场景特效复刻是独立的后续功能，不应与此次「已收录资源」混为一谈。
