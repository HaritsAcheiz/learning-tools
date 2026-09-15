from pathlib import Path
from app.ingest import scan_themes, clean_text, chunk_text, ingest_theme
from app.store import init_db, list_chunks

def test_scan_and_chunk(tmp_path):
    lm = tmp_path / "lm"
    (lm / "sub").mkdir(parents=True)
    (lm / "a.md").write_text("# Halo\n\nIni materi belajar.", encoding="utf-8")
    (lm / "sub" / "b.txt").write_text("baris satu", encoding="utf-8")
    themes = scan_themes(lm)
    assert sorted(t.id for t in themes) == ["a.md", "sub"]
    assert clean_text("  halo   dunia \n\n\n ok ") == "halo dunia\n\nok"
    parts = chunk_text("abcdefghij", size=4, overlap=2)
    assert parts == ["abcd", "cdef", "efgh", "ghij", "ij"]
    conn = init_db(tmp_path / "app.db")
    n = ingest_theme(lm, "a.md", conn)
    assert n == 1
    assert len(list_chunks(conn, "a.md")) == 1
    conn.close()
