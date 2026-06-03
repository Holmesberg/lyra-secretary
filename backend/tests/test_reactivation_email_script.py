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
