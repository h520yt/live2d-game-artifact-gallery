# 真人照片 Live2D 可行性验证

输入是一张 NASA 公开实拍肖像。模型从原照贴图、左右闭眼补片和新建网格生成，包含三个 Cubism 参数。歪头在照片网格上做局部形变，闭眼通过眼睑补片过渡。

[照片来源与公有领域说明](https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.astronaut) · [MOC3 写入库](https://pypi.org/project/py-moc3/0.1.0/) · [格式修正参考](https://github.com/fifteen42/live2d-from-art/blob/main/references/direct-moc3.md)

`portrait.model3.json` 引用 `portrait.moc3` 和 `portrait-texture.png`。`comparison.png` 从左到右是浏览器的默认姿态、左眼闭合、歪头并双眼闭合。

直接用 Chrome 或 Edge 打开本目录的 `preview.html`，再拖动滑块。页面通过同目录的 `preview-data.js` 和仓库自带的 Cubism Core 加载，可以离线运行。

Chrome 中使用仓库的 Live2D Cubism Core 验证了默认姿态、左右眼独立闭合、歪头及组合动作。测试检查了模型参数、网格顶点、眼睑透明度、帧像素变化和 WebGL 错误。原型仅验证运行时模型。Cubism Editor 工程、VTube Studio 面捕、说话口型和大幅转脸尚未验证。

## 复现

从仓库根目录运行以下命令。构建使用 Python 和 Pillow，验证使用仓库已有的 Playwright 及 Chrome。

```powershell
python verification/real-photo-cubism-poc/build.py
node verification/real-photo-cubism-poc/verify.cjs
```

也可以通过本地 HTTP 服务打开预览。在仓库根目录启动 `python -m http.server 8765 --bind 127.0.0.1`，访问 `http://127.0.0.1:8765/verification/real-photo-cubism-poc/preview.html`。
