"""Runtime contract for registered output surfaces."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import ReflectionViewLog, User
from app.services.exposure_ledger import record_decision, record_render, record_suppression
from app.utils.time_utils import now_utc, strip_tz


@dataclass(frozen=True)
class OutputSurfaceSpec:
    surface_id: str
    truth_class: str
    usage_class: str
    channel: str
    exposure_category: str
    signal_targets: tuple[str, ...]
    clean_profile: Optional[str]
    min_n: int
    time_window_days: Optional[int]
    fallback_mode: str
    operator_only: bool
    legacy_adapter: Optional[str]
    render_policy_version: str
    interruptiveness: str
    salience_level: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "truth_class": self.truth_class,
            "usage_class": self.usage_class,
            "channel": self.channel,
            "exposure_category": self.exposure_category,
            "signal_targets": list(self.signal_targets),
            "clean_profile": self.clean_profile,
            "min_n": self.min_n,
            "time_window_days": self.time_window_days,
            "fallback_mode": self.fallback_mode,
            "operator_only": self.operator_only,
            "legacy_adapter": self.legacy_adapter,
            "render_policy_version": self.render_policy_version,
            "interruptiveness": self.interruptiveness,
            "salience_level": self.salience_level,
        }


@lru_cache(maxsize=1)
def load_output_surface_registry() -> dict[str, OutputSurfaceSpec]:
    path = Path(__file__).resolve().parents[1] / "core" / "output_surface_registry.json"
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    surfaces: dict[str, OutputSurfaceSpec] = {}
    for surface_id, row in payload["surfaces"].items():
        surfaces[surface_id] = OutputSurfaceSpec(
            surface_id=surface_id,
            truth_class=row["truth_class"],
            usage_class=row["usage_class"],
            channel=row["channel"],
            exposure_category=row["exposure_category"],
            signal_targets=tuple(row["signal_targets"]),
            clean_profile=row.get("clean_profile"),
            min_n=int(row["min_n"]),
            time_window_days=row.get("time_window_days"),
            fallback_mode=row["fallback_mode"],
            operator_only=bool(row["operator_only"]),
            legacy_adapter=row.get("legacy_adapter"),
            render_policy_version=row["render_policy_version"],
            interruptiveness=row["interruptiveness"],
            salience_level=row["salience_level"],
        )
    return surfaces


def get_output_surface_spec(surface_id: str) -> OutputSurfaceSpec:
    try:
        return load_output_surface_registry()[surface_id]
    except KeyError as exc:
        raise ValueError(f"unregistered_output_surface:{surface_id}") from exc


def registered_surface_ids() -> list[str]:
    return sorted(load_output_surface_registry().keys())


def _snapshot_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, default=str)


def _assert_surface_allowed_for_user(
    db: Session,
    *,
    spec: OutputSurfaceSpec,
    user_id: int,
) -> None:
    if not spec.operator_only:
        return

    is_operator = (
        db.query(User.is_operator)
        .filter(User.user_id == user_id)
        .scalar()
    )
    if not is_operator:
        raise PermissionError(f"operator_only_output_surface:{spec.surface_id}")


def emit_surface_render(
    db: Session,
    *,
    surface_id: str,
    user_id: int,
    content_snapshot: Any,
    task_id: Optional[str] = None,
    eligible_at=None,
    rendered_at=None,
    content_template_id: Optional[str] = None,
    initiative: str = "system",
    trigger_source: Optional[str] = None,
    generating_model: Optional[str] = None,
    generating_version: Optional[str] = None,
    prompt_hash: Optional[str] = None,
    data_snapshot_hash: Optional[str] = None,
    randomization_arm: str = "none",
    randomization_policy_version: Optional[str] = None,
    delivered_at=None,
    create_legacy_view: bool = False,
    legacy_payload: Optional[Any] = None,
    legacy_viewed_at=None,
    legacy_dismissed_at=None,
    legacy_dwell_seconds: Optional[int] = None,
    legacy_outcome: Optional[str] = None,
) -> dict[str, Any]:
    spec = get_output_surface_spec(surface_id)
    _assert_surface_allowed_for_user(db, spec=spec, user_id=user_id)
    eligible_at = strip_tz(eligible_at or now_utc())
    rendered_at = strip_tz(rendered_at or eligible_at)
    content_snapshot_text = _snapshot_to_text(content_snapshot)
    decision = record_decision(
        db,
        user_id=user_id,
        task_id=task_id,
        eligible_at=eligible_at,
        decision_status="rendered",
        initiative=initiative,
        exposure_category=spec.exposure_category,
        content_template_id=content_template_id,
        trigger_source=trigger_source or surface_id,
        generating_model=generating_model,
        generating_version=generating_version,
        prompt_hash=prompt_hash,
        data_snapshot_hash=data_snapshot_hash,
        randomization_arm=randomization_arm,
        randomization_policy_version=randomization_policy_version,
        delivered_at=strip_tz(delivered_at) if delivered_at is not None else rendered_at,
    )
    render = record_render(
        db,
        exposure_id=decision.exposure_id,
        rendered_at=rendered_at,
        surface=surface_id,
        channel=spec.channel,
        content_snapshot=content_snapshot_text,
        render_policy_version=spec.render_policy_version,
        interruptiveness=spec.interruptiveness,
        salience_level=spec.salience_level,
    )

    legacy_view_id: Optional[str] = None
    if create_legacy_view and spec.legacy_adapter:
        row = ReflectionViewLog(
            view_id=str(uuid4()),
            user_id=user_id,
            reflection_type=spec.legacy_adapter,
            event_class="impression",
            task_id=task_id,
            payload=_snapshot_to_text(legacy_payload) if legacy_payload is not None else content_snapshot_text,
            fired_at=rendered_at,
            viewed_at=strip_tz(legacy_viewed_at),
            dismissed_at=strip_tz(legacy_dismissed_at),
            dwell_seconds=legacy_dwell_seconds,
            outcome=legacy_outcome,
        )
        db.add(row)
        db.flush()
        legacy_view_id = row.view_id

    return {
        "surface_id": surface_id,
        "truth_class": spec.truth_class,
        "usage_class": spec.usage_class,
        "clean_profile": spec.clean_profile,
        "fallback_mode": spec.fallback_mode,
        "legacy_adapter": spec.legacy_adapter,
        "signal_targets": list(spec.signal_targets),
        "exposure_id": decision.exposure_id,
        "render_id": render.render_id,
        "legacy_view_id": legacy_view_id,
    }


def emit_surface_suppression(
    db: Session,
    *,
    surface_id: str,
    user_id: int,
    suppression_reason: str,
    task_id: Optional[str] = None,
    eligible_at=None,
    suppressed_at=None,
    content_template_id: Optional[str] = None,
    initiative: str = "system",
    trigger_source: Optional[str] = None,
    generating_confidence: Optional[float] = None,
) -> dict[str, Any]:
    spec = get_output_surface_spec(surface_id)
    _assert_surface_allowed_for_user(db, spec=spec, user_id=user_id)
    eligible_at = strip_tz(eligible_at or now_utc())
    suppressed_at = strip_tz(suppressed_at or eligible_at)
    decision = record_decision(
        db,
        user_id=user_id,
        task_id=task_id,
        eligible_at=eligible_at,
        decision_status="suppressed",
        initiative=initiative,
        exposure_category=spec.exposure_category,
        content_template_id=content_template_id,
        trigger_source=trigger_source or surface_id,
        delivered_at=None,
    )
    suppression = record_suppression(
        db,
        exposure_id=decision.exposure_id,
        suppressed_at=suppressed_at,
        suppression_reason=suppression_reason,
        would_have_rendered_template_id=content_template_id,
        generating_confidence=generating_confidence,
    )
    return {
        "surface_id": surface_id,
        "truth_class": spec.truth_class,
        "usage_class": spec.usage_class,
        "clean_profile": spec.clean_profile,
        "fallback_mode": spec.fallback_mode,
        "legacy_adapter": spec.legacy_adapter,
        "signal_targets": list(spec.signal_targets),
        "exposure_id": decision.exposure_id,
        "suppression_id": suppression.suppression_id,
        "suppressed_reason": suppression_reason,
    }
