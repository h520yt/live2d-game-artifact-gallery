# 白凤 baifeng_3 · 黑色亮面马衔扣乐福鞋

在碧蓝航线查看器打开「Sunshower Fox Bride」，选择「换装 01 · 黑丝皮鞋」。鞋款依据随任务提供的《乐福鞋（金属马衔扣）》设计图，前景和后景分别绘制扣带、双环短连杆、鞋面高光、鞋口压边、围条与低跟。

## 浏览器验收

| 内容 | 截图 |
|---|---|
| 第一步，鞋口、鞋面、马衔扣及鞋底结构 | [结构稿完整帧](structure-render.png) |
| 第二步，黑漆皮明暗、缝线和银色扣件 | [最终完整帧](final-render.png) |
| 鞋胚与最终图，同一默认参数、同一机位和缩放 | [重绘前后](before-after.png) |
| 从结构到材质，同机位局部 | [两步对比](structure-material.png) |
| 两只鞋的独立放大图 | [前景鞋](foreground-detail.png) · [后景鞋](rear-detail.png) |
| 目标商品图、侧视和扣饰与最终画面 | [设计对照](reference-comparison.png) |

Chrome 以 1440 × 1000 视口、DPR 2 定格原模型默认参数，局部图在查看器内以同一 3 倍机位重新渲染。鞋胚、结构稿与材质稿的 398 次绘制调用顺序、索引、顶点、UV 和透明度一致。图集 Alpha 与覆盖蒙版逐像素相同，整帧足部检查区之外差异为零。模拟贴图加载失败后重试成功。两次切回原始装扮均逐像素复现原始帧，88 个原模型文件的 SHA-256 均匹配。 [检查数据](checks.json)

## 修改文件与回退

- `azur_lane/config/outfits/index.json` 将白凤的现有换装指向新图集配置。将 `file` 改回 `baifeng_3/outfit_01_repaint.json` 并刷新查看器可恢复本轮开始时的鞋胚。
- `azur_lane/config/outfits/baifeng_3/outfit_01_loafers.json` 复用鞋胚的 UV、局部补层和挂点配置，只换图集文件名。
- `azur_lane/config/outfits/baifeng_3/outfit_01_loafers.png` 是新图集。颜色修改限于已有鞋绘制区内具有 Alpha 的 texel。
- 本目录的 `paint.svg` 是前后鞋画稿，`repaint.py`、`capture.cjs` 与 `evidence.py` 用于编译与复验。七张 PNG 和 `checks.json` 是浏览器验收产物。

## 验收范围

后景鞋跟在默认姿态被前腿遮挡，内衬只在原鞋口可见范围内表现。参考图中完整的后跟、鞋垫和外底纹路在该姿态不可见。两只鞋沿用鞋胚现有的透视和鞋底厚度。验收仅覆盖默认静态姿态。

## 复现

从仓库根目录运行。需要本机白凤模型、Chrome、Playwright、Pillow 和 NumPy。最后一条命令的参数指向随任务提供的 1536 × 1024 PNG。

```powershell
node verification/baifeng_3-loafer-repaint/capture.cjs baseline
node verification/baifeng_3-loafer-repaint/capture.cjs structure-art
python -B verification/baifeng_3-loafer-repaint/repaint.py structure
node verification/baifeng_3-loafer-repaint/capture.cjs structure
node verification/baifeng_3-loafer-repaint/capture.cjs final-art
python -B verification/baifeng_3-loafer-repaint/repaint.py final
node verification/baifeng_3-loafer-repaint/capture.cjs final
python -B verification/baifeng_3-loafer-repaint/evidence.py <参考图路径>
```
