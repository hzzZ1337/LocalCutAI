# LocalCut AI — pierwsza wersja (Windows)

Lokalna aplikacja desktopowa do przygotowywania polskich napisów i podstawowego montażu klipów. Aplikacja jest napisana w Pythonie i ma graficzny interfejs. Nie wysyła filmu do internetowego API — rozpoznawanie mowy wykonywane jest na komputerze. Przy pierwszym uruchomieniu trzeba jednak pobrać pliki modelu Whisper.

## Co działa w tej wersji

- **Automatyczne polskie napisy** — rozpoznawanie mowy lokalnym `faster-whisper`, z czasami słów.
- **Pliki napisów** — eksport do `.SRT` (standardowy tekst) oraz `.ASS` (styl i podświetlanie słów w rytmie mowy); zapis transkrypcji do `.JSON`.
- **Edytor korekty napisów** — popraw tekst i czasy Start/Koniec w tabeli bez ponownego uruchamiania rozpoznawania mowy; zapisuje zmiany do SRT/ASS/JSON i pozwala od razu ponownie wypalić MP4.
- **Własne napisy** — przyciskiem „+ Dodaj napis” możesz wpisać tekst, określić czas początku i końca, a następnie wypalić go w filmie. Przycisk „Usuń zaznaczone” usuwa jeden lub kilka zaznaczonych wierszy; użyj Ctrl lub Shift, aby zaznaczyć więcej. Potem kliknij „Zapisz poprawki” albo „Zapisz i wypal MP4”, aby zapisać usunięcie do plików. Pusty wiersz jest również pomijany.
- **Wypal animowane napisy do MP4** — dodatkowy przycisk renderuje kolory, podświetlanie słów i animację z `.ASS` bezpośrednio do obrazu wideo, aby efekt był widoczny także w DaVinci Resolve.
- **Wygląd napisów** — zmiana czcionki, rozmiaru, koloru tekstu i koloru podświetlenia; podświetlanie słów oraz animacje: Pop-in, Fade-in, Slide-up, Zoom-in, Bounce i Bez animacji.
- **Usuwanie ciszy** — FFmpeg wykrywa dłuższe fragmenty o niskim poziomie dźwięku i składa pozostałe części filmu.
- **Propozycje fragmentów** — ranking okien na podstawie gęstości rozpoznanej mowy oraz znaków interpunkcyjnych.
- **Shortsy** — eksport wybranych propozycji w pionowym formacie 9:16 (1080 × 1920), z próbą wypalenia napisów w obrazie. Jeśli używany FFmpeg nie ma filtra napisów, aplikacja eksportuje wideo i zapisuje plik `.ASS` obok.
- **Lektor AI** — lokalna synteza polskiej mowy z kilkoma głosami, edytowalnym tekstem i czasami, odsłuchem próbki oraz eksportem MP4 z zastąpioną ścieżką audio.

### Uczciwe ograniczenia MVP

- Ranking „najlepszych fragmentów” jest **heurystyczny**. Ta wersja nie rozumie jeszcze semantycznie całego nagrania ani nie ocenia żartów, emocji czy kontekstu tak jak człowiek.
- Shorts są kadrowane centralnie. Nie ma jeszcze automatycznego śledzenia twarzy ani dynamicznego kadrowania postaci.
- To narzędzie do wybranych zadań, nie pełna wielościeżkowa oś czasu jak w profesjonalnym edytorze.
- Rozpoznawanie mowy potrafi się mylić przy muzyce, nakładających się głosach, slangu i słabej jakości dźwięku. Przed publikacją sprawdź transkrypcję.



## Lektor AI — lokalna podmiana głosu

W aplikacji dostępna jest osobna zakładka **Lektor AI**. Używa lokalnego Piper TTS i udostępnia pięć polskich głosów: Gosia, Darkman, MC Speech, Bass (wariant high, ok. 114 MB) oraz MLS 6892 (wariant low). Pierwsze użycie danego głosu pobiera model (około 60–115 MB); kolejne użycia korzystają z plików lokalnych.

Obok wyboru głosu dostępne są cztery **profile mówienia**: „Spokojny i naturalny”, „Miękki / stonowany”, „Neutralny” i „Żywszy / dynamiczny”. Profile dostrajają tempo i parametry zmienności syntezy. Nie tworzą nowego modelu i nie gwarantują realistycznej ludzkiej intonacji — głosy Piper są gotowymi głosami syntetycznymi. Przed eksportem odsłuchaj próbkę wybranego głosu i profilu. Dla spokojnego lektora zacznij od „Spokojny i naturalny” lub „Miękki / stonowany”.

