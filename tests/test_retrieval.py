# tests/test_retrieval.py
import pytest
from app.retrieval import embed, search, FaissIndex, sample_spread

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

def test_sample_spread_covers_whole_doc():
    texts = [f"chunk-{i}" for i in range(20)]
    idx = sample_spread(texts, n=8)
    assert len(idx) == 8
    assert idx == sorted(idx)
    assert idx[0] == 0
    assert idx[-1] == 19
    assert max(b - a for a, b in zip(idx, idx[1:])) <= 4

def test_sample_spread_short_doc_keeps_all():
    texts = ["a", "b", "c"]
    assert sample_spread(texts, n=8) == [0, 1, 2]
