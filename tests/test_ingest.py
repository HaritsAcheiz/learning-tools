from pathlib import Path
import pytest
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

def test_chunk_overlap_validation():
    with pytest.raises(ValueError):
        chunk_text("hello world", size=4, overlap=4)
    with pytest.raises(ValueError):
        chunk_text("hello world", size=4, overlap=8)

def test_ingest_skips_corrupt_file(tmp_path):
    lm = tmp_path / "lm"
    (lm / "theme").mkdir(parents=True)
    (lm / "theme" / "good.md").write_text("Mitokondria menghasilkan energi ATP untuk sel tumbuhan.", encoding="utf-8")
    (lm / "theme" / "bad.pdf").write_bytes(b"%PDF-1.4 garbage \x00\xff not a real pdf")
    conn = init_db(tmp_path / "app.db")
    n = ingest_theme(lm, "theme", conn)
    rows = list_chunks(conn, "theme")
    assert n >= 1
    assert len(rows) == n
    assert any("Mitokondria" in r["text"] for r in rows)
    conn.close()

def test_ingest_custom_chunk_params(tmp_path):
    lm = tmp_path / "lm"
    lm.mkdir(parents=True)
    (lm / "long.md").write_text("kata " * 200, encoding="utf-8")
    conn = init_db(tmp_path / "app.db")
    n_default = ingest_theme(lm, "long.md", conn)
    conn.execute("DELETE FROM chunks WHERE theme_id = 'long.md'")
    conn.commit()
    n_small = ingest_theme(lm, "long.md", conn, chunk_chars=50, overlap_chars=10)
    assert n_default == 1
    assert n_small > n_default
    conn.close()

def test_ingest_unknown_theme(tmp_path):
    lm = tmp_path / "lm"
    lm.mkdir(parents=True)
    conn = init_db(tmp_path / "app.db")
    with pytest.raises(ValueError):
        ingest_theme(lm, "nope", conn)
    conn.close()