1. Najpierw wygeneruj lub wczytaj napisy dla filmu.
2. Otwórz zakładkę **Lektor AI** i kliknij **Wczytaj tekst z edytora napisów**. Zostaną skopiowane aktualne teksty i czasy z edytora, włącznie z ręcznymi poprawkami.
3. Możesz edytować tekst, Start/Koniec, dodawać fragmenty i usuwać niepotrzebne wiersze.
4. Wybierz głos oraz styl mówienia, a następnie kliknij **Odsłuchaj próbkę głosu** albo **Generuj lektora i wypal MP4**. Możesz odsłuchać kilka kombinacji, zanim wygenerujesz cały film.
5. W folderze wynikowym znajdziesz `NAZWA_lektor_ai.mp4` oraz osobną ścieżkę dźwiękową `NAZWA_lektor_ai.wav`.

**Ograniczenie pierwszej wersji:** MP4 ma nową ścieżkę audio z wygenerowaną mową, a cała oryginalna ścieżka dźwiękowa (głos, muzyka i odgłosy) jest zastąpiona. W przerwach pomiędzy wypowiedziami pozostaje cisza. Zachowanie muzyki i odgłosów tła przy usunięciu samego głosu wymaga osobnego modelu separacji źródeł audio i nie jest jeszcze włączone.

Lektor korzysta z tekstu rozpoznanego przez Whisper — nie klonuje automatycznie oryginalnego głosu mówcy i w tej wersji nie tłumaczy wypowiedzi. Profile stylu delikatnie regulują parametry syntezy, ale nie są odpowiednikiem zaawansowanego systemu głosowego z pełną kontrolą emocji i intonacji. Przed komercyjnym wykorzystaniem sprawdź licencję danego modelu głosu. Biblioteka Piper i wybrane głosy są pobierane z publicznych repozytoriów; modele pobierane są dopiero po wybraniu danego głosu.

## Napisy animowane w DaVinci Resolve

DaVinci Resolve importuje napisy jako edytowalną ścieżkę m.in. z pliku `.SRT`, ale nie zachowuje formatu stylów i animacji `.ASS` przez zwykły import napisów. Dlatego po zaimportowaniu pliku `.SRT` zobaczysz tekst, ale nie podświetlanie słów i animację z LocalCut AI. To ograniczenie formatu/importera Resolve, nie błąd transkrypcji.

Aby mieć kolorowe i animowane napisy w Resolve:

1. W LocalCut AI kliknij **Generuj polskie napisy AI**.
2. Ustaw czcionkę, rozmiar, kolory, podświetlanie słów i animację.
3. Jeżeli rozpoznany tekst wymaga korekty, otwórz zakładkę **Popraw tekst napisów**. Dwukrotnie kliknij komórkę „Tekst napisów (edytuj)” i popraw błędne słowo, np. `DU PA` na `DUPA`.
4. Możesz także dwukrotnie kliknąć **Start** lub **Koniec**, aby zmienić moment pojawienia się i zniknięcia napisu. Obsługiwany format to `HH:MM:SS.mmm`, np. `00:00:03.500`; akceptowany jest też prostszy format `MM:SS` lub liczba sekund, np. `3.5`. Przykład `00:00:00.000`–`00:01:00.000` oznacza wyświetlanie od początku do 1 minuty.
5. Aby dodać tekst nieobecny w transkrypcji, kliknij **+ Dodaj napis**, wpisz tekst i ustaw Start/Koniec. Czas między słowami nowego napisu rozłożony zostanie proporcjonalnie do długości słów. Aby usunąć napis, kliknij jego wiersz i wybierz **Usuń zaznaczone**. Przytrzymaj Ctrl lub Shift, aby zaznaczyć kilka wierszy. Usunięcie staje się trwałe w plikach wynikowych po wybraniu **Zapisz poprawki** lub **Zapisz i wypal MP4**.
6. Wybierz animację w ustawieniach: **Pop-in**, **Fade-in**, **Slide-up**, **Zoom-in**, **Bounce** lub **Bez animacji**.
7. Kliknij **Zapisz poprawki**, aby zaktualizować pliki `.SRT`, `.ASS` oraz `.JSON`, albo **Zapisz i wypal MP4**, żeby zapisać korekty i od razu wyrenderować gotowy film. Główny przycisk **Wypal animowane napisy do MP4** również korzysta z tekstu i czasów aktualnie pokazanych w tabeli.
8. Po zakończeniu zaimportuj do Resolve plik `NAZWA_napisy_animowane.mp4` z folderu wynikowego.

