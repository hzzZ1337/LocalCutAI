@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist "dist\LocalCutAI.exe" (
  echo BLAD: Brak dist\LocalCutAI.exe.
  echo Najpierw uruchom build_exe.bat, aby zbudowac aplikacje z nowa ikona.
  pause
  exit /b 1
)
if exist release_stage rmdir /s /q release_stage
if not exist release mkdir release
mkdir release_stage
copy /y "dist\LocalCutAI.exe" "release_stage\LocalCutAI.exe" >nul
if exist "dist\ffmpeg.exe" copy /y "dist\ffmpeg.exe" "release_stage\ffmpeg.exe" >nul
if exist "dist\ffprobe.exe" copy /y "dist\ffprobe.exe" "release_stage\ffprobe.exe" >nul
(
 echo LocalCut AI - wersja dla Windows
 echo.
 echo Uruchom LocalCutAI.exe.
 echo Do funkcji wideo wymagane sa pliki ffmpeg.exe i ffprobe.exe obok aplikacji lub FFmpeg w PATH.
 echo Modele AI sa pobierane lokalnie przy pierwszym uzyciu wybranej funkcji.
 echo Zalecany system: Windows 10/11 64-bit.
 echo.
 echo Ten pakiet jest przygotowany dla tej wersji testowej LocalCut AI.
) > "release_stage\PRZECZYTAJ.txt"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%CD%\release_stage\*' -DestinationPath '%CD%\release\LocalCutAI-Windows.zip' -Force"
if errorlevel 1 (
  echo BLAD: Nie udalo sie stworzyc ZIP.
  pause
  exit /b 1
)
echo.
echo GOTOWE: %CD%\release\LocalCutAI-Windows.zip
echo Skopiuj ten ZIP do folderu downloads na stronie.
pause
