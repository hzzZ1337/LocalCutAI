@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Brak srodowiska. Uruchom najpierw install.bat
    pause
    exit /b 1
)
.venv\Scripts\python.exe main.py
if errorlevel 1 (
    echo.
    echo Aplikacja zakonczyla prace z bledem. Zajrzyj do komunikatu powyzej.
    pause
)
