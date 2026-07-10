"""NVIDIA NIM client payload contract tests.

These tests do not hit the network. They pin the Kimi K2.6 payload shape that
hosted parser enrichment relies on while keeping structured parser calls
machine-readable.
"""
import json

from app.services import llm_parser, nvidia_nim_client


class _FakeResponse:
    status_code = 200
    text = '{"ok": true}'

    def json(self):
        return {"choices": [{"message": {"content": "ok"}}]}


class _FakeClient:
    def __init__(self, *, captured: dict, timeout: int):
        self.captured = captured
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, *, headers, json):
        self.captured["url"] = url
        self.captured["headers"] = headers
        self.captured["payload"] = json
        self.captured["timeout"] = self.timeout
        return _FakeResponse()


def test_chat_completion_adds_kimi_thinking_kwargs(monkeypatch):
    captured = {}
    monkeypatch.setattr(nvidia_nim_client.settings, "NVIDIA_NIM_API_KEY", "nvapi-test")
    monkeypatch.setattr(
        nvidia_nim_client.settings, "NVIDIA_NIM_MODEL", "moonshotai/kimi-k2.6"
    )
    monkeypatch.setattr(nvidia_nim_client.settings, "NVIDIA_NIM_ENABLE_THINKING", True)
    monkeypatch.setattr(nvidia_nim_client.settings, "NVIDIA_NIM_TIMEOUT_SECONDS", 120)
    monkeypatch.setattr(
        nvidia_nim_client.httpx,
        "Client",
        lambda timeout: _FakeClient(captured=captured, timeout=timeout),
    )

    nvidia_nim_client.chat_completion(
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=16,
    )

    payload = captured["payload"]
    assert payload["model"] == "moonshotai/kimi-k2.6"
    assert payload["chat_template_kwargs"] == {"thinking": True}
    assert payload["max_tokens"] == 16
    assert captured["timeout"] == 120


def test_chat_completion_allows_structured_output_to_disable_thinking(monkeypatch):
    captured = {}
    monkeypatch.setattr(nvidia_nim_client.settings, "NVIDIA_NIM_API_KEY", "nvapi-test")
    monkeypatch.setattr(nvidia_nim_client.settings, "NVIDIA_NIM_ENABLE_THINKING", True)
    monkeypatch.setattr(
        nvidia_nim_client.httpx,
        "Client",
        lambda timeout: _FakeClient(captured=captured, timeout=timeout),
    )

    nvidia_nim_client.chat_completion(
        messages=[{"role": "user", "content": "json"}],
        response_format={"type": "json_object"},
        chat_template_kwargs={"thinking": False},
    )

    payload = captured["payload"]
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["chat_template_kwargs"] == {"thinking": False}


def test_chat_completion_accepts_per_call_timeout(monkeypatch):
    captured = {}
    monkeypatch.setattr(nvidia_nim_client.settings, "NVIDIA_NIM_API_KEY", "nvapi-test")
    monkeypatch.setattr(nvidia_nim_client.settings, "NVIDIA_NIM_TIMEOUT_SECONDS", 120)
    monkeypatch.setattr(
        nvidia_nim_client.httpx,
        "Client",
        lambda timeout: _FakeClient(captured=captured, timeout=timeout),
    )

    nvidia_nim_client.chat_completion(
        messages=[{"role": "user", "content": "json"}],
        timeout_seconds=15,
    )

    assert captured["timeout"] == 15


def test_jarvis_streaming_api_stays_removed():
    """Removed JARVIS diagnostics must not keep dead NIM APIs alive."""
    assert not hasattr(nvidia_nim_client, "chat_completion_stream")
    assert not hasattr(nvidia_nim_client, "health_check")


def test_llm_parser_disables_thinking_for_json_contract(monkeypatch):
    captured = {}

    def fake_chat_completion(**kwargs):
        captured.update(kwargs)
        return {"choices": [{"message": {"content": json.dumps({"priority": 3})}}]}

    monkeypatch.setattr(nvidia_nim_client, "chat_completion", fake_chat_completion)

    assert llm_parser._call_nim("Return JSON.") == {"priority": 3}
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["chat_template_kwargs"] == {"thinking": False}
    assert captured["timeout_seconds"] == (
        llm_parser.settings.NVIDIA_NIM_ENRICHMENT_TIMEOUT_SECONDS
    )
