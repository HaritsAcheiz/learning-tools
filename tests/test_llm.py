import json

import app.llm as llmmod
from app.llm import OllamaProvider, SafeProvider, get_provider


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_ollama_embeds_context_in_prompt(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["body"] = json.loads(req.data.decode())
        seen["url"] = req.full_url
        return _FakeResp({"response": "jawaban uji"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    out = OllamaProvider(model="uji-model").generate(
        "Pertanyaan", ["konteks satu", "konteks dua"])
    assert out == "jawaban uji"
    assert seen["url"] == "http://localhost:11434/api/generate"
    assert seen["body"]["model"] == "uji-model"
    assert seen["body"]["stream"] is False
    assert "konteks satu" in seen["body"]["prompt"]
    assert "konteks dua" in seen["body"]["prompt"]
    assert "context" not in seen["body"]


def test_get_provider_safe_default(monkeypatch):
    monkeypatch.setenv("LT_SAFE", "1")
    assert isinstance(get_provider(), SafeProvider)


def test_get_provider_falls_back_when_ollama_down(monkeypatch):
    monkeypatch.setenv("LT_SAFE", "0")

    def boom(*args, **kwargs):
        raise OSError("down")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    assert isinstance(get_provider(), SafeProvider)
