# Instrukcja Uruchomienia Aplikacji Księgarnia

Poniżej znajdują się kroki niezbędne do uruchomienia aplikacji na nowym środowisku.

## Wymagania Wstępne

*   Python 3.8+
*   pip (manager pakietów Python)
*   Git (opcjonalnie, jeśli klonujesz repozytorium)

## Kroki Instalacji i Uruchomienia

1.  **Sklonuj Repozytorium (jeśli jeszcze tego nie zrobiłeś):**
    ```bash
    git clone <adres-repozytorium>
    cd <nazwa-katalogu-repozytorium>
    ```

2.  **Utwórz i Aktywuj Wirtualne Środowisko:**
    Zalecane jest użycie wirtualnego środowiska do izolacji zależności projektu.

    *   Dla Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *   Dla macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Zainstaluj Wymagane Pakiety:**
    Wszystkie niezbędne pakiety znajdują się w pliku `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Skonfiguruj Zmienne Środowiskowe:**
    Skopiuj plik `.env.example` do nowego pliku o nazwie `.env`.
    ```bash
    # Dla Windows (Command Prompt)
    copy .env.example .env

    # Dla Windows (PowerShell)
    Copy-Item .env.example .env

    # Dla macOS/Linux
    cp .env.example .env
    ```
    Przejrzyj plik `.env` i dostosuj wartości, jeśli jest to konieczne. Domyślne ustawienia powinny działać dla środowiska deweloperskiego. Kluczowe zmienne to `SECRET_KEY` i `WTF_CSRF_SECRET_KEY` - dla bezpieczeństwa warto wygenerować nowe, unikalne wartości.

5.  **Zainicjalizuj Bazę Danych:**
    Aplikacja używa Flask-Migrate do zarządzania schematem bazy danych oraz posiada komendę do inicjalizacji bazy danych i utworzenia domyślnych użytkowników (admin, manager).
    Upewnij się, że jesteś w głównym katalogu projektu.

    ```bash
    flask db upgrade
    flask init-db
    ```
    Alternatywnie, jeśli `flask` nie jest rozpoznawane bezpośrednio (zależnie od konfiguracji PATH):
    ```bash
    python -m flask db upgrade
    python -m flask init-db
    ```
    Komenda `init-db` utworzy administratora z loginem `admin` i hasłem `adminpass` oraz managera z loginem `manager` i hasłem `managerpass`. **Pamiętaj, aby zmienić te hasła w środowisku produkcyjnym!**

6.  **Uruchom Aplikację:**
    Aplikację można uruchomić za pomocą skryptu `run.py`.
    ```bash
    python run.py
    ```
    Aplikacja powinna być dostępna pod adresem `http://127.0.0.1:5000` (lub innym portem, jeśli jest skonfigurowany inaczej).

## Dodatkowe Komendy CLI

Aplikacja może zawierać dodatkowe komendy CLI, np. do seedowania danych.

*   **Seedowanie książek (jeśli dostępne):**
    Sprawdź plik `run.py` lub `seed_data.py` w poszukiwaniu komend takich jak `flask seed-books`.
    ```bash
    flask seed-books
    ```

## Rozwiązywanie Problemów

*   **Brak modułu `X`:** Upewnij się, że wirtualne środowisko jest aktywne i wszystkie pakiety z `requirements.txt` zostały poprawnie zainstalowane.
*   **Problemy z bazą danych:** Sprawdź konfigurację `DATABASE_URL` w pliku `.env`. Upewnij się, że katalog `instance/` istnieje (powinien zostać utworzony automatycznie, jeśli nie istnieje). W razie problemów z migracjami, czasami pomocne może być usunięcie pliku bazy danych (`instance/ksiegarnia.db`) i katalogu `migrations/versions/` (ostrożnie, to usunie wszystkie dane!) i ponowne wykonanie `flask db init`, `flask db migrate -m "initial migration"`, `flask db upgrade`.
*   **Błąd `fatal error unable to create process using '...'` podczas aktywacji `venv`:** Ten błąd często występuje, gdy katalog `venv` został skopiowany z innego komputera lub przeniesiony, a ścieżki wewnątrz niego są nieaktualne. Aby to naprawić, należy usunąć istniejący katalog `venv` i utworzyć go na nowo:
    1.  **Dezaktywuj** aktualne wirtualne środowisko, jeśli jest aktywne (zazwyczaj komenda `deactivate`).
    2.  **Usuń** katalog `venv`:
        ```bash
        # Dla Windows (Command Prompt)
        rd /s /q venv

        # Dla Windows (PowerShell)
        Remove-Item -Recurse -Force venv

        # Dla macOS/Linux
        rm -rf venv
        ```
    3.  **Utwórz** nowe wirtualne środowisko i **aktywuj** je zgodnie z punktem 2. głównej instrukcji ("Utwórz i Aktywuj Wirtualne Środowisko").
    4.  **Zainstaluj ponownie** zależności: `pip install -r requirements.txt`.
