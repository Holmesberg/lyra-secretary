"""Central registry for user-owned export/delete surfaces.

The registry is the Wave 5A data-sovereignty boundary. Export and delete must
move through this file so new user-owned tables cannot silently fall outside
the account-governance surface.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import (
    ArchetypeAssignment,
    CalibrationNudgeEvent,
    Deadline,
    DeadlineCompletionEvent,
    EmailEngagementEvent,
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposurePolicyEffectLog,
    ExposureRenderEvent,
    ExternalEventOutcome,
    Feedback,
    JarvisInvocation,
    NotificationLifecycleEvent,
    PauseEvent,
    PausePredictionLog,
    ReflectionViewLog,
    ResumePredictionLog,
    StopwatchSession,
    SuppressionEvent,
    Task,
    TaskDeadlineOutcome,
    TaskExecutionCorrection,
    User,
)

REDACTED = "[redacted]"

_SECRET_COLUMNS = {
    "google_refresh_token",
    "moodle_ics_url",
    "moodle_ws_token",
}
_SECRET_NAME_PARTS = (
    "access_token",
    "authtoken",
    "credential",
    "password",
    "refresh_token",
    "secret",
    "token",
    "wstoken",
)
_SECRET_VALUE_MARKERS = (
    "access_token=",
    "authtoken=",
    "refresh_token=",
    "secret=",
    "token=",
    "wstoken=",
)


@dataclass(frozen=True)
class RegistryEntry:
    section: str
    model: type
    description: str
    delete_policy: str = "purge_on_account_delete"
    export_query: Callable[[Session, int], Iterable[Any]] | None = None


def _direct_user_rows(model: type) -> Callable[[Session, int], Iterable[Any]]:
    return lambda db, uid: db.query(model).filter(model.user_id == uid).all()


def _user_exposure_ids(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(ExposureDecisionEvent.exposure_id)
        .filter(ExposureDecisionEvent.user_id == user_id)
        .all()
    )
    return [str(row[0]) for row in rows]


def _exposure_child_rows(model: type) -> Callable[[Session, int], Iterable[Any]]:
    def _query(db: Session, uid: int) -> Iterable[Any]:
        exposure_ids = _user_exposure_ids(db, uid)
        if not exposure_ids:
            return []
        return db.query(model).filter(model.exposure_id.in_(exposure_ids)).all()

    return _query


USER_DATA_REGISTRY: tuple[RegistryEntry, ...] = (
    RegistryEntry("tasks", Task, "Task lifecycle rows."),
    RegistryEntry("deadlines", Deadline, "User-created and imported deadlines."),
    RegistryEntry(
        "deadline_completion_events",
        DeadlineCompletionEvent,
        "Deadline completion/provider candidate traces.",
    ),
    RegistryEntry(
        "task_deadline_outcomes",
        TaskDeadlineOutcome,
        "Frozen deadline outcome reconciliation rows.",
    ),
    RegistryEntry("stopwatch_sessions", StopwatchSession, "Explicit timer sessions."),
    RegistryEntry(
        "task_execution_corrections",
        TaskExecutionCorrection,
        "User/operator execution correction rows.",
    ),
    RegistryEntry("pause_events", PauseEvent, "Pause/resume event rows."),
    RegistryEntry(
        "pause_prediction_logs",
        PausePredictionLog,
        "Pause-prediction prompt lifecycle rows.",
    ),
    RegistryEntry(
        "resume_prediction_logs",
        ResumePredictionLog,
        "Resume-prediction prompt lifecycle rows.",
    ),
    RegistryEntry(
        "calibration_nudge_events",
        CalibrationNudgeEvent,
        "Calibration nudge decision/outcome rows.",
    ),
    RegistryEntry(
        "reflection_view_logs",
        ReflectionViewLog,
        "Reflection/impression rows.",
    ),
    RegistryEntry(
        "exposure_decision_events",
        ExposureDecisionEvent,
        "Exposure ledger decision rows.",
    ),
    RegistryEntry(
        "exposure_render_events",
        ExposureRenderEvent,
        "Exposure render rows linked by exposure_id.",
        export_query=_exposure_child_rows(ExposureRenderEvent),
    ),
    RegistryEntry(
        "exposure_ack_events",
        ExposureAckEvent,
        "Authenticated exposure acknowledgement rows.",
    ),
    RegistryEntry(
        "suppression_events",
        SuppressionEvent,
        "Exposure suppression rows linked by exposure_id.",
        export_query=_exposure_child_rows(SuppressionEvent),
    ),
    RegistryEntry(
        "exposure_policy_effect_logs",
        ExposurePolicyEffectLog,
        "Exposure policy diagnostic rows.",
    ),
    RegistryEntry("feedback", Feedback, "User-submitted feedback rows."),
    RegistryEntry(
        "external_event_outcomes",
        ExternalEventOutcome,
        "Calendar/provider attendance self-report rows.",
    ),
    RegistryEntry(
        "notification_lifecycle_events",
        NotificationLifecycleEvent,
        "Durable notification lifecycle rows.",
    ),
    RegistryEntry(
        "email_engagement_events",
        EmailEngagementEvent,
        "Operational email open/click telemetry rows.",
    ),
    RegistryEntry(
        "archetype_assignments",
        ArchetypeAssignment,
        "User archetype survey/assignment rows.",
    ),
    RegistryEntry(
        "jarvis_invocations",
        JarvisInvocation,
        "JARVIS tool-call audit rows.",
    ),
)


def registry_manifest() -> list[dict[str, str]]:
    return [
        {
            "section": entry.section,
            "table": entry.model.__tablename__,
            "delete_policy": entry.delete_policy,
            "description": entry.description,
        }
        for entry in USER_DATA_REGISTRY
    ]


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _should_redact_column(column_name: str) -> bool:
    lowered = column_name.lower()
    return lowered in _SECRET_COLUMNS or any(part in lowered for part in _SECRET_NAME_PARTS)


def _should_redact_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(marker in lowered for marker in _SECRET_VALUE_MARKERS)


def _row_to_dict(row: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        data[column.name] = (
            REDACTED
            if _should_redact_column(column.name) or _should_redact_value(value)
            else _jsonable(value)
        )
    return data


def _export_rows(db: Session, user_id: int, entry: RegistryEntry) -> list[dict[str, Any]]:
    query = entry.export_query or _direct_user_rows(entry.model)
    return [_row_to_dict(row) for row in query(db, user_id)]


def export_user_data(db: Session, user: User) -> dict[str, Any]:
    """Return a content-complete, secret-redacted export for one user."""
    payload = {
        "schema_version": "user_data_export_v2",
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "google_id": user.google_id,
            "google_first_name": user.google_first_name,
            "google_display_name": user.google_display_name,
            "timezone": user.timezone,
            "archetype_id": user.archetype_id,
            "terms_accepted_at": _jsonable(user.terms_accepted_at),
            "research_consent_at": _jsonable(user.research_consent_at),
            "onboarding_completed_at": _jsonable(user.onboarding_completed_at),
            "tutorial_completed_at": _jsonable(user.tutorial_completed_at),
            "tutorial_skipped_at": _jsonable(user.tutorial_skipped_at),
            "created_at": _jsonable(user.created_at),
        },
        "integration_state": {
            "google_calendar": {
                "connected": bool(user.google_refresh_token),
                "credential_exported": False,
            },
            "moodle_ics": {
                "connected": bool(user.moodle_ics_url),
                "credential_exported": False,
                "last_synced_at": _jsonable(user.moodle_last_synced_at),
                "disconnect_reason": user.moodle_disconnect_reason,
            },
            "moodle_ws": {
                "connected": bool(user.moodle_ws_token),
                "credential_exported": False,
                "last_synced_at": _jsonable(user.moodle_ws_last_synced_at),
                "disconnect_reason": user.moodle_ws_disconnect_reason,
                "moodle_userid_present": user.moodle_userid is not None,
                "base_url_present": bool(user.moodle_base_url),
            },
        },
        "governance_audit_policy": {
            "exported_in_this_file": False,
            "delete_policy": "append_only_redacted_security_governance_log",
            "reason": (
                "Security audit rows are governance-only and are controlled by "
                "the security audit retention contract, not behavioral export "
                "or clean-data pipelines."
            ),
        },
        "registry": registry_manifest(),
    }
    for entry in USER_DATA_REGISTRY:
        payload[entry.section] = _export_rows(db, user.user_id, entry)
    return payload


def _delete_exposure_children(db: Session, user_id: int) -> None:
    exposure_filter = (
        "SELECT exposure_id FROM exposure_decision_event WHERE user_id = :u"
    )
    db.execute(
        text(
            f"""
            DELETE FROM suppression_event
            WHERE exposure_id IN ({exposure_filter})
            """
        ),
        {"u": user_id},
    )
    db.execute(
        text(
            f"""
            DELETE FROM exposure_render_event
            WHERE exposure_id IN ({exposure_filter})
            """
        ),
        {"u": user_id},
    )


def purge_user_auxiliary_rows(db: Session, user_id: int) -> None:
    """Purge user-owned rows that are not retained research task/session rows."""
    _delete_exposure_children(db, user_id)

    # Break task/deadline references before purging deadline rows.
    db.execute(
        text(
            """
            UPDATE task
            SET deadline_id = NULL,
                llm_inferred_deadline_id = NULL
            WHERE user_id = :u
            """
        ),
        {"u": user_id},
    )

    # Delete child/direct rows before task/session/user rows.
    delete_order = [
        ExposureAckEvent,
        NotificationLifecycleEvent,
        ExposurePolicyEffectLog,
        ExposureDecisionEvent,
        Feedback,
        JarvisInvocation,
        ExternalEventOutcome,
        ArchetypeAssignment,
        EmailEngagementEvent,
        CalibrationNudgeEvent,
        ReflectionViewLog,
        PauseEvent,
        PausePredictionLog,
        ResumePredictionLog,
        TaskExecutionCorrection,
        TaskDeadlineOutcome,
        DeadlineCompletionEvent,
        Deadline,
    ]
    for model in delete_order:
        db.query(model).filter(model.user_id == user_id).delete(
            synchronize_session=False
        )


def anonymize_retained_task_session_rows(
    db: Session,
    *,
    user_id: int,
    retained_at: datetime,
    original_user_id_hash: str,
) -> None:
    """Retain timing rows for research while removing identifying task fields."""
    db.execute(
        text(
            """
            UPDATE task SET
                title = '[anonymized]',
                notes = NULL,
                description = NULL,
                notion_page_id = NULL,
                llm_deadline_candidates = NULL,
                llm_sub_items = NULL,
                llm_alternative_suggestion = NULL,
                post_deletion_retained_at = :now,
                original_user_id_hash = :hash
            WHERE user_id = :u
            """
        ),
        {"now": retained_at, "hash": original_user_id_hash, "u": user_id},
    )
    db.execute(
        text(
            """
            UPDATE stopwatch_session SET
                post_deletion_retained_at = :now,
                original_user_id_hash = :hash
            WHERE user_id = :u
            """
        ),
        {"now": retained_at, "hash": original_user_id_hash, "u": user_id},
    )


def hard_delete_retained_rows(db: Session, user_id: int) -> None:
    db.query(StopwatchSession).filter(StopwatchSession.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(Task).filter(Task.user_id == user_id).delete(synchronize_session=False)
