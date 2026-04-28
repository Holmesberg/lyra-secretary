"""Local-LLM async parser via Ollama HTTP API (Workstream 1, magic-for-alpha).

Lives behind a graceful-degradation contract:
  - Ollama unreachable / timeout → `task.llm_parse_status='unavailable'`
  - Ollama returns invalid JSON / schema mismatch → 1 retry → 'failed'
  - Success → 'enriched' + populated llm_* fields

The caller (the `llm_enrichment` background worker) treats both
non-success states as terminal — no infinite retry loops.

Architectural rule (operator-locked guardrail #1, plan section
"Operator-pushback"): Ollama is enrichment, not critical-path. POST
/v1/create has already returned by the time this runs. UI degrades
gracefully when llm_parse_status != 'enriched'.

Architectural rule (guardrail #2): no silent auto-binding. This module
populates `llm_inferred_deadline_id` (the LLM's suggestion). The user
must call `POST /v1/tasks/{id}/llm-confirm` to copy it across into the
canonical `deadline_id` field. Until they do, the existing parser_auto
or user_explicit binding (if any) remains the source of truth.

Pre-registration footprint: `Task.scope_bullet_count_at_plan` (regex
output) is unchanged. `task.llm_sub_items` is the LLM output, kept
separate. Rule 12 mediation analysis uses the regex column. No
MANIFESTO version bump for this service.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

import requests
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Deadline, Task
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)


# Pydantic schema the LLM is asked to emit. We validate the response
# against this; on ValidationError the task is marked 'failed' (after
# 1 retry).
#
# Research-integrity guard (2026-04-28 audit, MANIFESTO Rule 11/12):
# DO NOT surface `scope_estimate_minutes` as a user-visible chip or
# planned-duration suggestion without first amending Rule 11
# stratification + Rule 12 mediation test. The field is audit-only at
# present. Surfacing it would constitute a calibration_nudge analog and
# trigger VT-21 narrative-internalization risk on planned_duration.
# See docs/manifesto_alignment_audit_2026_04_28.md §6.
class LlmParseResult(BaseModel):
    priority: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="1=critical, 5=low. Null when the LLM can't infer.",
    )
    deadline_name: Optional[str] = Field(
        None,
        description="A natural-language deadline reference the user wrote, e.g. 'BCI paper'. Null when none.",
    )
    sub_items: list[str] = Field(
        default_factory=list,
        description="List of sub-tasks/scope items extracted from the description.",
    )
    scope_estimate_minutes: Optional[int] = Field(
        None,
        ge=1,
        le=720,
        description="LLM's rough estimate of total minutes for the task. Null when unsure.",
    )


def _build_prompt(task: Task, deadlines: list[Deadline]) -> str:
    """Construct the structured-output prompt for Ollama.

    The prompt is deliberately terse — local 7B models follow shorter
    instructions more reliably. JSON-mode (Ollama `format=json`) plus the
    schema-shape hint nudges the model toward valid output. Pydantic
    validates after.
    """
    deadline_lines = (
        "\n".join(
            f"  - id={d.deadline_id}: \"{d.title}\"" for d in deadlines
        )
        or "  (no active deadlines)"
    )
    title = (task.title or "").strip()
    description = (task.description or "").strip()
    return (
        "You are a structured-output parser for a productivity scheduler. "
        "Given the task title and description below, extract structured "
        "fields. Respond with ONLY a single JSON object matching the schema. "
        "No prose, no markdown, no commentary.\n\n"
        "Schema fields:\n"
        '  - priority: integer 1-5 (1=critical, 5=low), or null\n'
        '  - deadline_name: string referencing a deadline the user wrote, or null\n'
        '  - sub_items: array of strings (sub-tasks; empty if none)\n'
        '  - scope_estimate_minutes: integer (your estimate of total task minutes), or null\n\n'
        "Task title: " + title + "\n"
        "Task description:\n"
        + (description or "(empty)")
        + "\n\n"
        "Available deadlines (match deadline_name semantically, by intent — "
        "use natural-language fragments the user wrote):\n"
        + deadline_lines
        + "\n"
    )


def _rank_deadline_candidates(
    deadline_name: Optional[str],
    task_title: str,
    task_description: Optional[str],
    deadlines: list[Deadline],
    max_results: int = 5,
) -> list[dict]:
    """Score every user deadline against the LLM's `deadline_name`
    suggestion AND the task's own title/description tokens.

    Returns a ranked list (top first) of dicts:
        [{"deadline_id": "...", "title": "...", "confidence": 0..1}, ...]

    Empty list when no deadline scores above floor (0.30 — below this
    even the soft-ask Tier 2 wouldn't surface it). Tiers per
    operator-locked UX 2026-04-28:
      Tier 1 — top confidence > 0.85
      Tier 2 — top confidence 0.45-0.85
      Tier 3 — top confidence < 0.45 (or empty list) → no chip
      Tier 4 — manual picker (always available regardless)

    Confidence blends two signals:
      - Tokens shared with the LLM's `deadline_name` hint (high weight)
      - Tokens shared with task_title/description (medium weight)
    The blend defends against LLM hallucinating a `deadline_name` that
    doesn't match anything: when the hint is wrong, the title/description
    overlap still produces a useful ranking.
    """
    if not deadlines:
        return []

    hint_tokens = _tokenize(deadline_name or "")
    title_tokens = _tokenize(task_title) | _tokenize(task_description or "")
    # If neither signal has content, can't rank.
    if not hint_tokens and not title_tokens:
        return []

    scored: list[tuple[float, Deadline]] = []
    for d in deadlines:
        haystack = _tokenize(d.title) | _tokenize(d.description or "")
        if not haystack:
            continue
        # Two-signal blend.
        hint_score = (
            len(hint_tokens & haystack) / max(len(hint_tokens), 1)
            if hint_tokens
            else 0.0
        )
        title_score = (
            len(title_tokens & haystack) / max(len(title_tokens), 1)
            if title_tokens
            else 0.0
        )
        # Weighted blend: hint dominates when present (LLM is reading the
        # user's intent), title is the fallback.
        if hint_tokens:
            blended = 0.7 * hint_score + 0.3 * title_score
        else:
            blended = title_score
        scored.append((blended, d))

    scored.sort(key=lambda x: -x[0])
    out = []
    for score, d in scored[:max_results]:
        if score < 0.30:
            break
        out.append({
            "deadline_id": d.deadline_id,
            "title": d.title,
            "confidence": round(score, 3),
        })
    return out


_STOPWORDS = {
    "the",
    "a",
    "an",
    "to",
    "for",
    "of",
    "and",
    "or",
    "in",
    "on",
    "at",
    "by",
    "with",
    "due",
    "today",
    "tomorrow",
    "deadline",
}


def _tokenize(s: str) -> set[str]:
    import re

    if not s:
        return set()
    return {
        t
        for t in re.findall(r"[a-z0-9]+", s.lower())
        if t not in _STOPWORDS and len(t) >= 3
    }


def _strip_markdown_fence(s: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences if the model wraps
    the JSON in a code block. Apr 28: qwen2.5 family without explicit
    format=json mode tends to fence its output. We don't use format=json
    because Ollama 0.21.x has a llama-runner-crash bug with that flag.
    """
    s = s.strip()
    if s.startswith("```"):
        # Drop the opening fence (and any "json" tag after the backticks)
        first_newline = s.find("\n")
        if first_newline > 0:
            s = s[first_newline + 1 :]
        # Drop trailing fence
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3].rstrip()
    return s


