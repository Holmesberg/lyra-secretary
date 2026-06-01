"""
Tests for LYR-061: Insights must not fire on noise data.
- _insight_discrepancy_signal() must return None when no real signal
- Global gate must block insights below MIN_SESSIONS
"""
import json
from unittest.mock import MagicMock
from uuid import uuid4

from app.db.models import (
    ExposureDecisionEvent,
    ExposureRenderEvent,
    StopwatchSession,
    SuppressionEvent,
    Task,
    TaskState,
    User,
)
from app.api.v1.endpoints import analytics as analytics_module
from app.api.v1.endpoints.analytics import (
    _insight_abandonment,
    _insight_best_category,
    PRIMARY_SYNTHESIS_ID,
    _insight_discrepancy_signal,
    _insight_occupancy_footprint,
    _insight_pause_pattern,
    _insight_readiness,
    _insight_readiness_time_of_day,
    _insight_time_of_day,
    _insight_worst_category,
)
from app.utils.time_utils import now_utc
from tests.conftest import auth_headers
from datetime import timedelta


def _task(
    delta=None,
    disc_score=None,
    pre=None,
    post=None,
    state=TaskState.EXECUTED,
    tod_hour=9,
    category="study",
    initiation_status="started",
    pause_count=0,
    pause_overhead=0,
    session_span=60,
):
    t = MagicMock(spec=Task)
    t.state = state
    t.duration_delta_minutes = delta
    t.discrepancy_score = disc_score
    t.pre_task_readiness = pre
    t.post_task_reflection = post
    t.planned_start_utc = (now_utc() - timedelta(days=1)).replace(
        hour=tod_hour,
        minute=0,
        second=0,
    )
    t.executed_end_utc = t.planned_start_utc + timedelta(minutes=60)
    t.executed_duration_minutes = 60 if delta is not None else None
    t.category = category
    t.initiation_status = initiation_status
    t.pause_count = pause_count
    t.is_anchor = False
    session = MagicMock(spec=StopwatchSession)
    session.start_time_utc = t.planned_start_utc
    session.end_time_utc = t.planned_start_utc + timedelta(minutes=session_span)
    session.total_paused_minutes = pause_overhead
    session.auto_closed = False
    session.data_quality_flag = None
    t.stopwatch_sessions = [session]
    return t


def test_public_insight_translator_allowlists_fields():
    public = analytics_module._public_insight(
        {
            "id": "primary_synthesis",
            "observation": "Planning drift is clustering.",
            "data_points": 30,
            "confidence": "high",
            "strength": 52.0,
            "seen": True,
            "surface_id": "analytics.insights.primary_synthesis",
            "truth_class": "interpretation",
            "usage_class": "product",
            "clean_profile": "planning_calibration",
            "eligible_sample_count": 30,
            "min_n_required": 3,
            "authority_rung": "interpretation",
            "mutation_permission": "none",
            "public_translator": "registered_surface_translator",
            "internal_debug": "must not leak",
            "_facts": {"raw": "nope"},
            "_audit": {"evidence_packet_ids": ["evpkt_x"]},
        }
    )

    assert public["id"] == "primary_synthesis"
    assert public["title"] == "Primary pattern"
    assert public["body"] == "Planning drift is clustering."
    assert public["observation"] == public["body"]
    assert public["authority_label"] == "Interpretation"
    assert public["confidence_label"] == "High confidence"
    assert "internal_debug" not in public
    assert "_facts" not in public
    assert "_audit" not in public


def test_discrepancy_signal_returns_none_when_no_signal():
    """No 20% spread between high/low discrepancy buckets → None, not a noise message."""
    tasks = (
        [_task(delta=10, disc_score=4) for _ in range(3)] +
        [_task(delta=12, disc_score=0) for _ in range(3)]
    )
    result = _insight_discrepancy_signal(tasks)
    assert result is None


