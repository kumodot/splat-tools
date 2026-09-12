@echo off
cd /d "%~dp0"
echo SplatWalk dev server (Ctrl+C to stop)
python serve.py %*
pause
