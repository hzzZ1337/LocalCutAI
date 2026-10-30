# LocalCut AI — strona BETA i centrum pobierania

Responsywna strona HTML/CSS/JavaScript z animacjami, logo, autentycznymi fragmentami interfejsu aplikacji, przeglądarką kodu źródłowego i osobną stroną pobierania.

## Pliki pobierania Windows

Strona `downloads.html` udostępnia dwa pliki: `downloads/LocalCutAI-App-Windows.zip` oraz `downloads/LocalCutAI-FFmpeg-Windows.zip`. Są dostarczone jako osobne pliki obok paczki strony, aby uniknąć jednego bardzo dużego archiwum.

Aby włączyć przyciski w lokalnej kopii strony lub na hostingu obsługującym te pliki:
1. Rozpakuj `LocalCutAI_BETA_WEBSITE.zip`.
2. Pobierz osobno `LocalCutAI-App-Windows.zip` i `LocalCutAI-FFmpeg-Windows.zip`.
3. Skopiuj oba archiwa (bez rozpakowywania ich) do katalogu `downloads/` w folderze strony.
4. Opublikuj folder strony. Linki aktywują się po znalezieniu plików.

Możesz też wgrać oba archiwa jako assety publicznego GitHub Release i ustawić w `index.html` oraz `downloads.html` metadane `github-repo` w formacie `właściciel/repozytorium`. Skrypt pobierania wyszukuje assety o dokładnych nazwach `LocalCutAI-App-Windows.zip` i `LocalCutAI-FFmpeg-Windows.zip`; licznik na stronie głównej sumuje pobrania paczki aplikacji.

## Instalacja aplikacji przez użytkownika

Pobierz oba ZIP-y, rozpakuj je do jednego folderu (np. `C:\LocalCutAI`), tak aby `LocalCutAI.exe`, `ffmpeg.exe` i `ffprobe.exe` leżały obok siebie. Uruchom `LocalCutAI.exe`. Nie potrzeba osobnej instalacji Pythona ani CUDA w wersji CPU. Modele Whisper/Piper są pobierane przy pierwszym użyciu i wymagają wtedy Internetu.

Wydanie jest BETA. Przed publicznym udostępnieniem przetestuj paczkę na czystym Windows 10/11 x64. Sprawdź także licencje wszystkich zależności.

## Uruchomienie strony lokalnie

Uruchom `preview_site.bat` albo w terminalu wykonaj `py -3.12 -m http.server 8080`, następnie otwórz `http://localhost:8080`. Przeglądarka kodu używa `fetch()`, więc nie otwieraj pliku jako `file://`.

## Open source i licznik

Oryginalny kod aplikacji i strony jest publikowany na licencji MIT w zakresie plików objętych `LICENSE`. FFmpeg, modele AI, głosy i biblioteki zachowują własne licencje. Licznik pobrań wykorzystuje publiczne statystyki assetu `LocalCutAI-App-Windows.zip` z GitHub Releases; bez konfiguracji publicznego repozytorium pokazuje informację zamiast wymyślonej liczby.
