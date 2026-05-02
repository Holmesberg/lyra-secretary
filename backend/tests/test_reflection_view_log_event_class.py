"""Tests for reflection_view_log.event_class column (alembic 045, Phase 1.5).

Per docs/calibration_contract.md R7.1, event_class is promoted from JSON payload
to top-level NOT NULL column with btree index. This avoids the
NOT LIKE 'telemetry_%' sequential-scan when Phase 6 telemetry volume grows.

Covers:
- Default 'impression' applied on insert when event_class not specified
- Explicit 'telemetry' value persists correctly
- The btree index exists on event_class
- Existing impression-only queries (forward-port pattern: WHERE event_class =
  'impression') return same rows as the legacy NOT LIKE pattern would
- Cold-start: ReflectionViewLog with no rows still queryable correctly
"""
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import inspect, text

from app.db.models import ReflectionViewLog


def test_event_class_defaults_to_impression(db):
    """A row inserted without event_class gets DEFAULT 'impression'."""
    row = ReflectionViewLog(
        view_id=str(uuid4()),
        user_id=1,
        reflection_type="micro_mirror",
        payload="Test mirror text",
        fired_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    assert row.event_class == "impression"


def test_event_class_explicit_telemetry(db):
    """A row inserted with event_class='telemetry' persists that value."""
    row = ReflectionViewLog(
        view_id=str(uuid4()),
        user_id=1,
        reflection_type="telemetry_pause_hesitation",
        event_class="telemetry",
        payload='{"hesitation_seconds": 3.2, "schema_version": 1}',
        fired_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    assert row.event_class == "telemetry"


def test_event_class_index_exists(db):
    """idx_reflection_view_event_class btree index is registered on the table."""
    inspector = inspect(db.bind)
    indexes = inspector.get_indexes("reflection_view_log")
    index_names = {idx["name"] for idx in indexes}

    assert "idx_reflection_view_event_class" in index_names, (
        f"Expected idx_reflection_view_event_class in {index_names}"
    )

    # Verify the index covers the event_class column.
    matching = [idx for idx in indexes if idx["name"] == "idx_reflection_view_event_class"]
    assert matching, "Index entry missing"
    assert "event_class" in matching[0]["column_names"]


def test_impression_filter_query(db):
    """WHERE event_class = 'impression' returns only impression rows.

    Forward-port pattern: this is what existing VT-21 stratified-analysis queries
    will use post-Phase-6 instead of NOT LIKE 'telemetry_%'.

    Uses a unique user_id (99001) to isolate from other tests' rows since the
    conftest in-memory DB is shared across the file.
    """
    iso_user_id = 99001
    base_at = datetime.utcnow()
    rows = [
        ReflectionViewLog(
            view_id=str(uuid4()),
            user_id=iso_user_id,
            reflection_type="micro_mirror",
            payload="impression 1",
            fired_at=base_at,
        ),
        ReflectionViewLog(
            view_id=str(uuid4()),
            user_id=iso_user_id,
            reflection_type="calibration_nudge",
            payload="impression 2",
            fired_at=base_at + timedelta(minutes=1),
        ),
        ReflectionViewLog(
            view_id=str(uuid4()),
            user_id=iso_user_id,
            reflection_type="telemetry_modal_dwell",
            event_class="telemetry",
            payload='{"dwell_ms": 4200, "schema_version": 1}',
            fired_at=base_at + timedelta(minutes=2),
        ),
    ]
    for row in rows:
        db.add(row)
    db.commit()

    impressions = (
        db.query(ReflectionViewLog)
        .filter(
            ReflectionViewLog.user_id == iso_user_id,
            ReflectionViewLog.event_class == "impression",
        )
        .all()
    )
    assert len(impressions) == 2
    assert {r.reflection_type for r in impressions} == {"micro_mirror", "calibration_nudge"}

    telemetry = (
        db.query(ReflectionViewLog)
        .filter(
            ReflectionViewLog.user_id == iso_user_id,
            ReflectionViewLog.event_class == "telemetry",
        )
        .all()
    )
    assert len(telemetry) == 1
    assert telemetry[0].reflection_type == "telemetry_modal_dwell"


def test_event_class_not_nullable(db):
    """event_class column is NOT NULL — ORM-level default fires on omission."""
    inspector = inspect(db.bind)
    columns = {col["name"]: col for col in inspector.get_columns("reflection_view_log")}

    assert "event_class" in columns, "event_class column missing from schema"
    assert columns["event_class"]["nullable"] is False


def test_empty_table_query_succeeds(db):
    """Cold-start: a fresh user with no reflections is queryable for both classes.

    Uses a unique user_id (99002) for isolation since the in-memory DB is shared.
    No rows inserted for this user — both filters should return empty lists.
    """
    iso_user_id = 99002
    impressions = (
        db.query(ReflectionViewLog)
        .filter(
            ReflectionViewLog.user_id == iso_user_id,
            ReflectionViewLog.event_class == "impression",
        )
        .all()
    )
    telemetry = (
        db.query(ReflectionViewLog)
        .filter(
            ReflectionViewLog.user_id == iso_user_id,
            ReflectionViewLog.event_class == "telemetry",
        )
        .all()
    )
    assert impressions == []
    assert telemetry == []
