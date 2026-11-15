@echo off
chcp 65001 >nul
cd /d "%~dp0"
python azur_lane\scripts\install_curated_live2d.py list
if errorlevel 1 goto failed

echo.
echo ===== 开始安装 5 款 Live2D 和全部已索引原画变体 =====
python azur_lane\scripts\install_curated_live2d.py install
if errorlevel 1 goto failed

echo.
echo ===== 资源完整性检查通过，打开现有展示柜 =====
start "Azur Lane Viewer Server" cmd /k "python -m http.server 8000"
timeout /t 2 >nul
start "" "http://127.0.0.1:8000/azur_lane/viewer/"
exit /b 0

:failed
echo.
echo 安装未全部成功。可检查网络/代理后再次双击，已正确下载的资源会复用。
pause
exit /b 1
