# tests/test_learning.py (part 1 — quiz/SRS asserts appended in later tasks)
from app.llm import SafeProvider
from app.learning import summarize, rag_answer

CHUNKS = ["fotosintesis terjadi di kloroplas", "mitokondria menghasilkan energi ATP"]

def test_summarize_lists_points():
    out = summarize(CHUNKS, SafeProvider())
    assert "1." in out and "kloroplas" in out

def test_rag_answer_cites_chunk():
    answer, cited = rag_answer("Di mana fotosintesis terjadi?", CHUNKS, SafeProvider())
    assert cited == [0]
    assert "kloroplas" in answer
    assert "[0]" in answer

def test_rag_refuses_without_context():
    answer, cited = rag_answer("apa kabar?", [], SafeProvider())
    assert cited == []
    assert "tidak menemukan" in answer.lower()
