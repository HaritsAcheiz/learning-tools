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

def test_rag_answer_top_k():
    answer, cited = rag_answer("fotosintesis energi?", CHUNKS, SafeProvider(), top_k=1)
    assert len(cited) <= 1
    answer_all, cited_all = rag_answer("fotosintesis energi?", CHUNKS, SafeProvider(), top_k=5)
    assert len(cited_all) >= len(cited)

def test_rag_refuses_without_context():
    answer, cited = rag_answer("apa kabar?", [], SafeProvider())
    assert cited == []
    assert "tidak menemukan" in answer.lower()

from app.learning import make_cloze_quiz, grade_quiz
from app.store import init_db, record_mistake, get_confused

def test_cloze_quiz_and_grading():
    items = make_cloze_quiz(["Jakarta adalah ibu kota Indonesia"], ["d0:0"], num=1)
    assert len(items) == 1
    assert items[0].options[items[0].answer] == "Indonesia"
    assert items[0].answer != 0
    again = make_cloze_quiz(["Jakarta adalah ibu kota Indonesia"], ["d0:0"], num=1)
    assert again[0].options == items[0].options and again[0].answer == items[0].answer
    res = grade_quiz(items, [items[0].answer])
    assert res["score"] == 1.0 and res["details"][0]["correct"] is True

def test_confused_tracking(tmp_path):
    conn = init_db(tmp_path / "t.db")
    record_mistake(conn, "tema", "d0:0", "ibu kota")
    record_mistake(conn, "tema", "d0:0", "ibu kota")
    rows = get_confused(conn, "tema")
    assert rows[0]["count"] == 2
    conn.close()
from app.learning import srs_update, ensure_cards, due_cards
from app.models import Card

def test_sm2_progresses_and_regresses():
    c = Card("c1", "t", "front", "back", "d:0", 2.5, 0, 0, "2026-09-15")
    good = srs_update(c, 5, "2026-09-15")
    assert (good.reps, good.interval) == (1, 1)
    bad = srs_update(good, 2, "2026-09-16")
    assert bad.reps == 0 and bad.interval == 1

def test_due_list(tmp_path):
    conn = init_db(tmp_path / "s.db")
    n = ensure_cards(conn, "t", [{"id": "d:0", "text": "fotosintesis terjadi di kloroplas daun"}], "2026-09-15")
    assert n == 1
    assert len(due_cards(conn, "t", "2026-09-15")) == 1
    assert len(due_cards(conn, "t", "2026-09-14")) == 0
    conn.close()

def test_summarize_samples_whole_doc():
    chunks = [f"topik awal bagian-{i}" for i in range(5)]
    chunks += [f"topik tengah bagian-{i}" for i in range(5, 15)]
    chunks += [f"topik akhir bagian-{i} penutup" for i in range(15, 20)]
    out = summarize(chunks, SafeProvider())
    assert "topik awal" in out
    assert "topik akhir" in out
