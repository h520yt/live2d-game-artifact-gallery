# 碧蓝航线 Live2D：其他五款御姐系皮肤定向安装

这个包是在已验证 `fulici_2` 单皮流程基础上的 **5 款批量安装**，不包含已经安装的菲莉西娅。只新增安装脚本、测试和说明，不替换已有查看器或模型索引。

## 安装方法

1. 将压缩包**按目录合并**解压到 `D:\project_python\live2d-game-artifact-gallery\` 根目录（不要用压缩包替换整个项目）。
2. 此前 `requirements.txt` 已成功安装，无需再次安装；若环境变动，可执行 `python -m pip install -r requirements.txt -i https://pypi.org/simple`。
3. 双击 `安装其他五款Live2D.bat`，自动核对清单、按需下载、MD5 校验、提取模型和动作、还原原画变体、检查结果，再打开现有展示柜。

也可以 PowerShell 逐步执行（在仓库根目录）：

```powershell
python azur_lane/scripts/install_curated_live2d.py list
python azur_lane/scripts/install_curated_live2d.py install
python azur_lane/scripts/install_curated_live2d.py check
python -m http.server 8000
```

浏览器访问 `http://127.0.0.1:8000/azur_lane/viewer/`，搜索 `jianwu_2`、`aijier_4`、`ougen_8`、`luoen_4`、`shengluyisi_5`。

## 模型与皮肤 ID

| 中文皮肤 | 模型名 | 皮肤 ID | 原画变体 |
|---|---|---:|---:|
| 建武 · 妆点，只为今夜 | `jianwu_2` | 503011 | 3 |
| 埃吉尔 · 私密闲暇时 | `aijier_4` | 499053 | 4 |
| 欧根亲王 · 微醺与试探的距离 | `ougen_8` | 403037 | 8 |
| 罗恩 · 苍翠的安眠曲 | `luoen_4` | 499012 | 3 |
| 圣路易斯 · 邮轮上的诱人午后 | `shengluyisi_5` | 102134 | 2 |

## 可选命令

只安装指定一款或几款：

```powershell
python azur_lane/scripts/install_curated_live2d.py install --only ougen_8
python azur_lane/scripts/install_curated_live2d.py install --only jianwu_2 aijier_4
```

不需要本地 `127.0.0.1:7897` 代理：

```powershell
python azur_lane/scripts/install_curated_live2d.py install --direct
```

只要 Live2D，不下载原画变体：

```powershell
python azur_lane/scripts/install_curated_live2d.py install --no-paintings
```

## 验证范围

- 对每个 bundle 按资源清单严格检查下载大小和 MD5；重试会复用校验通过的缓存。
- 检查模型的 moc3、贴图、动作资源文件是否存在且被 model3 正确引用，原画验证 PNG 文件头。
- **不会生成、覆盖或缩减 `azur_lane/viewer/manifest.json`**，不会影响原来其他模型、已经安装的 `fulici_2`。
- 原游戏的高级点击区域、腿部特写、鞋履切换或场景状态不能仅凭动作文件完整就认定已还原，仍需单独验证。
- 此包只是可在你 Windows 本机运行的安装流程，当前环境无法直接操作你电脑上的文件；资源实际落地要以本机脚本执行结果为准。
- `azur_lane/data/` 与 `azur_lane/cache/` 位于仓库 `.gitignore`，不应公开提交或分发游戏素材。
