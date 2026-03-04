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

**Ważne – trwałość danych:** Na wdrożeniu aplikacja musi korzystać z **PostgreSQL**. Wtedy wszystkie dane (konta, kluby, wiadomości, znajomi) są trwale zapisane w bazie i **nie znikają** po restarcie ani po zamknięciu przeglądarki. W App Platform ustaw:

- **`DATABASE_URL`** = connection string do PostgreSQL (wystarczy to, aby domyślnie użyć Postgresa),
- ewentualnie **`USE_SQLITE=0`** – jeśli nie ustawisz, przy ustawionym `DATABASE_URL` i tak używany jest PostgreSQL.

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
| `DB_SCHEMA`       | **Przy współdzielonej bazie:** nazwa schematu dla tej aplikacji (np. `find_friends`). Tabele powstają w tym schemacie; druga apka może używać `public` lub innego. Puste = `public`. |
| `APP_PUBLIC_URL`  | Pełny URL aplikacji po wdrożeniu, np. `https://twoja-apka-xxxx.ondigitalocean.app`. |
| `ADMIN_TOTP_SECRET` | Opcjonalnie – secret do 2FA admina (TOTP). |
| `EMAIL_HOST`, `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_FROM`, `EMAIL_PORT` | Opcjonalnie – do wysyłki maili (reset hasła, weryfikacja). |
| `OPENCAGE_API_KEY` | Opcjonalnie – do geokodowania (mapa, lokalizacje). |

**Minimalna konfiguracja** do startu:

- `DATABASE_URL` = connection string do Twojej bazy
- `USE_SQLITE=0`
- `APP_PUBLIC_URL` = URL aplikacji na DO (możesz ustawić po pierwszym deployu i zaktualizować)

**Przy współdzielonej bazie z inną aplikacją** (żeby obie działały bez konfliktów):

- `DB_SCHEMA=find_friends` (lub inna nazwa; tylko litery, cyfry, podkreślenie)

## Krok 4: Migracje bazy – utworzenie tabel (users, clubs, itd.)

Aby **dane w aplikacji były trwałe** (logowanie, kluby, wiadomości – bez utraty po wylogowaniu), w bazie muszą istnieć wszystkie tabele. Możesz je utworzyć na dwa sposoby:

### A) Skrypt jednorazowy (zalecane przy pustej bazie)

W katalogu projektu, z ustawionym **`DATABASE_URL`** (np. w `.env` lub w środowisku):

```bash
python scripts/init_production_db.py
```

Skrypt tworzy schemat (jeśli ustawiony `DB_SCHEMA`) oraz wszystkie tabele: `users`, `clubs`, `members`, `follows`, `club_events`, `reports`, itd. Po uruchomieniu możesz odpalić aplikację – dane będą zapisywane w bazie 24/7.

**Nazwy tabel (do testów / diagnostyki):** Aplikacja **nie** używa tabel `events`, `messages`, `friends`, `recommendations`. Używane są: **`club_events`** (Wydarzenia), **`follows`** (Znajomi / obserwowani), **`private_messages`** / **`forum_messages`** (wiadomości). Rekomendacje są liczone zapytaniami na `users` + `follows`, bez osobnej tabeli.

W **DigitalOcean**: w **Console** (Settings → Console lub SSH do kontenera) ustaw `DATABASE_URL` i uruchom ten skrypt, albo uruchom go lokalnie z `.env` zawierającym `DATABASE_URL` z DO.

### B) Automatycznie przy starcie aplikacji

Schemat i migracje (`initialize_db()`) uruchamiane są przy pierwszym wejściu na stronę. Jeśli z jakiegoś powodu tabele nie powstają (np. błąd połączenia przy pierwszym ładowaniu), użyj skryptu z punktu A.

Jeśli Twoja baza jest już używana przez inną apkę, **nie** twórz tabel od zera w tym samym schemacie – upewnij się, że:

- Tabele aplikacji Find Friends (np. `users`, `clubs`, `members`, `reports`, itd.) **istnieją** w tej samej bazie (w osobnym schemacie lub z prefiksem, jeśli tak ma być),
- **albo** uruchomisz migracje tylko raz (np. przez skrypt lub pierwsze uruchomienie z pustą bazą dla tej aplikacji).

**Współdzielona baza – nieinwazyjność:**  
Ta aplikacja jest zaprojektowana tak, aby **bezpiecznie dzielić jeden klaster bazy** z inną aplikacją i być dla niej **nieinwazyjna**: nie modyfikuje ani nie czyta tabel drugiej apki, a swoje dane trzyma w osobnym schemacie (gdy jest ustawiony `DB_SCHEMA`).

