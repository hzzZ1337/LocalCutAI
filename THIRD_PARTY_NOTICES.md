# Uwagi dotyczące komponentów zewnętrznych

Licencja MIT w pliku `LICENSE` dotyczy oryginalnego kodu LocalCut AI i witryny. Nie zastępuje licencji zależności.

## FFmpeg / FFprobe dołączone do paczki Windows

Dostarczone binaria FFmpeg/FFprobe są kompilacją Windows x86_64 `N-128121-g86444dd368-20261027`. W ich wbudowanej konfiguracji znajdują się flagi `--enable-gpl` oraz `--enable-version3`, a program deklaruje GNU GPL wersja 3 lub późniejsza. Pełny tekst GPL jest dołączony do `LocalCutAI-FFmpeg-Windows.zip`.

Źródła i skrypty kompilacji: https://github.com/BtbN/FFmpeg-Builds
Dokładne wydanie: https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-10-27-18-38
Źródła FFmpeg: https://github.com/FFmpeg/FFmpeg
Warunki FFmpeg: https://ffmpeg.org/legal.html

Przy dalszej redystrybucji FFmpeg należy spełnić warunki GPLv3, w tym wymagania dotyczące licencji, informacji o prawach autorskich i dostępności odpowiadającego kodu źródłowego oraz skryptów budowania.

## Inne zależności

- Python — PSF License: https://www.python.org/
- PySide6 / Qt — licencje Qt zależne od sposobu użycia: https://www.qt.io/licensing/
- faster-whisper — MIT: https://github.com/SYSTRAN/faster-whisper
- CTranslate2 — MIT: https://github.com/OpenNMT/CTranslate2
- PyAV — sprawdź warunki konkretnego wydania: https://github.com/PyAV-Org/PyAV
- Pillow — HPND: https://python-pillow.org/
- Piper TTS i poszczególne głosy — sprawdź warunki repozytorium kodu i wybranego modelu głosu.

To nie jest porada prawna. Nie rozpowszechniaj modeli, głosów, fontów ani binariów bez sprawdzenia ich licencji.