def test_discrepancy_signal_fires_when_real_signal():
    """High discrepancy sessions have significantly more error → insight fires."""
    tasks = (
        [_task(delta=50, disc_score=4) for _ in range(3)] +   # high disc, big error
        [_task(delta=5,  disc_score=0) for _ in range(3)]     # low disc, small error
    )
    result = _insight_discrepancy_signal(tasks)
    assert result is not None
    assert "higher" in result["observation"]


def test_discrepancy_signal_needs_min_3_per_bucket():
    """Returns None if either bucket has fewer than 3 sessions."""
    tasks = (
        [_task(delta=50, disc_score=4) for _ in range(2)] +
        [_task(delta=5,  disc_score=0) for _ in range(3)]
    )
    result = _insight_discrepancy_signal(tasks)
    assert result is None


def test_time_of_day_requires_3_sessions():
    """Should not fire with only 2 sessions in a time-of-day bucket."""
    tasks = [_task(delta=30, tod_hour=9), _task(delta=25, tod_hour=9)]
    result = _insight_time_of_day(tasks)
    assert result is None


def test_rewritten_insight_copy_avoids_identity_language():
    readiness = _insight_readiness(
        [_task(delta=-5, pre=2) for _ in range(3)]
        + [_task(delta=-40, pre=5) for _ in range(3)]
    )
    assert readiness is not None
    assert "ability claim" in readiness["observation"]
    assert "outperform" not in readiness["observation"]

    abandonment = _insight_abandonment(
        [_task(state=TaskState.SKIPPED, initiation_status="abandoned", tod_hour=22) for _ in range(5)]
    )
    assert abandonment is not None
    assert "were not started" in abandonment["observation"]
    assert "abandon" not in abandonment["observation"].lower()

    pause = _insight_pause_pattern(
        [_task(pause_count=2) for _ in range(3)]
        + [_task(pause_count=0) for _ in range(2)]
    )
    assert pause is not None
    assert "Recorded pauses" in pause["observation"]
    assert "interruptions" not in pause["observation"]


def test_readiness_time_of_day_insight_is_bounded_planning_context():
    result = _insight_readiness_time_of_day(
        [_task(delta=-5, pre=5, tod_hour=6) for _ in range(3)]
        + [_task(delta=-40, pre=2, tod_hour=16) for _ in range(3)]
    )

    assert result is not None
    assert result["id"] == "readiness_time_of_day"
    observation = result["observation"].lower()
    assert "rated sessions" in observation
    assert "planning-context signal" in observation
    assert "ability or identity claim" in observation
    assert "cognitive" not in observation
    assert "functional" not in observation
    assert "focus" not in observation
    assert "mastery" not in observation


def test_occupancy_footprint_uses_neutral_downstream_language():
    result = _insight_occupancy_footprint(
        [
            _task(delta=-10, pause_overhead=20, session_span=80)
            for _ in range(5)
        ]
    )

    assert result is not None
    assert result["id"] == "occupancy_footprint"
    observation = result["observation"].lower()
    assert "active work" in observation
    assert "pause overhead" in observation
    assert "planning-window guidance" in observation
    for banned in ("avoid", "focus", "motivation", "identity"):
        assert banned not in observation


def test_occupancy_footprint_suppresses_without_meaningful_overhead():
    result = _insight_occupancy_footprint(
        [
            _task(delta=0, pause_overhead=5, session_span=65)
            for _ in range(5)
        ]
    )

    assert result is None


def test_category_insights_require_multiple_categories():
    tasks = [_task(delta=-30, category="academic") for _ in range(4)]
    assert _insight_best_category(tasks) is None
    assert _insight_worst_category(tasks) is None


