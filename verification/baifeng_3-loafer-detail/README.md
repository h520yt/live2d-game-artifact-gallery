# 白凤 baifeng_3 · 扣带、马衔扣和鞋面精修

在碧蓝航线查看器打开白凤「Sunshower Fox Bride」，选择「换装 01 · 黑丝皮鞋」。

## 验收图

| 内容 | 文件 |
|---|---|
| 校正带身、扣框和鞋面分区 | [结构稿](structure-render.png) |
| 恢复皮革高光、围缝和金属反光 | [最终浏览器整帧](final-render.png) |
| 同参数、同机位、同缩放 | [精修前后](before-after.png) · [结构稿与材质稿](structure-material.png) |
| 独立近景 | [前景鞋](foreground-detail.png) · [后景鞋](rear-detail.png) |
| 两只鞋的扣带和扣件 | [局部前后对比](buckle-comparison.png) |
| 同姿态参考与上一轮原款 | [参考对照](reference-comparison.png) |

## 与参考图的对应

- 前景带身从鞋面远侧跨过鞋背，沿近侧鞋帮弯到围条上方。后景单独绘制带宽和弯曲，近端由原前腿遮挡。两端保留压边和贴面阴影。
- 沿用银色马衔扣的两个矩形框、短连杆和黑色皮袢。每只鞋的两个扣框分别描绘，近端内孔略宽，远端按各自角度收窄。皮袢伸入端部横梁的内孔，框边用暗侧面及局部反光表现厚度。
- 依照同姿态参考，把围缝从扣带下引向圆头。鞋面用沿弧度收细的暖白反光，鞋帮保留较暗的侧光。参考图中的带身和扣饰按现有鞋胚的投影适配，因此角度与宽度以浏览器实际姿态为准。

## 校验与回退

Chrome 在 1440 × 1000 视口、DPR 2 下定格默认参数。鞋胚、结构稿和材质稿的 398 次 WebGL 绘制调用一致。图集 Alpha、覆盖蒙版及脚踝叠层逐像素一致，UV、绑定和现有补层配置相同。两轮切回原始装扮均复现原始帧，88 个原模型文件的 SHA-256 均匹配。验收限默认静态姿态。 [检查数据](checks.json)

- 换装索引 `azur_lane/config/outfits/index.json` 指向 `baifeng_3/outfit_01_loafer_detail.json` 和对应的新 PNG。可把索引的 `file` 改回 `baifeng_3/outfit_01_loafers.json` 以恢复本轮开始时的鞋。
- `detail.svg` 提供局部画稿。上一轮浏览器抓帧、UV 转写和证据脚本通过 `--refine` 生成本轮图集和截图。

从仓库根目录复验。最后一行的两个路径分别对应本轮同姿态参考和上一轮鞋款图板。

```powershell
node verification/baifeng_3-loafer-repaint/capture.cjs baseline --refine
node verification/baifeng_3-loafer-repaint/capture.cjs structure-art --refine
python -B verification/baifeng_3-loafer-repaint/repaint.py structure --refine
node verification/baifeng_3-loafer-repaint/capture.cjs structure --refine
node verification/baifeng_3-loafer-repaint/capture.cjs final-art --refine
python -B verification/baifeng_3-loafer-repaint/repaint.py final --refine
node verification/baifeng_3-loafer-repaint/capture.cjs final --refine
python -B verification/baifeng_3-loafer-repaint/evidence.py --refine "同姿态参考路径.png" "原鞋款图板路径.png"
```
