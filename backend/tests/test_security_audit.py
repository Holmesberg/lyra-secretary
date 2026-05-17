"""SecurityAuditEvent governance-only regressions."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.db.models import SecurityAuditEvent, User
from app.db.scoping import set_current_user_id
from app.services.security_audit import sanitize_metadata, write_security_audit_event
from tests.conftest import auth_headers


def _make_user(db, *, is_operator: bool = False) -> User:
    user = User(
        email=f"audit-{uuid4().hex[:8]}@example.test",
        timezone="Africa/Cairo",
        is_operator=is_operator,
        notion_enabled=False,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_security_audit_redacts_sensitive_metadata(db):
    set_current_user_id(None)
    db.query(SecurityAuditEvent).delete()
    db.commit()

    write_security_audit_event(
        db=db,
        event_type="provider_connected",
        surface="/unit",
        status="success",
        actor_user_id=7,
        user_id=7,
        target_type="provider",
        target_id="moodle_ws",
        redacted_metadata={
            "task_title": "Secret exam plan",
            "notes": "private note",
            "email": "student@example.edu",
            "token": "abc123",
            "refresh_token": "refresh-secret",
            "provider_url": "https://moodle.example.edu/calendar?authtoken=secret",
            "oauth_payload": {"access_token": "oauth-secret"},
            "moodle_ws_token": "ws-secret",
            "behavioral_session_content": "studied lecture 4 for 42 min",
            "safe_reason": "connected",
        },
    )

    event = db.query(SecurityAuditEvent).one()
    encoded = json.dumps(event.redacted_metadata, sort_keys=True)
    assert "Secret exam plan" not in encoded
    assert "private note" not in encoded
    assert "student@example.edu" not in encoded
    assert "abc123" not in encoded
    assert "refresh-secret" not in encoded
    assert "moodle.example.edu" not in encoded
    assert "oauth-secret" not in encoded
    assert "ws-secret" not in encoded
    assert "studied lecture" not in encoded
    assert event.redacted_metadata["safe_reason"] == "connected"


def test_security_audit_hashes_request_client_values(client, db):
    user = _make_user(db, is_operator=False)
    db.query(SecurityAuditEvent).delete()
    db.commit()

    response = client.get(
        "/v1/jarvis/health",
        headers={**auth_headers(user.user_id), "user-agent": "raw-test-agent"},
    )
    assert response.status_code == 403

    event = (
        db.query(SecurityAuditEvent)
        .filter(SecurityAuditEvent.event_type == "operator_access_denied")
        .one()
    )
    assert event.actor_user_id == user.user_id
    assert event.ip_hash is None or len(event.ip_hash) == 64
    assert event.user_agent_hash is not None
    assert event.user_agent_hash != "raw-test-agent"


def test_security_audit_sanitizer_redacts_sensitive_strings_without_key_context():
    payload = sanitize_metadata(
        {
            "reason": "https://moodle.example.edu/webservice/rest/server.php?wstoken=abc",
            "nested": ["student@example.edu", "plain-value"],
        }
    )
    assert payload["reason"] == "[redacted]"
    assert payload["nested"][0] == "[redacted]"
    assert payload["nested"][1] == "plain-value"


def test_security_audit_model_is_not_imported_by_behavioral_paths():
    """Audit rows must not become another inference dataset."""
    app_dir = Path(__file__).resolve().parents[1] / "app"
    allowed = {
        Path("db/models.py"),
        Path("services/security_audit.py"),
    }
    offenders: list[str] = []
    for path in app_dir.rglob("*.py"):
        rel = path.relative_to(app_dir)
        if rel in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if "SecurityAuditEvent" in text:
            offenders.append(str(rel))

    assert offenders == []
