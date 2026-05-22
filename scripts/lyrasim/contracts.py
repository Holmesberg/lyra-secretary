"""Contract vocabulary bridge for LyraSim reports."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.research_contracts import AUTHORITY_RUNGS  # noqa: E402


AUTHORITY_LADDER_VERSION = "research_contracts.AUTHORITY_RUNGS:v1"
RESOLUTION_RUNGS = ("suppress", "clarify", "repair", "recommend", "adapt")
EXPECTED_RESOLUTION_RUNGS = RESOLUTION_RUNGS + ("clarify_or_repair",)
SAFE_ACTION_TYPES = (
    "confirm_done_partial_discard",
    "confirm_coverage",
    "adjust_session_duration",
    "mark_open_unconfirmed",
    "ask_pause_continue_split",
    "none",
)
SCORER_VERSION = "lyrasim_scorers_v4"