Edytor wczytuje zapisaną transkrypcję automatycznie po wybraniu tego samego filmu, jeśli plik JSON znajduje się w wybranym folderze wynikowym. W razie potrzeby użyj **Wczytaj zapisane napisy**. Przy poprawkach zachowujących liczbę słów czasy słów nie zmieniają się; gdy połączysz kilka słów w jedno (np. `DU PA` → `DUPA`), nowe słowo obejmie czas oryginalnych słów, a pozostałe dopasowane słowa zachowają swoje znaczniki czasu. Jeśli zmieni się liczba słów w poprawianym fragmencie, czasy nowych słów są dopasowywane do tego fragmentu. Ręczna zmiana Start/Koniec skaluje znaczniki czasu słów w całym wierszu tak, aby odpowiadały nowemu przedziałowi.

Ten MP4 zawiera napisy na stałe w obrazie — kolory i animacje pozostaną widoczne w Resolve, ale samego tekstu nie będzie można edytować jako osobnej ścieżki napisów. Zachowaj oryginalny film oraz `.SRT`, jeśli chcesz mieć wersję bez napisów i wersję z edytowalnym tekstem. Przycisk wypalania wymaga FFmpeg z filtrem `subtitles`/libass (kompilacja GPL/static zwykle go zawiera).

## Instalacja — krok po kroku

### 1. Python

Zainstaluj **Python 3.11 lub 3.12, 64-bit** z:

<https://www.python.org/downloads/windows/>

Podczas instalacji zaznacz opcję **Add Python to PATH**. Po instalacji możesz zamknąć i ponownie otworzyć terminal.

### 2. FFmpeg

FFmpeg jest potrzebny do usuwania ciszy i renderowania Shortsów. Wejdź na oficjalną stronę pobierania:

<https://ffmpeg.org/download.html>

W sekcji Windows wybierz jedną z kompilacji dla Windows x64 (np. Gyan). Rozpakuj archiwum. Folder `bin` powinien zawierać co najmniej `ffmpeg.exe` i `ffprobe.exe`.

Możesz zrobić jedną z dwóch rzeczy:

1. Dodać folder `bin` FFmpeg do zmiennej środowiskowej **PATH** systemu Windows, albo
2. skopiować `ffmpeg.exe` i `ffprobe.exe` bezpośrednio do folderu projektu `LocalCutAI`.

Sprawdź w nowym terminalu, że działają polecenia `ffmpeg -version` i `ffprobe -version`.

### 3. Zainstaluj zależności

Rozpakuj projekt do zwykłego folderu, np. `C:\LocalCutAI`. Kliknij dwukrotnie **`install.bat`**. Skrypt utworzy wirtualne środowisko `.venv` i zainstaluje zależności, w tym bibliotekę Piper dla lektora AI.

Jeżeli aktualizujesz istniejącą instalację, rozpakuj nową paczkę do tego samego folderu i zastąp pliki aplikacji, ale **nie usuwaj folderu `.venv`**. Następnie uruchom `install.bat`, aby doinstalować nową zależność `piper-tts`; dopiero potem uruchamiaj `run.bat`.

Jeżeli Windows blokuje skrypt pobrany z Internetu, sprawdź źródło pliku i uruchom go świadomie. Nie uruchamiaj go jako administrator — nie powinno to być potrzebne.

### 4. Uruchom aplikację

Kliknij dwukrotnie **`run.bat`**. W aplikacji:

1. Kliknij **Wybierz film**.
2. Sprawdź folder zapisu.
3. Kliknij **Generuj polskie napisy AI**.
4. Poczekaj na ukończenie transkrypcji. Przy pierwszym uruchomieniu model może zostać pobrany z sieci.
5. Pliki `.SRT`, `.ASS` oraz `.JSON` znajdziesz w folderze `LocalCutAI_output` obok filmu (chyba że wybierzesz inny folder).
6. Aby usunąć ciszę, kliknij **Wykryj i usuń ciszę**.
8. Aby utworzyć Shortsy: najpierw wygeneruj napisy, kliknij **Znajdź najlepsze fragmenty**, zaznacz propozycje i kliknij **Utwórz pionowe Shortsy**.

## Tryb CPU — bez CUDA i bez bibliotek NVIDIA

Ta wersja projektu działa **wymuszenie na procesorze CPU** i nie używa karty NVIDIA. Nie trzeba instalować CUDA, cuBLAS ani cuDNN. Dla komputera z 16 GB RAM domyślnie wybrany jest model `base`, który zwykle działa szybciej na CPU. Model `small` może dać lepsze wyniki, ale zwykle będzie wolniejszy; `medium` wymaga jeszcze więcej czasu i pamięci.

