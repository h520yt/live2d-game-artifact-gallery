@echo off
chcp 65001 >nul
cd /d "%~dp0"
python azur_lane\scripts\install_batch3.py %*
if errorlevel 1 echo 第三批存在安装失败项，请检查 azur_lane\data\batch3-install-report.json
pause
