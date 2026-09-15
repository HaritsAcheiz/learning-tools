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
