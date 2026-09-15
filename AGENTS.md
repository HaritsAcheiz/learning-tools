# AGENTS.md

## What this is
- `learning-tools`: planned learning assistant app (Indonesian README). Users pick a study theme from material placed in `learning_material/`; the app should guide effective/efficient learning.
- Status: greenfield. No source code, no manifests, no build/test/lint config exist yet.

## Layout
- `learning_material/` — user-provided study content. Currently empty. Do not delete; new code should treat each file/subdir here as a selectable theme.
- `LICENSE` — GPLv3. Keep new code GPLv3-compatible.

## Tooling notes
- `.gitignore` is the standard Python template (`venv/`, `__pycache__/`, `.env`, etc.). It implies Python, but no interpreter version, `pyproject.toml`, or `requirements*.txt` is pinned yet.
- No verified commands exist: no package manager, test runner, formatter, or CI to document. When you introduce them, record the exact commands here.
- Windows dev host (`win32`, PowerShell 5.1). Prefer `workdir`-based commands; avoid `cd` inside commands.
- Test: `pytest -q` (full suite). Single file: `pytest tests/test_api.py -v`.
- Dev server: `python -m uvicorn app.main:app --port 8000`.
- SAFE offline mode is default; set `LT_SAFE=0` with Ollama running to use the local LLM.