def _call_ollama(prompt: str) -> dict:
    """Single Ollama call. Returns parsed JSON dict on success.

    Note on format=json: Ollama 0.21.x crashes the llama runner process
    when format=json is set on smaller qwen models — see operator dogfood
    Apr 28. Workaround: rely on the prompt's "JSON only" instruction +
    post-hoc markdown-fence stripping + json.loads. Pydantic validation
    in the caller catches any malformed output.

    Raises:
      - requests.ConnectionError / requests.Timeout — service unreachable
      - json.JSONDecodeError — invalid JSON in response
      - ValidationError — JSON valid but schema mismatch
    """
    response = requests.post(
        f"{settings.OLLAMA_URL}/api/generate",
        json={
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                # Lower temperature for structured output — we want
                # deterministic JSON, not creative writing.
                "temperature": 0.1,
                # Cap output to a reasonable JSON size.
                "num_predict": 512,
            },
            # Keep the model loaded for 30 min so the next task creation
            # in the session avoids the cold-load penalty.
            "keep_alive": "30m",
        },
        timeout=settings.OLLAMA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    body = response.json()
    raw = body.get("response", "").strip()
    raw = _strip_markdown_fence(raw)
    return json.loads(raw)


def enrich_task_via_llm(db: Session, task_id: str) -> str:
    """Single-attempt enrichment. Idempotent.

    Returns the resulting `llm_parse_status` string for observability.
    Caller (background worker) doesn't need to act on the return value;
    the value is also written to `task.llm_parse_status` in the same DB
    transaction.

    P0 stress-test guards (2026-04-28):
      - voided_at re-check on refetch: task can be voided between worker
        SELECT and this UPDATE. Without re-check, enrichment writes
        contaminate a soft-deleted row (silent audit-trail corruption).
      - deadline-write guard: only writes deadline_id-affecting fields
        when `deadline_match_source IN (NULL, 'parser_auto')`. If the
        user already confirmed (`'llm_auto_confirmed'`) or set explicit
        (`'user_explicit'`, `'user_corrected'`), enrichment leaves the
        canonical deadline alone but still populates audit fields.
        User intent always wins over async LLM.
    """
    task = db.query(Task).filter(
        Task.task_id == task_id,
        Task.voided_at.is_(None),
    ).first()
    if task is None:
        logger.info(
            "enrich_task_via_llm: task_id=%s not found or voided — skipping",
            task_id,
        )
        return "voided_or_missing"
    if task.llm_parse_status in ("enriched", "unavailable", "failed"):
        # Idempotent — already terminal. The background worker shouldn't
        # have selected this row but guard anyway.
        return task.llm_parse_status

    deadlines = (
        db.query(Deadline)
        .filter(
            Deadline.user_id == task.user_id,
            Deadline.voided_at.is_(None),
            Deadline.state.in_(("planned", "active")),
        )
        .all()
    )
    prompt = _build_prompt(task, deadlines)

    last_error: Optional[Exception] = None
    parsed: Optional[dict] = None
    for attempt in (1, 2):
        try:
            parsed = _call_ollama(prompt)
            break
        except (requests.ConnectionError, requests.Timeout) as e:
            # Service down. Don't retry — likely the service will still
            # be down on retry. Mark unavailable and let the next worker
            # cycle pick it up if/when ollama is back.
            logger.info(
                "enrich_task_via_llm: ollama unreachable for task=%s: %s",
                task_id,
                e,
            )
            task.llm_parse_status = "unavailable"
            db.commit()
            return "unavailable"
        except (json.JSONDecodeError, ValueError) as e:
            # JSON parse failure — give it one retry (LLM might output
            # better JSON the second time at slightly different sampling).
            last_error = e
            logger.info(
                "enrich_task_via_llm: invalid JSON attempt %d for task=%s: %s",
                attempt,
                task_id,
                e,
            )
            if attempt == 2:
                task.llm_parse_status = "failed"
                db.commit()
                return "failed"

    if parsed is None:
        # Defensive — shouldn't reach here without parsed set.
        task.llm_parse_status = "failed"
        db.commit()
        return "failed"

    try:
        validated = LlmParseResult(**parsed)
    except ValidationError as e:
        logger.info(
            "enrich_task_via_llm: pydantic validation failed for task=%s: %s",
            task_id,
            e,
        )
        task.llm_parse_status = "failed"
        db.commit()
        return "failed"

    candidates = _rank_deadline_candidates(
        validated.deadline_name,
        task.title or "",
        task.description,
        deadlines,
    )

    # Audit-trail fields: ALWAYS write these. They never affect the
    # canonical user-facing binding; they're the LLM's record of what it
    # saw, used by analytics + the chip render decision.
    task.llm_priority = validated.priority
    task.llm_sub_items = [
        {"text": s, "scope_bullet": True} for s in validated.sub_items if s.strip()
    ]
    task.llm_parsed_at = now_utc()

    # Deadline-write guard (P0 stress-test 2026-04-28): only write
    # deadline-related fields when the user hasn't already taken
    # ownership of the binding. If `deadline_match_source` is set by
    # user_explicit, user_corrected, or llm_auto_confirmed (the user
    # already accepted a previous LLM suggestion — possible if
    # enrichment retries on a re-queued row), DO NOT overwrite with
    # async LLM output. User intent wins.
    user_owns_deadline = task.deadline_match_source not in (None, "parser_auto")
    if user_owns_deadline:
        # Skip deadline-related writes; preserve nullability of the
        # candidate fields (not a confidence, not a misleading list).
        task.llm_deadline_candidates = None
        task.llm_inferred_deadline_id = None
        task.llm_deadline_match_confidence = None
    else:
        task.llm_deadline_candidates = candidates
        if candidates:
            # Top entry is the canonical "single best" candidate for
            # query convenience — the JSON list is the authoritative
            # source.
            task.llm_inferred_deadline_id = candidates[0]["deadline_id"]
            task.llm_deadline_match_confidence = candidates[0]["confidence"]
        else:
            task.llm_inferred_deadline_id = None
            task.llm_deadline_match_confidence = None

    task.llm_parse_status = "enriched"
    db.commit()
    return "enriched"
