# 白凤·晴雨狐嫁鞋履最终重绘

碧蓝航线 · `baifeng_3` · 皮肤 `307162`。在展示柜打开「Sunshower Fox Bride」，选择「换装 01 · 黑丝皮鞋」。

## 当前鞋胚与最新参考的差异

| 部位 | 本轮开始时 | 最新完整穿鞋图与重绘处理 |
|---|---|---|
| 鞋型与鞋口 | 前后鞋轮廓和踝部贴合已稳定，鞋头、鞋面与鞋帮之间亮暗较接近 | 参考图的包头、鞋帮和围条分层更清楚。沿现有轮廓重画包边、鞋头卷边和低跟层次，复用原鞋口 Alpha 和前后遮挡 |
| 扣带与鞋舌 | 扣带较长，沿鞋帮向下延伸。鞋舌与带身的层次较弱 | 参考图的带尾较短，有可见皮袢和隆起的亮面鞋舌。分开画鞋舌、贴合曲面的横带、皮袢及压边 |
| 银色马衔扣 | 两个框的可见开口较接近，金属明暗变化较少 | 参考图的近环开口更宽，远环明显压扁。两只鞋分别画四个闭合扣框的投影、短连杆、边沿反光和接触暗部 |
| 皮革与鞋底 | 鞋面反光偏弥散，鞋头与外底反光区分较弱 | 参考图有连贯的冷白弧形主反光、细暖边光与较暗鞋帮。漆皮、围条与较哑的外底分开着色 |

最新完整角色图是外观基准。上一轮三视图和拆解只帮助识别围条、鞋舌、皮袢与扣件结构。图集由两份独立画稿编译，最新参考图的裁区仅用于对照图。 [最新参考对照](reference-comparison.png)

## 实际渲染

| 验收内容 | 文件 |
|---|---|
| 前景鞋先行核对 | [单独制作前景鞋的结构和材质](foreground-stages.png) |
| 两只鞋的结构与材质阶段 | [结构整帧](structure-render.png) · [两阶段对比](structure-material.png) |
| 同机位和缩放的重绘前后 | [前后对比](before-after.png) |
| 两只鞋及其放大 | [完整足部](both-shoes.png) · [前景鞋](foreground-detail.png) · [后景鞋](rear-detail.png) |
| 银色双环、连杆与皮袢 | [马衔扣局部](horsebit-detail.png) |
| 同一默认姿态的角色整帧 | [原始装扮](original-render.png) · [换装 01](final-render.png) |

## UV、贴合与换装验证

- 主脚掌为 `ArtMesh13`、`ArtMesh18`，前脚背过渡为 `ArtMesh214`。`ArtMesh230–235` 和 `ArtMesh156` 保持原脚趾裁剪和 UV。踝侧仍使用 `ArtMesh12`、`ArtMesh217` 的原网格叠层，本轮只协调鞋口附近的颜色。
- 两只鞋继续由原脚部 UV 承担主体，脚掌原有的局部轮廓补层分别跟随 `ArtMesh13` 和 `ArtMesh18`。配置除了图集名相同。Alpha、覆盖蒙版逐像素一致。
- Chrome 在 1440 × 1000 视口、DPR 2 下定格默认姿态。结构稿、最终稿和本轮开始时的相机、姿态与 398 次 WebGL 绘制调用一致。实测贴图加载失败可重试，两轮切回原始装扮都复现原始帧，再换装均复现最终帧。88 个原模型文件的 SHA-256 匹配。 [自动检查](checks.json)
- 原脚部透视与遮挡决定后景鞋的可见面积，两只鞋的相对落点沿用默认模型。参考图小尺寸扣件的微小接头轮廓只能近似描绘，如需核准该细节，需要同角度的马衔扣高清独立近景。验收仅覆盖默认静态姿态。

## 文件与回退

新配置和图集为 `azur_lane/config/outfits/baifeng_3/outfit_01_final_repaint.json`、`outfit_01_final_repaint.png`。将 `azur_lane/config/outfits/index.json` 中白凤换装 01 的 `file` 改回 `baifeng_3/outfit_01_loafer_detail.json` 并刷新，可恢复本轮开始时的版本。

`fore.svg`、`rear.svg` 是独立画稿。浏览器和 UV 脚本复用上一轮验证工具，从项目根目录运行如下命令。最后一行填本轮最新完整角色图。

```powershell
$capture = "verification/baifeng_3-loafer-repaint/capture.cjs"
$repaint = "verification/baifeng_3-loafer-repaint/repaint.py"
node $capture baseline --final-repaint
node $capture structure-art --final-repaint --foreground
python -B $repaint structure --final-repaint --foreground
node $capture structure --final-repaint --foreground
node $capture final-art --final-repaint --foreground
python -B $repaint final --final-repaint --foreground
node $capture preview --final-repaint --foreground
node $capture structure-art --final-repaint
python -B $repaint structure --final-repaint
node $capture structure --final-repaint
node $capture final-art --final-repaint
python -B $repaint final --final-repaint
node $capture final --final-repaint
python -B verification/baifeng_3-loafer-repaint/evidence.py --final-repaint "最新角色图路径.png"
```
