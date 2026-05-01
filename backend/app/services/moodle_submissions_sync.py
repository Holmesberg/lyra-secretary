"""Moodle Web Services submission detection (Phase B 2026-05-01).

Auto-marks Lyra deadlines complete when Moodle confirms the user
submitted the corresponding assignment. Solves operator's complaint:
"the overdue task from moodle still hasn't synced up, still shows
overdue even though I submitted it on moodle." iCal feeds carry due
dates ONLY — Web Services is the only path to submission status.

ARCHITECTURE — course-code matching (operator decision 2026-05-01):
  Lyra deadline matches a Moodle assignment ONLY when they share the
  same course (deadline.category_hint == course_short, or both
  contain the same course code like "CSE281"). Title fuzzy-match +
  due-date proximity then breaks ties WITHIN that course's
  assignments.

  Why course-code constraint instead of bound-task gate or threshold:
  the false-positive operator caught was "Formative quiz 1 closes"
  (CSE281, an iCal close event for a quiz) matching "Quiz 1 (5 marks)"
  (PHM112, a graded assignment). Title fuzzy-match said they overlap.
  Course-code constraint says they're different subjects → never
  considered. Bumping the title threshold would also have helped but
  is more brittle; course-code is the structural fix.

  Side benefits:
    - Reduces per-sync API call surface (only assignments in user's
      engaged courses)
    - Eliminates noise from quiz close events, lecture notes, forum
      posts (none of which are mod_assign type — they don't appear
      in the assignment list at all)

DECISION RULE — what counts as "submitted":
  - submission.status == 'submitted'  → mark complete
  - feedback.grade.grade is not None  → mark complete (graded means
    submitted even for quiz-style with no separate submission row)
  - status == 'draft' / 'new' / None  → leave alone

MATCHING:
  Lyra deadline title + due_at_utc → best Moodle assignment via
  (title_similarity + due_proximity) score. Each Moodle assignment
  binds to AT MOST ONE Lyra deadline (greedy first-served by score).
  Min score 0.30; high-confidence + due-date proximity protects
  against false matches even at the broader threshold (operator's
  "subject-aware" filter is the primary noise gate).

SAFETY:
  - Only acts on deadlines in {planned, active}; preserves user
    intent for {skipped, voided}; idempotent for {completed, missed}.
  - Single batched Telegram summary per sync run (not per-mark).
  - 4xx WS responses → set moodle_ws_disconnect_reason='invalidtoken'
    + skip user until they reconnect via Settings.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Optional
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.db.models import Deadline, User
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)

WS_HTTP_TIMEOUT = 20.0
MIN_MATCH_SCORE = 0.30
MAX_TITLE_OVERLAP_BONUS_DELTA_HOURS = 48
MEDIUM_DELTA_HOURS = 168  # 7d
PENALTY_DELTA_HOURS = 720  # 30d

# Backfill window for assignments that exist on Moodle but not in
# Lyra's deadline table (operator request 2026-05-01 — "submitted
# tasks should pop up", "could Lyra pick up unsubmitted as overdue").
# Looking too far back drags in last semester's noise; the operator
# typically cares about the current term + a 90d safety margin.
BACKFILL_PAST_DAYS = 90
BACKFILL_DEDUP_TITLE_THRESHOLD = 0.7
BACKFILL_DEDUP_DUE_HOURS = 24


@dataclass
class SubmissionSyncResult:
    """Returned per-user from sync_user(). Counts + list for telegram."""
    matched: int = 0
    marked_complete: int = 0
    skipped_unbound: int = 0
    skipped_no_match: int = 0
    skipped_not_submitted: int = 0
    backfilled_completed: int = 0
    backfilled_planned: int = 0
    backfilled_missed: int = 0
    marked_titles: list[str] = field(default_factory=list)
    backfilled_titles: list[str] = field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Title matching — pure functions, easy to unit test
# ---------------------------------------------------------------------------


# Course-code regex — matches patterns like "CSE281", "PHM123",
# "CSE281 (UG2023) - ...". Captures the alphanumeric prefix that
# typically identifies a course across both iCal CATEGORIES tags
# and Moodle course shortnames. Conservative — only 3+ uppercase
# letters followed by digits, so noise tokens like "Lab" or "1" don't
# get misread as course codes.
_COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5}\d{2,4})\b")


def _extract_course_code(s: Optional[str]) -> Optional[str]:
    """Pull a course code (e.g., 'CSE281') from a category_hint OR
    a Moodle course shortname. Returns None when no recognizable
    code is present, which causes the matcher to fall through to
    the no-constraint path (degraded mode)."""
    if not s:
        return None
    match = _COURSE_CODE_RE.search(s)
    return match.group(1) if match else None


def _normalize(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    if not s:
        return ""
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in s.lower())
    return " ".join(cleaned.split())


def title_similarity(a: str, b: str) -> float:
    """0..1 similarity blending sequence ratio + token overlap."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return 0.0
    seq_ratio = SequenceMatcher(None, na, nb).ratio()
    tokens_a, tokens_b = set(na.split()), set(nb.split())
    if not tokens_a or not tokens_b:
        return seq_ratio
    overlap = len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))
    # Token overlap dominates — "HandsOn Lab8 is due" vs "HandsOn Lab8"
    # should match strongly via shared tokens even though suffix differs.
    return 0.6 * overlap + 0.4 * seq_ratio


