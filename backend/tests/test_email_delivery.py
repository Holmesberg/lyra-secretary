from types import SimpleNamespace

from app.services import email_delivery
from app.services.email_delivery import send_resend_email


def test_shared_resend_sender_is_hello(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(email_delivery.settings, "RESEND_API_KEY", "resend-key")

    def fake_post(*_args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status_code=202, text="accepted")

    monkeypatch.setattr(email_delivery.requests, "post", fake_post)

    result = send_resend_email(
        to="user@example.test",
        subject="Hello",
        text="Plain",
        html="<p>HTML</p>",
        scheduled_at="2026-06-03T17:00:00Z",
        idempotency_key="test-key",
    )

    assert result.sent is True
    payload = calls[0]["json"]
    assert payload["from"] == "LyraOS <hello@lyraos.org>"
    assert payload["to"] == ["user@example.test"]
    assert payload["html"] == "<p>HTML</p>"
    assert payload["scheduled_at"] == "2026-06-03T17:00:00Z"
    assert calls[0]["headers"]["Idempotency-Key"] == "test-key"
    assert calls[0]["headers"]["User-Agent"] == "lyraos-email/1.0"


def test_shared_resend_error_keeps_safe_provider_message(monkeypatch):
    monkeypatch.setattr(email_delivery.settings, "RESEND_API_KEY", "resend-key")

    def fake_post(*_args, **_kwargs):
        return SimpleNamespace(
            status_code=403,
            text="",
            json=lambda: {
                "message": (
                    "The lyraos.org domain is not verified. Please, add and "
                    "verify your domain."
                )
            },
        )

    monkeypatch.setattr(email_delivery.requests, "post", fake_post)

    result = send_resend_email(
        to="user@example.test",
        subject="Hello",
        text="Plain",
    )

    assert result.sent is False
    assert result.error == (
        "http_403:The lyraos.org domain is not verified. Please, add and "
        "verify your domain."
    )
