# db.py – PostgreSQL lub SQLite (zapisywanie danych)
"""
Warstwa dostępu do bazy.
- USE_SQLITE=1: SQLite (plik data/app.db) – do testów bez Postgresa.
- USE_SQLITE=0 i DATABASE_URL/DB_*: PostgreSQL (produkcja, np. DO).
- get_connection(), get_pool(), db_conn(), db_release(), initialize_db()
"""

import logging
import os
import re
import sqlite3

import config
import streamlit as st

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQLite: wrapper żeby używać placeholderów %s jak w psycopg2
# ---------------------------------------------------------------------------

def _sqlite_adapt_sql(sql):
    """Zamienia placeholdery %s na ? oraz ILIKE na LIKE (SQLite nie ma ILIKE)."""
    sql = re.sub(r"(?<![%])%s(?![a-z])", "?", sql)
    sql = re.sub(r"\bILIKE\b", "LIKE", sql, flags=re.IGNORECASE)
    return sql


class _SQLiteCursorWrapper:
    def __init__(self, cursor):
        self._c = cursor

    def execute(self, sql, params=None):
        if params is not None:
            sql = _sqlite_adapt_sql(sql)
        if params:
            self._c.execute(sql, params)
        else:
            self._c.execute(sql)

    def executemany(self, sql, params):
        sql = _sqlite_adapt_sql(sql)
        self._c.executemany(sql, params)

    def fetchone(self):
        return self._c.fetchone()

    def fetchall(self):
        return self._c.fetchall()

    def close(self):
        self._c.close()

    @property
    def description(self):
        return getattr(self._c, "description", None)

    @property
    def connection(self):
        return self._c.connection


class _SQLiteConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _SQLiteCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._conn.commit()
        return False


def _sqlite_connect():
    path = config.SQLITE_PATH
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # opcjonalnie: dostęp przez nazwy kolumn
    return _SQLiteConnectionWrapper(conn)


# ---------------------------------------------------------------------------
# PostgreSQL (oryginalna logika + osobny schemat przy współdzielonej bazie)
# Przy współdzielonym klastrze aplikacja jest nieinwazyjna: swoje tabele w DB_SCHEMA.
# ---------------------------------------------------------------------------

def _pg_schema_name() -> str:
    """Zwraca bezpieczną nazwę schematu (tylko [a-zA-Z0-9_]) lub pustą przy public."""
    s = getattr(config, "DB_SCHEMA", "") or ""
    if not s:
        return ""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", s):
        logger.warning("Invalid DB_SCHEMA ignored: %r", s)
        return ""
    return s


def _pg_set_schema(conn):
    """
    Dla PostgreSQL: jeśli DB_SCHEMA ustawiony – tworzy schemat (jeśli może) i ustawia search_path.
    Gdy użytkownik bazy nie ma praw CREATE SCHEMA (np. współdzielona baza DO), nie przerywamy:
    ustawiamy search_path na public, żeby aplikacja działała jak wcześniej.
    """
    schema = _pg_schema_name()
    if not schema:
        return
    cur = conn.cursor()
    try:
        cur.execute("CREATE SCHEMA IF NOT EXISTS %s" % schema)
        cur.execute("SET search_path TO %s" % schema)
        conn.commit()
        # Jeśli w tym schemacie nie ma tabel (np. users), tabele są w public – przełącz na public
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = 'users' LIMIT 1",
            (schema,),
        )
        if cur.fetchone() is None:
            logger.warning("DB schema %r jest pusty (brak tabel) – używam public", schema)
            cur.execute("SET search_path TO public")
            conn.commit()
    except Exception as e:
        logger.warning("DB schema %r: %s – używam public", schema, e)
        try:
            cur.execute("SET search_path TO public")
            conn.commit()
        except Exception:
            pass
    finally:
        cur.close()


def _pg_connection():
    import psycopg2
    if config.DATABASE_URL:
        conn = psycopg2.connect(config.DATABASE_URL)
    else:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            port=config.DB_PORT,
        )
    _pg_set_schema(conn)
    return conn


