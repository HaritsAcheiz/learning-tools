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
