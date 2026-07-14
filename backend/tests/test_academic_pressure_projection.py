from datetime import datetime, timedelta

import pytest

from app.services.academic_pressure_projection import (
    DemandCoverageScenario,
    MinuteEnvelope,
    TimeInterval,
    project_demand_coverage,
    union_interval_minutes,
)


def scenario(
    scenario_id: str,
    *,
    total: int,
    completed: int = 0,
    coverage: int = 0,
) -> DemandCoverageScenario:
    return DemandCoverageScenario(
        scenario_id=scenario_id,
        total_estimate_minutes=total,
        completed_scope_credit_minutes=completed,
        feasible_future_coverage_minutes=coverage,
    )


def test_projection_reconciles_remaining_applied_and_unscheduled_demand():
    projection = project_demand_coverage(
        [scenario("baseline", total=300, coverage=120)]
    )

    result = projection.scenario_results[0]
    assert result.remaining_demand_minutes == 300
    assert result.applied_coverage_minutes == 120
    assert result.unscheduled_demand_minutes == 180
    assert result.overcoverage_minutes == 0
    assert result.identities_hold is True
    assert projection.scenario_count == 1


def test_projection_reports_overcoverage_instead_of_negative_demand():
    projection = project_demand_coverage(
        [scenario("overcovered", total=60, coverage=120)]
    )

    result = projection.scenario_results[0]
    assert result.remaining_demand_minutes == 60
    assert result.applied_coverage_minutes == 60
    assert result.unscheduled_demand_minutes == 0
    assert result.overcoverage_minutes == 60
    assert result.identities_hold is True


def test_projection_marks_scope_credit_beyond_estimate_as_inconsistent():
    projection = project_demand_coverage(
        [scenario("estimate-too-low", total=60, completed=90, coverage=30)]
    )

    result = projection.scenario_results[0]
    assert result.remaining_demand_minutes == 0
    assert result.applied_coverage_minutes == 0
    assert result.overcoverage_minutes == 30
    assert result.estimate_inconsistent is True
    assert projection.inconsistent_scenario_ids == ("estimate-too-low",)


def test_projection_envelopes_are_derived_from_joint_scenarios():
    projection = project_demand_coverage(
        [
            scenario("narrow", total=240, completed=60, coverage=90),
            scenario("wide", total=360, completed=0, coverage=180),
        ]
    )

    assert projection.total_estimate == MinuteEnvelope(low=240, high=360)
    assert projection.remaining_demand == MinuteEnvelope(low=180, high=360)
    assert projection.applied_coverage == MinuteEnvelope(low=90, high=180)
    assert projection.unscheduled_demand == MinuteEnvelope(low=90, high=180)
    assert projection.overcoverage == MinuteEnvelope(low=0, high=0)
    assert all(result.identities_hold for result in projection.scenario_results)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("total_estimate_minutes", -1),
        ("completed_scope_credit_minutes", -1),
        ("feasible_future_coverage_minutes", -1),
        ("total_estimate_minutes", 1.5),
        ("total_estimate_minutes", True),
    ],
)
def test_scenario_rejects_invalid_minute_values(field, value):
    values = {
        "total_estimate_minutes": 60,
        "completed_scope_credit_minutes": 0,
        "feasible_future_coverage_minutes": 0,
    }
    values[field] = value

    with pytest.raises(ValueError, match="non-negative integer"):
        DemandCoverageScenario(scenario_id="invalid", **values)


def test_projection_rejects_empty_or_duplicate_scenarios():
    with pytest.raises(ValueError, match="at least one"):
        project_demand_coverage([])

    duplicate = scenario("same", total=60)
    with pytest.raises(ValueError, match="must be unique"):
        project_demand_coverage([duplicate, duplicate])


def test_minute_envelope_rejects_inverted_bounds():
    with pytest.raises(ValueError, match="low cannot exceed high"):
        MinuteEnvelope(low=90, high=60)


def test_interval_union_clips_and_counts_overlaps_once():
    start = datetime(2026, 7, 12, 8, 0)
    projection = union_interval_minutes(
        [
            TimeInterval(
                interval_id="before-and-inside",
                start=start - timedelta(hours=1),
                end=start + timedelta(hours=1),
            ),
            TimeInterval(
                interval_id="overlap",
                start=start + timedelta(minutes=30),
                end=start + timedelta(hours=2),
            ),
            TimeInterval(
                interval_id="after-window",
                start=start + timedelta(hours=4),
                end=start + timedelta(hours=5),
            ),
        ],
        window_start=start,
        window_end=start + timedelta(hours=3),
    )

    assert projection.total_minutes == 120
    assert projection.contributing_interval_ids == (
        "before-and-inside",
        "overlap",
    )
    assert len(projection.segments) == 1
    assert projection.segments[0].start == start
    assert projection.segments[0].end == start + timedelta(hours=2)


def test_interval_union_keeps_disjoint_segments_and_floors_subminute_time():
    start = datetime(2026, 7, 12, 8, 0)
    projection = union_interval_minutes(
        [
            TimeInterval(
                interval_id="first",
                start=start,
                end=start + timedelta(minutes=30, seconds=45),
            ),
            TimeInterval(
                interval_id="second",
                start=start + timedelta(hours=1),
                end=start + timedelta(hours=1, minutes=15, seconds=30),
            ),
        ],
        window_start=start,
        window_end=start + timedelta(hours=2),
    )

    assert projection.total_minutes == 46
    assert len(projection.segments) == 2


def test_interval_union_rejects_invalid_windows_and_duplicate_ids():
    start = datetime(2026, 7, 12, 8, 0)
    interval = TimeInterval(
        interval_id="duplicate",
        start=start,
        end=start + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="window_end"):
        union_interval_minutes(
            [interval],
            window_start=start,
            window_end=start,
        )

    with pytest.raises(ValueError, match="must be unique"):
        union_interval_minutes(
            [interval, interval],
            window_start=start,
            window_end=start + timedelta(hours=2),
        )


def test_time_interval_rejects_empty_id_and_inverted_time():
    start = datetime(2026, 7, 12, 8, 0)
    with pytest.raises(ValueError, match="non-empty"):
        TimeInterval(
            interval_id=" ",
            start=start,
            end=start + timedelta(minutes=1),
        )
    with pytest.raises(ValueError, match="after start"):
        TimeInterval(interval_id="invalid", start=start, end=start)
