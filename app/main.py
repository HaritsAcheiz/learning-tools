import html
import os
from datetime import date
from pathlib import Path
from fastapi import FastAPI, HTTPException
from app.config import get_settings
from app import store
from app.ingest import scan_themes, ingest_theme
from app.learning import summarize, rag_answer, make_cloze_quiz, grade_quiz, ensure_cards, due_cards, srs_update
from app.llm import get_provider
from app.models import Card, QuizItem

app = FastAPI(title="learning-tools")

def _ctx():
    mat = os.environ.get("LT_MATERIAL")
    db = os.environ.get("LT_DB")
    defaults = get_settings()
    s = get_settings(
        material_dir=Path(mat) if mat else defaults.material_dir,
        db_path=Path(db) if db else defaults.db_path,
    )
    return s, store.init_db(s.db_path)

def _require_theme(conn, s, theme_id: str) -> None:
    known = {t.id for t in scan_themes(s.material_dir)}
    known |= {t["id"] for t in store.list_themes(conn)}
    if theme_id not in known:
        raise HTTPException(status_code=404, detail=f"Unknown theme: {theme_id}")

@app.get("/")
def index():
    s, conn = _ctx()
    try:
        themes = store.list_themes(conn)
        items = "".join(
            f"<li><a href='/themes/{html.escape(t['id'])}'>{html.escape(t['name'])}</a></li>"
            for t in themes
        )
        return f"<h1>learning-tools</h1><form method='post' action='/rescan'><button>Rescan</button></form><ul>{items}</ul>"
    finally:
        conn.close()

@app.post("/rescan")
def rescan():
    s, conn = _ctx()
    try:
        themes = scan_themes(s.material_dir)
        for t in themes:
            try:
                ingest_theme(s.material_dir, t.id, conn, s.chunk_chars, s.overlap_chars)
            except Exception:
                continue
        return {"themes": [t.id for t in themes]}
    finally:
        conn.close()

@app.get("/themes/{theme_id}")
def read_theme(theme_id: str):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        chunks = store.list_chunks(conn, theme_id)
        texts = [c["text"] for c in chunks]
        return {"theme": theme_id, "chunks": len(texts), "summary": summarize(texts, get_provider())}
    finally:
        conn.close()

@app.post("/themes/{theme_id}/ask")
def ask(theme_id: str, payload: dict):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        texts = [c["text"] for c in store.list_chunks(conn, theme_id)]
        answer, cited = rag_answer(payload.get("question", ""), texts, get_provider(), top_k=s.top_k)
        return {"answer": answer, "cited": cited}
    finally:
        conn.close()

@app.get("/themes/{theme_id}/quiz")
def get_quiz(theme_id: str, num: int = 5):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        chunks = store.list_chunks(conn, theme_id)
        items = make_cloze_quiz([c["text"] for c in chunks], [c["id"] for c in chunks], num)
        return {"total": len(items), "items": [i.__dict__ for i in items]}
    finally:
        conn.close()

@app.post("/themes/{theme_id}/quiz")
def submit_quiz(theme_id: str, payload: dict):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        if payload.get("items"):
            items = [QuizItem(**d) for d in payload["items"]]
        else:
            chunks = store.list_chunks(conn, theme_id)
            items = make_cloze_quiz([c["text"] for c in chunks], [c["id"] for c in chunks], len(payload.get("answers", [])))
        result = grade_quiz(items, payload.get("answers", []))
        for it, d in zip(items, result["details"]):
            if not d["correct"]:
                store.record_mistake(conn, theme_id, d["chunk_id"], it.question[:120])
        return result
    finally:
        conn.close()

@app.get("/themes/{theme_id}/review")
def get_review(theme_id: str):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        today = date.today().isoformat()
        chunks = store.list_chunks(conn, theme_id)
        ensure_cards(conn, theme_id, chunks, today)
        return {"due": due_cards(conn, theme_id, today), "confused": store.get_confused(conn, theme_id)}
    finally:
        conn.close()

@app.post("/themes/{theme_id}/review")
def submit_review(theme_id: str, payload: dict):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        try:
            quality = int(payload.get("quality", 4))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="quality must be an integer")
        quality = max(0, min(5, quality))
        today = date.today().isoformat()
        for row in due_cards(conn, theme_id, today):
            if row["id"] == payload.get("card_id"):
                card = Card(**{k: row[k] for k in ("id", "theme_id", "front", "back", "chunk_id", "ease", "interval", "reps", "due")})
                updated = srs_update(card, quality, today)
                conn.execute(
                    "UPDATE cards SET ease=?, interval=?, reps=?, due=? WHERE id=?",
                    (updated.ease, updated.interval, updated.reps, updated.due, updated.id),
                )
                conn.commit()
                return {"card": updated.__dict__}
        raise HTTPException(status_code=404, detail="card not due")
    finally:
        conn.close()
