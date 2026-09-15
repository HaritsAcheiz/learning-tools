import hashlib
import re
from pathlib import Path
from docx import Document as DocxDocument
from pypdf import PdfReader
from app.config import CHUNK_CHARS, OVERLAP_CHARS
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
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def chunk_text(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    if overlap >= size:
        raise ValueError(f"overlap ({overlap}) must be < size ({size})")
    text = clean_text(text)
    if not text:
        return []
    if len(text) <= size:
        return [text]
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text), step) if text[i:i + size].strip()]

def ingest_theme(
    material_dir: Path,
    theme_id: str,
    conn,
    chunk_chars: int = CHUNK_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> int:
    from app.store import upsert_theme, insert_chunks
    theme = next((t for t in scan_themes(material_dir) if t.id == theme_id), None)
    if theme is None:
        raise ValueError(f"Unknown theme: {theme_id}")
    total = 0
    if theme.kind == "file":
        path = Path(theme.path)
        doc_id = hashlib.sha1(str(path).encode()).hexdigest()[:12]
        try:
            chunks = chunk_text(extract_text(path), size=chunk_chars, overlap=overlap_chars)
        except Exception:
            return 0
        upsert_theme(conn, theme.id, theme.name, theme.path, theme.kind)
        insert_chunks(conn, theme.id, doc_id, chunks)
        total += len(chunks)
    else:
        upsert_theme(conn, theme.id, theme.name, theme.path, theme.kind)
        for path in sorted(Path(theme.path).rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED:
                try:
                    chunks = chunk_text(extract_text(path), size=chunk_chars, overlap=overlap_chars)
                except Exception:
                    continue
                doc_id = hashlib.sha1(str(path).encode()).hexdigest()[:12]
                insert_chunks(conn, theme.id, doc_id, chunks)
                total += len(chunks)
    return total
