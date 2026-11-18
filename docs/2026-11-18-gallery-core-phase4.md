# 多游戏展示柜 · 第四阶段收尾与发布验收（2026-11-18）

## 本阶段目标

第四阶段是**架构重构的收尾**，不增添新的游戏平台和渲染引擎。
完成索引/本地核验一致性修复、插件命令兼容、静态诊断、HTTP 路由与可选 Chrome 浏览器烟测；
真实版权素材及特殊互动效果的人工验收由本地 Windows 环境完成。

## 已落地改造

- `gallery_core/catalog.py` 为稳定资源数据生成 SHA-256 `catalog_digest`，其值不取决于运行时间。
- `verify_catalog` 返回相同摘要；`gallery/app.js` 仅采用摘要一致的校验报告，旧报告不会对应到新目录。
- `gallery/styles.css` 明确支持 `[hidden]`，避免分页等隐藏控件被样式意外显示。
- `scripts/gallery.py list --game` 允许已经注册的新游戏 ID；`sync-index` 统计包括新增游戏。
- `gallery_core/doctor.py` 和 `python scripts/gallery.py doctor` 校验游戏页面、桥接注册、资源归属、路径等；生成本地忽略的 `gallery/doctor-report.json`。
- `tests/test_gallery_phase4.py` 在不下载素材的前提下测试索引摘要、诊断、实际 HTTP 路由。
- `scripts/smoke_browser.py` 在找到本地 Chrome/Chromium 时执行页面 JS、检查统一目录卡片及直达 URL。未安装浏览器时会明确跳过。
- GitHub Actions 加入第四阶段静态诊断、HTTP 与浏览器烟测。

请区分三种验收：

| 层级 | 代表能力 | 能说明什么 |
|---|---|---|
| 单元与语法测试 | Python / JS / 四游戏已有逻辑 | 代码结构和核心函数未明显回退 |
| HTTP 与浏览器目录烟测 | HTTP 路由、统一目录初始化与链接 | 页面能够加载、生成预期条目 |
| Windows 本地真实素材实测 | Cubism / Spine / 动作/图层/互动 | 动态效果是否真正可用 |

**前两种不能代替第三种。** 仓库不提交游戏版权素材，因此 GitHub CI 不具备完整的动态皮肤验收条件。

## Windows 本地验收操作

请先确认代码修改已保存，避免切换分支覆盖自己的未提交工作。

~~~powershell
cd D:\project_python\live2d-game-artifact-gallery
git fetch origin
git switch refactor/gallery-core-20261118
git pull --ff-only origin refactor/gallery-core-20261118

# 1. 生成统一资源索引
python scripts/gallery.py sync-index

# 2. 检查资源注册、页面和桥接契约；详情见 gallery/doctor-report.json
python scripts/gallery.py doctor

# 3. 检查已下载的本地必要入口文件；详情见 gallery/verification-report.json
python scripts/gallery.py verify

# 4. 重新生成当前目录与验收报告，并启动本机网页
python scripts/gallery.py serve --port 8000
~~~

浏览器地址：<http://127.0.0.1:8000/gallery/>。
`serve` 监听 `127.0.0.1`，不会下载或删除任何版权素材。
如果更新了素材后不重启服务器，请重新执行 `sync-index` 与 `verify` 并刷新页面。

## 必须人工确认的验收清单

- [ ] 在统一目录选择四个游戏，每个游戏至少选一套**已经实际安装**的皮肤，确认能准确直达而非默认打开第一项
- [ ] 碧蓝航线：真实 Live2D 模型、动作触发、ArtMesh 前景隐藏、人物+背景合成及导出流程正常
- [ ] NIKKE：fb/cover/aim 存在的姿态切换成功、技能动作播放后能回到待机、原画/背景展示未回退
- [ ] 重返未来1999：含中文皮肤名的资源 ID 能直达；Cubism、Spine、商城场景/点唱机原画各选一个实测
- [ ] 棕色尘埃2：人物角色、cutscene、interaction、interaction2 中已安装的类型可以切换；idle/mix 连续动作不被通用桥接中断
- [ ] 选一个不存在的资源 ID，确认页面清楚提示找不到，而不是显示其他角色
- [ ] 从角色列表切换多个模型，浏览器不出现持续累积的 WebGL/Spine 上下文错误或严重卡顿
- [ ] 更新资源后重建索引/文件校验，确认不沿用旧目录的错误状态；“文件齐全”仍不代表互动已审核
- [ ] 在浏览器开发者工具 Network / Console 中检查真实素材请求失败情况，并区别资源未下载与代码 Bug
- [ ] 新游戏脚手架使用 `--dry-run` 预览，测试注册与只读目录；动态插件须自行实现游戏渲染适配器

## 合并 main 的门槛

1. GitHub Actions 流水线全部通过，`doctor` 不存在 error（仅告警可以逐项评估）。
2. 上面的本地四游戏真实资源测试通过，尤其是复杂的 Spine 连续互动和碧蓝航线特殊图层。
3. 没有导致素材删除、重下或旧页面无法使用的回归问题。
4. 记录具体失败皮肤 ID / 动作 / 浏览器日志并修复后再合并。
5. 完成上述确认后，把 PR 从 Draft 转为可合并状态，再合并 `main`。

**本阶段代码提交与 CI 通过，不代表已经完成第 2 条。未经真实素材验收，不会自动合并 `main`。**

## 未来开发边界

第四阶段结束后，后续更多游戏、画廊筛选、4K Wallpaper 导出、编辑 ArtMesh 等属于正常功能迭代，
优先通过新游戏插件和统一资源 API 扩展，不再以“第五阶段架构重构”重复推翻已有基础。

完整架构与第一至第三阶段说明分别在本目录的 phase1、phase2、phase3 文档。