Rozpoznawanie mowy nadal jest lokalne. Pierwsze uruchomienie pobiera pliki wybranego modelu, a kolejne może korzystać z lokalnej kopii. Szybkość zależy od procesora i długości filmu.

## Naprawa błędu `metadata_errors`

Jeśli podczas generowania napisów pojawi się komunikat `open() got an unexpected keyword argument 'metadata_errors'`, jest to konflikt wersji `faster-whisper` i PyAV, a nie problem z plikiem wideo. W tym projekcie wymaganie `av>=11,<18` zapobiega instalowaniu niekompatybilnych nowszych wersji PyAV.

W istniejącej instalacji zamknij aplikację i uruchom w folderze projektu polecenie:

```bat
.venv\Scripts\python.exe -m pip install "av>=11,<18"
```

Następnie uruchom ponownie `run.bat`. Przy kolejnej instalacji `install.bat` skorzysta z ograniczenia zapisanego w `requirements.txt`.

## Typowe problemy

**„Nie znaleziono ffmpeg.exe”** — zainstaluj FFmpeg i dodaj jego folder `bin` do PATH albo skopiuj `ffmpeg.exe` i `ffprobe.exe` do folderu projektu.

**Model pobiera się długo przy pierwszym uruchomieniu** — to normalne; wagi modelu są pobierane raz i później korzysta się z lokalnej kopii.

**Komunikat o `cublas64_12.dll`** — ta wersja wymusza CPU i nie powinna ładować CUDA. Jeśli błąd nadal się pojawia, sprawdź, czy uruchamiasz `run.bat` z tego samego folderu, do którego rozpakowałeś tę wersję projektu.

**Shorts eksportują się bez napisów** — plik `.ASS` będzie zapisany obok filmu. Zainstaluj kompilację FFmpeg z obsługą filtra `subtitles`/libass, jeśli chcesz wypalać napisy bezpośrednio w obrazie.

**Tekst napisów jest błędny** — wybierz zakładkę **Popraw tekst napisów**, dwukrotnie kliknij tekst w tabeli, popraw go i kliknij **Zapisz poprawki** lub **Zapisz i wypal MP4**.

## Struktura projektu

```text
LocalCutAI/
├── main.py                 # start aplikacji
├── install.bat             # instalacja środowiska
├── run.bat                 # uruchamianie aplikacji
├── requirements.txt        # zależności Pythona
├── README_PL.md            # ta instrukcja
└── app/
    ├── main_window.py      # interfejs graficzny
    ├── ai.py               # lokalne rozpoznawanie mowy
    ├── captions.py         # eksport SRT/ASS/JSON i korekta tekstu z zachowaniem czasów
    ├── video_ops.py        # FFmpeg: cisza, fragmenty i Shorts
    └── worker.py           # zadania w tle, żeby interfejs nie zawieszał się
```

## Licencje

Projekt integruje biblioteki zewnętrzne, w tym PySide6, faster-whisper oraz FFmpeg. Każda z nich ma własne warunki licencyjne. Sprawdź je przed redystrybucją aplikacji lub przygotowaniem komercyjnego instalatora.

## Budowanie aplikacji do EXE

Aby stworzyć jednoplikową aplikację Windows, kliknij dwukrotnie `build_exe.bat`. Skrypt najpierw sprawdza biblioteki i automatycznie uruchomi `install.bat`, jeśli środowisko lub wymagane moduły są nieobecne. Następnie instaluje PyInstaller i buduje `dist\LocalCutAI.exe`. Jeśli budowanie się nie powiedzie, szczegóły znajdziesz w `build_exe.log`. Szczegółowe instrukcje i ograniczenia znajdują się w `README_EXE_PL.md`. Modele AI nie są wbudowane w EXE i pobierają się lokalnie dopiero przy pierwszym użyciu.


### Gdy instalator nie wykrywa Pythona

Nowsza wersja `install.bat` sprawdza launcher `py`, rejestr Windows oraz standardowe foldery instalacji. Jeśli nadal zgłasza brak Pythona 3.11/3.12, otwórz nowe okno CMD i uruchom `py -0p`. Na liście musi być instalacja 3.11 lub 3.12 64-bit. Jeśli jej nie ma, uruchom instalator Python 3.12 64-bit ponownie. Jeśli jest, ale skrypt nadal jej nie wykrywa, zachowaj wynik `py -0p` i prześlij go do diagnostyki.
