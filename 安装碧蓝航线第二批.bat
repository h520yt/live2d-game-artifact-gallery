@echo off
chcp 65001 >nul
cd /d "%~dp0"
python azur_lane\scripts\install_batch2.py %*
if errorlevel 1 echo 安装中存在错误，请检查上述输出和 azur_lane\data\batch2-install-report.json
pause
