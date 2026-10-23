import sqlite3
from contextlib import contextmanager
from app.config import DB_PATH


def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def db_cursor():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_site_settings() -> dict:
    with db_cursor() as cur:
        cur.execute("SELECT key, value FROM site_settings")
        return {row["key"]: row["value"] for row in cur.fetchall()}


def update_site_setting(key: str, value: str):
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO site_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
