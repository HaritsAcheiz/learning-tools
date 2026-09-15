import json
import os
from datetime import date
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app import pages
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

def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")

def _is_form(request: Request) -> bool:
    return request.headers.get("content-type", "").startswith(
        "application/x-www-form-urlencoded")

def _theme_context(conn, s, theme_id: str, num: int = 5) -> dict:
    chunks = store.list_chunks(conn, theme_id)
    texts = [c["text"] for c in chunks]
    today = date.today().isoformat()
    ensure_cards(conn, theme_id, chunks, today)
    names = {t["id"]: t["name"] for t in store.list_themes(conn)}
    return {
        "theme_id": theme_id,
        "name": names.get(theme_id, theme_id),
        "chunks": len(texts),
        "summary": summarize(texts, get_provider()),
        "quiz_items": [i.__dict__ for i in make_cloze_quiz(
            texts, [c["id"] for c in chunks], num)],
        "due": due_cards(conn, theme_id, today),
        "confused": store.get_confused(conn, theme_id),
    }

@app.get("/")
def index():
    s, conn = _ctx()
    try:
        themes = store.list_themes(conn)
        return HTMLResponse(pages.home(themes))
    finally:
        conn.close()

@app.post("/rescan")
async def rescan(request: Request):
    s, conn = _ctx()
    try:
        themes = scan_themes(s.material_dir)
        for t in themes:
            try:
                ingest_theme(s.material_dir, t.id, conn, s.chunk_chars, s.overlap_chars)
            except Exception:
                continue
        if _is_form(request):
            return RedirectResponse(url="/", status_code=303)
        return {"themes": [t.id for t in themes]}
    finally:
        conn.close()

@app.get("/themes/{theme_id}")
async def read_theme(theme_id: str, request: Request):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        if _wants_html(request):
            return HTMLResponse(pages.theme_page(_theme_context(conn, s, theme_id)))
        chunks = store.list_chunks(conn, theme_id)
        texts = [c["text"] for c in chunks]
        return {"theme": theme_id, "chunks": len(texts), "summary": summarize(texts, get_provider())}
    finally:
        conn.close()

@app.post("/themes/{theme_id}/ask")
async def ask(theme_id: str, request: Request):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        texts = [c["text"] for c in store.list_chunks(conn, theme_id)]
        if _is_form(request):
            form = await request.form()
            question = str(form.get("question", ""))
            answer, cited = rag_answer(question, texts, get_provider(), top_k=s.top_k)
            ctx = _theme_context(conn, s, theme_id)
            return HTMLResponse(pages.theme_page(
                ctx, active="tanya", answer={"answer": answer, "cited": cited}))
        payload = await request.json()
        answer, cited = rag_answer(payload.get("question", ""), texts, get_provider(), top_k=s.top_k)
        return {"answer": answer, "cited": cited}
    finally:
        conn.close()

@app.get("/themes/{theme_id}/tanya")
async def tanya_page(theme_id: str, request: Request):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        return HTMLResponse(pages.theme_page(
            _theme_context(conn, s, theme_id), active="tanya"))
    finally:
        conn.close()

@app.get("/themes/{theme_id}/quiz")
async def get_quiz(theme_id: str, request: Request, num: int = 5):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        if _wants_html(request):
            return HTMLResponse(pages.theme_page(
                _theme_context(conn, s, theme_id, num), active="kuis"))
        chunks = store.list_chunks(conn, theme_id)
        items = make_cloze_quiz([c["text"] for c in chunks], [c["id"] for c in chunks], num)
        return {"total": len(items), "items": [i.__dict__ for i in items]}
    finally:
        conn.close()

@app.post("/themes/{theme_id}/quiz")
async def submit_quiz(theme_id: str, request: Request):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        if _is_form(request):
            form = await request.form()
            items = []
            answers = []
            i = 0
            while f"item-{i}" in form:
                items.append(QuizItem(**json.loads(str(form[f"item-{i}"]))))
                try:
                    answers.append(int(str(form.get(f"answer-{i}", "-1"))))
                except ValueError:
                    answers.append(-1)
                i += 1
            if not items:
                raise HTTPException(status_code=422, detail="no quiz items submitted")
            result = grade_quiz(items, answers)
            for it, d in zip(items, result["details"]):
                if not d["correct"]:
                    store.record_mistake(conn, theme_id, d["chunk_id"], it.question[:120])
            ctx = _theme_context(conn, s, theme_id)
            return HTMLResponse(pages.theme_page(ctx, active="kuis", quiz_result=result, quiz_items=items))
        payload = await request.json()
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
async def get_review(theme_id: str, request: Request):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        if _wants_html(request):
            return HTMLResponse(pages.theme_page(
                _theme_context(conn, s, theme_id), active="review"))
        today = date.today().isoformat()
        chunks = store.list_chunks(conn, theme_id)
        ensure_cards(conn, theme_id, chunks, today)
        return {"due": due_cards(conn, theme_id, today), "confused": store.get_confused(conn, theme_id)}
    finally:
        conn.close()

@app.post("/themes/{theme_id}/review")
async def submit_review(theme_id: str, request: Request):
    s, conn = _ctx()
    try:
        _require_theme(conn, s, theme_id)
        if _is_form(request):
            form = await request.form()
            card_id = str(form.get("card_id", ""))
            raw_quality = form.get("quality", 4)
        else:
            payload = await request.json()
            card_id = payload.get("card_id")
            raw_quality = payload.get("quality", 4)
        try:
            quality = int(str(raw_quality))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="quality must be an integer")
        quality = max(0, min(5, quality))
        today = date.today().isoformat()
        for row in due_cards(conn, theme_id, today):
            if row["id"] == card_id:
                card = Card(**{k: row[k] for k in ("id", "theme_id", "front", "back", "chunk_id", "ease", "interval", "reps", "due")})
                updated = srs_update(card, quality, today)
                conn.execute(
                    "UPDATE cards SET ease=?, interval=?, reps=?, due=? WHERE id=?",
                    (updated.ease, updated.interval, updated.reps, updated.due, updated.id),
                )
                conn.commit()
                if _is_form(request):
                    ctx = _theme_context(conn, s, theme_id)
                    return HTMLResponse(pages.theme_page(
                        ctx, active="review", notice=f"Kartu dijadwalkan ulang: {updated.due}."))
                return {"card": updated.__dict__}
        raise HTTPException(status_code=404, detail="card not due")
    finally:
        conn.close()
