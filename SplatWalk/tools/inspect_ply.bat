@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Drag a .ply file onto this .bat, or run:
  echo   python splat_prep_v0.1.0.py yourfile.ply -o out.ply --target 1500000
  pause
  exit /b
)
python splat_prep_v0.1.0.py "%~1"
echo.
echo Above are the stats. To actually convert, run the suggested command.
pause
