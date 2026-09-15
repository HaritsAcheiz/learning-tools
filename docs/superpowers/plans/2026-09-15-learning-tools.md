# learning-tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the local FastAPI + RAG learning web app from the approved spec, phase by phase, with tests passing at every task.

**Architecture:** Monolithic Python app: FastAPI serves a local web UI; `ingest` turns each `learning_material/` file/subdir into a theme with cleaned chunks; `retrieval` does offline TF-IDF-hash embeddings plus cosine search with an optional FAISS wrapper; `learning` adds SAFE-mode summarization, grounded RAG answers, cloze quizzes, SM-2 SRS, and confused-concept tracking; SQLite persists everything.

**Tech Stack:** Python >= 3.10, FastAPI, uvicorn, pypdf, python-docx, numpy, sqlite3 (stdlib), pytest, httpx; `faiss-cpu` optional only.

**Spec:** `docs/superpowers/specs/2026-09-15-learning-tools-design.md`

## Global Constraints

- `learning_material/` is user content: never delete it; each file/subdir is one selectable theme.
- New code must stay GPLv3-compatible (no proprietary-only dependencies).
- Offline-first: every feature works in SAFE mode with no network, no API key, no Ollama running.
- Windows dev host (win32, PowerShell 5.1): use `workdir`-based commands, never `cd` inside commands.
- Chunking: `CHUNK_CHARS=2000`, `OVERLAP_CHARS=200`; retrieval default `TOP_K=5`.
- Test command: `pytest -q`; FAISS tests skip when `faiss-cpu` is absent; LLM-touching tests use mocks/fakes only.

---

## File Map

- Create: `pyproject.toml` — project metadata, dependencies, pytest config.
- Create: `app/__init__.py` — empty package marker.
- Create: `app/config.py` — `Settings` dataclass + `get_settings()`; owns `MATERIAL_DIR`, `DB_PATH`, chunk constants.
- Create: `app/models.py` — `Theme`, `Document`, `QuizItem`, `Card` dataclasses.
- Create: `app/store.py` — SQLite schema + CRUD used by all later tasks.
- Create: `app/ingest.py` — `scan_themes`, `extract_text`, `clean_text`, `chunk_text`, `ingest_theme`.
- Create: `app/retrieval.py` — `embed`, `search`, `FaissIndex` (optional wrapper with numpy fallback).
- Create: `app/llm.py` — `LLMProvider` protocol, `SafeProvider`, `OllamaProvider`, `get_provider`.
- Create: `app/learning.py` — `summarize`, `rag_answer`, `make_cloze_quiz`, `grade_quiz`, `record_mistake`, `get_confused`, `srs_update`, `due_cards`, card CRUD helpers.
- Create: `app/main.py` — FastAPI app with theme/read/ask/quiz/review endpoints + minimal HTML.
- Create: `tests/test_store_config.py`, `tests/test_ingest.py`, `tests/test_retrieval.py`, `tests/test_learning.py`, `tests/test_api.py`.
- Modify: `AGENTS.md` — append the verified `pytest` / `uvicorn` commands introduced here.
- Create: `data/.gitkeep` — keeps the SQLite directory present without committing the db file.

---

