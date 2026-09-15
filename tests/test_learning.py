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

def test_summarize_prompt_is_english():
    seen = {}

    class P:
        def generate(self, prompt, context):
            seen["prompt"] = prompt
            return "ok"

    assert summarize(["chunk satu", "chunk dua"], P()) == "ok"
    assert "Summarize" in seen["prompt"]
    for word in ("Ringkas", "berikut", "konteks", "Jawab"):
        assert word not in seen["prompt"]

def test_summarize_sections_structure():
    from app.learning import summarize_sections

    texts = [
        "Cover page and foreword text here.",
        "Section A.1, ICT Governance, begins with definitions",
        "Governance details part one here.",
        "Governance details part two here.",
        "Section A.2, ICT Management, promotes processes",
        "Management details here.",
    ]
    calls = []

    class P:
        def generate(self, prompt, context):
            calls.append((prompt, list(context)))
            return "takeaways"

    out = summarize_sections(texts, P(), per_section=2)
    assert [s["title"] for s in out] == [
        "Introduction", "Section A.1, ICT Governance, begins with definitions",
        "Section A.2, ICT Management, promotes processes"]
    assert all(s["summary"] == "takeaways" for s in out)
    assert out[0]["chunk_ids"] == [0]
    assert out[1]["chunk_ids"] == [1, 3]
    assert out[2]["chunk_ids"] == [4, 5]
    assert len(calls) == 3
    assert all("takeaway" in p.lower() or "Takeaway" in p for p, _ in calls)

def test_summarize_sections_no_headings():
    from app.learning import summarize_sections

    out = summarize_sections(["only text here"], SafeProvider())
    assert len(out) == 1
    assert out[0]["title"] == "Full document"
    assert out[0]["chunk_ids"] == [0]

def test_summarize_sections_skips_boundary_chunks():
    from app.learning import summarize_sections

    texts = ["prev-tail", "body-1", "body-2", "body-3", "body-4", "next-head"]
    seen = {}

    class P:
        def generate(self, prompt, context):
            seen["context"] = list(context)
            return "ok"

    summarize_sections(texts, P(), per_section=2)
    assert seen["context"] == ["body-1", "body-4"]

def test_split_sections_bare_heading():
    from app.sections import split_sections

    out = split_sections(["intro here", "A.2. ICT Management", "body text"])
    assert [s["title"] for s in out] == ["Introduction", "A.2. ICT Management"]
    assert out[1]["indices"] == [1, 2]

def test_split_sections_merges_duplicate_titles():
    from app.sections import split_sections

    out = split_sections(
        ["toc", "Section A.1, Foo", "x", "Section A.1, Foo", "y"])
    assert [s["title"] for s in out] == ["Introduction", "Section A.1, Foo"]
    assert out[0]["indices"] == [0]
    assert out[1]["indices"] == [1, 2, 3, 4]

def test_split_sections_merges_toc_variants_and_subsections():
    from app.sections import split_sections

    out = split_sections([
        "A.3. ICT Service Delivery 18",
        "toc filler",
        "A.3. ICT Service Delivery",
        "body one",
        "C.1.1. Sub detail",
        "body two",
    ])
    # TOC line (trailing page number) is skipped; body heading wins.
    assert [s["title"] for s in out] == [
        "Introduction", "A.3. ICT Service Delivery", "C.1.1. Sub detail"]
    assert out[0]["indices"] == [0, 1]
    assert out[1]["indices"] == [2, 3]
    assert out[2]["indices"] == [4, 5]

def test_split_sections_prefers_canonical_title():
    from app.sections import split_sections

    out = split_sections([
        "Section A.1, ICT Governance, begins with the definition of things",
        "A.1. ICT Governance",
        "body",
    ])
    assert [s["title"] for s in out] == ["A.1. ICT Governance"]
    assert out[0]["indices"] == [0, 1, 2]

def test_group_key_needs_dotted_number():
    from app.sections import _group_key

    assert _group_key("Section A.1, ICT Governance, begins with x") == "A.1"
    assert _group_key("section 4.2.3, Control of Documents") == "4.2"
    assert _group_key("Part A, ICT Governance and Management") == "part a"
    assert _group_key("C.1.1. Master Data Governance") == "C.1"
