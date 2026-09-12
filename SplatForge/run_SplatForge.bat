@echo off
cd /d "%~dp0"
title SplatForge

rem The newest SplatForge_v*.py wins, so an older build never launches by accident.
set "APP="
for /f "delims=" %%f in ('dir /b /o-n SplatForge_v*.py 2^>nul') do if not defined APP set "APP=%%f"
if not defined APP (
  echo No SplatForge_v*.py found in this folder.
  pause
  exit /b 1
)

python -c "import PyQt6, cv2, numpy" 2>nul
if errorlevel 1 (
  echo Installing the Python packages SplatForge needs, one time only...
  python -m pip install -r requirements.txt
)

echo Starting %APP%
python "%APP%"
if errorlevel 1 pause
