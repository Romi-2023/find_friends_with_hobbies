# Struktura projektu – Find Friends with Hobbies

Kod został podzielony na segmenty, żeby ułatwić dalszy rozwój i uniknąć „rozjechania” jednego pliku.

## Główne pliki

| Plik | Odpowiedzialność |
|------|------------------|
| **app.py** | Punkt wejścia Streamlit: i18n (tłumaczenia, `t()`), konfiguracja strony, **router** (menu, logowanie / widoki zalogowanego), **wszystkie widoki UI** (dashboard, kluby, wydarzenia, wiadomości, profil, admin itd.). Tu są też wrappery wywołujące moduły i wyświetlające błędy (`db_conn`, `save_upload`, `initialize_db`). |
| **config.py** | Zmienne środowiska (`get_env`), stałe (MEDIA_DIR, EMAIL_*, APP_PUBLIC_URL, OPENCAGE_API_KEY, ADMIN_TOTP_SECRET itd.), inicjalizacja logowania (`init_logging`, `get_logger`). |
| **db.py** | Baza PostgreSQL: `get_connection()`, `get_pool()`, `db_conn()`, `db_release()`, schemat `INIT_SQL`, `initialize_db()`. Bez wyświetlania błędów w UI – to robi app.py. |
| **geo_weather.py** | Geokodowanie (OpenCage) i pogoda (Open-Meteo): `geocode_with_opencage()`, `resolve_city_coordinates()`, `get_weather(city, lang)`. |
| **email_service.py** | Wysyłka e-maili (SMTP): `send_email(to, subject, body)`. |
| **uploads.py** | Zapis plików do galerii: `save_upload(file, club_id)` → `(path, media_type)` lub `(None, None)`. Walidacja typów i rozmiaru. |

## Zasady na przyszłość

1. **Nowa funkcjonalność bazy / połączeń** → `db.py`.
2. **Nowe zewnętrzne API (mapy, pogoda, inne serwisy)** → nowy moduł (np. `geo_weather.py`) lub rozszerzenie istniejącego.
3. **Nowe stałe i zmienne z .env** → `config.py`.
4. **Nowe tłumaczenia** → słownik `translations` w `app.py` (docelowo można przenieść do modułu `i18n`).
5. **Nowe widoki / ekrany** → w `app.py` w odpowiedniej sekcji (Auth, Dashboard, Clubs, Events, Messages, Profile, Admin) albo w osobnym pliku w pakiecie `views/`, jeśli taki powstanie.
6. **Logika biznesowa bez UI** (np. obliczenia, walidacje, zapytania do bazy) → najlepiej w osobnym module (np. `users.py`, `clubs.py`), a w `app.py` tylko wywołania i wyświetlanie wyników/błędów.

## Uruchomienie

```bash
streamlit run app.py
```

Zmienne środowiska: `.env` (wzór: `.env.example`). Baza: PostgreSQL (config w `config.py` / `db.py`).
