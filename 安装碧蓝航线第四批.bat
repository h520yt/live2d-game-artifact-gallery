@echo off
chcp 65001 >nul
cd /d "%~dp0"
python azur_lane\scripts\install_batch4.py %*
if errorlevel 1 echo 第四批存在未完成资源，请查看 azur_lane\data\batch4-install-report.json
pause