### Task 1: Scaffold + config + SQLite store

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/models.py`
- Create: `app/store.py`
- Create: `data/.gitkeep`
- Test: `tests/test_store_config.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `app/config.py`: `Settings(material_dir: Path, db_path: Path, chunk_chars: int, overlap_chars: int, top_k: int)`, `get_settings() -> Settings`
  - `app/models.py`: `Theme(id: str, name: str, path: str, kind: str)`, `Document(id: str, theme_id: str, path: str, text: str)`, `QuizItem(question: str, options: list[str], answer: int, explanation: str, chunk_id: str)`, `Card(id: str, theme_id: str, front: str, back: str, chunk_id: str, ease: float, interval: int, reps: int, due: str)`
  - `app/store.py`: `init_db(path: Path) -> sqlite3.Connection`, `list_themes(conn) -> list[dict]`, `upsert_theme(conn, theme_id: str, name: str, path: str, kind: str) -> None`, `insert_chunks(conn, theme_id: str, doc_id: str, chunks: list[str]) -> None`, `list_chunks(conn, theme_id: str) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store_config.py
from pathlib import Path
from app.config import get_settings
from app.store import init_db, upsert_theme, list_themes, insert_chunks, list_chunks

def test_settings_defaults(tmp_path):
    s = get_settings(material_dir=tmp_path / "lm", db_path=tmp_path / "app.db")
    assert s.chunk_chars == 2000
    assert s.overlap_chars == 200
    assert s.top_k == 5

def test_store_roundtrip(tmp_path):
    db = tmp_path / "app.db"
    conn = init_db(db)
    upsert_theme(conn, "intro", "Intro", "intro.pdf", "file")
    assert [t["id"] for t in list_themes(conn)] == ["intro"]
    insert_chunks(conn, "intro", "doc1", ["hello world", "second chunk"])
    rows = list_chunks(conn, "intro")
    assert [r["text"] for r in rows] == ["hello world", "second chunk"]
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_config.py -v`
Expected: FAIL with "No module named 'app'" (scaffold does not exist yet).

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[project]
name = "learning-tools"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["fastapi", "uvicorn", "pypdf", "python-docx", "numpy"]

[project.optional-dependencies]
test = ["pytest", "httpx"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```python
# app/__init__.py
```

```python
# app/config.py
from dataclasses import dataclass
from pathlib import Path

CHUNK_CHARS = 2000
OVERLAP_CHARS = 200
TOP_K = 5

@dataclass
class Settings:
    material_dir: Path
    db_path: Path
    chunk_chars: int = CHUNK_CHARS
    overlap_chars: int = OVERLAP_CHARS
    top_k: int = TOP_K

def get_settings(material_dir: Path | None = None, db_path: Path | None = None) -> Settings:
    root = Path(__file__).resolve().parent.parent
    return Settings(
        material_dir=material_dir or (root / "learning_material"),
        db_path=db_path or (root / "data" / "app.db"),
    )
```

```python
# app/models.py
from dataclasses import dataclass

@dataclass
class Theme:
    id: str
    name: str
    path: str
    kind: str

@dataclass
class Document:
    id: str
    theme_id: str
    path: str
    text: str

@dataclass
class QuizItem:
    question: str
    options: list[str]
    answer: int
    explanation: str
    chunk_id: str

@dataclass
class Card:
    id: str
    theme_id: str
    front: str
    back: str
    chunk_id: str
    ease: float
    interval: int
    reps: int
    due: str
```

```python
# app/store.py
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS themes (id TEXT PRIMARY KEY, name TEXT, path TEXT, kind TEXT);
CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, theme_id TEXT, doc_id TEXT, idx INTEGER, text TEXT);
CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, theme_id TEXT, front TEXT, back TEXT, chunk_id TEXT, ease REAL, interval INTEGER, reps INTEGER, due TEXT);
CREATE TABLE IF NOT EXISTS mistakes (theme_id TEXT, chunk_id TEXT, label TEXT, count INTEGER, PRIMARY KEY (theme_id, chunk_id));
"""

def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

def upsert_theme(conn: sqlite3.Connection, theme_id: str, name: str, path: str, kind: str) -> None:
    conn.execute(
        "INSERT INTO themes (id, name, path, kind) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, path=excluded.path, kind=excluded.kind",
        (theme_id, name, path, kind),
    )
    conn.commit()

def list_themes(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT id, name, path, kind FROM themes ORDER BY id")]

def insert_chunks(conn: sqlite3.Connection, theme_id: str, doc_id: str, chunks: list[str]) -> None:
    conn.execute("DELETE FROM chunks WHERE theme_id = ? AND doc_id = ?", (theme_id, doc_id))
    for i, text in enumerate(chunks):
        conn.execute(
            "INSERT INTO chunks (id, theme_id, doc_id, idx, text) VALUES (?, ?, ?, ?, ?)",
            (f"{doc_id}:{i}", theme_id, doc_id, i, text),
        )
    conn.commit()

def list_chunks(conn: sqlite3.Connection, theme_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, theme_id, doc_id, idx, text FROM chunks WHERE theme_id = ? ORDER BY doc_id, idx",
        (theme_id,),
    )]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_config.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml app tests/test_store_config.py data/.gitkeep
git commit -m "feat: scaffold config, models, and sqlite store"
```

---

### Task 2: Ingest — scan themes, extract PDF/DOCX/TXT/MD, clean, chunk

**Files:**
- Create: `app/ingest.py`
- Test: `tests/test_ingest.py`

**Interfaces:**
- Consumes: `app/config.Settings`, `app/store.upsert_theme`, `app/store.insert_chunks`.
- Produces:
  - `app/ingest.py`: `scan_themes(material_dir: Path) -> list[Theme]`, `extract_text(path: Path) -> str`, `clean_text(text: str) -> str`, `chunk_text(text: str, size: int = 2000, overlap: int = 200) -> list[str]`, `ingest_theme(material_dir: Path, theme_id: str, conn) -> int`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingest.py
from pathlib import Path
from app.ingest import scan_themes, clean_text, chunk_text, ingest_theme
from app.store import init_db, list_chunks

def test_scan_and_chunk(tmp_path):
    lm = tmp_path / "lm"
    (lm / "sub").mkdir(parents=True)
    (lm / "a.md").write_text("# Halo\n\nIni materi belajar.", encoding="utf-8")
    (lm / "sub" / "b.txt").write_text("baris satu", encoding="utf-8")
    themes = scan_themes(lm)
    assert sorted(t.id for t in themes) == ["a.md", "sub"]
    assert clean_text("  halo   dunia \n\n\n ok ") == "halo dunia\n\nok"
    parts = chunk_text("abcdefghij", size=4, overlap=2)
    assert parts == ["abcd", "cdef", "efgh", "ghij"]
    conn = init_db(tmp_path / "app.db")
    n = ingest_theme(lm, "a.md", conn)
    assert n == 1
    assert len(list_chunks(conn, "a.md")) == 1
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest.py -v`
Expected: FAIL with "No module named 'app.ingest'".

- [ ] **Step 3: Write minimal implementation**

```python
# app/ingest.py
import hashlib
import re
from pathlib import Path
from docx import Document as DocxDocument
from pypdf import PdfReader
from app.models import Theme

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}

