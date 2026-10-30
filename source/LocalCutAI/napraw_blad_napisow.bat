@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================================
echo   Naprawa LocalCut AI - problem PyAV / Whisper
echo ================================================
if not exist ".venv\Scripts\python.exe" (
  echo Nie znaleziono .venv. Najpierw uruchom install.bat.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install "av>=11,<18"
if errorlevel 1 (
  echo.
  echo Nie udalo sie zainstalowac zgodnej wersji PyAV.
  pause
  exit /b 1
)
echo.
echo Gotowe. Uruchom teraz run.bat i ponownie wygeneruj napisy.
echo Zastosowano ograniczenie PyAV do wersji zgodnych z faster-whisper 1.2.1.
pause
