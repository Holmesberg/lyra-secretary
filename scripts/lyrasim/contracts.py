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
SCORER_VERSION = "lyrasim_scorers_v2"
