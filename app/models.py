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
