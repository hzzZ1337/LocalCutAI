@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ==========================================
echo   Instalacja LocalCut AI
echo ==========================================
echo.

rem Reuse an existing supported environment. Rebuild it safely if it uses
rem a Python version unsupported by the Windows package dependencies.
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import sys, struct; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>nul
    if errorlevel 1 goto :repair_venv
    goto :venv_ready
)
goto :create_venv

:repair_venv
call :select_supported_python
if not defined PYTHON goto :wrong_python
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss" 2^>nul') do set "STAMP=%%I"
if not defined STAMP set "STAMP=backup"
set "BACKUP=.venv_stare_%STAMP%"
if exist "%BACKUP%" set "BACKUP=.venv_stare_backup"
echo Istniejace .venv nie uzywa Pythona 3.11/3.12. Zachowuje stare srodowisko jako %BACKUP%.
ren .venv "%BACKUP%"
if errorlevel 1 goto :error

echo.
echo Tworzenie nowego srodowiska z %PYTHON%...

:create_venv
if not defined PYTHON call :select_supported_python
if not defined PYTHON goto :wrong_python
%PYTHON% --version
if errorlevel 1 goto :no_python
%PYTHON% -c "import sys, struct; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) and struct.calcsize('P')*8 == 64 else 1)"
if errorlevel 1 goto :wrong_python
%PYTHON% -m venv .venv
if errorlevel 1 goto :error

:venv_ready
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import sys, struct; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) and struct.calcsize('P')*8 == 64 else 1)"
if errorlevel 1 goto :wrong_venv

.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error

.venv\Scripts\python.exe -c "import PySide6, faster_whisper, av, piper; print('Biblioteki LocalCut AI: OK')"
if errorlevel 1 goto :error

echo.
echo Instalacja zakonczona. Mozesz uruchomic run.bat albo build_exe.bat.
pause
exit /b 0

:select_supported_python
set "PYTHON="
rem Detect Python through the launcher, registry, common install paths and PATH.
rem The helper validates that the interpreter is 64-bit Python 3.11 or 3.12.
for /f "usebackq delims=" %%I in (`powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_python.ps1" 2^>nul`) do set "PYTHON="%%I""
if defined PYTHON exit /b 0
rem Fallback for Python Launcher installs whose output format differs.
where py.exe >nul 2>nul
if not errorlevel 1 (
    py -3.12 -c "import sys,struct; raise SystemExit(0 if sys.version_info[:2] == (3,12) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON=py -3.12"
    if not defined PYTHON (
        py -3.11 -c "import sys,struct; raise SystemExit(0 if sys.version_info[:2] == (3,11) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>nul
        if not errorlevel 1 set "PYTHON=py -3.11"
    )
)
exit /b 0

:no_python
echo.
echo Nie znaleziono Pythona. Zainstaluj Python 3.11 lub 3.12 64-bit z https://www.python.org/downloads/windows/
echo Podczas instalacji zaznacz Add Python to PATH.
pause
exit /b 1

:wrong_python
echo.
echo LocalCut AI wymaga Pythona 3.11 lub 3.12 (64-bit). Nie znaleziono zgodnej instalacji.
echo Sprawdz w nowym oknie CMD polecenie: py -0p
echo Jesli lista jest pusta, uruchom instalator Python 3.12 64-bit ponownie.
echo Zainstaluj Python 3.12: https://www.python.org/downloads/windows/
pause
exit /b 1

:wrong_venv
echo.
echo Istniejace .venv uzywa innej wersji Pythona niz 3.11/3.12.
echo Jesli problem nadal wystepuje, zmien nazwe folderu .venv i uruchom install.bat ponownie.
pause
exit /b 1

:error
echo.
echo Instalacja nie powiodla sie. Skopiuj komunikat bledu i sprawdz README_PL.md
echo Jesli wystapil blad pobierania, sprawdz Internet i uruchom install.bat ponownie.
pause
exit /b 1
