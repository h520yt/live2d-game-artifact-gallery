@echo off
chcp 65001 >nul
cd /d "%~dp0"
python azur_lane\scripts\probe_fulici.py install
if errorlevel 1 (
  echo.
  echo 资源下载或校验未通过，请查看上述错误并确认网络/代理。
  pause
  exit /b 1
)
start "Live2D Server" cmd /k "python -m http.server 8000"
timeout /t 2 >nul
start "" "http://127.0.0.1:8000/azur_lane/viewer/fulici_probe.html"
