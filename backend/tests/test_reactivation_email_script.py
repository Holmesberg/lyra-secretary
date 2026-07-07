from types import SimpleNamespace

from scripts import send_reactivation_email


def test_recipient_first_name_handles_user_without_first_name():
    user = SimpleNamespace(user_id=9, email="moriartyholmesberg@gmail.com")

    assert send_reactivation_email._recipient_first_name(user) == "Moriartyholmesberg"


def test_recipient_first_name_prefers_explicit_name():
    user = send_reactivation_email._Recipient(
        "explicit-test",
        "operator@example.test",
        "Ali",
    )

    assert send_reactivation_email._recipient_first_name(user) == "Ali"


def test_reactivation_html_uses_signed_tracking_links(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_engagement.settings.EMAIL_TRACKING_BASE_URL",
        "https://api.barzakh.app",
    )
    user = send_reactivation_email._Recipient(
        "explicit-test",
        "operator@example.test",
        "Ali",
    )

    text, html = send_reactivation_email._render_body(user)

    assert "https://barzakh.app" in text
    assert "https://api.barzakh.app/v1/email-engagement/click?t=" in html
    assert "https://api.barzakh.app/v1/email-engagement/open.gif?t=" in html
    assert "operator@example.test" not in html
