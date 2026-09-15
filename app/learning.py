# app/learning.py (part 1)
from app.retrieval import search, sample_spread

REFUSE_MSG = "Maaf, saya tidak menemukan konteks yang cukup di materi ini."

SUMMARY_CHUNKS = 8


def summarize(chunks: list[str], provider, n: int = SUMMARY_CHUNKS) -> str:
    if not chunks:
        return "Belum ada materi pada tema ini."
    picked = [chunks[i] for i in sample_spread(chunks, n)]
    return provider.generate("Ringkas poin kunci materi berikut:", picked)


def rag_answer(question: str, chunks: list[str], provider, top_k: int = 5) -> tuple[str, list[int]]:
    if not chunks:
        return (REFUSE_MSG, [])
    hits = search(question, chunks, top_k=top_k)
    cited = [i for i, s in hits if s > 0]
    if not cited:
        return (REFUSE_MSG, [])
    ctx = [chunks[i] for i in cited]
    draft = provider.generate(f"Jawab berdasarkan konteks. Pertanyaan: {question}", ctx)
    return (f"{draft}\nSumber: {', '.join(f'[{i}]' for i in cited)}", cited)

import random
import re
from app.models import QuizItem

_STOP = {"adalah", "yang", "dengan", "untuk", "dari", "pada", "sebuah", "ini", "itu", "dan", "atau", "di", "ke"}

def _keyword(sentence: str) -> str | None:
    words = [w for w in re.findall(r"[A-Za-z]{4,}", sentence) if w.lower() not in _STOP]
    return sorted(words, key=len, reverse=True)[0] if words else None

def make_cloze_quiz(chunks: list[str], chunk_ids: list[str], num: int = 5) -> list[QuizItem]:
    items: list[QuizItem] = []
    for text, cid in zip(chunks[:num], chunk_ids[:num]):
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]
        if not sentences:
            continue
        key = _keyword(sentences[0])
        if not key:
            continue
        question = sentences[0].replace(key, "____", 1)
        distractors = [w for w in sorted(set(re.findall(r"[A-Za-z]{4,}", " ".join(chunks))) - {key})[:2]]
        while len(distractors) < 2:
            distractors.append("konsep lain")
        options = [key] + distractors[:2]
        rng = random.Random(question)
        rng.shuffle(options)
        items.append(QuizItem(
            question=question, options=options, answer=options.index(key),
            explanation=f"Jawaban benar '{key}' berasal dari kalimat: {sentences[0][:160]}",
            chunk_id=cid,
        ))
    return items

def grade_quiz(items: list[QuizItem], answers: list[int]) -> dict:
    details = [{"correct": a == it.answer, "chunk_id": it.chunk_id} for it, a in zip(items, answers)]
    score = sum(1 for d in details if d["correct"]) / len(details) if details else 0.0
    return {"score": score, "correct": sum(1 for d in details if d["correct"]), "total": len(details), "details": details}
from datetime import date, timedelta
from app.models import Card

def srs_update(card: Card, quality: int, today: str) -> Card:
    q = max(0, min(5, quality))
    ease = max(1.3, card.ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
    if q < 3:
        reps, interval = 0, 1
    else:
        reps = card.reps + 1
        interval = 1 if reps == 1 else (6 if reps == 2 else round(card.interval * ease))
    due = (date.fromisoformat(today) + timedelta(days=interval)).isoformat()
    return Card(card.id, card.theme_id, card.front, card.back, card.chunk_id, round(ease, 2), interval, reps, due)

def ensure_cards(conn, theme_id: str, chunks: list[dict], today: str) -> int:
    from app.store import upsert_card
    n = 0
    for ch in chunks:
        front = ch["text"][:120].strip()
        if len(front) < 20:
            continue
        upsert_card(conn, f"card:{ch['id']}", theme_id, f"Jelaskan: {front}...", ch["text"][:500], ch["id"], today)
        n += 1
    return n

def due_cards(conn, theme_id: str, today: str) -> list[dict]:
    from app.store import list_due_cards
    return list_due_cards(conn, theme_id, today)
