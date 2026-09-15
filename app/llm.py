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
    """Local LLM via Ollama /api/generate.

    Retrieved chunks are inlined into the prompt text: Ollama's `context`
    field carries token-id arrays for conversation continuity, not source
    text, so sending chunks there would be a protocol error.
    Model is selectable via the LT_MODEL env var.
    """

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("LT_MODEL", "llama3.2:3b")

    def generate(self, prompt: str, context: list[str]) -> str:
        import json
        import urllib.request

        ctx_block = "\n\n".join(f"[{i}] {c}" for i, c in enumerate(context))
        full = f"{prompt}\n\nContext:\n{ctx_block}"
        body = json.dumps(
            {
                "model": self.model,
                "prompt": full,
                "stream": False,
                "options": {"num_ctx": 8192, "temperature": 0},
            }
        ).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", data=body)
        with urllib.request.urlopen(req, timeout=120) as res:
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