@st.cache_resource
def _pg_pool():
    from psycopg2.pool import SimpleConnectionPool
    if config.DATABASE_URL:
        return SimpleConnectionPool(1, 10, dsn=config.DATABASE_URL)
    return SimpleConnectionPool(
        1, 10,
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT,
    )


# ---------------------------------------------------------------------------
# API: get_connection, get_pool, db_conn, db_release
# ---------------------------------------------------------------------------

def get_connection():
    """Pojedyncze połączenie (np. do geo). Gdy SKIP_DB i nie SQLite – None."""
    if getattr(config, "USE_SQLITE", False):
        return _sqlite_connect()
    if getattr(config, "SKIP_DB", False):
        return None
    return _pg_connection()


class _SQLitePool:
    """Pseudopool dla SQLite – każde getconn() to nowe połączenie, putconn zamyka."""
    def getconn(self):
        return _sqlite_connect()

    def putconn(self, conn):
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@st.cache_resource
def get_pool():
    """Pool (PostgreSQL) lub pseudopool (SQLite). Gdy SKIP_DB i nie SQLite – None."""
    if getattr(config, "USE_SQLITE", False):
        return _SQLitePool()
    if getattr(config, "SKIP_DB", False):
        return None
    try:
        return _pg_pool()
    except Exception as e:
        logger.error("Postgres pool error: %s", e)
        return None


def db_conn():
    """Zwraca połączenie z poolu (lub None). Dla PostgreSQL z DB_SCHEMA ustawia search_path."""
    pool = get_pool()
    if not pool:
        return None
    try:
        conn = pool.getconn()
        if not getattr(config, "USE_SQLITE", False) and _pg_schema_name():
            _pg_set_schema(conn)
        return conn
    except Exception as e:
        logger.error("DB connection error: %s", e)
        return None


def db_release(conn):
    """Oddaje połączenie do poolu (lub zamyka przy SQLite)."""
    if not conn:
        return
    try:
        pool = get_pool()
        if pool:
            pool.putconn(conn)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Schemat SQLite (odpowiednik INIT_SQL)
# ---------------------------------------------------------------------------

INIT_SQL_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    city TEXT NOT NULL,
    profile_picture TEXT,
    description TEXT DEFAULT '',
    is_admin INTEGER DEFAULT 0,
    email TEXT,
    is_verified INTEGER DEFAULT 0,
    language TEXT DEFAULT 'en',
    last_activity TEXT,
    referrer TEXT
);

