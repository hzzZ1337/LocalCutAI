@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo =====================================================
echo   LocalCut AI - automatyczne budowanie pliku EXE
echo =====================================================
echo.

rem Automatically install / repair project dependencies before building.
if not exist ".venv\Scripts\python.exe" goto :install_deps
.venv\Scripts\python.exe -c "import sys, PySide6, faster_whisper, av, piper; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>nul
if errorlevel 1 goto :install_deps
goto :deps_ready

:install_deps
echo [1/5] Brak srodowiska lub bibliotek. Uruchamiam teraz install.bat...
if not exist "install.bat" (
    echo BLAD: Brak pliku install.bat w folderze projektu.
    goto :error
)
call "%~dp0install.bat"
if errorlevel 1 goto :error
if not exist ".venv\Scripts\python.exe" (
    echo BLAD: install.bat zakonczyl sie bez utworzenia .venv.
    goto :error
)
.venv\Scripts\python.exe -c "import PySide6, faster_whisper, av, piper" >nul 2>nul
if errorlevel 1 (
    echo BLAD: Biblioteki nadal nie sa kompletne po install.bat.
    goto :error
)

:deps_ready
echo.
echo [2/5] Sprawdzanie wersji Pythona i bibliotek...
.venv\Scripts\python.exe -c "import sys,struct; print('Python:',sys.version.split()[0],'|',struct.calcsize('P')*8,'bit'); raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) and struct.calcsize('P')*8 == 64 else 1)"
if errorlevel 1 (
    echo BLAD: Budowanie EXE wymaga Python 3.11 lub 3.12 64-bit.
    goto :error
)
.venv\Scripts\python.exe -c "import PySide6, faster_whisper, av, piper; print('PySide6, faster-whisper, PyAV i Piper: OK')"
if errorlevel 1 goto :error

echo.
echo [3/5] Instalowanie PyInstaller...
.venv\Scripts\python.exe -m pip install --upgrade "pyinstaller>=6.10,<7"
if errorlevel 1 goto :error

echo.
echo [4/5] Czyszczenie starego buildu...
if exist build rmdir /s /q build
if exist dist\LocalCutAI.exe del /q dist\LocalCutAI.exe
if exist dist\LocalCutAI rmdir /s /q dist\LocalCutAI
if not exist dist mkdir dist

echo.
echo [5/5] Budowanie aplikacji. To moze potrwac; nie zamykaj okna.
echo Log budowania: %CD%\build_exe.log
.venv\Scripts\python.exe -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name LocalCutAI ^
  --icon "assets\LocalCutAI.ico" ^
  --add-data "assets\LocalCutAI.ico;assets" ^
  --add-data "assets\localcutai-logo.png;assets" ^
  --collect-all PySide6 ^
  --collect-all shiboken6 ^
  --collect-all faster_whisper ^
  --collect-all ctranslate2 ^
  --collect-all av ^
  --collect-all tokenizers ^
  --collect-all huggingface_hub ^
  --collect-all piper ^
  --collect-all piper_phonemize ^
  --collect-all onnxruntime ^
  --collect-all numpy ^
  --copy-metadata faster-whisper ^
  --copy-metadata piper-tts ^
  --copy-metadata ctranslate2 ^
  --hidden-import app.ai ^
  --hidden-import app.captions ^
  --hidden-import app.video_ops ^
  --hidden-import app.tts ^
  --hidden-import app.worker ^
  main.py > build_exe.log 2>&1
if errorlevel 1 goto :build_failed

if not exist "dist\LocalCutAI.exe" (
    echo BLAD: PyInstaller zakonczyl prace, ale nie znaleziono dist\LocalCutAI.exe.
    goto :build_failed
)

rem Copy FFmpeg binaries beside EXE, from the project folder or PATH, if present.
set "FFMPEG_SOURCE="
set "FFPROBE_SOURCE="
if exist "ffmpeg.exe" set "FFMPEG_SOURCE=%CD%\ffmpeg.exe"
if exist "ffprobe.exe" set "FFPROBE_SOURCE=%CD%\ffprobe.exe"
if not defined FFMPEG_SOURCE for /f "delims=" %%F in ('where ffmpeg.exe 2^>nul') do if not defined FFMPEG_SOURCE set "FFMPEG_SOURCE=%%F"
if not defined FFPROBE_SOURCE for /f "delims=" %%F in ('where ffprobe.exe 2^>nul') do if not defined FFPROBE_SOURCE set "FFPROBE_SOURCE=%%F"
if defined FFMPEG_SOURCE copy /y "%FFMPEG_SOURCE%" "dist\ffmpeg.exe" >nul
if defined FFPROBE_SOURCE copy /y "%FFPROBE_SOURCE%" "dist\ffprobe.exe" >nul

echo.
echo ========================================
echo   GOTOWE - PLIK EXE ZOSTAL UTWORZONY
echo ========================================
echo.
echo EXE: %CD%\dist\LocalCutAI.exe
if exist "dist\ffmpeg.exe" (echo Dodano ffmpeg.exe obok EXE.) else (echo UWAGA: nie znaleziono ffmpeg.exe - wymagany obok EXE lub w PATH.)
if exist "dist\ffprobe.exe" (echo Dodano ffprobe.exe obok EXE.) else (echo UWAGA: nie znaleziono ffprobe.exe - wymagany obok EXE lub w PATH.)
echo Modele AI pobieraja sie przy pierwszym uzyciu i zapisuja obok EXE lub w cache.
echo.
echo Gdyby EXE nie uruchamial sie, najpierw sprawdz run.bat. Build log jest w build_exe.log.
pause
exit /b 0

:build_failed
echo.
echo BLAD BUDOWANIA EXE. Ostatnie linie logu:
if exist build_exe.log powershell -NoProfile -Command "Get-Content -Tail 50 'build_exe.log'"
echo.
echo Pelny log: %CD%\build_exe.log
goto :error

:error
echo.
echo Budowanie nie powiodlo sie. Sprawdz komunikat powyzej.
echo Nie usuwaj build_exe.log - zawiera szczegoly bledu.
pause
exit /b 1
