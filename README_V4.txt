白凤·晴雨狐嫁 (baifeng_3) 鞋面和扣饰 V4 资源包（默认姿态测试）
资源文件: azur_lane/config/outfits/baifeng_3/outfit_01_final_repaint.png

安装（Windows）：
1. 完全关闭或停止展示柜网页，先备份项目中的 azur_lane/config/outfits/baifeng_3/outfit_01_final_repaint.png。
2. 将此 ZIP 中的目录解压到 D:\project_python\live2d-game-artifact-gallery 根目录，覆盖同名 PNG。
3. 不修改 outfit_01_final_repaint.json、换装列表、原始 texture_00.png 和 moc3。
4. 在项目根目录执行 python -m http.server 8000（如之前已启动，保留服务即可）。
5. 打开展示柜，白凤（baifeng_3）→ 选择“换装 01”，Ctrl+Shift+R 强制刷新资源。
6. 对照默认姿态下前景鞋/后景鞋的鞋面鼓起、金属马衔扣透视、鞋头轮廓及鞋口衔接。
7. 若问题未解决或其他动作异常，立即恢复备份，并记录同机位局部截图便于下一轮定位。

技术约束与验证范围：
- 图集大小仍为 2048×1324 RGBA。
- 保留 V2 图集的完整 alpha、白色功能遮罩以及原坐标/JSON 布局。
- 只重绘主前景鞋、前景部分鞋、后景鞋、下方附加鞋等四个区域。
- 贴图层测试已完成；原始 baifeng_3.moc3 不在已上传文件中，未做真实 Live2D 浏览器视觉验收。
- 因运行时 ArtMesh/UV 可能进一步形变，不能承诺金属扣透视及鞋头效果已最终正确。

回退方法：用安装前备份的原始同名 PNG 覆盖恢复。
