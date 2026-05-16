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