def scan_themes(material_dir: Path) -> list[Theme]:
    material_dir.mkdir(parents=True, exist_ok=True)
    themes: list[Theme] = []
    for child in sorted(material_dir.iterdir()):
        if child.is_dir():
            themes.append(Theme(id=child.name, name=child.name, path=str(child), kind="dir"))
        elif child.suffix.lower() in SUPPORTED:
            themes.append(Theme(id=child.name, name=child.stem, path=str(child), kind="file"))
    return themes

def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if suffix == ".docx":
        doc = DocxDocument(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    raise ValueError(f"Unsupported format: {suffix}")

def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def chunk_text(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    if len(text) <= size:
        return [text]
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text), step) if text[i:i + size].strip()]

def ingest_theme(material_dir: Path, theme_id: str, conn) -> int:
    from app.store import upsert_theme, insert_chunks
    theme = next(t for t in scan_themes(material_dir) if t.id == theme_id)
    total = 0
    if theme.kind == "file":
        path = Path(theme.path)
        doc_id = hashlib.sha1(str(path).encode()).hexdigest()[:12]
        chunks = chunk_text(extract_text(path))
        upsert_theme(conn, theme.id, theme.name, theme.path, theme.kind)
        insert_chunks(conn, theme.id, doc_id, chunks)
        total += len(chunks)
    else:
        upsert_theme(conn, theme.id, theme.name, theme.path, theme.kind)
        for path in sorted(Path(theme.path).rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED:
                doc_id = hashlib.sha1(str(path).encode()).hexdigest()[:12]
                chunks = chunk_text(extract_text(path))
                insert_chunks(conn, theme.id, doc_id, chunks)
                total += len(chunks)
    return total
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingest.py tests/test_store_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/ingest.py tests/test_ingest.py
git commit -m "feat: ingest themes from pdf/docx/txt/md with chunking"
```

---

### Task 3: Retrieval — offline embeddings, cosine search, optional FAISS

**Files:**
- Create: `app/retrieval.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: chunk text lists from `app/store.list_chunks`.
- Produces:
  - `app/retrieval.py`: `embed(texts: list[str]) -> numpy.ndarray` (shape `(n, 512)`, L2-normalized), `search(query: str, chunks: list[str], top_k: int = 5) -> list[tuple[int, float]]`, `FaissIndex(dim: int)` with `add(vectors)`, `search(vector, top_k)`, class attribute `available: bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_retrieval.py
import pytest
from app.retrieval import embed, search, FaissIndex

CHUNKS = ["kucing makan ikan", "belajar efektif dengan repetisi", "ikan hidup di air"]

def test_embed_normalized():
    v = embed(CHUNKS)
    assert v.shape == (3, 512)
    assert abs(float((v[0] ** 2).sum()) - 1.0) < 1e-5

def test_search_ranks_relevant_chunk_first():
    hits = search("repetisi belajar", CHUNKS, top_k=2)
    assert hits[0][0] == 1
    assert hits[0][1] > hits[1][1]

def test_faiss_optional():
    if not FaissIndex.available:
        pytest.skip("faiss-cpu not installed")
    idx = FaissIndex(dim=512)
    idx.add(embed(CHUNKS))
    assert idx.search(embed(["repetisi"])[0], 1)[0][0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieval.py -v`
Expected: FAIL with "No module named 'app.retrieval'".

- [ ] **Step 3: Write minimal implementation**

```python
# app/retrieval.py
import hashlib
import re
import numpy as np

DIM = 512

def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

def embed(texts: list[str]) -> np.ndarray:
    vecs = np.zeros((len(texts), DIM), dtype=np.float64)
    for i, text in enumerate(texts):
        for tok in _tokens(text):
            h = int(hashlib.sha256(tok.encode()).hexdigest(), 16) % DIM
            vecs[i, h] += 1.0
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms

def search(query: str, chunks: list[str], top_k: int = 5) -> list[tuple[int, float]]:
    if not chunks:
        return []
    q = embed([query])[0]
    m = embed(chunks)
    scores = m @ q
    order = np.argsort(-scores)[:top_k]
    return [(int(i), float(scores[i])) for i in order]

class FaissIndex:
    try:
        import faiss  # type: ignore
        available = True
    except Exception:
        available = False

    def __init__(self, dim: int = DIM):
        if not self.available:
            raise RuntimeError("faiss-cpu is not installed")
        self.index = self.faiss.IndexFlatIP(dim)

    def add(self, vectors: np.ndarray) -> None:
        self.index.add(np.ascontiguousarray(vectors.astype(np.float32)))

    def search(self, vector: np.ndarray, top_k: int = 5) -> list[tuple[int, float]]:
        scores, ids = self.index.search(np.ascontiguousarray(vector.astype(np.float32)).reshape(1, -1), top_k)
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_retrieval.py -v`
Expected: PASS (or 2 passed + 1 skipped without faiss-cpu).

- [ ] **Step 5: Commit**

```bash
git add app/retrieval.py tests/test_retrieval.py
git commit -m "feat: offline embeddings with cosine search and optional faiss"
```

---

### Task 4: LLM abstraction + summarize + grounded RAG answers (SAFE default)

**Files:**
- Create: `app/llm.py`
- Create: `app/learning.py` (part 1: `summarize`, `rag_answer` only; quiz/SRS come in Tasks 5–6)
- Test: `tests/test_learning.py` (part 1 asserts for summarize/rag_answer)

**Interfaces:**
- Consumes: `app/retrieval.search`.
- Produces:
  - `app/llm.py`: `LLMProvider` (protocol with `generate(prompt: str, context: list[str]) -> str`), `SafeProvider`, `OllamaProvider(model: str)`, `get_provider() -> LLMProvider` (returns `SafeProvider` when env `LT_SAFE=1` or Ollama unreachable)
  - `app/learning.py`: `summarize(chunks: list[str], provider) -> str`, `rag_answer(question: str, chunks: list[str], provider, top_k: int = 5) -> tuple[str, list[int]]`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_learning.py -v`
Expected: FAIL with "No module named 'app.learning'".

- [ ] **Step 3: Write minimal implementation**

```python
# app/llm.py
import os
from typing import Protocol

class LLMProvider(Protocol):
    def generate(self, prompt: str, context: list[str]) -> str: ...

class SafeProvider:
    def generate(self, prompt: str, context: list[str]) -> str:
        lines = [f"{i + 1}. {c[:200]}" for i, c in enumerate(context)]
        return f"{prompt}\n" + "\n".join(lines)

class OllamaProvider:
    def __init__(self, model: str = "llama3.1"):
        self.model = model

    def generate(self, prompt: str, context: list[str]) -> str:
        import urllib.request, json
        body = json.dumps({"model": self.model, "prompt": prompt, "context": context, "stream": False}).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", data=body)
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read().decode()).get("response", "")

