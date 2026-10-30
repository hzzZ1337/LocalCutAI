@echo off
setlocal
cd /d "%~dp0"
echo Starting LocalCut AI website preview at http://localhost:8080
start "" cmd /c "timeout /t 2 >nul & start http://localhost:8080"
py -3.12 -m http.server 8080
pause
