"""Read-only pause prediction analytics projection."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import PausePredictionLog

PRIMARY_METRIC = "acceptance_rate (MANIFESTO §VT-17, pre-registered)"


def _rate(num: list, denom: list) -> float:
    return round(len(num) / len(denom), 3) if denom else 0.0


def pause_prediction_snapshot(db: Session) -> dict:
    """Build the VT-17 pause prediction dashboard payload."""

    all_rows = db.query(PausePredictionLog).all()

    primary = [row for row in all_rows if row.parent_firing_id is None]
    reconciled = [row for row in primary if row.user_response is not None]
    unreconciled = [row for row in primary if row.user_response is None]
    accepted = [row for row in reconciled if row.user_response == "pause_now"]
    no_response = [row for row in reconciled if row.user_response == "no_response"]
    dismissed = [row for row in reconciled if row.user_response == "dismiss"]

    summary = {
        "total_fires": len(primary),
        "total_reconciled": len(reconciled),
        "total_unreconciled": len(unreconciled),
        "accepted": len(accepted),
        "no_response": len(no_response),
        "dismissed": len(dismissed),
        "acceptance_rate": _rate(accepted, reconciled),
        "snooze_refires_excluded": len(all_rows) - len(primary),
    }

    by_mechanism = []
    for mechanism in ("clock_anchor", "work_rhythm"):
        mech_rows = [row for row in primary if row.mechanism == mechanism]
        mech_reconciled = [row for row in mech_rows if row.user_response is not None]
        mech_accepted = [
            row for row in mech_reconciled if row.user_response == "pause_now"
        ]
        by_mechanism.append({
            "mechanism": mechanism,
            "fires": len(mech_rows),
            "reconciled": len(mech_reconciled),
            "accepted": len(mech_accepted),
            "acceptance_rate": _rate(mech_accepted, mech_reconciled),
        })

    return {
        "summary": summary,
        "by_mechanism": by_mechanism,
        "primary_metric": PRIMARY_METRIC,
    }
