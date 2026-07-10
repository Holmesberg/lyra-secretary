"""Pause prediction service — VT-17 research instrument.

Two mechanisms (see MANIFESTO.md §VT-17 and docs/archive/legacy/planning/building_phases.md Tier 1.5):

  1. clock_anchor — hour-of-day × weekday-bucket median minute-of-hour. When
     historical pauses cluster near the same clock time, predict a pause will
     fire near that same minute today (if the user's current minute lines up
     with the required [MIN_LEAD_MINUTES, MAX_LEAD_MINUTES] lead window).

  2. work_rhythm — per-category median time from task executed_start to first
     pause. When the active task's category has a stable "I usually pause N
     minutes in" rhythm, project predicted_at = executed_start + N and fire if
     the lead lands in the same window.

Gating — a prediction is suppressed (None returned) unless ALL hold:
  * ≥ HISTORY_GATE_DAYS of pause_event history since the user's first row
    (Option A in the April 14 structural investigation — pre-accumulate data
    before the predictor is allowed to fire)
  * ≥ MIN_SAMPLES in the relevant bucket (clock_anchor: hour × weekend bucket;
    work_rhythm: category bucket)
  * predicted_at − now in [MIN_LEAD_MINUTES, MAX_LEAD_MINUTES]
  * confidence ≥ MIN_CONFIDENCE (calibrated to the VT-17 kill criterion:
    ≥0.40 acceptance_rate ships / <0.20 kills; the MIN_CONFIDENCE gate is not
    the kill criterion itself, it's a floor so we don't spam at pre-registered
    noise levels).

Tuning knobs are named constants so the operator notebook can surface how the
predictor's behavior changed across commits without grepping source code.

The predictor is pure read — it does not write to pause_prediction_log. The
scheduler job (commit 5) writes the firing row after calling predict() and
before pushing the telegram notification.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median, stdev
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import PauseEvent, StopwatchSession, Task
from app.services.exposure_ledger import is_exposed
from app.utils.time_utils import now_utc, strip_tz

HISTORY_GATE_DAYS = 7
MIN_SAMPLES = 5
LOOKBACK_DAYS = 28
MIN_LEAD_MINUTES = 2
MAX_LEAD_MINUTES = 3
# Floor for firing — below this we suppress. Not the VT-17 kill threshold
# (that's pre-registered against acceptance_rate in MANIFESTO §VT-17, not
# against confidence). Raising this reduces fire rate; lowering increases it.
MIN_CONFIDENCE = 0.40


@dataclass
class PausePrediction:
    user_id: int
    mechanism: str  # 'clock_anchor' | 'work_rhythm'
    fired_at: datetime
    predicted_at: datetime
    confidence: float
    lead_minutes: int
    sample_size: int
    active_task_id: Optional[str] = None


class PausePredictor:
    """Compute a PausePrediction or return None.

    Stateless over a request — one instance per scheduler tick is fine.
    All methods accept an explicit `now` so tests don't need to freeze time.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(
        self,
        user_id: int,
        active_task: Optional[Task],
        now: Optional[datetime] = None,
    ) -> Optional[PausePrediction]:
        """Run both mechanisms, return the highest-confidence candidate that
        passes all gates, or None."""
        if now is None:
            now = now_utc()

        if not self._has_sufficient_history(user_id, now=now):
            return None

        candidates = []
        anchor = self._clock_anchor(user_id, now, active_task)
        if anchor is not None:
            candidates.append(anchor)
        if active_task is not None:
            rhythm = self._work_rhythm(user_id, now, active_task)
            if rhythm is not None:
                candidates.append(rhythm)

        candidates = [c for c in candidates if c.confidence >= MIN_CONFIDENCE]
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.confidence)

    # ------------------------------------------------------------------
    # Gates
    # ------------------------------------------------------------------

    def _has_sufficient_history(self, user_id: int, now: datetime) -> bool:
        """Return True iff the user's earliest pause_event row is at least
        HISTORY_GATE_DAYS old. Pre-registered gate from the April 14
        structural investigation."""
        earliest = (
            self.db.query(func.min(PauseEvent.paused_at_utc))
            .filter(PauseEvent.user_id == user_id)
            .scalar()
        )
        if earliest is None:
            return False
        # strip_tz: Supabase TIMESTAMPTZ default returns aware
        span_days = (now - strip_tz(earliest)).total_seconds() / 86400.0
        return span_days >= HISTORY_GATE_DAYS

    # ------------------------------------------------------------------
    # Mechanisms
    # ------------------------------------------------------------------

    def _clock_anchor(
        self,
        user_id: int,
        now: datetime,
        active_task: Optional[Task],
    ) -> Optional[PausePrediction]:
        lookback = now - timedelta(days=LOOKBACK_DAYS)
        is_weekend = now.weekday() >= 5

        # Training-data integrity: retroactive self-reports (chip on
        # /today, 2026-04-22) attach paused_at_utc = predicted_at, i.e.
        # the value this same predictor emitted. Including them here
        # would self-reinforce existing predictions and prevent the
        # model from tracking drift in the operator's actual pause
        # timing. Retroactive rows stay in pause_event for VT-17d
        # stratified acceptance-rate analysis but are excluded from
        # training. See docs/archive/legacy/planning/feedback_loops_closure_plan.md §Loop 9
        # closure and MANIFESTO v1.9 §VT-17d.
        rows = (
            self.db.query(PauseEvent.paused_at_utc)
            .filter(
                PauseEvent.user_id == user_id,
                PauseEvent.paused_at_utc >= lookback,
                PauseEvent.paused_at_utc < now,
                PauseEvent.self_reported_retroactively.is_(False),
            )
            .all()
        )

        # Bucket: same hour-of-day AND same weekday/weekend class
        minutes_in_bucket = []
        for (paused_at,) in rows:
            paused_at = strip_tz(paused_at)
            if paused_at.hour != now.hour or (paused_at.weekday() >= 5) != is_weekend:
                continue
            if (
                is_exposed(
                    self.db,
                    user_id=user_id,
                    event_time=paused_at,
                    signal_target="pause_behavior",
                ).state
                != "NONE"
            ):
                continue
            minutes_in_bucket.append(paused_at.minute + paused_at.second / 60.0)
        if len(minutes_in_bucket) < MIN_SAMPLES:
            return None

        median_minute = median(minutes_in_bucket)
        predicted_at = now.replace(
            minute=int(median_minute),
            second=int(round((median_minute % 1) * 60)),
            microsecond=0,
        )
        # The bucket is hourly; if the median minute has already passed today
        # in this hour, the anchor doesn't fire (we don't roll to next hour —
        # the lead window would miss anyway).
        if predicted_at <= now:
            return None

        lead = (predicted_at - now).total_seconds() / 60.0
        if lead < MIN_LEAD_MINUTES or lead > MAX_LEAD_MINUTES:
            return None

        return _build(
            user_id=user_id,
            mechanism="clock_anchor",
            now=now,
            predicted_at=predicted_at,
            lead_minutes=lead,
            samples=minutes_in_bucket,
            active_task=active_task,
        )

    def _active_task_start(self, user_id: int, active_task: Task) -> Optional[datetime]:
        """Return the live session anchor for an active task.

        `Task.executed_start_utc` is finalized on stop, so an EXECUTING task
        can legitimately have a NULL executed_start while its open
        StopwatchSession carries the real live start. Pause prediction runs
        during the session, so it must use the open session anchor.
        """
        if active_task.executed_start_utc is not None:
            return strip_tz(active_task.executed_start_utc)

        session = (
            self.db.query(StopwatchSession.start_time_utc)
            .filter(
                StopwatchSession.user_id == user_id,
                StopwatchSession.task_id == active_task.task_id,
                StopwatchSession.end_time_utc.is_(None),
                StopwatchSession.auto_closed == False,  # noqa: E712
                StopwatchSession.data_quality_flag.is_(None),
            )
            .order_by(StopwatchSession.start_time_utc.desc())
            .first()
        )
        if session is None or session[0] is None:
            return None
        return strip_tz(session[0])

    def _work_rhythm(
        self,
        user_id: int,
        now: datetime,
        active_task: Task,
    ) -> Optional[PausePrediction]:
        active_start = self._active_task_start(user_id, active_task)
        if active_start is None or active_task.category is None:
            return None

        lookback = now - timedelta(days=LOOKBACK_DAYS)

        # Same training-data integrity rule as clock_anchor: exclude
        # retroactive self-reports so the work_rhythm medians track
        # real-time capture, not the predictor's own output.
        rows = (
            self.db.query(
                StopwatchSession.start_time_utc,
                func.min(PauseEvent.paused_at_utc).label("first_pause_at"),
            )
            .join(PauseEvent, PauseEvent.session_id == StopwatchSession.session_id)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(
                PauseEvent.self_reported_retroactively.is_(False),
                StopwatchSession.user_id == user_id,
                StopwatchSession.start_time_utc >= lookback,
                Task.category == active_task.category,
                # Use == False (not .is_(False)) so SQLite boolean 0/1 matches.
                StopwatchSession.auto_closed == False,  # noqa: E712
                Task.voided_at.is_(None),
                # Exclude sessions retrofitted as contaminated by the April 14 audit.
                StopwatchSession.data_quality_flag.is_(None),
            )
            .group_by(StopwatchSession.session_id, StopwatchSession.start_time_utc)
            .all()
        )

        deltas = []
        for (start, first_pause) in rows:
            if first_pause is None or start is None:
                continue
            first_pause = strip_tz(first_pause)
            if (
                is_exposed(
                    self.db,
                    user_id=user_id,
                    event_time=first_pause,
                    signal_target="pause_behavior",
                ).state
                != "NONE"
            ):
                continue
            deltas.append((first_pause - strip_tz(start)).total_seconds() / 60.0)
        if len(deltas) < MIN_SAMPLES:
            return None

        median_delta = median(deltas)
        predicted_at = active_start + timedelta(minutes=median_delta)
        if predicted_at <= now:
            return None

        lead = (predicted_at - now).total_seconds() / 60.0
        if lead < MIN_LEAD_MINUTES or lead > MAX_LEAD_MINUTES:
            return None

        return _build(
            user_id=user_id,
            mechanism="work_rhythm",
            now=now,
            predicted_at=predicted_at,
            lead_minutes=lead,
            samples=deltas,
            active_task=active_task,
        )