def get_provider() -> LLMProvider:
    if os.environ.get("LT_SAFE", "1") == "1":
        return SafeProvider()
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434", timeout=1).close()
        return OllamaProvider()
    except Exception:
        return SafeProvider()
```

```python
# app/learning.py (part 1)
from app.retrieval import search

def summarize(chunks: list[str], provider) -> str:
    if not chunks:
        return "Belum ada materi pada tema ini."
    return provider.generate("Ringkas poin kunci materi berikut:", chunks[:5])

def rag_answer(question: str, chunks: list[str], provider, top_k: int = 5) -> tuple[str, list[int]]:
    if not chunks:
        return ("Maaf, saya tidak menemukan konteks yang cukup di materi ini.", [])
    hits = search(question, chunks, top_k=top_k)
    cited = [i for i, _ in hits]
    ctx = [chunks[i] for i in cited]
    draft = provider.generate(f"Jawab berdasarkan konteks. Pertanyaan: {question}", ctx)
    return (f"{draft}\nSumber: {', '.join(f'[{i}]' for i in cited)}", cited)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_learning.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add app/llm.py app/learning.py tests/test_learning.py
git commit -m "feat: llm abstraction with safe provider, summarize and rag answer"
```

---

### Task 5: Quiz generation + grading + confused-concept tracking

**Files:**
- Modify: `app/learning.py` (append quiz functions)
- Modify: `app/store.py` (append `record_mistake`, `get_confused`)
- Modify: `tests/test_learning.py` (append quiz asserts)

**Interfaces:**
- Consumes: `QuizItem` from `app/models`, chunks from store.
- Produces:
  - `app/learning.py`: `make_cloze_quiz(chunks: list[str], chunk_ids: list[str], num: int = 5) -> list[QuizItem]`, `grade_quiz(items: list[QuizItem], answers: list[int]) -> dict`
  - `app/store.py`: `record_mistake(conn, theme_id: str, chunk_id: str, label: str) -> None`, `get_confused(conn, theme_id: str) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_learning.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_learning.py -v`
Expected: FAIL with "cannot import name 'make_cloze_quiz'".

- [ ] **Step 3: Write minimal implementation**

```python
# append to app/learning.py
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
```

```python
# append to app/store.py
def record_mistake(conn: sqlite3.Connection, theme_id: str, chunk_id: str, label: str) -> None:
    conn.execute(
        "INSERT INTO mistakes (theme_id, chunk_id, label, count) VALUES (?, ?, ?, 1) "
        "ON CONFLICT(theme_id, chunk_id) DO UPDATE SET count = count + 1",
        (theme_id, chunk_id, label),
    )
    conn.commit()

