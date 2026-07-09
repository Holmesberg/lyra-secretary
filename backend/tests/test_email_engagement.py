from datetime import datetime
from uuid import uuid4

from app.db.models import EmailEngagementEvent, User
from app.services.email_engagement import build_click_tracking_url
from tests.conftest import TestingSession, auth_headers


def _make_user(db, *, is_operator: bool = False) -> User:
    user = User(
        email=f"email-engagement-{uuid4().hex[:8]}@example.test",
        timezone="Africa/Cairo",
        is_operator=is_operator,
        notion_enabled=False,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_public_click_endpoint_records_event_and_redirects(client, db, monkeypatch):
    db.query(EmailEngagementEvent).delete()
    db.commit()
    monkeypatch.setattr(
        "app.api.v1.endpoints.email_engagement.SessionLocal",
        TestingSession,
    )
    user = _make_user(db)
    url = build_click_tracking_url(
        campaign_version="unit-campaign",
        recipient_key="abc123",
        user_id=user.user_id,
        target_url="https://barzakh.app",
    )
    path = url.replace("https://api.barzakh.app", "")

    response = client.get(path, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://barzakh.app"
    event = (
        db.query(EmailEngagementEvent)
        .filter(EmailEngagementEvent.campaign_version == "unit-campaign")
        .one()
    )
    assert event.event_type == "click"
    assert event.user_id == user.user_id
    assert event.recipient_key == "abc123"
    assert event.target_url == "https://barzakh.app"


def test_invalid_email_tracking_token_does_not_record(client, db, monkeypatch):
    db.query(EmailEngagementEvent).delete()
    db.commit()
    monkeypatch.setattr(
        "app.api.v1.endpoints.email_engagement.SessionLocal",
        TestingSession,
    )

    response = client.get(
        "/v1/email-engagement/click?t=not-a-real-token",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://barzakh.app"
    assert db.query(EmailEngagementEvent).count() == 0


def test_operator_email_engagement_summary_counts_distinct_recipients(client, db):
    db.query(EmailEngagementEvent).delete()
    db.commit()
    operator = _make_user(db, is_operator=True)
    user = _make_user(db)
    db.add_all(
        [
            EmailEngagementEvent(
                user_id=user.user_id,
                campaign_version="unit-summary",
                event_type="open",
                recipient_key="r1",
            ),
            EmailEngagementEvent(
                user_id=user.user_id,
                campaign_version="unit-summary",
                event_type="open",
                recipient_key="r1",
            ),
            EmailEngagementEvent(
                user_id=user.user_id,
                campaign_version="unit-summary",
                event_type="click",
                recipient_key="r1",
                target_url="https://barzakh.app",
            ),
        ]
    )
    db.commit()

    response = client.get(
        "/v1/admin/email-engagement?campaign_version=unit-summary",
        headers=auth_headers(operator.user_id),
    )

    assert response.status_code == 200
    campaign = response.json()["campaigns"][0]
    assert campaign["opens"] == {"events": 2, "distinct_recipients": 1}
    assert campaign["clicks"] == {"events": 1, "distinct_recipients": 1}
