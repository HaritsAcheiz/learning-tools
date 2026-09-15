import os
from datetime import date
from pathlib import Path
from fastapi import FastAPI
from app.config import get_settings
from app import store
from app.ingest import scan_themes, ingest_theme
from app.learning import summarize, rag_answer, make_cloze_quiz, grade_quiz, ensure_cards, due_cards, srs_update
from app.llm import get_provider
from app.models import Card

app = FastAPI(title="learning-tools")

def _ctx():
    s = get_settings(
        material_dir=Path(os.environ.get("LT_MATERIAL", "learning_material")),
        db_path=Path(os.environ.get("LT_DB", "data/app.db")),
    )
    return s, store.init_db(s.db_path)

@app.get("/")
def index():
    s, conn = _ctx()
    themes = store.list_themes(conn)
    items = "".join(f"<li><a href='/themes/{t['id']}'>{t['name']}</a></li>" for t in themes)
    return f"<h1>learning-tools</h1><form method='post' action='/rescan'><button>Rescan</button></form><ul>{items}</ul>"

@app.post("/rescan")
def rescan():
    s, conn = _ctx()
    themes = scan_themes(s.material_dir)
    for t in themes:
        ingest_theme(s.material_dir, t.id, conn)
    return {"themes": [t.id for t in themes]}

@app.get("/themes/{theme_id}")
def read_theme(theme_id: str):
    _, conn = _ctx()
    chunks = store.list_chunks(conn, theme_id)
    texts = [c["text"] for c in chunks]
    return {"theme": theme_id, "chunks": len(texts), "summary": summarize(texts, get_provider())}

@app.post("/themes/{theme_id}/ask")
def ask(theme_id: str, payload: dict):
    _, conn = _ctx()
    texts = [c["text"] for c in store.list_chunks(conn, theme_id)]
    answer, cited = rag_answer(payload.get("question", ""), texts, get_provider())
    return {"answer": answer, "cited": cited}

@app.get("/themes/{theme_id}/quiz")
def get_quiz(theme_id: str, num: int = 5):
    _, conn = _ctx()
    chunks = store.list_chunks(conn, theme_id)
    items = make_cloze_quiz([c["text"] for c in chunks], [c["id"] for c in chunks], num)
    return {"total": len(items), "items": [i.__dict__ for i in items]}

@app.post("/themes/{theme_id}/quiz")
def submit_quiz(theme_id: str, payload: dict):
    _, conn = _ctx()
    chunks = store.list_chunks(conn, theme_id)
    items = make_cloze_quiz([c["text"] for c in chunks], [c["id"] for c in chunks], len(payload.get("answers", [])))
    result = grade_quiz(items, payload.get("answers", []))
    for d in result["details"]:
        if not d["correct"]:
            store.record_mistake(conn, theme_id, d["chunk_id"], d["chunk_id"])
    return result

@app.get("/themes/{theme_id}/review")
def get_review(theme_id: str):
    _, conn = _ctx()
    today = date.today().isoformat()
    chunks = store.list_chunks(conn, theme_id)
    ensure_cards(conn, theme_id, chunks, today)
    return {"due": due_cards(conn, theme_id, today), "confused": store.get_confused(conn, theme_id)}

@app.post("/themes/{theme_id}/review")
def submit_review(theme_id: str, payload: dict):
    _, conn = _ctx()
    today = date.today().isoformat()
    for row in due_cards(conn, theme_id, today):
        if row["id"] == payload.get("card_id"):
            card = Card(**{k: row[k] for k in ("id", "theme_id", "front", "back", "chunk_id", "ease", "interval", "reps", "due")})
            updated = srs_update(card, int(payload.get("quality", 4)), today)
            conn.execute(
                "UPDATE cards SET ease=?, interval=?, reps=?, due=? WHERE id=?",
                (updated.ease, updated.interval, updated.reps, updated.due, updated.id),
            )
            conn.commit()
            return {"card": updated.__dict__}
    return {"error": "card not due"}