def get_confused(conn: sqlite3.Connection, theme_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT theme_id, chunk_id, label, count FROM mistakes WHERE theme_id = ? ORDER BY count DESC",
        (theme_id,),
    )]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_learning.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add app/learning.py app/store.py tests/test_learning.py
git commit -m "feat: cloze quiz generation, grading, confused tracking"
```

---

### Task 6: Flashcards + SM-2 SRS + due list

**Files:**
- Modify: `app/learning.py` (append `srs_update`, `ensure_cards`, `due_cards`)
- Modify: `app/store.py` (append `upsert_card`, `list_due_cards`)
- Modify: `tests/test_learning.py` (append SRS asserts)

**Interfaces:**
- Consumes: `Card` model, chunks from store.
- Produces:
  - `app/learning.py`: `srs_update(card: Card, quality: int, today: str) -> Card`, `ensure_cards(conn, theme_id: str, chunks: list[dict], today: str) -> int`, `due_cards(conn, theme_id: str, today: str) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_learning.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_learning.py::test_sm2_progresses_and_regresses -v`
Expected: FAIL with "cannot import name 'srs_update'".

- [ ] **Step 3: Write minimal implementation**

```python
# append to app/learning.py
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
```

```python
# append to app/store.py
def upsert_card(conn: sqlite3.Connection, card_id: str, theme_id: str, front: str, back: str, chunk_id: str, today: str) -> None:
    conn.execute(
        "INSERT INTO cards (id, theme_id, front, back, chunk_id, ease, interval, reps, due) "
        "VALUES (?, ?, ?, ?, ?, 2.5, 0, 0, ?) ON CONFLICT(id) DO NOTHING",
        (card_id, theme_id, front, back, chunk_id, today),
    )
    conn.commit()

