# 白凤·晴雨狐嫁默认姿态鞋履重绘

在碧蓝航线查看器打开 `baifeng_3`（皮肤 `307162`），选择「换装 01 · 黑丝皮鞋」。换装使用两只独立绘制的亮面皮鞋。切回「原始装扮」时恢复原模型纹理。旧外挂鞋可通过查看器的 `?shoe_backup=1` 入口选择，`?shoe_debug=1` 继续提供旧方案的分层调试。

## 验收图

| 内容 | 文件 |
|---|---|
| 原始贴图上的 UV 三角形和原模型网格覆盖 | [原始 UV](original-uv.png) · [默认姿态网格](pose-meshes.png) |
| 原始裸足和脚部提取 | [原始默认姿态](original.png) · [前脚提取](fore-original-extracted.png) · [后脚提取](rear-original-extracted.png) |
| 两只鞋的重绘素材 | [前脚](fore-repaint.png) · [后脚](rear-repaint.png) · [原轮廓与补层](outline-coverage.png) |
| 查看器实际渲染 | [换装整图](dressed.png) · [前脚局部](foreground-detail.png) · [后脚局部](rear-detail.png) |
| 同姿态、同机位换装对比 | [原始装扮与换装 01](comparison.png) |

整图来自现有 PIXI/Cubism 查看器的 WebGL 帧缓冲。局部图来自同一查看器把相机放大 3 倍后的再次渲染。对比图把两次局部渲染并排呈现。

## 原网格覆盖与遮挡

- 前脚由 `ArtMesh13`、脚背过渡 `ArtMesh214` 和六个独立脚趾 `ArtMesh230–235` 构成。`ArtMesh12` 在鞋口局部叠于脚部网格之上。
- 后脚由 `ArtMesh18` 和趾部 `ArtMesh156` 构成，踝侧有 `ArtMesh217` 的局部叠合。后跟和一侧鞋帮按原有绘制顺序受前脚和前腿遮挡。
- 两张原图均为 4096 × 4096。默认姿态参与重绘的 12 个 ArtMesh 都使用 `texture_00.png`。三角占用扫描检查了原图上同页的其他 ArtMesh，相关 UV 之间未检出共享占用。每个 ArtMesh 在换装图集中仍有各自的区块。
- 脚趾分片造成鞋尖边缘的凹口，原脚背外缘和接地边缘也缺少鞋面厚度与低跟的余量。轮廓图中的青线对应原脚 Alpha 边缘，紫色对应沿鞋尖、前掌外沿、鞋底和鞋跟填补的区域。按绘图平面的 Alpha 加权面积估算，补层约占前脚鞋绘制面积的 16.8% 和后脚的 20.1%。这个比例包含被前腿遮挡的部分。

导出的 [ArtMesh 数据](foot-meshes.json) 含原始顶点、UV、三角索引、遮罩和绘制顺序。[测量及原件哈希](analysis.json) 给出贴图像素范围、重叠检查和各原模型文件的 SHA-256。

## 制作与复用

1. 从实际查看器定格并导出原姿态。按 ArtMesh 隔离渲染能同时观察贴图 Alpha、各片网格和前后遮挡。源文件中的 `v` 坐标转换为贴图顶部原点后再标注。
2. 在同一屏幕坐标系内为两只脚分别画鞋。鞋口沿原脚踝和脚背收口，鞋面明暗、搭扣及鞋底都依据各自的投影。通过鞋轮廓的保留遮罩消除圆鞋头外的独立脚趾轮廓。
3. 以原始 UV 三角形为采样域，对每个贴图像素用三角形重心权重求对应的默认姿态位置，再从鞋画稿中采样。运行时仅为命中的 ArtMesh 指定新图集坐标，继续使用原顶点、索引和绘制顺序。踝侧两层以原网格和原 Alpha 提交局部鞋口颜色，主腿仍从原图采样。
4. 在原脚网格的 Alpha 覆盖不足处求轮廓差，用同一张画稿填补。每只脚提交一张透明补层，挂在该脚掌网格之前，因此前腿仍按原顺序遮挡后鞋。

复现需要本机安装白凤和 `qiye_10` 资源、Chrome、Playwright、Pillow 与 NumPy。以下命令从仓库根目录执行。

```powershell
node verification/baifeng_3-foot-repaint/capture.cjs
node verification/baifeng_3-foot-repaint/capture.cjs --art
python verification/baifeng_3-foot-repaint/build.py
node verification/baifeng_3-foot-repaint/capture.cjs --verify
python verification/baifeng_3-foot-repaint/make_evidence.py
```

## 验证范围

- 对默认姿态实测首次贴图加载失败后可重试。两轮切回原装、重新穿鞋都复现同一 WebGL 帧。前后对比中足部裁区之外的差异像素为零。88 个原模型文件的 SHA-256 全部匹配。 [像素核对](render-check.json)
- 切到 `qiye_10` 时换装菜单隐藏，且该模型使用自己的两张纹理。返回白凤时默认选中原始装扮。旧外挂备份通过原有的 83 个动作浏览器回归。
- 新鞋画稿的验收范围是默认静态姿态。`ArtMesh229` 抬脚、`ArtMesh223` 脚底、`Param71` 视角过渡和 `touch_drag9` 属于后续画稿适配。