Ustaw zmienną **`DB_SCHEMA`** (np. `find_friends`). Aplikacja wtedy:
- tworzy schemat `find_friends` w bazie (jeśli ma uprawnienia; jeśli nie – działa dalej na `public`),
- ustawia `search_path` na ten schemat przy każdym połączeniu,
- wszystkie tabele (users, clubs, members, follows, club_events itd.) powstają w `find_friends`.

Druga aplikacja korzysta z schematu `public` (domyślny). Obie apki działają na jednej bazie, bez wspólnych tabel i bez ingerencji w dane drugiej.

## Krok 5: Deploy i weryfikacja

1. Zapisz konfigurację i uruchom **Deploy**.
2. Po zbudowaniu obrazu i starcie kontenera aplikacja będzie dostępna pod adresem typu:  
   `https://<twoja-app>.ondigitalocean.app`
3. Ustaw **`APP_PUBLIC_URL`** na ten adres (jeśli jeszcze nie ustawione).
4. Sprawdź logi w DO (Runtime Logs), czy nie ma błędów połączenia do bazy lub brakujących zmiennych.

## Uwagi

- **Pliki multimedialne (upload):** Domyślnie zapis są w katalogu `media/` w kontenerze. Na App Platform dysk jest nietrwały – po redeploy pliki znikną. Trwałe przechowywanie: **Spaces (S3)** i zmiana ścieżki uploadu w aplikacji (np. `MEDIA_DIR` lub integracja z S3).
- **Sesja Streamlit:** Stan logowania (`logged_in`, `username`) jest w pamięci – po zamknięciu przeglądarki użytkownik musi zalogować się ponownie. **Dane konta** (profil, kluby, wiadomości, znajomi) są w PostgreSQL i pozostają na stałe. Przy wielu instancjach warto rozważyć zewnętrzne przechowywanie sesji (np. Redis) – na start jedna instancja wystarczy.
- **HTTPS:** App Platform domyślnie wystawia HTTPS; `APP_PUBLIC_URL` powinien być z `https://`.

## Podsumowanie

1. Baza: ta sama PostgreSQL na DO – ustaw **`DATABASE_URL`** i **`USE_SQLITE=0`**.  
2. App: **Create App** → źródło z repo → build z **Dockerfile**.  
3. Env: `DATABASE_URL`, `USE_SQLITE`, `APP_PUBLIC_URL` (i opcjonalnie mail, TOTP, OpenCage).  
4. Deploy i ustawienie `APP_PUBLIC_URL` na docelowy URL.

Po wdrożeniu aplikacja będzie działać na DO App Platform z Twoją istniejącą bazą PostgreSQL.

---

## Sprawdzenie: czy baza jest podpięta pod aplikację

Na App Platform **baza nie pojawia się w komponentach aplikacji** – masz osobny Managed Database (`db-postgresql-fra1-17985`) i użytkownika `find_friends_app`. Aplikacja łączy się z nią **wyłącznie przez zmienne środowiskowe**. Jeśli ich nie ma lub są błędne, dostaniesz biały ekran.

### Checklist w DigitalOcean

1. **Zmienne środowiskowe aplikacji**
   - Wejdź: **Apps** → **find-friend-with-hobby-app** → **Settings** (lub **Components** → klik w komponent **find-friends-with-hobbies**).
   - Sekcja **Environment Variables** (lub **App-Level Environment Variables**).
   - **Muszą być ustawione:**
     - **`DATABASE_URL`** – connection string do bazy (patrz niżej). Bez tego aplikacja nie wie, gdzie się łączyć.
     - **`USE_SQLITE`** = **`0`** (żeby używać PostgreSQL zamiast SQLite).

2. **Skąd wziąć DATABASE_URL**
   - **Databases** → **db-postgresql-fra1-17985**.
   - W zakładce **Overview** (lub **Connection details**) znajdź **Connection string** albo **Connection parameters**.
   - Użyj użytkownika **`find_friends_app`** (i jego hasła – „show” przy użytkowniku). Format:
     ```text
     postgresql://find_friends_app:HASLO@HOST:PORT/defaultdb?sslmode=require
     ```
     Zastąp `HASLO` prawdziwym hasłem, `HOST` i `PORT` wartościami z panelu bazy. Dla Managed Database DO zwykle **musi** być `?sslmode=require`.

3. **Dostęp sieciowy**
   - W bazie: **Settings** → **Trusted Sources** (lub **Network**). Aplikacje App Platform w tym samym koncie często mają dostęp domyślnie; jeśli baza ma ograniczenie do konkretnych adresów, upewnij się, że ruch z App Platform jest dozwolony (np. „Allow all” lub odpowiedni zakres).