def list_due_cards(conn: sqlite3.Connection, theme_id: str, today: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM cards WHERE theme_id = ? AND due <= ? ORDER BY due, id",
        (theme_id, today),
    )]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_learning.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add app/learning.py app/store.py tests/test_learning.py
git commit -m "feat: sm-2 srs flashcards with due list"
```

---

### Task 7: FastAPI web wiring + end-to-end check + docs

**Files:**
- Create: `app/main.py`
- Test: `tests/test_api.py`
- Modify: `AGENTS.md` (append verified commands)

**Interfaces:**
- Consumes: all `app/*` interfaces above.
- Produces: FastAPI routes `GET /`, `POST /rescan`, `GET /themes/{id}`, `POST /themes/{id}/ask`, `GET /themes/{id}/quiz`, `POST /themes/{id}/quiz`, `GET /themes/{id}/review`, `POST /themes/{id}/review`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py
from pathlib import Path
from fastapi.testclient import TestClient
from app.store import init_db

def test_theme_flow(tmp_path, monkeypatch):
    lm = tmp_path / "lm"
    lm.mkdir()
    (lm / "bio.md").write_text("Mitokondria menghasilkan energi ATP untuk sel.", encoding="utf-8")
    monkeypatch.setenv("LT_MATERIAL", str(lm))
    monkeypatch.setenv("LT_DB", str(tmp_path / "app.db"))
    from app.main import app
    client = TestClient(app)
    assert client.post("/rescan").status_code == 200
    assert "bio.md" in client.get("/").text
    quiz = client.get("/themes/bio.md/quiz").json()
    assert quiz["total"] >= 1
    ask = client.post("/themes/bio.md/ask", json={"question": "Apa fungsi mitokondria?"}).json()
    assert "ATP" in ask["answer"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL with "No module named 'app.main'".

- [ ] **Step 3: Write minimal implementation**

```python
# app/main.py
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
```

- [ ] **Step 4: Run full suite + manual smoke test**

Run: `pytest -q`
Expected: all tests PASS.

Run: `python -m uvicorn app.main:app --port 8000`
Expected: `GET http://localhost:8000/` renders the theme list; `/rescan` picks up new files in `learning_material/`.

- [ ] **Step 5: Record commands in AGENTS.md, ignore the SQLite db, then commit**

Append `data/*.db` on its own line at the end of `.gitignore` so `data/app.db` is never committed.

Append to `AGENTS.md` under Tooling notes:

```markdown
- Test: `pytest -q` (full suite). Single file: `pytest tests/test_api.py -v`.
- Dev server: `python -m uvicorn app.main:app --port 8000`.
- SAFE offline mode is default; set `LT_SAFE=0` with Ollama running to use the local LLM.
```

```bash
git add app/main.py tests/test_api.py AGENTS.md .gitignore
git commit -m "feat: fastapi web wiring for read/ask/quiz/review"
```