def due_proximity_bonus(lyra_due_utc: datetime, moodle_duedate_epoch: int) -> float:
    """Bonus 0..0.3 when dates close, penalty -0.2 when >30d apart."""
    if not moodle_duedate_epoch:
        return 0.0
    moodle_dt = datetime.utcfromtimestamp(moodle_duedate_epoch)
    delta_h = abs((lyra_due_utc - moodle_dt).total_seconds()) / 3600.0
    if delta_h <= MAX_TITLE_OVERLAP_BONUS_DELTA_HOURS:
        return 0.3
    if delta_h <= MEDIUM_DELTA_HOURS:
        return 0.15
    if delta_h >= PENALTY_DELTA_HOURS:
        return -0.2
    return 0.0


def _has_existing_deadline(
    ma: dict,
    deadlines: list,
    *,
    title_threshold: float,
    due_window_hours: float,
) -> bool:
    """True when `ma` (a Moodle assignment) is already represented in
    Lyra's deadline table.

    Three-tier check (any hit short-circuits):
      1. Exact key — if external_source='moodle_ws_backfill' AND
         external_id == str(assign_id), it's the SAME row (re-sync).
      2. Same course code + due-date within 6h. Two assignments in the
         same course landing on the same due date are almost certainly
         the same; title fuzziness shouldn't be needed (catches the
         operator's "HandsOn Lab8" vs "HandsOn Lab8 is due" gap where
         iCal added " is due" suffix).
      3. Course code + fuzzy title (>= title_threshold) + due-date
         within `due_window_hours`. The original conservative path for
         when due-dates are close-but-not-exact.
    """
    assign_id_str = str(ma["assign_id"])
    ma_course_code = _extract_course_code(ma["course_short"])
    ma_due = datetime.utcfromtimestamp(ma["duedate"]) if ma["duedate"] else None
    for d in deadlines:
        if (
            d.external_source == "moodle_ws_backfill"
            and d.external_id == assign_id_str
        ):
            return True
        d_course_code = _extract_course_code(d.category_hint)
        # Course-code mismatch is a hard reject — skip this deadline.
        if ma_course_code and d_course_code and ma_course_code != d_course_code:
            continue
        # Tier 2: exact-due-date match within 6h, course code aligned.
        if (
            ma_due
            and d.due_at_utc
            and ma_course_code
            and d_course_code
            and ma_course_code == d_course_code
        ):
            delta_h = abs((ma_due - d.due_at_utc).total_seconds()) / 3600.0
            if delta_h <= 6.0:
                return True
        # Tier 3: fuzzy title + within due window.
        if title_similarity(ma["name"], d.title) < title_threshold:
            continue
        if ma_due and d.due_at_utc:
            delta_h = abs((ma_due - d.due_at_utc).total_seconds()) / 3600.0
            if delta_h > due_window_hours:
                continue
        return True
    return False


def is_submitted(status_resp: dict) -> tuple[bool, str]:
    """Map a mod_assign_get_submission_status response → (mark_complete, reason).

    Reason is a short human-readable string used in logs + telegram
    summary. Pure function — no I/O, easy to unit test.
    """
    sub = (status_resp.get("lastattempt") or {}).get("submission") or {}
    fb = status_resp.get("feedback") or {}
    grade = (fb.get("grade") or {}).get("grade")
    status = sub.get("status")
    if status == "submitted":
        return True, "Moodle says submitted"
    if grade is not None:
        return True, f"graded ({grade})"
    return False, f"status={status or 'no-submission'}"


