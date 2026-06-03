"""Transactional activation email regressions."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from sqlalchemy.exc import IntegrityError

from app.core import security
from app.db.models import User
from app.services import email_delivery, user_mailer
from app.services.user_mailer import (
    ActivationEmailResult,
    activation_email_text,
    record_activation_email_result,
    send_activation_email,
)
from tests.conftest import TestingSession


def _user(email: str | None = None) -> User:
    return User(
        email=email or f"activation-{uuid4().hex[:8]}@example.test",
        google_id=f"google-{uuid4().hex[:8]}",
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        created_at=datetime.utcnow(),
    )


def _token(email: str, *, sub: str = "google-user") -> str:
    secret = "activation-email-test-secret-at-least-32-bytes"
    return jwt.encode(
        {
            "email": email,
            "sub": sub,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
        },
        secret,
        algorithm="HS256",
    )


def test_activation_mailer_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(user_mailer.settings, "USER_EMAIL_ENABLED", False)

    def fail_post(*_args, **_kwargs):
        raise AssertionError("Resend should not be called when disabled")

    monkeypatch.setattr(email_delivery.requests, "post", fail_post)

    result = send_activation_email(_user())

    assert result == ActivationEmailResult(status="skipped_disabled", sent=False)


def test_activation_mailer_skips_without_resend_key(monkeypatch):
    monkeypatch.setattr(user_mailer.settings, "USER_EMAIL_ENABLED", True)
    monkeypatch.setattr(user_mailer.settings, "RESEND_API_KEY", None)

    def fail_post(*_args, **_kwargs):
        raise AssertionError("Resend should not be called without API key")

    monkeypatch.setattr(email_delivery.requests, "post", fail_post)

    result = send_activation_email(_user())

    assert result == ActivationEmailResult(status="skipped_unconfigured", sent=False)


def test_activation_mailer_sends_plain_transactional_payload(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(user_mailer.settings, "USER_EMAIL_ENABLED", True)
    monkeypatch.setattr(user_mailer.settings, "RESEND_API_KEY", "resend-key")
    monkeypatch.setattr(user_mailer.settings, "USER_EMAIL_FROM", "hello@lyraos.org")
    monkeypatch.setattr(user_mailer.settings, "FRONTEND_URL", "https://lyraos.org")

    def fake_post(*_args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status_code=202, text="accepted")

    monkeypatch.setattr(email_delivery.requests, "post", fake_post)

    result = send_activation_email(_user("student@example.test"))

    assert result.sent is True
    payload = calls[0]["json"]
    assert payload["from"] == "LyraOS <hello@lyraos.org>"
    assert payload["to"] == ["student@example.test"]
    assert payload["subject"] == "Welcome to LyraOS"
    assert "https://lyraos.org" in payload["text"]
    assert "export your account data" in payload["text"]
    assert "delete your account" in payload["text"]
    forbidden = [
        "task title",
        "deadline",
        "we noticed",
        "studied",
        "moodle",
        "oauth",
        "token",
        "adaptive",
    ]
    assert all(term not in payload["text"].lower() for term in forbidden)


def test_activation_mailer_redacts_provider_failures(monkeypatch):
    monkeypatch.setattr(user_mailer.settings, "USER_EMAIL_ENABLED", True)
    monkeypatch.setattr(user_mailer.settings, "RESEND_API_KEY", "resend-key")

    def fake_post(*_args, **_kwargs):
        return SimpleNamespace(status_code=401, text="raw provider token secret")

    monkeypatch.setattr(email_delivery.requests, "post", fake_post)

    result = send_activation_email(_user())

    assert result.sent is False
    assert result.error == "http_401:provider_error_redacted"
    assert "secret" not in result.error


def test_activation_mailer_request_exception_is_non_throwing(monkeypatch):
    monkeypatch.setattr(user_mailer.settings, "USER_EMAIL_ENABLED", True)
    monkeypatch.setattr(user_mailer.settings, "RESEND_API_KEY", "resend-key")

    def fake_post(*_args, **_kwargs):
        raise RuntimeError("raw network failure with secret")

    monkeypatch.setattr(email_delivery.requests, "post", fake_post)

    result = send_activation_email(_user())

    assert result.sent is False
    assert result.error == "request_failed"


def test_activation_email_status_stamps_sent_and_failure(db, monkeypatch):
    monkeypatch.setattr(user_mailer, "SessionLocal", TestingSession)
    sent_user = _user()
    failed_user = _user()
    db.add_all([sent_user, failed_user])
    db.commit()
    sent_id = sent_user.user_id
    failed_id = failed_user.user_id

    record_activation_email_result(
        sent_id,
        ActivationEmailResult(status="sent", sent=True),
    )
    record_activation_email_result(
        failed_id,
        ActivationEmailResult(status="failed", sent=False, error="http_500"),
    )

    db.expire_all()
    sent = db.query(User).filter(User.user_id == sent_id).one()
    failed = db.query(User).filter(User.user_id == failed_id).one()
    assert sent.activation_email_sent_at is not None
    assert sent.activation_email_last_error is None
    assert failed.activation_email_failed_at is not None
    assert failed.activation_email_last_error == "http_500"


def test_first_new_user_provisioning_sends_one_activation_email(db, monkeypatch):
    monkeypatch.setattr(security, "SessionLocal", TestingSession)
    monkeypatch.setattr(user_mailer, "SessionLocal", TestingSession)
    monkeypatch.setattr(security.settings, "JWT_SECRET", "activation-email-test-secret-at-least-32-bytes")
    monkeypatch.setattr(security.settings, "JWT_ALGORITHM", "HS256")
    calls: list[int] = []

    def fake_send(user: User) -> ActivationEmailResult:
        calls.append(user.user_id)
        return ActivationEmailResult(status="sent", sent=True)

    monkeypatch.setattr(user_mailer, "send_activation_email", fake_send)

    email = f"new-{uuid4().hex[:8]}@example.test"
    token = _token(email)
    first = security.resolve_user_from_token(token)
    second = security.resolve_user_from_token(token)

    assert first.user_id == second.user_id
    assert calls == [first.user_id]
    db.expire_all()
    row = db.query(User).filter(User.email == email).one()
    assert row.activation_email_sent_at is not None


def test_existing_user_login_does_not_send_activation_email(db, monkeypatch):
    monkeypatch.setattr(security, "SessionLocal", TestingSession)
    monkeypatch.setattr(security.settings, "JWT_SECRET", "activation-email-test-secret-at-least-32-bytes")
    monkeypatch.setattr(security.settings, "JWT_ALGORITHM", "HS256")
    existing = _user()
    db.add(existing)
    db.commit()

    def fail_send(_user: User) -> ActivationEmailResult:
        raise AssertionError("existing users must not receive activation email")

    monkeypatch.setattr(user_mailer, "send_activation_email", fail_send)

    resolved = security.resolve_user_from_token(_token(existing.email, sub=existing.google_id or "google-existing"))

    assert resolved.user_id == existing.user_id


def test_integrity_error_race_loser_adopts_existing_user_without_email(monkeypatch):
    existing = _user("race@example.test")
    existing.user_id = 123
    calls: list[str] = []

    class FakeQuery:
        def __init__(self, session):
            self.session = session

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            self.session.query_count += 1
            if self.session.query_count == 1:
                return None
            return existing

    class FakeSession:
        def __init__(self):
            self.query_count = 0

        def query(self, *_args, **_kwargs):
            return FakeQuery(self)

        def add(self, _row):
            pass

        def commit(self):
            raise IntegrityError("INSERT user", {}, Exception("duplicate email"))

        def rollback(self):
            pass

        def close(self):
            pass

    def fail_send(_user: User) -> ActivationEmailResult:
        calls.append("send")
        raise AssertionError("race loser must not send activation email")

    monkeypatch.setattr(security, "SessionLocal", FakeSession)
    monkeypatch.setattr(security.settings, "JWT_SECRET", "activation-email-test-secret-at-least-32-bytes")
    monkeypatch.setattr(security.settings, "JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(user_mailer, "send_activation_email", fail_send)

    resolved = security.resolve_user_from_token(_token(existing.email))

    assert resolved is existing
    assert calls == []


def test_activation_email_copy_is_plain_account_infrastructure():
    text = activation_email_text(frontend_url="https://lyraos.org")

    assert "Welcome to LyraOS." in text
    forbidden = [
        "we noticed",
        "task",
        "deadline",
        "study",
        "focus",
        "streak",
        "optimize",
        "adaptive",
        "moodle",
        "calendar event",
    ]
    assert all(term not in text.lower() for term in forbidden)


def test_activation_email_state_is_not_consumed_by_behavioral_paths():
    app_dir = Path(__file__).resolve().parents[1] / "app"
    allowed = {
        Path("core/config.py"),
        Path("core/security.py"),
        Path("db/models.py"),
        Path("services/user_mailer.py"),
    }
    offenders: list[str] = []
    tokens = ("activation_email", "user_mailer")
    for path in app_dir.rglob("*.py"):
        rel = path.relative_to(app_dir)
        if rel in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token in text:
                offenders.append(f"{rel}:{token}")

    assert offenders == []
