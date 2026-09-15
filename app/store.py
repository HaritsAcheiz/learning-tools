import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS themes (id TEXT PRIMARY KEY, name TEXT, path TEXT, kind TEXT);
CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, theme_id TEXT, doc_id TEXT, idx INTEGER, text TEXT);
CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, theme_id TEXT, front TEXT, back TEXT, chunk_id TEXT, ease REAL, interval INTEGER, reps INTEGER, due TEXT);
CREATE TABLE IF NOT EXISTS mistakes (theme_id TEXT, chunk_id TEXT, label TEXT, count INTEGER, PRIMARY KEY (theme_id, chunk_id));
"""

def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

def upsert_theme(conn: sqlite3.Connection, theme_id: str, name: str, path: str, kind: str) -> None:
    conn.execute(
        "INSERT INTO themes (id, name, path, kind) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, path=excluded.path, kind=excluded.kind",
        (theme_id, name, path, kind),
    )
    conn.commit()

def list_themes(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT id, name, path, kind FROM themes ORDER BY id")]

def insert_chunks(conn: sqlite3.Connection, theme_id: str, doc_id: str, chunks: list[str]) -> None:
    conn.execute("DELETE FROM chunks WHERE theme_id = ? AND doc_id = ?", (theme_id, doc_id))
    for i, text in enumerate(chunks):
        conn.execute(
            "INSERT INTO chunks (id, theme_id, doc_id, idx, text) VALUES (?, ?, ?, ?, ?)",
            (f"{doc_id}:{i}", theme_id, doc_id, i, text),
        )
    conn.commit()

def list_chunks(conn: sqlite3.Connection, theme_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, theme_id, doc_id, idx, text FROM chunks WHERE theme_id = ? ORDER BY doc_id, idx",
        (theme_id,),
    )]

def record_mistake(conn: sqlite3.Connection, theme_id: str, chunk_id: str, label: str) -> None:
    conn.execute(
        "INSERT INTO mistakes (theme_id, chunk_id, label, count) VALUES (?, ?, ?, 1) "
        "ON CONFLICT(theme_id, chunk_id) DO UPDATE SET count = count + 1",
        (theme_id, chunk_id, label),
    )
    conn.commit()

def get_confused(conn: sqlite3.Connection, theme_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT theme_id, chunk_id, label, count FROM mistakes WHERE theme_id = ? ORDER BY count DESC",
        (theme_id,),
    )]
def upsert_card(conn: sqlite3.Connection, card_id: str, theme_id: str, front: str, back: str, chunk_id: str, today: str) -> None:
    conn.execute(
        "INSERT INTO cards (id, theme_id, front, back, chunk_id, ease, interval, reps, due) "
        "VALUES (?, ?, ?, ?, ?, 2.5, 0, 0, ?) ON CONFLICT(id) DO NOTHING",
        (card_id, theme_id, front, back, chunk_id, today),
    )
    conn.commit()

def list_due_cards(conn: sqlite3.Connection, theme_id: str, today: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM cards WHERE theme_id = ? AND due <= ? ORDER BY due, id",
        (theme_id, today),
    )]