# ---------------------------------------------------------------------------
# WS client — thin wrapper over Moodle's REST endpoint
# ---------------------------------------------------------------------------


class _MoodleWS:
    """Per-call wrapper around Moodle's WS REST endpoint. Raises
    `_WSAuthError` on invalidtoken so the caller can flip the user's
    moodle_ws_disconnect_reason. Other exceptions bubble up.
    """

    def __init__(self, base_url: str, token: str):
        self.endpoint = f"{base_url.rstrip('/')}/webservice/rest/server.php"
        self.token = token

    def call(self, fn: str, **params) -> object:
        q = {
            "wstoken": self.token,
            "wsfunction": fn,
            "moodlewsrestformat": "json",
            **{str(k): v for k, v in params.items()},
        }
        with httpx.Client(timeout=WS_HTTP_TIMEOUT, follow_redirects=True) as client:
            r = client.get(self.endpoint, params=q)
            r.raise_for_status()
        body = r.json()
        if isinstance(body, dict) and body.get("exception"):
            err = body.get("errorcode", "")
            if err in ("invalidtoken", "accessexception"):
                raise _WSAuthError(body.get("message", err))
            raise RuntimeError(f"WS error {err}: {body.get('message')}")
        return body


class _WSAuthError(RuntimeError):
    """Raised when Moodle returns invalidtoken/accessexception. The
    caller should set the user's moodle_ws_disconnect_reason and stop
    syncing for that user until they reconnect."""


# ---------------------------------------------------------------------------
# Per-user sync entry-point
# ---------------------------------------------------------------------------