CREATE TABLE IF NOT EXISTS hobbies (
    username TEXT NOT NULL,
    hobby TEXT NOT NULL,
    PRIMARY KEY (username, hobby),
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clubs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    description TEXT,
    members_count INTEGER DEFAULT 0,
    latitude REAL,
    longitude REAL,
    owner_username TEXT,
    deputy_username TEXT,
    privacy_level TEXT NOT NULL DEFAULT 'public',
    is_hidden INTEGER DEFAULT 0,
    FOREIGN KEY (owner_username) REFERENCES users(username) ON DELETE SET NULL,
    FOREIGN KEY (deputy_username) REFERENCES users(username) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS members (
    username TEXT NOT NULL,
    club_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    PRIMARY KEY (username, club_id),
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    club_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    review TEXT,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS media_gallery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    media_type TEXT NOT NULL,
    media_path TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    read INTEGER DEFAULT 0,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS private_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (sender) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (receiver) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS blocks (
    blocker TEXT NOT NULL,
    blocked TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (blocker, blocked),
    FOREIGN KEY (blocker) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (blocked) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter TEXT NOT NULL,
    reported_user TEXT,
    reported_club INTEGER,
    reported_message_id INTEGER,
    reported_message_type TEXT,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (reporter) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (reported_user) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (reported_club) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_customizations (
    username TEXT PRIMARY KEY,
    background_color TEXT DEFAULT '#FFFFFF',
    font_size TEXT DEFAULT 'medium',
    font_family TEXT DEFAULT 'Arial',
    theme TEXT DEFAULT 'light',
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS club_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    event_date TEXT NOT NULL,
    event_time TEXT,
    location TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS forum_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS city_locations (
    city TEXT PRIMARY KEY,
    latitude REAL,
    longitude REAL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS follows (
    follower TEXT NOT NULL,
    following TEXT NOT NULL,
    PRIMARY KEY (follower, following),
    FOREIGN KEY (follower) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (following) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS club_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS password_resets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    used INTEGER DEFAULT 0,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feed_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    city TEXT,
    club_id INTEGER,
    payload TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (actor) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    unlocked_at TEXT DEFAULT (datetime('now')),
    UNIQUE (username, code),
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_rsvps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('going','maybe','not_going')),
    UNIQUE(event_id, username),
    FOREIGN KEY (event_id) REFERENCES club_events(id) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS club_join_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(club_id, username),
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS club_partnerships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    partner_club_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','declined')),
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(club_id, partner_club_id),
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE,
    FOREIGN KEY (partner_club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_club_partnerships_partner ON club_partnerships(partner_club_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_username ON user_achievements(username);
CREATE INDEX IF NOT EXISTS idx_feed_created_at ON feed_activities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feed_city ON feed_activities(city);
CREATE INDEX IF NOT EXISTS idx_feed_club_id ON feed_activities(club_id);
CREATE INDEX IF NOT EXISTS idx_hobbies_hobby ON hobbies(hobby);
CREATE INDEX IF NOT EXISTS idx_members_club_id ON members(club_id);
CREATE INDEX IF NOT EXISTS idx_pm_receiver ON private_messages(receiver);
CREATE INDEX IF NOT EXISTS idx_clubs_city ON clubs(city);
CREATE INDEX IF NOT EXISTS idx_email_verifications_token ON email_verifications(token);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;
"""


# ---------------------------------------------------------------------------
# Schemat PostgreSQL (bez zmian)
# ---------------------------------------------------------------------------

INIT_SQL = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    city TEXT NOT NULL,
    profile_picture TEXT,
    description TEXT DEFAULT '',
    is_admin INTEGER DEFAULT 0,
    email TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    language TEXT DEFAULT 'en',
    last_activity TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS hobbies (
    username TEXT NOT NULL,
    hobby TEXT NOT NULL,
    PRIMARY KEY (username, hobby),
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clubs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    description TEXT,
    members_count INTEGER DEFAULT 0,
    latitude REAL,
    longitude REAL,
    owner_username TEXT REFERENCES users(username) ON DELETE SET NULL,
    deputy_username TEXT REFERENCES users(username) ON DELETE SET NULL,
    privacy_level TEXT NOT NULL DEFAULT 'public',
    is_hidden INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS members (
    username TEXT NOT NULL,
    club_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    PRIMARY KEY (username, club_id),
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    club_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    review TEXT,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS media_gallery (
    id SERIAL PRIMARY KEY,
    club_id INTEGER NOT NULL,
    media_type TEXT NOT NULL,
    media_path TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT DEFAULT (CURRENT_TIMESTAMP),
    read INTEGER DEFAULT 0,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS private_messages (
    id SERIAL PRIMARY KEY,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (sender) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (receiver) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS blocks (
    blocker TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    blocked TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (blocker, blocked)
);

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    reporter TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    reported_user TEXT REFERENCES users(username) ON DELETE CASCADE,
    reported_club INTEGER REFERENCES clubs(id) ON DELETE CASCADE,
    reported_message_id INTEGER,
    reported_message_type TEXT,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_customizations (
    username TEXT PRIMARY KEY,
    background_color TEXT DEFAULT '#FFFFFF',
    font_size TEXT DEFAULT 'medium',
    font_family TEXT DEFAULT 'Arial',
    theme TEXT DEFAULT 'light',
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS club_events (
    id SERIAL PRIMARY KEY,
    club_id INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    event_date TEXT NOT NULL,
    event_time TEXT,
    location TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS forum_messages (
    id SERIAL PRIMARY KEY,
    club_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS city_locations (
    city TEXT PRIMARY KEY,
    latitude REAL,
    longitude REAL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS follows (
    follower TEXT NOT NULL,
    following TEXT NOT NULL,
    PRIMARY KEY (follower, following),
    FOREIGN KEY (follower) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (following) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS club_reviews (
    id SERIAL PRIMARY KEY,
    club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS password_resets (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS email_verifications (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    used BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS feed_activities (
    id SERIAL PRIMARY KEY,
    activity_type TEXT NOT NULL,
    actor TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    city TEXT,
    club_id INTEGER REFERENCES clubs(id) ON DELETE CASCADE,
    payload TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    unlocked_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (username, code)
);

CREATE TABLE IF NOT EXISTS event_rsvps (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES club_events(id) ON DELETE CASCADE,
    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('going','maybe','not_going')),
    UNIQUE(event_id, username)
);

CREATE INDEX IF NOT EXISTS idx_user_achievements_username ON user_achievements(username);
CREATE INDEX IF NOT EXISTS idx_feed_created_at ON feed_activities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feed_city ON feed_activities(city);
CREATE INDEX IF NOT EXISTS idx_feed_club_id ON feed_activities(club_id);
CREATE INDEX IF NOT EXISTS idx_hobbies_hobby ON hobbies(hobby);
CREATE INDEX IF NOT EXISTS idx_members_club_id ON members(club_id);
CREATE INDEX IF NOT EXISTS idx_pm_receiver ON private_messages(receiver);
CREATE INDEX IF NOT EXISTS idx_clubs_city ON clubs(city);
ALTER TABLE club_events ADD COLUMN IF NOT EXISTS event_time TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer TEXT REFERENCES users(username);
CREATE INDEX IF NOT EXISTS idx_email_verifications_token ON email_verifications(token);
"""


def run_postgres_schema(conn):
    """
    Wykonuje pełny schemat PostgreSQL + migracje na przekazanym połączeniu.
    Używane przez initialize_db() oraz przez skrypt scripts/init_production_db.py.
    """
    with conn:
        cur = conn.cursor()
        cur.execute(INIT_SQL)
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'en';")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity TIMESTAMPTZ;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer TEXT REFERENCES users(username);")
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;
        """)
        cur.execute("""
            ALTER TABLE clubs ADD COLUMN IF NOT EXISTS owner_username TEXT REFERENCES users(username) ON DELETE SET NULL;
        """)
        cur.execute("""
            ALTER TABLE clubs ADD COLUMN IF NOT EXISTS deputy_username TEXT REFERENCES users(username) ON DELETE SET NULL;
        """)
        cur.execute("""
            ALTER TABLE clubs ADD COLUMN IF NOT EXISTS privacy_level TEXT NOT NULL DEFAULT 'public';
        """)
        cur.execute("""
            ALTER TABLE clubs ADD COLUMN IF NOT EXISTS is_hidden INTEGER DEFAULT 0;
        """)
        cur.execute("""
            ALTER TABLE members ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'member';
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS club_join_requests (
                id SERIAL PRIMARY KEY,
                club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
                username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(club_id, username)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS club_partnerships (
                id SERIAL PRIMARY KEY,
                club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
                partner_club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','declined')),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(club_id, partner_club_id)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_club_partnerships_partner ON club_partnerships(partner_club_id);")


def initialize_db() -> bool:
    """Wykonuje schemat (PostgreSQL lub SQLite) i migracje. Zwraca True przy sukcesie."""
    conn = db_conn()
    if not conn:
        return False
    try:
        if config.USE_SQLITE:
            cur = conn.cursor()
            # SQLite: tylko jedna instrukcja na wywołanie execute()
            for stmt in (s.strip() for s in INIT_SQL_SQLITE.split(";") if s.strip()):
                cur.execute(stmt)
            # Migracje: nowe kolumny w istniejących tabelach (SQLite 3.35+)
            try:
                cur.execute("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS deputy_username TEXT;")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS is_hidden INTEGER DEFAULT 0;")
            except Exception:
                pass
            conn.commit()
            cur.close()
            return True
        else:
            run_postgres_schema(conn)
            return True
    except Exception as e:
        logger.error("Schema init error: %s", e)
        return False
    finally:
        db_release(conn)
