import asyncio
import logging

import httpx

from app.services import telegram_notifier


def test_telegram_error_summary_redacts_token_for_http_status_error():
    token = "fake-token-for-test"
    request = httpx.Request(
        "POST",
        f"https://api.telegram.org/bot{token}/sendMessage",
    )
    response = httpx.Response(400, request=request)
    exc = httpx.HTTPStatusError(
        "Bad Request",
        request=request,
        response=response,
    )

    summary = telegram_notifier._telegram_error_summary(exc)

    assert token not in summary
    assert "bot<redacted>" in summary
    assert "status_code=400" in summary


def test_sync_wrapper_logs_sanitized_telegram_request_error(monkeypatch, caplog):
    token = "fake-token-for-test"

    async def _raise_request_error(_text):
        request = httpx.Request(
            "POST",
            f"https://api.telegram.org/bot{token}/sendMessage",
        )
        raise httpx.RequestError("network down", request=request)

    monkeypatch.setattr(telegram_notifier, "send_telegram_message", _raise_request_error)

    with caplog.at_level(logging.ERROR):
        ok = telegram_notifier.send_telegram_message_sync("hello")

    assert ok is False
    assert token not in caplog.text
    assert "bot<redacted>" in caplog.text


def test_send_telegram_uses_configured_timeout(monkeypatch):
    captured = {}

    class _Response:
        def raise_for_status(self):
            return None

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, _url, *, json, timeout):
            captured["json"] = json
            captured["timeout"] = timeout
            return _Response()

    monkeypatch.setattr(telegram_notifier.settings, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(telegram_notifier.settings, "TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(telegram_notifier.settings, "TELEGRAM_TIMEOUT_SECONDS", 1.5)
    monkeypatch.setattr(telegram_notifier.httpx, "AsyncClient", lambda: _Client())

    assert telegram_notifier.send_telegram_message_sync("hello")
    assert captured["timeout"] == 1.5


def test_sync_wrapper_handles_running_event_loop(monkeypatch):
    async def _send(_text):
        return True

    monkeypatch.setattr(telegram_notifier, "send_telegram_message", _send)
    monkeypatch.setattr(telegram_notifier.settings, "TELEGRAM_TIMEOUT_SECONDS", 1.0)

    async def _call_sync_wrapper_from_async_context():
        return telegram_notifier.send_telegram_message_sync("hello")

    assert asyncio.run(_call_sync_wrapper_from_async_context()) is True


def test_httpx_info_logs_are_suppressed_to_avoid_token_url_leaks():
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
