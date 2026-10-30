# Jak zbudować LocalCut AI jako EXE (Windows)

W tym środowisku przygotowano kod i skrypt budujący, ale nie gotowy binarny plik Windows EXE: projekt musi być spakowany na Windowsie, gdzie zainstalowane są jego biblioteki. Skrypt robi to automatycznie na Twoim komputerze.

## Przed uruchomieniem

1. Korzystaj z aktualnego folderu projektu `C:\LocalCutAI`.
2. Upewnij się, że aplikacja uruchamia się przez `run.bat`.
4. Przygotuj FFmpeg. Najprościej umieścić `ffmpeg.exe` oraz `ffprobe.exe` w folderze projektu albo dodać folder `bin` FFmpeg do Windows PATH. Skrypt spróbuje skopiować te pliki obok EXE, jeśli będzie mógł je znaleźć.

## Budowanie

1. Zamknij LocalCut AI.
2. Kliknij dwukrotnie `build_exe.bat`. Skrypt sam sprawdzi biblioteki i automatycznie uruchomi `install.bat`, jeśli brakuje środowiska `.venv` lub wymaganych modułów.
3. Jeżeli otworzy się okno instalacji, postępuj zgodnie z instrukcjami i naciśnij klawisz, gdy skrypt instalacyjny poprosi o zakończenie. Potem budowanie będzie kontynuowane automatycznie.
4. Poczekaj na zakończenie PyInstaller. Potrzebne jest połączenie z Internetem, a plik będzie duży. Szczegółowy log znajduje się w `build_exe.log`.
5. Gotowy plik znajdziesz pod ścieżką `C:\LocalCutAI\dist\LocalCutAI.exe`.
6. Uruchamiaj EXE z folderu, do którego masz prawo zapisu, np. `C:\LocalCutAI\dist\`. Pierwszy wybrany głos Piper oraz model Whisper nadal będą pobierane przy pierwszym użyciu i przechowywane w lokalnych cache/modelach.

To jest **jednoplikowy EXE** aplikacji. Dla działania funkcji związanych z filmem potrzebny jest również FFmpeg: jeśli nie został skopiowany jako `dist\ffmpeg.exe` i `dist\ffprobe.exe`, musi być dostępny przez PATH albo należy ręcznie skopiować oba pliki obok `LocalCutAI.exe`.

## Ważne ograniczenia

- Plik EXE jest tworzony na Twoim komputerze; nie wolno kopiować do niego plików `.venv` ani usuwać ich w czasie budowania.
- Jednoplikowy EXE może uruchamiać się wolniej, ponieważ PyInstaller wypakowuje biblioteki do katalogu tymczasowego. To normalne.
- Modele Whisper i Piper nie są dołączone do EXE, ponieważ zwiększyłoby to plik o setki megabajtów. Są pobierane lokalnie przy pierwszym użyciu danego modelu.
- Nie uruchamiaj aplikacji z folderu tylko do odczytu, np. `Program Files`, bo program zapisuje w folderze aplikacji pliki modeli głosowych.
- Windows Defender może ostrzec przy samodzielnie zbudowanych aplikacjach PyInstaller. Upewnij się, że budujesz EXE z własnego projektu i nie zezwalaj na pliki, których źródła nie znasz.
- Przed dalszym rozpowszechnianiem EXE sprawdź licencje wszystkich dołączonych bibliotek oraz FFmpeg, jeśli dołączysz jego pliki binarne.

## Jeśli EXE mignie i zamknie się

Uruchom wersję źródłową przez `run.bat`, aby sprawdzić, czy projekt nadal działa. Jeżeli problem występuje tylko w EXE, odpal `build_exe.bat` ponownie i zapisz cały komunikat z terminala. Nie usuwaj `build` ani logów przed zebraniem komunikatu.