def test_category_insights_quarantine_legacy_work_bucket():
    tasks = (
        [_task(delta=-2, category="work") for _ in range(5)]
        + [_task(delta=-35, category="study") for _ in range(5)]
        + [_task(delta=-80, category="academic") for _ in range(5)]
    )

    best = _insight_best_category(tasks)
    worst = _insight_worst_category(tasks)

    assert best is not None
    assert "work tasks" not in best["observation"]
    assert "study tasks" in best["observation"]
    assert worst is not None
    assert "work tasks" not in worst["observation"]
    assert "academic tasks" in worst["observation"]


def test_category_insights_suppress_when_only_legacy_work_and_one_clean_category():
    tasks = (
        [_task(delta=-2, category="work") for _ in range(5)]
        + [_task(delta=-35, category="study") for _ in range(5)]
    )

    assert _insight_best_category(tasks) is None
    assert _insight_worst_category(tasks) is None


def _db_task(
    *,
    user_id: int,
    planned_start,
    executed_duration: int = 65,
    planned_duration: int = 60,
    initiation_delay: int = 10,
    initiation_status: str = "started",
    category: str = "study",
) -> Task:
    executed_start = planned_start + timedelta(minutes=initiation_delay)
    return Task(
        title=f"Task {uuid4()}",
        user_id=user_id,
        category=category,
        planned_start_utc=planned_start,
        planned_end_utc=planned_start + timedelta(minutes=planned_duration),
        planned_duration_minutes=planned_duration,
        executed_start_utc=executed_start,
        executed_end_utc=executed_start + timedelta(minutes=executed_duration),
        executed_duration_minutes=executed_duration,
        state=TaskState.EXECUTED,
        initiation_status=initiation_status,
        initiation_delay_minutes=initiation_delay,
        created_at=planned_start - timedelta(days=1),
    )


class _FakeRedis:
    def __init__(self):
        self.client = self
        self.keys: set[str] = set()
        self.setex_calls: list[tuple[str, int, str]] = []

    def exists(self, key, *_args, **_kwargs):
        return key in self.keys

    def sismember(self, *_args, **_kwargs):
        return False

    def sadd(self, *_args, **_kwargs):
        return None

    def expire(self, *_args, **_kwargs):
        return None

    def setex(self, key, ttl, value):
        self.keys.add(key)
        self.setex_calls.append((key, ttl, value))
        return None


def _db_planned_not_started_task(
    *,
    user_id: int,
    planned_start,
    category: str = "study",
) -> Task:
    return Task(
        title=f"Task {uuid4()}",
        user_id=user_id,
        category=category,
        planned_start_utc=planned_start,
        planned_end_utc=planned_start + timedelta(minutes=60),
        planned_duration_minutes=60,
        state=TaskState.SKIPPED,
        initiation_status="abandoned",
        created_at=planned_start - timedelta(days=1),
    )


def test_insights_endpoint_only_returns_contract_safe_generators(
    db, client, monkeypatch
):
    user = User(email=f"insights-wave3-{uuid4()}@example.com")
    db.add(user)
    db.flush()

    base = now_utc() - timedelta(days=20)
    tasks = []
    for i in range(5):
        tasks.append(
            _db_task(
                user_id=user.user_id,
                planned_start=base + timedelta(days=i),
                executed_duration=90,
            )
        )
    for i in range(5, 10):
        tasks.append(
            _db_task(
                user_id=user.user_id,
                planned_start=base + timedelta(days=i),
                executed_duration=65,
            )
        )
    db.add_all(tasks)
    db.commit()

    monkeypatch.setattr(
        analytics_module,
        "_eligible_tasks_for_surface",
        lambda _db, tasks, _surface_id: tasks,
    )
    fake_redis = _FakeRedis()
    monkeypatch.setattr(analytics_module, "RedisClient", lambda: fake_redis)

    response = client.get(
        "/v1/analytics/insights?auto_mark=true",
        headers=auth_headers(user.user_id),
    )
    assert response.status_code == 200
    payload = response.json()

    ids = {insight["id"] for insight in payload["insights"]}
    assert "estimation_accuracy_trend" in ids
    assert "initiation_delay" in ids
    assert "time_of_day_bias" in ids
    assert ids <= {
        "estimation_accuracy_trend",
        "primary_synthesis",
        "initiation_delay",
        "retroactive_rate",
        "time_of_day_bias",
        "readiness_predicts_outcome",
        "readiness_time_of_day",
        "abandonment_pattern",
        "best_category",
        "worst_category",
        "discrepancy_signal",
        "pause_pattern",
        "occupancy_footprint",
        "morning_anchor_cascade",
        "archetype_divergence",
        "calibration_maturation",
    }
    assert payload["surface_id"] == "analytics.insights"
    assert payload["truth_class"] == "interpretation"
    assert payload["clean_profile"] == "planning_calibration"
    assert payload["eligible_sample_count"] == 10
    assert all(
        key.startswith(f"insight_shown:{user.user_id}:")
        for key, _ttl, _value in fake_redis.setex_calls
    )

    suppressed = {
        row["id"]: row
        for row in payload["suppressed_generators"]
    }
    assert suppressed == {}

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(
            ExposureDecisionEvent.user_id == user.user_id,
            ExposureDecisionEvent.trigger_source == "analytics.insights",
        )
        .order_by(ExposureDecisionEvent.eligible_at.desc())
        .first()
    )
    assert decision is not None
    assert decision.decision_status == "rendered"


