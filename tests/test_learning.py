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

from app.learning import make_cloze_quiz, grade_quiz
from app.store import init_db, record_mistake, get_confused

def test_cloze_quiz_and_grading():
    items = make_cloze_quiz(["Jakarta adalah ibu kota Indonesia"], ["d0:0"], num=1)
    assert len(items) == 1
    assert items[0].answer in (0, 1, 2)
    assert len(items[0].options) == 3
    res = grade_quiz(items, [items[0].answer])
    assert res["score"] == 1.0 and res["details"][0]["correct"] is True

def test_confused_tracking(tmp_path):
    conn = init_db(tmp_path / "t.db")
    record_mistake(conn, "tema", "d0:0", "ibu kota")
    record_mistake(conn, "tema", "d0:0", "ibu kota")
    rows = get_confused(conn, "tema")
    assert rows[0]["count"] == 2
    conn.close()
