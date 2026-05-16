from unittest.mock import patch

import pytest

from app.services.operator_notifier import (
    clear_operator_notification_dedupe,
    notify_operator,
)


@pytest.fixture(autouse=True)
def _clear_dedupe():
    clear_operator_notification_dedupe()
    yield
    clear_operator_notification_dedupe()


def test_notify_operator_formats_source_and_severity():
    with patch(
        "app.services.operator_notifier.send_telegram_message_sync"
    ) as mock_send:
        mock_send.return_value = True

        assert notify_operator("hello", source="unit.test", severity="warn")

    text = mock_send.call_args.args[0]
    assert "`[unit.test]`" in text
    assert "hello" in text


def test_notify_operator_dedupes_with_cooldown():
    with patch(
        "app.services.operator_notifier.send_telegram_message_sync"
    ) as mock_send:
        mock_send.return_value = True

        assert notify_operator(
            "first",
            source="unit.test",
            severity="error",
            dedupe_key="same",
            cooldown_seconds=60,
        )
        assert not notify_operator(
            "second",
            source="unit.test",
            severity="error",
            dedupe_key="same",
            cooldown_seconds=60,
        )

    assert mock_send.call_count == 1


def test_notify_operator_never_raises_on_sender_failure():
    with patch(
        "app.services.operator_notifier.send_telegram_message_sync"
    ) as mock_send:
        mock_send.side_effect = RuntimeError("telegram down")

        assert not notify_operator("hello", source="unit.test", severity="error")