def test_insights_endpoint_primary_synthesis_preserves_source_cards_when_supported(
    db, client, monkeypatch
):
    user = User(email=f"insights-primary-synthesis-{uuid4()}@example.com")
    db.add(user)
    db.flush()

    base = (now_utc() - timedelta(days=60)).replace(hour=19, minute=0, second=0)
    tasks = []
    skipped_hours = [6, 13, 18, 22]
    for i in range(12):
        skipped_start = (base + timedelta(days=i)).replace(
            hour=skipped_hours[i % len(skipped_hours)]
        )
        tasks.append(
            _db_planned_not_started_task(
                user_id=user.user_id,
                planned_start=skipped_start,
                category="study",
            )
        )
    for i in range(12, 30):
        tasks.append(
            _db_task(
                user_id=user.user_id,
                planned_start=base + timedelta(days=i),
                planned_duration=60,
                executed_duration=110,
                initiation_delay=12,
                category="study",
            )
        )
    db.add_all(tasks)
    db.commit()

    monkeypatch.setattr(
        analytics_module,
        "_eligible_tasks_for_surface",
        lambda _db, tasks, _surface_id: tasks,
    )
    monkeypatch.setattr(analytics_module, "RedisClient", lambda: _FakeRedis())

    response = client.get(
        "/v1/analytics/insights",
        headers=auth_headers(user.user_id),
    )
    assert response.status_code == 200
    payload = response.json()
    ids = [insight["id"] for insight in payload["insights"]]

    assert PRIMARY_SYNTHESIS_ID in ids
    assert "abandonment_pattern" in ids
    assert ids.index(PRIMARY_SYNTHESIS_ID) < ids.index("abandonment_pattern")
    primary = next(
        insight for insight in payload["insights"]
        if insight["id"] == PRIMARY_SYNTHESIS_ID
    )
    assert primary["surface_id"] == "analytics.insights.primary_synthesis"
    assert primary["truth_class"] == "interpretation"
    assert "study tasks" in primary["observation"]
    assert "late-day execution" in primary["observation"]
    assert "should" not in primary["observation"].lower()
    assert "optimal" not in primary["observation"].lower()
    assert "_facts" not in primary

    evidence_sources = {
        item["source_insight_id"]
        for item in primary["evidence"]
    }
    assert "abandonment_pattern" in evidence_sources
    assert "time_of_day_bias" in evidence_sources

    render = (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.render_id == payload["render_id"])
        .one()
    )
    assert "study tasks" not in render.content_snapshot
    assert "late-day execution" not in render.content_snapshot
    assert "_audit" not in render.content_snapshot
    assert "_facts" not in render.content_snapshot
    snapshot = json.loads(render.content_snapshot)
    assert snapshot["schema_version"] == "analytics_insights_exposure_snapshot_v1"
    assert snapshot["insight_count"] == len(payload["insights"])
    assert snapshot["insight_ids"] == ids
    audit_by_id = {
        envelope["insight_id"]: envelope
        for envelope in snapshot["audit_envelopes"]
    }
    assert PRIMARY_SYNTHESIS_ID in audit_by_id
    primary_audit = audit_by_id[PRIMARY_SYNTHESIS_ID]
    assert primary_audit["evidence_packet_ids"]
    assert primary_audit["source_refs"]
    assert primary_audit["admissibility"]["packet_count"] >= 2


