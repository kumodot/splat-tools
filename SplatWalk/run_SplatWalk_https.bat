@echo off
cd /d "%~dp0"
echo SplatWalk HTTPS server for the Quest browser (Ctrl+C to stop)
python serve.py --https --no-open
pause