4. **Logi po uruchomieniu**
   - **Apps** → Twoja aplikacja → **Runtime Logs**.
   - Otwórz stronę w przeglądarce (żeby wywołać połączenie do bazy), odśwież logi. Szukaj: `Postgres pool error`, `Schema init error`, `connection refused`, `timeout`, `permission denied`. To potwierdzi, czy problem to brak/źle podpiętej bazy.

**Podsumowanie:** Baza jest „podpięta” tylko wtedy, gdy w ustawieniach **Web Service** masz ustawione `DATABASE_URL` (i `USE_SQLITE=0`). Brak `DATABASE_URL` lub błąd w connection stringu = biały ekran.

---

## Rozwiązywanie problemów: biała strona mimo statusu „Healthy”

Jeśli w przeglądarce widzisz **białą stronę**, a w DO aplikacja ma status **Healthy**, kontener się uruchamia, ale pierwsze renderowanie strony się nie udaje. Sprawdź poniższe punkty.

### 1. Runtime Logs (najważniejsze)

W DO: **Apps** → Twoja aplikacja → zakładka **Runtime Logs** (lub **Console**).

- Szukaj błędów typu: `Postgres pool error`, `Schema init error`, `connection refused`, `timeout`, `permission denied`.
- Jeśli przy pierwszym wejściu na stronę w logach pojawia się wyjątek z `db.py` lub `app.py`, to właśnie on blokuje wyświetlenie interfejsu.

### 2. Współdzielona baza danych – możliwe przyczyny

Tak, **współdzielona baza z inną aplikacją może być przyczyną** białej strony lub błędów. Typowe problemy:

| Problem | Objaw / co sprawdzić |
|--------|----------------------|
| **Brak uprawnień** | Użytkownik bazy nie ma praw `CREATE` / `ALTER` w schemacie `public`. Aplikacja przy starcie wywołuje `initialize_db()` (CREATE TABLE IF NOT EXISTS, ALTER TABLE …). Brak uprawnień → błąd w logach, strona może zostać pusta. |
| **Konflikt tabel** | Druga aplikacja ma tabele o tych samych nazwach (`users`, `clubs`, …) ale innej strukturze. `CREATE TABLE IF NOT EXISTS` nic nie zmieni, ale kolejne `ALTER TABLE … ADD COLUMN …` mogą się wyłożyć (np. inny typ kolumny). |
| **Limit połączeń** | Dwie aplikacje łączące się do jednej bazy zużywają łącznie więcej połączeń. Przekroczenie limitu → błąd połączenia przy starcie, możliwa biała strona. |
| **Timeout / sieć** | Wolna lub przeciążona baza albo problemy sieciowe. Połączenie trwa zbyt długo → request HTTP do aplikacji się przekracza → użytkownik widzi pustą stronę. |

**Rekomendacja przy współdzielonej bazie:**

- Użyj **osobnego schematu** (np. `find_friends`) i ustaw w `DATABASE_URL` opcję `options=-c search_path=find_friends` (oraz utwórz ten schemat w bazie), **albo**
- Upewnij się, że tabele Find Friends (np. `users`, `clubs`, `members`, …) **istnieją i są zgodne** z tym, czego oczekuje ta aplikacja, i że użytkownik ma uprawnienia do `CREATE`/`ALTER` w tym schemacie.

### 3. Zmienne środowiskowe

W **Settings** → **App-Level** lub **Component** → zmienne środowiskowe sprawdź:

- **`DATABASE_URL`** – poprawny connection string (np. `postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require`). Dla Managed Database DO zwykle potrzebny jest `sslmode=require`.
- **`USE_SQLITE`** – na wdrożeniu ustaw **`0`** (PostgreSQL). Gdy brakuje tej zmiennej, domyślnie może być używany SQLite, co na App Platform nie ma sensu i może prowadzić do błędów.
- **`APP_PUBLIC_URL`** – ustaw na faktyczny URL aplikacji (np. `https://find-friend-with-hobby-app-9smie.ondigitalocean.app`).

### 4. Szybki test bazy

Jeśli masz dostęp do bazy (psql lub inny klient):

- Połącz się tym samym użytkownikiem i tym samym hasłem co w `DATABASE_URL`.
- Wykonaj: `SELECT 1;` oraz np. `SELECT current_user, current_database();`.
- Sprawdź uprawnienia: czy użytkownik może tworzyć tabele w wybranym schemacie (np. `CREATE TABLE IF NOT EXISTS test_perm (id int); DROP TABLE test_perm;`).

Dzięki temu upewnisz się, że problem nie leży w samym połączeniu ani w uprawnieniach.
