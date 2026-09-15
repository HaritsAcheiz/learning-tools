"""Structure-aware section splitting for long documents.

Detects part/chapter/section headings inside chunked text and groups chunk
indices per section, so summaries can cover the whole document instead of
just its opening. Pure heuristics, no LLM calls.
"""
import re

_PATTERNS = [
    re.compile(r"(?im)^\s*(section\s+(?:[A-Z]\.?)?\d+(\.\d+)*\b.{0,80})"),
    re.compile(r"(?im)^\s*((?:part|chapter|appendix)\s+[A-Z0-9]+.{0,80})"),
    # Bare dotted headings without a keyword ("A.2. ICT Management").
    # Requires LETTER.DIGITS. and a capitalized title to avoid list items.
    re.compile(r"(?im)^\s*([A-Z]\.\d+(?:\.\d+)*\.\s+[A-Z].{0,80})"),
]

INTRO_TITLE = "Introduction"
FULL_TITLE = "Full document"

#: Bare-pattern match ending in a page number ("A.1. ICT Governance 6").
TOC_TAIL = re.compile(r"\s\d+$")


def _is_toc(kind: str, title: str) -> bool:
    return kind == "bare" and bool(TOC_TAIL.search(title))


def _title_rank(title: str) -> tuple[int, int]:
    """Canonical headings ("A.1. ICT Governance") sort before descriptive
    sentences and TOC variants; ties break toward the shorter title."""
    canonical = 0 if re.match(r"^[A-Z]\.\d+", title) else 1
    return (canonical, len(title))


def _group_key(title: str) -> str:
    """Coarse key so TOC lines, wrapped headings, and sub-sections merge.

    Requires a dotted number (LETTER.DIGITS or DIGITS.DIGITS) so a bare
    digit elsewhere in the title can never become the key.
    """
    m = re.search(r"(part\s+[A-Z])\b", title, re.I)
    if m:
        return m.group(1).lower()
    m = re.search(r"([A-Z]\.\d+(?:\.\d+)*|\b\d+\.\d+(?:\.\d+)*)", title)
    if m:
        return ".".join(m.group(1).split(".")[:2]).upper()
    return title.lower()


def split_sections(texts: list[str]) -> list[dict]:
    """Group chunk indices by detected section.

    Returns [{"title": str, "indices": [int, ...]}] in document order.
    Chunks before the first heading become "Introduction"; with no headings
    at all the whole text is one "Full document" section.
    """
    if not texts:
        return []
    bounds: list[tuple[int, str]] = []
    for i, text in enumerate(texts):
        for kind, pat in (("kw", _PATTERNS[0]), ("kw", _PATTERNS[1]), ("bare", _PATTERNS[2])):
            for m in pat.finditer(text):
                title = " ".join(m.group(1).split())[:100]
                if _is_toc(kind, title):
                    continue  # table-of-contents entry, not a section start
                if not bounds or bounds[-1][1] != title:
                    bounds.append((i, title))
    if not bounds:
        return [{"title": FULL_TITLE, "indices": list(range(len(texts)))}]
    out = []
    if bounds[0][0] > 0:
        out.append({"title": INTRO_TITLE, "indices": list(range(bounds[0][0]))})
    # Same section can repeat (table of contents, wrapped heading lines,
    # sub-sections): merge by coarse key, first-seen order.
    groups: dict[str, list[tuple[int, int]]] = {}
    titles: dict[str, str] = {}
    for k, (start, title) in enumerate(bounds):
        end = bounds[k + 1][0] if k + 1 < len(bounds) else len(texts)
        key = _group_key(title)
        groups.setdefault(key, []).append((start, end))
        current = titles.get(key)
        if current is None or _title_rank(title) < _title_rank(current):
            titles[key] = title
    for key, ranges in groups.items():
        idx = sorted({i for s, e in ranges for i in range(s, e)})
        if idx:
            out.append({"title": titles[key], "indices": idx})
    return out
