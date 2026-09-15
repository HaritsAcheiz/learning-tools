from fastapi.testclient import TestClient

def _setup_client(tmp_path, monkeypatch):
    lm = tmp_path / "lm"
    lm.mkdir()
    (lm / "bio.md").write_text("Mitokondria menghasilkan energi ATP untuk sel.", encoding="utf-8")
    (lm / "sel.md").write_text("Kloroplas menjalankan fotosintesis pada tumbuhan hijau.", encoding="utf-8")
    monkeypatch.setenv("LT_MATERIAL", str(lm))
    monkeypatch.setenv("LT_DB", str(tmp_path / "app.db"))
    from app.main import app
    return TestClient(app)

def test_theme_flow(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    assert "bio.md" in client.get("/").text
    quiz = client.get("/themes/bio.md/quiz").json()
    assert quiz["total"] >= 1
    ask = client.post("/themes/bio.md/ask", json={"question": "Apa fungsi mitokondria?"}).json()
    assert "ATP" in ask["answer"]
    items = quiz["items"]
    answers = [it["answer"] for it in items]
    graded = client.post("/themes/bio.md/quiz", json={"items": items, "answers": answers}).json()
    assert graded["score"] == 1.0
    wrong = [(a + 1) % len(it["options"]) for it, a in zip(items, answers)]
    graded_wrong = client.post("/themes/bio.md/quiz", json={"items": items, "answers": wrong}).json()
    assert graded_wrong["score"] == 0.0
    review = client.get("/themes/bio.md/review").json()
    assert review["confused"], "expected confused concepts after wrong answers"
    assert all(c["label"] != c["chunk_id"] for c in review["confused"])

def test_index_renders_html(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.text.startswith("<h1>")

def test_unknown_theme_404(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    assert client.get("/themes/nope").status_code == 404
    assert client.get("/themes/nope/quiz").status_code == 404

def test_review_validation(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    due = client.get("/themes/bio.md/review").json()["due"]
    assert due, "expected at least one due card"
    card_id = due[0]["id"]
    assert client.post("/themes/bio.md/review", json={"card_id": "nope", "quality": 4}).status_code == 404
    assert client.post("/themes/bio.md/review", json={"card_id": card_id, "quality": "bagus"}).status_code == 422
    assert client.post("/themes/bio.md/review", json={"card_id": card_id, "quality": 99}).status_code == 200
    due2 = client.get("/themes/sel.md/review").json()["due"]
    assert due2, "expected at least one due card"
    assert client.post("/themes/sel.md/review", json={"card_id": due2[0]["id"], "quality": -3}).status_code == 200
