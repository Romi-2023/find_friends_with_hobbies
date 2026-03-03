#!/usr/bin/env python3
"""
Skrypt jednorazowy: tworzy wszystkie tabele w bazie PostgreSQL (produkcja).
Uruchom z katalogu głównego projektu, z ustawionym DATABASE_URL (i opcjonalnie DB_SCHEMA).

Przykład (lokalnie z .env):
    python scripts/init_production_db.py

W DigitalOcean Console (po ustawieniu DATABASE_URL w env):
    python scripts/init_production_db.py
"""
import os
import re
import sys

# Ścieżka do katalogu głównego projektu (parent of scripts/)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.chdir(ROOT)

def main():
    # Wczytaj .env (python-dotenv lub ręcznie)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        env_path = os.path.join(ROOT, ".env")
        if os.path.isfile(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Błąd: brak zmiennej DATABASE_URL. Ustaw ją w .env lub w środowisku.")
        sys.exit(1)

    schema = (os.environ.get("DB_SCHEMA") or "").strip()
    if schema and not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", schema):
        print("Błąd: nieprawidłowa wartość DB_SCHEMA (dozwolone: litery, cyfry, podkreślenie).")
        sys.exit(1)

    import psycopg2
    conn = psycopg2.connect(url)

    if schema:
        cur = conn.cursor()
        try:
            cur.execute("CREATE SCHEMA IF NOT EXISTS %s" % schema)
            cur.execute("SET search_path TO %s" % schema)
            conn.commit()
            print("Schemat: %s" % schema)
        except Exception as e:
            print("Uwaga: CREATE SCHEMA nie powiodło się (%s). Ustawiam search_path na public." % e)
            try:
                cur.execute("SET search_path TO public")
                conn.commit()
            except Exception:
                pass
        finally:
            cur.close()

    from db import run_postgres_schema
    run_postgres_schema(conn)
    conn.close()

    print("Gotowe. Wszystkie tabele (users, clubs, members, follows, club_events itd.) zostały utworzone.")
    print("Możesz uruchomić aplikację – dane będą zapisywane w bazie (wylogowanie nie usuwa danych).")


if __name__ == "__main__":
    main()
