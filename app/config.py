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
