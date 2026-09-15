# app/learning.py (part 1)
from app.retrieval import search

REFUSE_MSG = "Maaf, saya tidak menemukan konteks yang cukup di materi ini."


def summarize(chunks: list[str], provider) -> str:
    if not chunks:
        return "Belum ada materi pada tema ini."
    return provider.generate("Ringkas poin kunci materi berikut:", chunks[:5])


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
        items.append(QuizItem(
            question=question, options=options, answer=0,
            explanation=f"Jawaban benar '{key}' berasal dari kalimat: {sentences[0][:160]}",
            chunk_id=cid,
        ))
    return items

def grade_quiz(items: list[QuizItem], answers: list[int]) -> dict:
    details = [{"correct": a == it.answer, "chunk_id": it.chunk_id} for it, a in zip(items, answers)]
    score = sum(1 for d in details if d["correct"]) / len(details) if details else 0.0
    return {"score": score, "correct": sum(1 for d in details if d["correct"]), "total": len(details), "details": details}
