# 菲莉西娅·鲁梅 Schwarzes Kaninchen 单皮验证包

## 安装到现有展示柜

将本压缩包**解压到** `D:\project_python\live2d-game-artifact-gallery\`，与现有的 `azur_lane/`、`index.html` **合并文件夹**，不要替换整个文件夹。不会覆盖原有脚本、播放器、manifest。

确认依赖：

```powershell
cd D:\project_python\live2d-game-artifact-gallery
pip install -r requirements.txt
```

双击根目录 `单皮验证-菲莉西娅.bat`，脚本会只下载并重建单个模型及一张封面，然后启动本地服务并打开测试页。

也可以手动逐步运行：

```powershell
python azur_lane/scripts/probe_fulici.py catalog
python azur_lane/scripts/probe_fulici.py install
python azur_lane/scripts/probe_fulici.py check
python -m http.server 8000
```

浏览器访问：`http://127.0.0.1:8000/azur_lane/viewer/fulici_probe.html`。

已有 `127.0.0.1:7897` 代理按项目默认配置使用；若无需代理，使用：

```powershell
python azur_lane/scripts/probe_fulici.py install --direct
```

如想只验证模型，不下载封面：

```powershell
python azur_lane/scripts/probe_fulici.py install --no-cover
```

## 当前已验证事实

- 仓库 `azur_lane/viewer/manifest.json` 中已有模型 `fulici_2`，皮肤 ID `407041`，`Schwarzes Kaninchen`，Cubism moc3 版本号 `4`。
- `azur_lane/config/hashes/L2D.csv` 中有精确条目 `live2d/fulici_2`，原始 bundle 大小 17,392,434 B，MD5 `84ad5e37d133d1019aecbe5c98fcc48a`。
- `azur_lane/config/hashes/PAINTING.csv` 中有 `painting/fulici_2_rw_tex` 封面资源。
- **未在云端完成真实模型的浏览器渲染验证**。具体加载、透明贴图、骨骼动作须在你的本机跑测试页后确认。

## 验证目标与判定

| 条目 | 判定方式 | 说明 |
|---|---|---|
| 文件完整 | `check` 的路径、文件头、JSON 引用校验通过 | 不等于视觉正常 |
| 模型渲染 | 测试页内角色出现，贴图没有明显缺损 | 需本地浏览器核验 |
| 动作播放 | 页面列出动作组，点击逐个播放 | 支持现有提取的 `motion3.json` |
| 点击动作 | 单击模型区域循环触发已提取 `touch_*` 动作组 | **并非游戏原版按身体区域精确触发** |
| 高级互动 | 实测游戏中的特殊姿势 / 鞋履变化 / 腿部特写 | **当前无法保证**，需要原游戏交互配置和切换状态数据 |

## 注意

- 这是独立验证入口，不更改主展示柜所有模型的行为。
- 刻意**不运行** `gen_manifest.generate()`：如果本机没有下载完整 271 套资源，直接重生清单会让原目录只剩一个模型索引。
- `azur_lane/data/` 与 `azur_lane/cache/` 仍由原 `.gitignore` 排除，资源不提交 Git。
- 所有游戏资源仅用于个人本地研究，不公开再分发。
