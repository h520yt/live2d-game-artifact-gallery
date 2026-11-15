@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [Azur Lane] Scan installed character artwork and backfill background layers...
python azur_lane\scripts\install_scene_layers.py %*
if errorlevel 1 (
  echo.
  echo [WARN] Some resources failed. Please review azur_lane\data\scene-layer-report.json
) else (
  echo.
  echo [OK] Backfill finished. Start the gallery server with: python -m http.server 8000
)
pause
