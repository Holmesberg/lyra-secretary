"""Pydantic schemas for the onboarding brain-dump multi-item parser.

Used by POST /v1/brain-dump/parse (preview) and POST /v1/brain-dump/commit
(write-through). Heuristic-only fan-out per operator decision 2026-04-28:
no LLM dependency on the synchronous critical path; LLM async enrichment
fires per-task afterward via the existing llm_enrichment worker and may
surface "Possible better match" via the trust-not-rewrite contract.
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


ItemKind = Literal["task", "deadline"]
BindingTier = Literal["tier1_auto", "tier2_ask", "tier3_skip"]
ParserStatus = Literal["heuristic_parsed", "empty"]


class BrainDumpParsedItem(BaseModel):
    """One parsed entry from the user's free-text dump."""
    item_id: str
    kind: ItemKind
    title: str
    description: Optional[str] = None
    # ISO datetime in user's local TZ.
    # For tasks: planned_start_local (default now+30min when no anchor parsed).
    # For deadlines: due_at_local (required for deadline kind).
    when_local: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    # Heuristic confidence in this item being correctly typed.
    # High (≥0.85): explicit deadline keyword + date, or unambiguous task
    # Medium (0.45-0.85): one signal, ambiguous typing
    # Low (<0.45): brittle — surface for user edit
    confidence: float = 1.0


class BrainDumpBindingSuggestion(BaseModel):
    """Suggested link between a parsed task and a parsed deadline."""
    task_item_id: str
    deadline_item_id: str
    deadline_title: str
    confidence: float
    tier: BindingTier
    source: str  # 'heuristic_exact_title' | 'heuristic_startswith' | 'heuristic_substring'


class BrainDumpParseRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=8000)
    current_local_iso: Optional[str] = None


class BrainDumpParseResponse(BaseModel):
    items: list[BrainDumpParsedItem]
    bindings: list[BrainDumpBindingSuggestion]
    parser_status: ParserStatus


class BrainDumpCommitItem(BaseModel):
    """User-confirmed item from the preview step."""
    item_id: str
    kind: ItemKind
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    when_local: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=720)


class BrainDumpCommitBinding(BaseModel):
    """User-confirmed binding from the one-tap question block."""
    task_item_id: str
    deadline_item_id: str


class BrainDumpCommitRequest(BaseModel):
    items: list[BrainDumpCommitItem] = Field(..., min_length=0)
    bindings: list[BrainDumpCommitBinding] = Field(default_factory=list)


class BrainDumpFailedItem(BaseModel):
    """An item in the commit batch that couldn't be created.

    Surfaced in BrainDumpCommitResponse.failed_items so the frontend
    can render a retry-or-edit panel instead of silently dropping the
    user's input. LYR-114 fix 2026-04-30 — pre-fix the endpoint logged
    failures + returned 200 with no per-item failure surface, so the
    user thought 5 tasks committed when actually 2 did.
    """
    item_id: str
    kind: ItemKind
    title: str
    # Stable machine-readable reason code for branchable UX:
    #   - "past_time"      → start time was in the past (TaskManager 5-min guard)
    #   - "missing_when"   → deadline had no when_local
    #   - "deadline_terminal_state" → bound deadline already completed/missed
    #   - "deadline_not_found" → bound deadline_id didn't resolve
    #   - "validation"     → other ValueError
    #   - "internal"       → unexpected exception (catch-all; logged with exc_info)
    reason: str
    # Human-readable detail for tooltip / debug context
    detail: str
    # UX hint — what the frontend should offer as a one-click recovery
    # action. None when no obvious retry exists (e.g., internal errors).
    #   - "schedule_tomorrow_same_time"
    #   - "edit_when_local"
    #   - "remove_deadline_binding"
    #   - None
    retry_hint: Optional[str] = None


class BrainDumpCommitResponse(BaseModel):
    tasks_created: int
    deadlines_created: int
    bindings_applied: int
    task_ids: list[str]
    deadline_ids: list[str]
    # LYR-114 fix 2026-04-30: per-item failure surface. Empty when all
    # items committed cleanly. Frontend renders a dismissible warning
    # panel listing failures + a retry affordance per item.
    failed_items: list[BrainDumpFailedItem] = Field(default_factory=list)