def test_insights_endpoint_scopes_before_sample_gate_and_reports_suppression(
    db, client, monkeypatch
):
    user = User(email=f"insights-scope-{uuid4()}@example.com")
    other = User(email=f"insights-other-{uuid4()}@example.com")
    db.add_all([user, other])
    db.flush()

    base = now_utc() - timedelta(days=20)
    db.add(
        _db_task(
            user_id=user.user_id,
            planned_start=base,
            executed_duration=65,
        )
    )
    for i in range(10):
        db.add(
            _db_task(
                user_id=other.user_id,
                planned_start=base + timedelta(days=i),
                executed_duration=90,
            )
        )
    db.commit()

    monkeypatch.setattr(
        analytics_module,
        "_eligible_tasks_for_surface",
        lambda _db, tasks, _surface_id: tasks,
    )

    response = client.get(
        "/v1/analytics/insights",
        headers=auth_headers(user.user_id),
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["ready"] is False
    assert payload["sessions_analyzed"] == 1
    assert payload["eligible_sample_count"] == 1
    assert payload["suppressed_reason"] == "insufficient_clean_samples"
    assert payload["suppressed_generators"] == []

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(
            ExposureDecisionEvent.user_id == user.user_id,
            ExposureDecisionEvent.trigger_source == "analytics.insights",
        )
        .order_by(ExposureDecisionEvent.eligible_at.desc())
        .first()
    )
    assert decision is not None
    assert decision.decision_status == "suppressed"
    suppression = (
        db.query(SuppressionEvent)
        .filter(SuppressionEvent.exposure_id == decision.exposure_id)
        .one()
    )
    assert suppression.suppression_reason == "insufficient_clean_samples"


def test_insights_endpoint_can_render_planning_history_without_executed_sessions(
    db, client, monkeypatch
):
    user = User(email=f"insights-planning-history-{uuid4()}@example.com")
    db.add(user)
    db.flush()

    base = (now_utc() - timedelta(days=10)).replace(hour=22, minute=0, second=0)
    db.add_all(
        [
            _db_planned_not_started_task(
                user_id=user.user_id,
                planned_start=base + timedelta(days=i),
                category="study",
            )
            for i in range(6)
        ]
    )
    db.commit()

    monkeypatch.setattr(
        analytics_module,
        "_eligible_tasks_for_surface",
        lambda _db, tasks, _surface_id: tasks,
    )
    monkeypatch.setattr(analytics_module, "RedisClient", lambda: _FakeRedis())

    response = client.get(
        "/v1/analytics/insights",
        headers=auth_headers(user.user_id),
    )
    assert response.status_code == 200
    payload = response.json()

    ids = {insight["id"] for insight in payload["insights"]}
    assert payload["ready"] is True
    assert payload["sessions_analyzed"] == 0
    assert payload["history_events_analyzed"] == 6
    assert PRIMARY_SYNTHESIS_ID not in ids
    assert "abandonment_pattern" in ids
    abandonment = next(
        insight for insight in payload["insights"]
        if insight["id"] == "abandonment_pattern"
    )
    assert abandonment["truth_class"] == "interpretation"
    assert "were not started" in abandonment["observation"]
