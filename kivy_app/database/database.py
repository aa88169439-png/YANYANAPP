"""
Vocabulary database (vocabulary.db / vocabulary table).

Stores the user's personal saved words.
"""

import sqlite3
from pathlib import Path
from utils import app_dir


DB_DIR = Path(app_dir())
DB_PATH = DB_DIR / "vocabulary.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                english      TEXT NOT NULL,
                chinese      TEXT NOT NULL DEFAULT '',
                pinyin       TEXT DEFAULT '',
                note         TEXT DEFAULT '',
                example      TEXT DEFAULT '',
                created_time TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                review_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vocab_english ON vocabulary(english)")
        conn.commit()


def save_word(data: dict) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO vocabulary (english, chinese, pinyin, note, example)
               VALUES (?, ?, ?, ?, ?)""",
            (
                data.get("english", ""),
                data.get("chinese", ""),
                data.get("pinyin", ""),
                data.get("note", ""),
                data.get("example", ""),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_all_words() -> list:
    with _conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM vocabulary ORDER BY created_time DESC"
        ).fetchall()]


def search_words(keyword: str) -> list:
    pattern = f"%{keyword}%"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM vocabulary WHERE english LIKE ? OR chinese LIKE ? ORDER BY created_time DESC",
            (pattern, pattern),
        ).fetchall()]


def delete_word(word_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM vocabulary WHERE id = ?", (word_id,))
        conn.commit()
