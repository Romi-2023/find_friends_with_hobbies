# Wdrożenie na DigitalOcean App Platform

Aplikacja **Find Friends with Hobbies** może być wdrożona na DigitalOcean App Platform z użyciem **istniejącej bazy PostgreSQL** (np. tej samej, z której korzysta inna aplikacja).

## Wymagania

- Konto DigitalOcean
- Baza PostgreSQL na DO (Managed Database lub inna) – **już masz**
- Repozytorium z kodem (GitHub/GitLab) lub wgrywasz przez DO

## Krok 1: Baza danych

Używasz **tej samej bazy** co inna apka:

- W DO: **Databases** → wybierz swoją bazę PostgreSQL.
- Skopiuj **Connection string** (albo host, port, user, password, dbname).
- Dla App Platform najlepiej ustawić zmienną **`DATABASE_URL`** w formacie:
  ```text
  postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require
  ```
  (Dla bazy DO zwykle wymagany jest `sslmode=require`.)

Alternatywnie możesz ustawić osobno: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (bez `USE_SQLITE`).

**Ważne:** Na wdrożeniu aplikacja musi korzystać z **PostgreSQL**, nie SQLite. Ustaw w App Platform:

- **`USE_SQLITE=0`**  
  **albo** po prostu **nie ustawiaj** `USE_SQLITE` i ustaw tylko **`DATABASE_URL`** – wtedy `config`/`db.py` używają Postgresa.

## Krok 2: Utworzenie aplikacji na App Platform

1. W DigitalOcean: **Apps** → **Create App**.
2. Źródło kodu:
   - **GitHub** (lub GitLab) – podłącz repozytorium i wybierz branch (np. `main`),
   - **albo** **Dockerfile** – jeśli wgrywasz repozytorium z plikiem `Dockerfile` w katalogu głównym, App Platform wykryje go i zbuduje obraz.
3. **Build**: wybierz **Dockerfile** (ścieżka: `Dockerfile` w root).
4. **Run**: App Platform uruchomi kontener z komendą z Dockerfile (Streamlit na porcie z `PORT`).

## Krok 3: Zmienne środowiskowe (Environment Variables)

W ustawieniach komponentu **Web Service** (Twoja aplikacja) dodaj zmienne:

| Zmienna           | Wartość / opis |
|-------------------|----------------|
| `DATABASE_URL`    | Connection string do PostgreSQL (z DO lub innej bazy). |
| `USE_SQLITE`      | `0` (żeby wymusić PostgreSQL). |
| `APP_PUBLIC_URL`  | Pełny URL aplikacji po wdrożeniu, np. `https://twoja-apka-xxxx.ondigitalocean.app`. |
| `ADMIN_TOTP_SECRET` | Opcjonalnie – secret do 2FA admina (TOTP). |
| `EMAIL_HOST`, `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_FROM`, `EMAIL_PORT` | Opcjonalnie – do wysyłki maili (reset hasła, weryfikacja). |
| `OPENCAGE_API_KEY` | Opcjonalnie – do geokodowania (mapa, lokalizacje). |

**Minimalna konfiguracja** do startu:

- `DATABASE_URL` = connection string do Twojej bazy
- `USE_SQLITE=0`
- `APP_PUBLIC_URL` = URL aplikacji na DO (możesz ustawić po pierwszym deployu i zaktualizować)

## Krok 4: Migracje bazy

Schemat i migracje (np. `initialize_db()`) uruchamiane są przy starcie aplikacji przy pierwszym połączeniu z bazą (jeśli tak jest w kodzie).  
Jeśli Twoja baza jest już używana przez inną apkę, **nie** twórz tabel od zera – upewnij się, że:

- Tabele aplikacji Find Friends (np. `users`, `clubs`, `members`, `reports`, itd.) **istnieją** w tej samej bazie (w osobnym schemacie lub z prefiksem, jeśli tak ma być),
- **albo** uruchomisz migracje tylko raz (np. przez skrypt lub pierwsze uruchomienie z pustą bazą dla tej aplikacji).

Jeśli **współdzielisz bazę** z inną aplikacją, najlepiej użyć **osobnego schematu** (np. `find_friends`) albo upewnić się, że nazwy tabel się nie kłócą. Obecny kod zakłada tabele w domyślnym schemacie `public`.

## Krok 5: Deploy i weryfikacja

1. Zapisz konfigurację i uruchom **Deploy**.
2. Po zbudowaniu obrazu i starcie kontenera aplikacja będzie dostępna pod adresem typu:  
   `https://<twoja-app>.ondigitalocean.app`
3. Ustaw **`APP_PUBLIC_URL`** na ten adres (jeśli jeszcze nie ustawione).
4. Sprawdź logi w DO (Runtime Logs), czy nie ma błędów połączenia do bazy lub brakujących zmiennych.

## Uwagi

- **Pliki multimedialne (upload):** Domyślnie zapis są w katalogu `media/` w kontenerze. Na App Platform dysk jest nietrwały – po redeploy pliki znikną. Trwałe przechowywanie: **Spaces (S3)** i zmiana ścieżki uploadu w aplikacji (np. `MEDIA_DIR` lub integracja z S3).
- **Sesja Streamlit:** Domyślnie stan jest w pamięci. Przy wielu instancjach warto rozważyć zewnętrzne przechowywanie sesji (np. Redis) – na start jedna instancja wystarczy.
- **HTTPS:** App Platform domyślnie wystawia HTTPS; `APP_PUBLIC_URL` powinien być z `https://`.

## Podsumowanie

1. Baza: ta sama PostgreSQL na DO – ustaw **`DATABASE_URL`** i **`USE_SQLITE=0`**.  
2. App: **Create App** → źródło z repo → build z **Dockerfile**.  
3. Env: `DATABASE_URL`, `USE_SQLITE`, `APP_PUBLIC_URL` (i opcjonalnie mail, TOTP, OpenCage).  
4. Deploy i ustawienie `APP_PUBLIC_URL` na docelowy URL.

Po wdrożeniu aplikacja będzie działać na DO App Platform z Twoją istniejącą bazą PostgreSQL.
