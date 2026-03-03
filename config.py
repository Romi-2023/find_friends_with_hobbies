# config.py – zmienne środowiska, stałe aplikacji, konfiguracja logowania
"""
Centralna konfiguracja aplikacji.
Wszystkie zmienne z .env i stałe używane w wielu modułach.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()


def get_env(name: str, default=None, cast=str):
    """
    Bezpieczne pobieranie zmiennych środowiskowych.
    - jeśli nie ma w env: zwraca default
    - jeśli podano cast=int/bool – spróbuje rzutować
    """
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default

    if cast is bool:
        return raw.lower() in ("1", "true", "yes", "y", "t")

    if cast is int:
        try:
            return int(raw)
        except ValueError:
            return default

    return raw


# --- Stałe z env ---
MEDIA_DIR = get_env("MEDIA_DIR", "media")
LOG_LEVEL = get_env("LOG_LEVEL", "INFO").upper()
LOG_FILE = get_env("LOG_FILE", "logs/app.log")

# E-mail
EMAIL_HOST = get_env("EMAIL_HOST", "")
EMAIL_PORT = get_env("EMAIL_PORT", 587, cast=int)
EMAIL_USER = get_env("EMAIL_USER", "")
EMAIL_PASSWORD = get_env("EMAIL_PASSWORD", "")
EMAIL_USE_TLS = get_env("EMAIL_USE_TLS", True, cast=bool)
EMAIL_FROM = get_env("EMAIL_FROM", EMAIL_USER or "no-reply@example.com")

# Aplikacja
APP_PUBLIC_URL = get_env("APP_PUBLIC_URL", "http://localhost:8501")

# Admin 2FA
ADMIN_TOTP_SECRET = (get_env("ADMIN_TOTP_SECRET", "") or "").strip()

# Geokodowanie / mapa
OPENCAGE_API_KEY = (get_env("OPENCAGE_API_KEY", "") or "").strip()
DEFAULT_COUNTRY = (get_env("DEFAULT_COUNTRY", "") or "").strip()

# Baza (używane też w db.py)
DB_HOST = get_env("DB_HOST", "localhost")
DB_NAME = get_env("DB_NAME", "hobby")
DB_USER = get_env("DB_USER", "postgres")
DB_PASSWORD = get_env("DB_PASSWORD", "haslo123")
DB_PORT = get_env("DB_PORT", 5432, cast=int)
DATABASE_URL = get_env("DATABASE_URL", None)
# Osobny schemat PostgreSQL przy współdzielonej bazie (np. find_friends). Puste = public.
DB_SCHEMA = (get_env("DB_SCHEMA", "") or "").strip()

# Baza: PostgreSQL (produkcja) lub SQLite (lokalne testy)
# Ustaw USE_SQLITE=1 aby zapisywać dane w pliku (data/app.db) bez instalacji Postgresa.
# Na wdrożeniu: USE_SQLITE=0 i podaj DATABASE_URL z DO.
USE_SQLITE = get_env("USE_SQLITE", "1").strip().lower() in ("1", "true", "yes")
SQLITE_PATH = get_env("SQLITE_PATH", "data/app.db")

# Stary tryb „bez bazy” (demo) – wyłączony; do testów używaj SQLite (USE_SQLITE=1).
SKIP_DB = get_env("SKIP_DB", "0").strip().lower() in ("1", "true", "yes")


def is_db_configured() -> bool:
    """True jeśli aplikacja ma używać bazy (PostgreSQL lub SQLite)."""
    if USE_SQLITE:
        return True
    return not SKIP_DB


def init_logging():
    """Konfiguruje logging do konsoli i pliku."""
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def get_logger(name: str = "ClubApp") -> logging.Logger:
    return logging.getLogger(name)