def sync_user(user: User, base_url: str, db: Session) -> SubmissionSyncResult:
    """Run submission detection for one user. Returns a SubmissionSyncResult
    summarizing the outcome (counts + list of marked titles + error).

    Caller is responsible for committing the DB session AND firing the
    operator-Telegram fanout (this function only mutates Deadline rows
    in the session and updates user.moodle_ws_last_synced_at).

    Architectural note (operator decision 2026-05-01): only deadlines
    with at least one BOUND (non-voided) Lyra task are synced. Unbound
    deadlines = noise the user didn't engage with; skipped silently.
    """
    result = SubmissionSyncResult()

    if not user.moodle_ws_token:
        result.error = "no_token"
        return result

    # Fetch the user's planned/active Moodle deadlines. NO task-bound
    # gate (operator decision 2026-05-01) — instead, the course-code
    # match below is the structural noise filter. Imported deadlines
    # without an associated task still get auto-tracked when Moodle
    # confirms submission.
    candidate_deadlines = (
        db.query(Deadline)
        .filter(
            Deadline.user_id == user.user_id,
            Deadline.voided_at.is_(None),
            Deadline.external_source == "moodle_ics",
            Deadline.state.in_(("planned", "active")),
        )
        .all()
    )
    # NB: even with zero candidates we still hit Moodle — the backfill
    # path below is the operator's main case (iCal feed is sparse, WS
    # has the full submission history).

    ws = _MoodleWS(base_url, user.moodle_ws_token)

    # Resolve MOODLE userid (NOT Lyra user_id — the two are different).
    # For Phase B v1 we only support the operator (1 user) with an
    # explicit MOODLE_WS_USERID env. Multi-user requires a per-user
    # moodle_userid column on `user` — Phase B+1 work.
    #
    # Bug fix 2026-05-01: prior code passed user.user_id (Lyra ID, =1
    # for operator) to core_enrol_get_users_courses. Moodle returned
    # empty list (no courses for Moodle user 1) and the broken
    # `isinstance(courses, list)` fallback didn't catch it because the
    # empty list IS a list. Result: all syncs returned matched=0 with
    # no error surfaced. Fix: resolve moodle_userid up-front + always
    # pass it to WS calls.
    import os
    moodle_userid = int(os.environ.get("MOODLE_WS_USERID") or 0)
    if not moodle_userid:
        result.error = "no_moodle_userid"
        return result

    try:
        courses = ws.call("core_enrol_get_users_courses", userid=moodle_userid)
        if not isinstance(courses, list):
            result.error = f"unexpected_courses_response: {type(courses).__name__}"
            return result
        course_ids = [c["id"] for c in courses]
    except _WSAuthError as e:
        user.moodle_ws_disconnect_reason = "invalidtoken"
        result.error = "auth"
        logger.warning(
            "moodle_ws: user_id=%s auth failed: %s", user.user_id, e
        )
        return result
    except Exception as e:
        result.error = f"courses_fetch: {type(e).__name__}"
        logger.warning(
            "moodle_ws: user_id=%s course fetch error: %s",
            user.user_id, e,
        )
        return result

    if not course_ids:
        return result

    try:
        asg_resp = ws.call(
            "mod_assign_get_assignments",
            **{f"courseids[{i}]": cid for i, cid in enumerate(course_ids)},
        )
    except _WSAuthError as e:
        user.moodle_ws_disconnect_reason = "invalidtoken"
        result.error = "auth"
        logger.warning("moodle_ws: assign fetch auth fail user=%s: %s", user.user_id, e)
        return result
    except Exception as e:
        result.error = f"assigns_fetch: {type(e).__name__}"
        logger.warning("moodle_ws: assign fetch error user=%s: %s", user.user_id, e)
        return result

    # Build assignment list keyed by course_short so we can constrain
    # matching by course code. Also retain the raw assignment data
    # for the title/date scoring.
    moodle_assigns: list[dict] = []
    for course in (asg_resp.get("courses") or []):
        for a in (course.get("assignments") or []):
            moodle_assigns.append({
                "assign_id": a["id"],
                "name": a.get("name", ""),
                "duedate": a.get("duedate") or 0,
                "course_short": course.get("shortname") or "",
            })

    # Best-match each candidate deadline; the course-code constraint
    # is the primary noise filter (operator's subject-aware fix), the
    # title + due-date scoring is the within-course tie-breaker.
    # `used_assign_ids` so the same Moodle assignment doesn't bind to
    # two Lyra deadlines.
    matched_pairs: list[tuple[Deadline, dict, float]] = []
    used_assign_ids: set[int] = set()
    for d in candidate_deadlines:
        deadline_course_code = _extract_course_code(d.category_hint)
        scored = []
        for ma in moodle_assigns:
            if ma["assign_id"] in used_assign_ids:
                continue
            # Course-code gate: same course, OR neither side has a
            # parseable course code (degraded mode for legacy/manual
            # deadlines without category_hint).
            assign_course_code = _extract_course_code(ma["course_short"])
            if deadline_course_code and assign_course_code:
                if deadline_course_code != assign_course_code:
                    continue
            # If only one side has a code, fall through to title+date
            # match (no constraint applied).
            sim = title_similarity(d.title, ma["name"])
            if sim < MIN_MATCH_SCORE:
                continue
            score = sim + due_proximity_bonus(d.due_at_utc, ma["duedate"])
            scored.append((score, ma))
        if not scored:
            result.skipped_no_match += 1
            continue
        scored.sort(key=lambda t: -t[0])
        best_score, best_ma = scored[0]
        used_assign_ids.add(best_ma["assign_id"])
        matched_pairs.append((d, best_ma, best_score))
        result.matched += 1

    # Query submission status per matched pair.
    now = now_utc()
    for d, ma, _score in matched_pairs:
        try:
            status_resp = ws.call(
                "mod_assign_get_submission_status",
                assignid=ma["assign_id"],
                userid=moodle_userid,
            )
        except _WSAuthError as e:
            user.moodle_ws_disconnect_reason = "invalidtoken"
            result.error = "auth"
            logger.warning("moodle_ws: status auth fail user=%s: %s", user.user_id, e)
            return result
        except Exception as e:
            logger.info(
                "moodle_ws: status fetch failed for assign=%s (will retry next cycle): %s",
                ma["assign_id"], e,
            )
            continue
        should_mark, reason = is_submitted(status_resp)
        if should_mark:
            d.state = "completed"
            d.completed_at = now
            result.marked_complete += 1
            result.marked_titles.append(d.title)
            logger.info(
                "moodle_ws: marked deadline=%s ('%s') complete — %s",
                d.deadline_id, d.title, reason,
            )
        else:
            result.skipped_not_submitted += 1

    # ---------------------------------------------------------------
    # Backfill — for any Moodle assignment we DIDN'T match to an
    # existing Lyra deadline, create one. Operator request 2026-05-01:
    # "submitted tasks should pop up in deadlines" + "could Lyra pick
    # up other unsubmitted as overdue".
    #
    # Why: Moodle's iCal "Recent and upcoming" filter drops past
    # assignments + items the school disabled in the calendar export.
    # Operator ended up with 11+ submitted CSE assignments on Moodle
    # but only 4 deadlines in Lyra. This backfills from WS so the
    # timeline reflects the real workload.
    #
    # Research-integrity (per VT-29 / H1): backfilled rows carry
    # external_source='moodle_ws_backfill', so research queries
    # filtering `WHERE external_source IS NULL` still exclude them.
    # ---------------------------------------------------------------
    cutoff = now - timedelta(days=BACKFILL_PAST_DAYS)
    # Pull EVERY Moodle deadline including voided ones — the unique
    # constraint `uq_deadline_external` covers voided rows too, AND we
    # want to honor an explicit user void as "don't resurrect" (mirrors
    # DeadlineManager.upsert_external_deadline's 'skipped_voided' rule).
    all_moodle_deadlines = (
        db.query(Deadline)
        .filter(
            Deadline.user_id == user.user_id,
            Deadline.external_source.in_(("moodle_ics", "moodle_ws_backfill")),
        )
        .all()
    )
    for ma in moodle_assigns:
        if ma["assign_id"] in used_assign_ids:
            continue
        if not ma["duedate"]:
            continue  # info-only assignments (no due date) — skip
        ma_due = datetime.utcfromtimestamp(ma["duedate"])
        if ma_due < cutoff:
            continue  # too old, likely last semester
        # Dedup against any non-voided Moodle deadline (iCal or prior
        # backfill). Match by course-code + fuzzy title + due-date.
        if _has_existing_deadline(
            ma, all_moodle_deadlines,
            title_threshold=BACKFILL_DEDUP_TITLE_THRESHOLD,
            due_window_hours=BACKFILL_DEDUP_DUE_HOURS,
        ):
            continue
        try:
            status_resp = ws.call(
                "mod_assign_get_submission_status",
                assignid=ma["assign_id"],
                userid=moodle_userid,
            )
        except _WSAuthError as e:
            user.moodle_ws_disconnect_reason = "invalidtoken"
            result.error = "auth"
            logger.warning("moodle_ws: backfill status auth fail user=%s: %s", user.user_id, e)
            return result
        except Exception as e:
            logger.info(
                "moodle_ws: backfill status fetch failed for assign=%s: %s",
                ma["assign_id"], e,
            )
            continue
        submitted, _reason = is_submitted(status_resp)
        completed_at = None
        if submitted:
            sub = (status_resp.get("lastattempt") or {}).get("submission") or {}
            ts = sub.get("timemodified") or sub.get("timecreated")
            if ts:
                completed_at = datetime.utcfromtimestamp(int(ts))
            else:
                completed_at = now
            state = "completed"
            result.backfilled_completed += 1
        elif ma_due < now:
            state = "missed"
            result.backfilled_missed += 1
        else:
            state = "planned"
            result.backfilled_planned += 1
        new_deadline = Deadline(
            deadline_id=str(uuid4()),
            user_id=user.user_id,
            title=ma["name"] or f"Moodle assignment {ma['assign_id']}",
            due_at_utc=ma_due,
            category_hint=_extract_course_code(ma["course_short"]) or ma["course_short"],
            state=state,
            external_source="moodle_ws_backfill",
            external_id=str(ma["assign_id"]),
            created_at=now,
            imported_at=now,
            completed_at=completed_at,
        )
        db.add(new_deadline)
        all_moodle_deadlines.append(new_deadline)  # so subsequent iterations dedup
        result.backfilled_titles.append(ma["name"] or f"#{ma['assign_id']}")
        logger.info(
            "moodle_ws: backfilled deadline ('%s', state=%s, due=%s)",
            ma["name"], state, ma_due,
        )

    # Stamp success — also clears any prior disconnect reason.
    user.moodle_ws_last_synced_at = now
    user.moodle_ws_disconnect_reason = None
    return result