def _build(
    *,
    user_id: int,
    mechanism: str,
    now: datetime,
    predicted_at: datetime,
    lead_minutes: float,
    samples: list,
    active_task: Optional[Task],
) -> PausePrediction:
    """Compose a PausePrediction with a calibrated confidence.

    Confidence formula:
        base 0.30
      + 0.30 * min(n/15, 1.0)                   # sample-size term
      + 0.40 * max(0, 1 - stddev/30_minutes)    # dispersion term
      capped at 0.95.

    Bounded above to keep the notebook's per-mechanism calibration curves
    from flat-lining at 1.0 for large samples.
    """
    n = len(samples)
    try:
        dispersion = stdev(samples) if n > 1 else 0.0
    except Exception:
        dispersion = 0.0
    sample_factor = min(1.0, n / 15.0)
    dispersion_factor = max(0.0, 1.0 - dispersion / 30.0)
    confidence = min(0.95, 0.30 + 0.30 * sample_factor + 0.40 * dispersion_factor)

    return PausePrediction(
        user_id=user_id,
        mechanism=mechanism,
        fired_at=now,
        predicted_at=predicted_at,
        confidence=round(confidence, 3),
        lead_minutes=int(round(lead_minutes)),
        sample_size=n,
        active_task_id=active_task.task_id if active_task else None,
    )
