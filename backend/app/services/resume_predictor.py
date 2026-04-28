"""Resume prediction service (W2 magic-for-alpha 2026-04-28).

Sibling of `pause_predictor.py` for the *opposite* direction. The pause
predictor predicts WHEN a future pause will occur. The resume predictor
predicts WHEN AN ACTIVE PAUSE has gone on long enough that the user
typically resumes by now.

Mechanism (single — no clock_anchor sibling needed; resumes are inherently
session-anchored):
  - For the active task's (category, time_of_day_at_pause), compute the
    historical p75 of (resumed_at_utc - paused_at_utc) over the last
    LOOKBACK_DAYS.
  - If paused_for_minutes >= p75 → fire a banner.
  - Per-session 5min cooldown to avoid re-firing.

Cold-start fallback (operator decision 2026-04-28): when the
(category, time_of_day) cell has < MIN_SAMPLES OR the user has < 7d
pause history overall:
  - Use COLD_START_FLAT_CAP (30min) as the fire threshold
  - mechanism='cold_start_synthetic'
  - p75_pause_minutes = NULL on the log row
  - Banner copy: "Lyra hasn't seen enough yet — picking it up?"

Filters (mirror pause_predictor research-integrity discipline):
  - Exclude pause_event rows where self_reported_retroactively=TRUE
    (per VT-17d: retroactive pauses don't predict; using them as
    training data would self-reinforce)
  - Exclude pause_event rows where data_quality_flag IS NOT NULL

VT-17 sibling pre-registration footnote (per
docs/manifesto_alignment_audit_2026_04_28.md item #4): instrument-
intervention threats apply symmetrically (anchor drift, induced-resume
behavior). At n ≥ 30 firings per user, parallel VT-17a/b analysis with
pause→resume substitution. No new MANIFESTO rule yet (sample-size
threshold not crossed).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import PauseEvent, StopwatchSession, Task
from app.services.bias_factor_service import _time_of_day
from app.utils.time_utils import now_utc, to_local

HISTORY_GATE_DAYS = 7
MIN_SAMPLES = 5
LOOKBACK_DAYS = 28
COOLDOWN_MINUTES = 5
COLD_START_FLAT_CAP = 30  # minutes
MIN_CONFIDENCE = 0.40


@dataclass
class ResumePrediction:
    user_id: int
    session_id: str
    task_id: str
    fired_at: datetime
    paused_for_minutes: float
    p75_pause_minutes: Optional[float]
    mechanism: str  # 'category_tod' | 'cold_start_synthetic'
    confidence: float
    sample_size: int


class ResumePredictor:
    """Compute a ResumePrediction for an active paused session, or None.

    Stateless over a request — one instance per scheduler tick is fine.
    All methods accept an explicit `now` for testability.
    """

    def __init__(self, db: Session):
        self.db = db

    def predict(
        self,
        user_id: int,
        session: StopwatchSession,
        task: Task,
        paused_at_utc: datetime,
        now: Optional[datetime] = None,
    ) -> Optional[ResumePrediction]:
        """Run the predictor for a single active paused session. Returns
        None if not ready to fire, or a ResumePrediction if it is."""
        if now is None:
            now = now_utc()

        paused_for = (now - paused_at_utc).total_seconds() / 60.0
        if paused_for <= 0:
            return None

        # Cold-start path: insufficient history → 30min flat cap
        if not self._has_sufficient_history(user_id, now=now):
            return self._cold_start(
                user_id, session, task, paused_for, now
            )

        # Per-cell p75 over lookback window
        cell_pauses = self._collect_cell_pauses(
            user_id, task, paused_at_utc, now
        )
        n = len(cell_pauses)
        if n < MIN_SAMPLES:
            # Cell-level cold start → also fall back to flat cap
            return self._cold_start(user_id, session, task, paused_for, now)

        p75 = _percentile(cell_pauses, 0.75)
        if paused_for < p75:
            return None  # not yet at the historical median dwell

        # Confidence rises with sample size; saturates at n=30
        confidence = min(1.0, MIN_CONFIDENCE + 0.02 * n)
        if confidence < MIN_CONFIDENCE:
            return None

        return ResumePrediction(
            user_id=user_id,
            session_id=session.session_id,
            task_id=task.task_id,
            fired_at=now,
            paused_for_minutes=round(paused_for, 1),
            p75_pause_minutes=round(p75, 1),
            mechanism="category_tod",
            confidence=round(confidence, 3),
            sample_size=n,
        )

    # ── helpers ───────────────────────────────────────────────────────

    def _cold_start(
        self,
        user_id: int,
        session: StopwatchSession,
        task: Task,
        paused_for: float,
        now: datetime,
    ) -> Optional[ResumePrediction]:
        if paused_for < COLD_START_FLAT_CAP:
            return None
        return ResumePrediction(
            user_id=user_id,
            session_id=session.session_id,
            task_id=task.task_id,
            fired_at=now,
            paused_for_minutes=round(paused_for, 1),
            p75_pause_minutes=None,
            mechanism="cold_start_synthetic",
            confidence=MIN_CONFIDENCE,  # explicit: floor-only, no signal
            sample_size=0,
        )

    def _has_sufficient_history(self, user_id: int, now: datetime) -> bool:
        earliest = (
            self.db.query(func.min(PauseEvent.paused_at_utc))
            .filter(
                PauseEvent.user_id == user_id,
                PauseEvent.self_reported_retroactively.is_(False),
            )
            .scalar()
        )
        if earliest is None:
            return False
        return (now - earliest).days >= HISTORY_GATE_DAYS

    def _collect_cell_pauses(
        self,
        user_id: int,
        active_task: Task,
        paused_at_utc: datetime,
        now: datetime,
    ) -> list[float]:
        """Pull pause durations matching the active task's (category, tod)
        cell over the last LOOKBACK_DAYS. Excludes retroactive pauses (per
        VT-17d), data-quality-flagged sessions, voided tasks, and unresumed
        pauses. PauseEvent has session_id but not task_id, so join via
        StopwatchSession → Task."""
        target_tod = _time_of_day(to_local(paused_at_utc))
        target_category = active_task.category
        cutoff = now - timedelta(days=LOOKBACK_DAYS)

        rows = (
            self.db.query(PauseEvent, Task)
            .join(StopwatchSession, StopwatchSession.session_id == PauseEvent.session_id)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(
                PauseEvent.user_id == user_id,
                PauseEvent.self_reported_retroactively.is_(False),
                StopwatchSession.data_quality_flag.is_(None),
                PauseEvent.resumed_at_utc.isnot(None),
                PauseEvent.paused_at_utc >= cutoff,
                Task.voided_at.is_(None),
            )
            .all()
        )

        durations: list[float] = []
        for pe, t in rows:
            if t.category != target_category:
                continue
            if _time_of_day(to_local(pe.paused_at_utc)) != target_tod:
                continue
            d = (pe.resumed_at_utc - pe.paused_at_utc).total_seconds() / 60.0
            if d > 0:
                durations.append(d)
        return durations


def _percentile(values: list[float], p: float) -> float:
    """Simple p75 (or any percentile) on a list. No numpy dependency.
    Returns 0.0 on empty input — caller should already have gated on
    MIN_SAMPLES so this branch is defensive."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_v) - 1)
    if f == c:
        return sorted_v[f]
    return sorted_v[f] + (sorted_v[c] - sorted_v[f]) * (k - f)
