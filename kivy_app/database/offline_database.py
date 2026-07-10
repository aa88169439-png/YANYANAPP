"""
Offline translation memory (offline_translation.db).

Stores previously fetched translations so the same query can be served
without calling the AI API again.
"""

import sqlite3
from pathlib import Path
from utils import app_dir


DB_DIR = Path(app_dir())
DB_PATH = DB_DIR / "offline_translation.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_offline_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translation_memory (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                english             TEXT NOT NULL,
                literal_translation TEXT DEFAULT '',
                natural_chinese     TEXT DEFAULT '',
                internet_expression TEXT DEFAULT '',
                acg_expression      TEXT DEFAULT '',
                pinyin              TEXT DEFAULT '',
                culture_note        TEXT DEFAULT '',
                example_sentence    TEXT DEFAULT '',
                example_translation TEXT DEFAULT '',
                category            TEXT DEFAULT 'daily',
                source              TEXT DEFAULT 'api',
                frequency           INTEGER DEFAULT 1,
                created_time        TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tm_lookup
            ON translation_memory(english, category)
        """)
        conn.commit()


def search_translation(english: str, category: str = "daily") -> dict | None:
    """Return the cached translation for (english, category) or None."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM translation_memory WHERE english = ? AND category = ?",
            (english.strip().lower(), category),
        ).fetchone()
        if row:
            # increment frequency
            conn.execute(
                "UPDATE translation_memory SET frequency = frequency + 1 WHERE id = ?",
                (row["id"],),
            )
            conn.commit()
            return dict(row)
    return None


def save_translation(data: dict) -> int:
    """Insert a new translation record; returns row id."""
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO translation_memory
               (english, literal_translation, natural_chinese, internet_expression,
                acg_expression, pinyin, culture_note, example_sentence,
                example_translation, category, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("english", "").strip().lower(),
                data.get("literal_translation", ""),
                data.get("natural_chinese", ""),
                data.get("internet_expression", ""),
                data.get("acg_expression", ""),
                data.get("pinyin", ""),
                data.get("culture_note", ""),
                data.get("example_sentence", ""),
                data.get("example_translation", ""),
                data.get("category", "daily"),
                data.get("source", "api"),
            ),
        )
        conn.commit()
        return cur.lastrowid
