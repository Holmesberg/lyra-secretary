from types import SimpleNamespace

import pytest

from app.services.academic_pressure import (
    _classify_obligation,
    _classify_task_obligation,
    _deadline_boundary,
    _estimate,
    _task_boundary,
    _task_estimate,
)


@pytest.mark.parametrize(
    ("title", "obligation_type", "low_minutes", "high_minutes", "assumption"),
    [
        ("Quiz checkpoint", "quiz", 240, 420, "quiz prior from assessment type"),
        ("Midterm checkpoint", "midterm", 480, 840, "midterm prior from assessment type"),
        (
            "Final checkpoint",
            "final",
            720,
            1200,
            "final-exam prior from assessment type",
        ),
        ("Exam checkpoint", "exam", 480, 840, "exam prior from assessment type"),
        (
            "Assignment checkpoint",
            "assignment",
            120,
            300,
            "assignment prior from assessment type",
        ),
        ("Lab checkpoint", "lab", 90, 240, "lab prior from assessment type"),
        (
            "Project checkpoint",
            "project",
            360,
            900,
            "project prior from assessment type",
        ),
        (
            "Lecture checkpoint",
            "lecture",
            90,
            150,
            "lecture/revision prior without recording duration",
        ),
        ("Milestone checkpoint", "deadline", 90, 240, "generic academic-deadline prior"),
    ],
)
def test_deadline_prior_ranges_and_title_families_are_frozen(
    title,
    obligation_type,
    low_minutes,
    high_minutes,
    assumption,
):
    deadline = SimpleNamespace(
        title=title,
        category_hint="academic",
        external_source=None,
    )

    estimate = _estimate(deadline)

    assert _classify_obligation(title) == obligation_type
    assert (estimate.low_minutes, estimate.high_minutes) == (
        low_minutes,
        high_minutes,
    )
    assert estimate.confidence == "low"
    assert estimate.assumptions[0] == assumption
    assert estimate.assumptions[1] == "medium complexity tier from title/category heuristics"


@pytest.mark.parametrize(
    ("title", "expected_range", "complexity_assumption"),
    [
        (
            "Algorithms Quiz",
            (330, 570),
            "high complexity tier from title/category heuristics",
        ),
        ("Quiz reading", (210, 360), "low complexity tier from title/category heuristics"),
    ],
)
def test_deadline_complexity_multiplier_and_outward_rounding_are_frozen(
    title,
    expected_range,
    complexity_assumption,
):
    deadline = SimpleNamespace(
        title=title,
        category_hint="academic",
        external_source=None,
    )

    estimate = _estimate(deadline)

    assert (estimate.low_minutes, estimate.high_minutes) == expected_range
    assert estimate.assumptions[1] == complexity_assumption


def test_deadline_source_labels_are_frozen():
    native = _deadline_boundary(SimpleNamespace(external_source=None))
    external = _deadline_boundary(SimpleNamespace(external_source="moodle_ics"))

    assert vars(native) == {
        "source": "native_obligation",
        "source_class": "native",
        "evidence_class": "native_obligation",
        "provider_kind": "lyra",
        "raw_authority_level": "self_reported",
        "redaction_status": "not_provider_payload",
    }
    assert vars(external) == {
        "source": "external_obligation",
        "source_class": "external",
        "evidence_class": "external_obligation",
        "provider_kind": "moodle",
        "raw_authority_level": "provider_reachable",
        "redaction_status": "metadata_only",
    }


@pytest.mark.parametrize(
    (
        "category",
        "title",
        "kind",
        "obligation_type",
        "source",
        "confidence",
        "assumption_phrase",
    ),
    [
        (
            "study",
            "Read chapter",
            "study",
            "self_study",
            "lyra_self_study_task",
            "medium",
            "not completed work",
        ),
        (
            "academic",
            "Attend lecture",
            "academic",
            "lecture",
            "lyra_academic_task",
            "low",
            "visible schedule structure",
        ),
    ],
)
def test_task_source_and_planned_duration_semantics_are_frozen(
    category,
    title,
    kind,
    obligation_type,
    source,
    confidence,
    assumption_phrase,
):
    task = SimpleNamespace(
        category=category,
        title=title,
        planned_duration_minutes=60,
        planned_start_utc=None,
        planned_end_utc=None,
    )

    boundary = _task_boundary(kind)
    estimate = _task_estimate(task)

    assert _classify_task_obligation(task) == obligation_type
    assert boundary.source == source
    assert boundary.source_class == "lyra_task"
    assert boundary.evidence_class == "scheduled_intention"
    assert (estimate.low_minutes, estimate.high_minutes) == (60, 60)
    assert estimate.confidence == confidence
    assert assumption_phrase in " ".join(estimate.assumptions)
