from pathlib import Path
from app.config import get_settings
from app.store import init_db, upsert_theme, list_themes, insert_chunks, list_chunks

def test_settings_defaults(tmp_path):
    s = get_settings(material_dir=tmp_path / "lm", db_path=tmp_path / "app.db")
    assert s.chunk_chars == 2000
    assert s.overlap_chars == 200
    assert s.top_k == 5

def test_store_roundtrip(tmp_path):
    db = tmp_path / "app.db"
    conn = init_db(db)
    upsert_theme(conn, "intro", "Intro", "intro.pdf", "file")
    assert [t["id"] for t in list_themes(conn)] == ["intro"]
    insert_chunks(conn, "intro", "doc1", ["hello world", "second chunk"])
    rows = list_chunks(conn, "intro")
    assert [r["text"] for r in rows] == ["hello world", "second chunk"]
    conn.close()
