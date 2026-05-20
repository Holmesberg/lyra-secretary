from app.services.task_manager import TaskManager


def test_academic_schedule_terms_infer_academic_without_manual_category(db):
    manager = TaskManager(db)

    assert manager._infer_category("CO MARS labs") == "academic"
    assert manager._infer_category("Operating Systems tutorial") == "academic"
    assert manager._infer_category("AI lecture 5") == "academic"


def test_self_study_terms_infer_study_without_manual_category(db):
    manager = TaskManager(db)

    assert manager._infer_category("AI final revision") == "study"
    assert manager._infer_category("read CO slides") == "study"
    assert manager._infer_category("solve algorithms problem set") == "study"