*   **Błąd `the term flask is not recognized as the name of a cmdlet, function, script file, or operable program` (lub podobny):** Ten błąd oznacza, że system nie może znaleźć komendy `flask`. Możliwe przyczyny i rozwiązania:
    1.  **Wirtualne środowisko nie jest aktywne:** Upewnij się, że aktywowałeś wirtualne środowisko (`venv`) w bieżącej sesji terminala. Nazwa aktywnego środowiska powinna być widoczna w wierszu poleceń (np. `(venv) C:\path\to\project>`). Jeśli nie jest, aktywuj je ponownie (patrz krok 2. "Utwórz i Aktywuj Wirtualne Środowisko").
    2.  **Flask nie jest zainstalowany w aktywnym `venv`:** Po utworzeniu/ponownym utworzeniu i aktywacji `venv`, upewnij się, że wszystkie zależności zostały zainstalowane komendą:
        ```bash
        pip install -r requirements.txt
        ```
    3.  **Alternatywne wywołanie komend Flask:** Jeśli powyższe kroki nie pomogą, a masz pewność, że Flask jest zainstalowany w `venv`, możesz spróbować wywoływać komendy Flask bezpośrednio przez moduł Pythona:
        ```bash
        python -m flask db upgrade
        python -m flask init-db
        # itd.
        ```
        Ta metoda czasami omija problemy związane ze ścieżkami systemowymi.
*   **Błąd `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file` (często przy Uvicorn/ASGI):**
    Ten błąd oznacza, że aplikacja nie może znaleźć lub otworzyć pliku bazy danych SQLite. Przejdź przez poniższą listę kontrolną **krok po kroku**:
    1.  **Weryfikacja pliku `.env` i ścieżki `DATABASE_URL`:**
        *   **Lokalizacja pliku `.env`**: Upewnij się, że plik nazywa się dokładnie `.env` (z kropką na początku, bez dodatkowych rozszerzeń typu `.txt`) i znajduje się **bezpośrednio w głównym katalogu projektu** (np. `D:\Projekt\ksiegarnia\.env`).
        *   **Poprawność `DATABASE_URL`**:
            *   Jeśli używasz **ścieżki względnej** (zalecane): `DATABASE_URL='sqlite:///instance/ksiegarnia.db'`
            *   Jeśli używasz **ścieżki absolutnej** (np. dla `D:\Projekt\ksiegarnia\`): `DATABASE_URL='sqlite:///D:/Projekt/ksiegarnia/instance/ksiegarnia.db'`
                *   Sprawdź dokładnie literówki. Pamiętaj o użyciu `/` zamiast `\` w ścieżce w pliku `.env`.
    2.  **Weryfikacja katalogu `instance/`:**
        *   **Istnienie katalogu**: Przejdź do głównego katalogu projektu (np. `D:\Projekt\ksiegarnia\`) i **sprawdź, czy istnieje tam podkatalog o nazwie `instance`**.
        *   **Jeśli katalog `instance/` nie istnieje, utwórz go ręcznie.**
    3.  **Inicjalizacja bazy danych (PO SPRAWDZENIU PUNKTÓW 1 i 2):**
        *   Upewnij się, że masz **aktywne środowisko wirtualne (`venv`)**.
        *   Będąc w głównym katalogu projektu, wykonaj **ponownie** następujące komendy, jedna po drugiej:
            ```bash
            flask db upgrade
            ```
            A następnie:
            ```bash
            flask init-db
            ```
            Lub, jeśli `flask` nie jest rozpoznawane:
            ```bash
            python -m flask db upgrade
            ```
            A następnie:
            ```bash
            python -m flask init-db
            ```
        *   **Weryfikacja po inicjalizacji**: Po wykonaniu tych komend, **sprawdź fizycznie**, czy w katalogu `instance/` (np. `D:\Projekt\ksiegarnia\instance\`) pojawił się plik `ksiegarnia.db`. Jeśli go tam nie ma, komendy inicjalizacji nie zadziałały poprawnie (może być inny błąd widoczny w terminalu podczas ich wykonywania).
    4.  **Uruchamianie Uvicorn z właściwego katalogu:**
        *   Upewnij się, że komendę `uvicorn main_asgi:app --reload` (lub podobną) uruchamiasz **będąc w głównym katalogu projektu** (tam, gdzie jest `main_asgi.py` i `.env`).
    5.  **Uprawnienia (mniej prawdopodobne, ale do sprawdzenia w ostateczności):**
        *   Sprawdź, czy użytkownik, na którego koncie uruchamiasz aplikację, ma uprawnienia do odczytu i zapisu w katalogu `instance/` oraz do pliku `ksiegarnia.db`.

To wszystko! Aplikacja powinna być gotowa do użytku.
