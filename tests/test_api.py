import json

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
    assert "<h1>" in r.text

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

def test_theme_page_html(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    r = client.get("/themes/bio.md", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "<h1>" in r.text
    for href in ("/themes/bio.md/tanya", "/themes/bio.md/quiz", "/themes/bio.md/review"):
        assert href in r.text
    assert "answer-0" not in r.text

def test_step_pages_html(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    cases = [
        ("/themes/bio.md/tanya", "name='question'", "Tanya"),
        ("/themes/bio.md/quiz", "answer-0", "Kuis"),
        ("/themes/bio.md/review", "Lupa", "Review"),
    ]
    for path, marker, label in cases:
        r = client.get(path, headers={"Accept": "text/html"})
        assert r.status_code == 200, path
        assert r.headers["content-type"].startswith("text/html"), path
        assert marker in r.text, path
        assert "aria-current='page'>" + label in r.text, path

def test_theme_json_default(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    r = client.get("/themes/bio.md")
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["chunks"] == 1

def test_ask_form(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    r = client.post("/themes/bio.md/ask", data={"question": "Apa fungsi mitokondria?"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "ATP" in r.text

def test_quiz_form(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    quiz = client.get("/themes/bio.md/quiz").json()
    assert quiz["total"] >= 1
    form = {}
    for i, it in enumerate(quiz["items"]):
        form[f"item-{i}"] = json.dumps(it)
        form[f"answer-{i}"] = str(it["answer"])
    r = client.post("/themes/bio.md/quiz", data=form)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Skor" in r.text

def test_review_form(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    assert client.post("/rescan").status_code == 200
    due = client.get("/themes/bio.md/review").json()["due"]
    assert due, "expected at least one due card"
    r = client.post("/themes/bio.md/review", data={"card_id": due[0]["id"], "quality": "5"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "dijadwalkan ulang" in r.text

def test_rescan_form_redirect(tmp_path, monkeypatch):
    client = _setup_client(tmp_path, monkeypatch)
    r = client.post("/rescan", content=b"",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"
