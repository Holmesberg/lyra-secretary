from unittest.mock import patch

import pytest

from app.services.operator_notifier import (
    clear_operator_notification_dedupe,
    format_alert_context,
    notify_operator,
    redacted_user_ref,
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


def test_redacted_user_ref_is_stable_and_non_raw():
    first = redacted_user_ref(17)
    second = redacted_user_ref(17)

    assert first == second
    assert first.startswith("user#")
    assert "17" not in first


def test_format_alert_context_includes_triage_fields():
    context = format_alert_context(
        affected="scheduler.per-user / database bootstrap",
        scope="unknown user count",
        retry="Retries once, then skips this scheduler tick.",
        user_action="No user action; operator should inspect backend logs.",
        data_integrity="No mutation attempted before bootstrap completed.",
    )

    assert "Affected provider/subsystem:" in context
    assert "Affected user scope:" in context
    assert "Retry behavior:" in context
    assert "User action needed:" in context
    assert "Data integrity risk:" in context
