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
        import json
        import urllib.request

        body = json.dumps(
            {"model": self.model, "prompt": prompt, "context": context, "stream": False}
        ).encode()
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
