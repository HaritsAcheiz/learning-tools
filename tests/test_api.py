from pathlib import Path
from fastapi.testclient import TestClient
from app.store import init_db

def test_theme_flow(tmp_path, monkeypatch):
    lm = tmp_path / "lm"
    lm.mkdir()
    (lm / "bio.md").write_text("Mitokondria menghasilkan energi ATP untuk sel.", encoding="utf-8")
    monkeypatch.setenv("LT_MATERIAL", str(lm))
    monkeypatch.setenv("LT_DB", str(tmp_path / "app.db"))
    from app.main import app
    client = TestClient(app)
    assert client.post("/rescan").status_code == 200
    assert "bio.md" in client.get("/").text
    quiz = client.get("/themes/bio.md/quiz").json()
    assert quiz["total"] >= 1
    ask = client.post("/themes/bio.md/ask", json={"question": "Apa fungsi mitokondria?"}).json()
    assert "ATP" in ask["answer"]
