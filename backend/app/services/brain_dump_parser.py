"""Brain-dump multi-item heuristic parser (2026-04-28).

Synchronously splits a free-text brain-dump into tasks + deadlines. NO
LLM dependency — operator-locked: "deterministic over magic" for the
onboarding moment. Async LLM enrichment still fires per-task via the
existing `llm_enrichment` worker and may post a "Possible better match"
chip later via the trust-not-rewrite contract.

Algorithm:
  1. Split raw text on commas / newlines / semicolons / " then "
  2. For each segment, classify as task vs deadline via keyword set
  3. Extract anchor date/time via dateparser (already wired)
  4. Build BrainDumpParsedItem with confidence per signal strength
  5. Run deadline_heuristic.score_deadlines for each task against the
     parsed-deadline set → BrainDumpBindingSuggestion array

Confidence bands:
  ≥0.85 — explicit deadline keyword + parseable date, OR action verb
          + parseable date
  0.45–0.85 — one signal (date OR keyword) but ambiguous typing
  <0.45 — bare segment, brittle classification (still committed but
          flagged in UI for edit)

Tier mapping for bindings (mirrors the existing chip's Tier 1/2/3):
  ≥0.85 → tier1_auto (UI shows pre-checked binding)
  0.45–0.85 → tier2_ask (UI shows "Bind? [Yes] [No]" pill)
  <0.45 → tier3_skip (no binding suggested)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import dateparser

from app.db.models import Deadline
from app.schemas.brain_dump import (
    BrainDumpBindingSuggestion,
    BrainDumpParsedItem,
    BrainDumpParseResponse,
)
from app.services.deadline_heuristic import score_deadlines

logger = logging.getLogger(__name__)


# Keywords that strongly signal a deadline-typed item rather than a task.
# Match on whole-word boundaries via _has_deadline_kw — substring match
# would false-positive ("submission" matched inside "submitting").
#
# Note: many of these (test, final, presentation) double as English
# verbs/adjectives. The classifier prioritises a leading action verb
# over deadline-keyword presence so phrases like "test the API tomorrow"
# or "study for midterm" stay as tasks.
DEADLINE_KEYWORDS = {
    "deadline", "due", "submission",
    "exam", "exams", "final", "finals", "midterm", "midterms",
    "test", "quiz", "assignment", "presentation",
}

# Action verbs at start of segment → task. Lowercase match on first word
# after stripping leading punctuation.
TASK_LEADING_VERBS = {
    "read", "write", "do", "study", "review", "watch",
    "complete", "finish", "start", "begin", "draft", "outline",
    "prepare", "practice", "research", "build", "code",
    "debug", "fix", "ship", "deploy", "test", "edit", "revise",
    "send", "email", "call", "meet", "discuss", "plan",
    "organize", "clean", "fill", "fillout", "submit",
    "initiate", "trigger", "configure", "install",
    "attend", "join", "lecture",
    "go", "make", "buy", "get", "pick", "drop", "schedule",
    "give", "present", "show", "run", "take", "set",
    "check", "follow", "ask", "reply", "respond", "update",
    "wash", "cook", "pay", "book", "reserve", "order",
    "create", "design", "draw", "paint", "record", "shoot",
    "memorize", "rehearse", "summarize",
}

# Tokens that anchor a date/time. Matched as alternatives — phrases
# combining multiple alternatives ("Friday at 10am") are reassembled by
# _extract_when via span-join.
DATE_HINTS = re.compile(
    r"\b("
    # Relative anchors
    r"today|tomorrow|tonight|tomorrow\s+morning|tomorrow\s+night|"
    # Time-of-day anchors
    r"morning|afternoon|evening|noon|midnight|"
    # Days of week
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    # Modifier prefixes pulling in the next token
    r"next\s+\w+|this\s+\w+|last\s+\w+|"
    # "in N <unit>"
    r"in\s+\d+\s+(?:hours?|days?|weeks?|months?|years?)|"
    # Slash dates: 16/5 or 16/5/2026
    r"\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?|"
    # Times: 10am, 3 PM, 14:30, 3:30pm, 9:00 a.m.
    r"\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)|"
    r"\d{1,2}:\d{2}(?:\s*(?:am|pm|a\.m\.|p\.m\.))?|"
    # "the 15th" / "the 1st"
    r"the\s+\d{1,2}(?:st|nd|rd|th)?|"
    # Month names (full + 3-letter) + day. "may" without a number is
    # excluded because of the trailing \s+\d to avoid matching the
    # modal verb "may". Sept variant included.
    r"(?:january|february|march|april|may|june|july|august|"
    r"september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"\s+\d{1,2}(?:st|nd|rd|th)?"
    r")\b",
    re.IGNORECASE,
)

# Splitting: comma, newline, semicolon, " then ", " + ".
# We preserve "and" as in-segment text — joining verbs across "and"
# usually creates one logical task ("read X and review Y" is one item
# in practice for brain-dump format). " then " is a sequence marker.
SEGMENT_SPLIT = re.compile(r"[,\n;]+|\s+then\s+|\s+\+\s+", re.IGNORECASE)


# LYR-115 fix (2026-04-30): explicit user-provided durations.
# Surfaced by stress test cases D2/D3/D5/D7/D8/E1/E3/E5/E7/E8 — the
# parser was ignoring "60 min", "30 minutes", etc. and falling back
# to the 30-min default, silently breaking the planned-vs-executed
# measurement contract.
#
# Regex is conservative — only matches digit + explicit time unit:
#   - minute / minutes / min / mins
#   - hour / hours / hr / hrs
#   - h (single letter, only word-boundary matched)
# Optional "for " prefix swallowed so "for 30 min" doesn't leave
# "for" dangling in the title after duration strip.
# Excludes single-letter "m" (too prone to false positives in
# productivity vocab like "for the m..."). Operator can revisit.
DURATION_RE = re.compile(
    r"\b(?:for\s+)?(\d{1,3}(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?|h)\b",
    re.IGNORECASE,
)


# Time-range parsing fix (2026-04-30): inputs like "2-4pm",
# "1:30-3:30pm", "2-2:30pm" weren't extracting duration AND were
# leaving title debris like "study 1" / "break". Surfaced by stress
# test cases F1, F3, F4. End am/pm is required to anchor the range;
# start am/pm is inferred from end if missing.
TIME_RANGE_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*[-–]\s*"
    r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
    re.IGNORECASE,
)


def _extract_duration(segment: str) -> Optional[int]:
    """Extract user-provided duration in minutes. Returns None when no
    explicit duration is present (caller falls back to default).

    Matches patterns like "60 min", "30 minutes", "1 hr", "1.5 hours",
    "90 mins", "2h" (with word boundary). Caps at the schema's
    BrainDumpCommitItem.duration_minutes max (720) — values above
    are clamped (rare; "12 hours" → 720 not 1440).
    """
    match = DURATION_RE.search(segment)
    if match is None:
        return None
    value_str, unit = match.group(1), match.group(2).lower()
    try:
        value = float(value_str)
    except (ValueError, TypeError):
        return None
    if unit.startswith("min"):
        minutes = value
    else:  # hour / hours / hr / hrs / h
        minutes = value * 60
    minutes_int = int(round(minutes))
    if minutes_int < 1:
        return None
    return min(720, minutes_int)


def _extract_time_range_and_normalize(segment: str) -> tuple[Optional[int], str]:
    """Detect time-range patterns ("2-4pm", "1:30-3pm") and return:
      - duration_minutes derived from end-start (or None if no range)
      - segment with the range replaced by JUST the start time so
        downstream dateparser can resolve it normally

    The caller uses the normalized segment for both `_extract_when`
    and `_strip_date_tokens` so date extraction sees a clean single
    time and the title-strip removes only the start time.

    Edge cases:
      - End am/pm REQUIRED (anchors the inference); ranges like "2-4"
        without any am/pm marker aren't parsed (too ambiguous).
      - Start am/pm inferred from end when omitted ("2-4pm" → both pm).
      - Crossing midnight (e.g., "11pm-1am") is flagged as duration
        mod-24h ("11pm-1am" → 120 min, two hours forward).
      - Invalid ranges (negative or >720 min) → returned as no-match.
    """
    match = TIME_RANGE_RE.search(segment)
    if match is None:
        return None, segment
    try:
        start_h = int(match.group(1))
        start_m = int(match.group(2) or 0)
        start_ampm = (match.group(3) or "").lower()
        end_h = int(match.group(4))
        end_m = int(match.group(5) or 0)
        end_ampm = match.group(6).lower()
    except (ValueError, AttributeError, TypeError):
        return None, segment

    if not start_ampm:
        # End-only am/pm: assume start has the same am/pm as end (the
        # natural reading of "2-4pm" is "2pm to 4pm").
        start_ampm = end_ampm

    # Convert to 24h.
    def to_24h(h: int, ampm: str) -> int:
        if ampm == "pm" and h < 12:
            return h + 12
        if ampm == "am" and h == 12:
            return 0
        return h

    s24, e24 = to_24h(start_h, start_ampm), to_24h(end_h, end_ampm)
    start_total = s24 * 60 + start_m
    end_total = e24 * 60 + end_m
    duration = end_total - start_total
    if duration <= 0:
        # Cross-midnight — wrap around 24h.
        duration += 24 * 60
    if duration <= 0 or duration > 720:
        return None, segment

    # Replace the matched range with the start time as a clean
    # parseable token (e.g., "2pm" or "1:30pm"). dateparser handles
    # this format natively.
    if start_m == 0:
        start_str = f"{start_h % 12 or 12}{start_ampm}"
    else:
        start_str = f"{start_h % 12 or 12}:{start_m:02d}{start_ampm}"
    new_segment = segment[: match.start()] + start_str + segment[match.end() :]
    return duration, new_segment


def _has_deadline_kw(segment_lower: str) -> bool:
    """True if a deadline keyword appears as a whole word in the
    segment. Substring match ('submit' in 'submitting') would false-
    positive."""
    return any(
        re.search(rf"\b{re.escape(kw)}\b", segment_lower)
        for kw in DEADLINE_KEYWORDS
    )


def _now_local(now_iso: Optional[str]) -> datetime:
    """Resolve the user's "current local time" anchor. Falls back to
    server local time. Strips tz to match Lyra's naive-internal
    convention."""
    if now_iso:
        try:
            dt = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None)
        except (ValueError, TypeError):
            pass
    return datetime.now()


def _classify_kind(segment: str) -> tuple[str, float]:
    """Return (kind, kind_confidence) for a single segment.

    Decision order (operator-tuned 2026-04-29 after edge-case battery):
      1. LEADING ACTION VERB WINS — even when a deadline keyword is
         present elsewhere in the segment. "study for midterm tomorrow"
         is a TASK (commit to study), even though "midterm" is a
         deadline keyword. The user's intent is the verb.
      2. Deadline keyword (no leading verb) → deadline.
      3. Bare date → task with low confidence.
      4. Bare segment → task with very low confidence.
    """
    lower = segment.lower()
    has_deadline_kw = _has_deadline_kw(lower)
    # First alpha word after any leading punctuation / bullet / digits.
    # "1. study chapter" → "study"; "- read chapter" → "read"
    first_word = re.match(r"^[\W_\d]*([a-z]+)", lower)
    leading_verb = first_word.group(1) if first_word else ""
    has_action = leading_verb in TASK_LEADING_VERBS
    has_date = bool(DATE_HINTS.search(segment))

    # 1. Action verb at the front — TASK, even if deadline kw appears.
    if has_action and has_date:
        return "task", 0.88
    if has_action:
        return "task", 0.70
    # 2. Deadline keyword without a leading verb.
    if has_deadline_kw and has_date:
        return "deadline", 0.92
    if has_deadline_kw:
        return "deadline", 0.78  # demoted to task downstream if no date
    # 3. Date alone, no verb, no deadline keyword → ambiguous, default task.
    if has_date:
        return "task", 0.55
    # 4. Bare segment.
    return "task", 0.42


# dateparser has surprising gaps: it returns None for "this weekend",
# "this evening", "this morning", "tomorrow night", and resolves bare
# "the Nth" to the SAME-month Nth even when that's in the past. We
# rewrite these forms before invoking the parser, then post-validate
# that the result lies in the future.
# dateparser surprisingly returns None for "next <weekday>" / "next
# weekend" / "this weekend" / "this evening" / "this morning" — it
# only resolves the bare day. We pre-rewrite these to forms it
# accepts. PREFER_DATES_FROM=future then handles the future-bumping.
_PHRASE_REWRITES = [
    (re.compile(r"\bthis weekend\b", re.IGNORECASE), "saturday"),
    (re.compile(r"\bnext weekend\b", re.IGNORECASE), "saturday"),
    (re.compile(r"\bthis evening\b", re.IGNORECASE), "today 18:00"),
    (re.compile(r"\bthis afternoon\b", re.IGNORECASE), "today 14:00"),
    (re.compile(r"\bthis morning\b", re.IGNORECASE), "today 09:00"),
    (re.compile(r"\btomorrow night\b", re.IGNORECASE), "tomorrow 20:00"),
    (re.compile(r"\btomorrow morning\b", re.IGNORECASE), "tomorrow 09:00"),
    (re.compile(r"\btonight\b", re.IGNORECASE), "today 20:00"),
    # "next monday" → "monday" (PREFER_DATES_FROM=future bumps to
    # the next occurrence; "next" prefix breaks dateparser).
    (re.compile(r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE),
     r"\1"),
    (re.compile(r"\bthis\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE),
     r"\1"),
]


def _rewrite_phrases(segment: str) -> str:
    """Apply pre-dateparser phrase substitutions for forms dateparser
    fails to interpret natively."""
    out = segment
    for pat, repl in _PHRASE_REWRITES:
        out = pat.sub(repl, out)
    return out


def _bump_to_future(parsed: datetime, now_local: datetime) -> datetime:
    """If `parsed` is in the past relative to `now_local`, bump it
    forward by the smallest sensible interval.

    Used for "the 15th" / "May 16" / similar — dateparser sometimes
    returns the same-month occurrence even when it's already passed.
    Heuristic: if the date is more than 12h in the past, advance by
    one month. If it's <12h in the past, leave it (could be a same-day
    deadline the user is racing).
    """
    delta = (now_local - parsed).total_seconds()
    if delta <= 12 * 3600:
        return parsed
    # Bump month forward
    if parsed.month == 12:
        return parsed.replace(year=parsed.year + 1, month=1)
    return parsed.replace(month=parsed.month + 1)


def _extract_when(segment: str, now_local: datetime) -> Optional[datetime]:
    """Run dateparser against the segment with future-dates preference.
    Returns naive local datetime or None.

    Three-phase strategy:
      1. Phrase-rewrite ("this weekend" → "next Saturday").
      2. Try parsing the whole rewritten segment.
      3. If that fails, extract every DATE_HINTS regex span and try
         the joined-span substring first, then individual spans by
         length descending.
      4. Post-validate via `_bump_to_future` so "the 15th" doesn't
         resolve to a past date.
    """
    rewritten = _rewrite_phrases(segment)
    settings = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": now_local,
        # Lyra's production timezone is Cairo and the onboarding audience uses
        # day/month numeric dates. Without this, dateparser treats ambiguous
        # slash dates as US-style month/day, so "6/9" lands on June 9 instead
        # of September 6 while the visible title has the date stripped.
        "DATE_ORDER": "DMY",
        "PREFER_LOCALE_DATE_ORDER": False,
    }
    try:
        parsed = dateparser.parse(rewritten, settings=settings)
        if parsed is not None:
            return _bump_to_future(parsed.replace(tzinfo=None), now_local)
    except Exception as e:
        logger.debug(f"brain_dump_parser: dateparser whole-segment failed on {segment!r}: {e}")

    # Extract candidate spans via DATE_HINTS regex. Each match is one
    # alternative (e.g. "Friday" OR "10am") so phrases like "Friday at
    # 10am" produce two adjacent matches. Try in this order:
    #   (a) the substring from the first match start to the last match
    #       end (catches "Friday 10am" / "Friday at 10am" by span join)
    #   (b) the longest individual match (fallback)
    spans = [m.span() for m in DATE_HINTS.finditer(rewritten)]
    if not spans:
        return None

    attempts: list[str] = []
    if spans:
        joined = rewritten[spans[0][0]:spans[-1][1]]
        attempts.append(joined)
    individual = sorted(
        (rewritten[s:e] for s, e in spans),
        key=lambda t: (-len(t), t),
    )
    attempts.extend(individual)

    seen: set[str] = set()
    for text in attempts:
        if text in seen:
            continue
        seen.add(text)
        try:
            parsed = dateparser.parse(text, settings=settings)
            if parsed is not None:
                return _bump_to_future(parsed.replace(tzinfo=None), now_local)
        except Exception as e:
            logger.debug(f"brain_dump_parser: dateparser span failed on {text!r}: {e}")
            continue
    return None


_TRAILING_PREP_RE = re.compile(
    r"\s+(at|on|by|before|after|until|till|from|to|in|the|for|of|"
    r"during|around|about|deadline|due)\s*$",
    re.IGNORECASE,
)
_LEADING_BULLET_RE = re.compile(
    r"^\s*(?:[-*•·●◦▪►▶]+\s+|\d+[.)]\s+|\(\d+\)\s+)",
)


def _strip_date_tokens(segment: str) -> str:
    """Remove date hints + duration tokens from a segment to produce a
    cleaner title.

    Cleanup passes (in order — order matters):
      1. Strip leading bullet markers ("- read", "* write", "1. study").
      2. Remove duration tokens ("60 min", "1.5 hours", "for 30 minutes")
         FIRST, before date stripping. If we stripped date first, the
         "for" in "for 30 min" might already be at end-of-string and
         not match the trailing-prep peel; doing duration first avoids
         that ordering trap. (LYR-115 fix 2026-04-30.)
      3. Remove every DATE_HINTS span. Phrases like "Friday at 10am"
         become "  at  ".
      4. Strip leading deadline framing words ("deadline:", "due ",
         "by ").
      5. Strip trailing prepositions left dangling by steps 2-3 ("call
         advisor at" → "call advisor"). Looped — consecutive trailing
         words like "at for" get peeled in two passes. (LYR-115 also
         clears the dangling-prep xfail because step 2 removes
         duration tokens, exposing trailing 'at'/'for' for step 5.)
      6. Collapse whitespace + trim punctuation.
    """
    cleaned = _LEADING_BULLET_RE.sub("", segment).strip()
    cleaned = DURATION_RE.sub(" ", cleaned)
    cleaned = DATE_HINTS.sub(" ", cleaned)
    cleaned = re.sub(
        r"^\s*(deadline\s*[:\-]?\s*|due\s+|by\s+)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Iteratively peel trailing prepositions / connectors. Cap at 4
    # passes so we never loop on pathological input.
    for _ in range(4):
        new = _TRAILING_PREP_RE.sub("", cleaned).rstrip()
        if new == cleaned:
            break
        cleaned = new
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;:-")
    return cleaned or segment.strip()


def _default_when_for_task(now_local: datetime, task_index: int) -> datetime:
    """Default scheduling when the segment has no parseable date.
    Stagger consecutive defaults by 30min so they don't all collide
    at the same moment in /today."""
    return now_local + timedelta(minutes=30 + 30 * task_index)


def _binding_tier(score: float) -> str:
    """Map heuristic score to chip-style tier label."""
    if score >= 0.85:
        return "tier1_auto"
    if score >= 0.45:
        return "tier2_ask"
    return "tier3_skip"


def parse_brain_dump(
    raw_text: str,
    now_local_iso: Optional[str] = None,
) -> BrainDumpParseResponse:
    """Heuristic fan-out of a free-text brain-dump into tasks + deadlines.

    Pure function — no DB access. The endpoint layer handles persistence
    via /commit. The deadline-binding step uses parsed deadlines only;
    pre-existing user deadlines aren't matched here (they would be in
    a /v1/brain-dump variant for non-onboarding users — out of scope
    for this commit).
    """
    now_local = _now_local(now_local_iso)
    raw = raw_text.strip()
    if not raw:
        return BrainDumpParseResponse(items=[], bindings=[], parser_status="empty")

    # Split on commas/newlines/semicolons/" then "
    segments = [s.strip() for s in SEGMENT_SPLIT.split(raw) if s.strip()]
    if not segments:
        return BrainDumpParseResponse(items=[], bindings=[], parser_status="empty")

    items: list[BrainDumpParsedItem] = []
    task_default_index = 0

    for seg in segments:
        # Two-stage extraction (LYR-115 + time-range fix 2026-04-30):
        # 1. Pull time-range patterns ("2-4pm") FIRST. Returns the
        #    range duration AND a normalized segment where the range
        #    is replaced by just the start time so dateparser sees
        #    a clean single time downstream.
        # 2. Pull explicit duration tokens ("60 min", "1.5 hours") on
        #    the normalized segment. Explicit duration wins over the
        #    range-derived duration if both are somehow present (rare).
        # 3. Date extraction + title stripping run on the normalized
        #    segment so the title doesn't get range-debris like
        #    "study 1" / "break".
        range_duration, normalized = _extract_time_range_and_normalize(seg)
        explicit_duration = _extract_duration(normalized)
        derived_duration = explicit_duration if explicit_duration is not None else range_duration

        kind, kind_conf = _classify_kind(normalized)
        when = _extract_when(normalized, now_local)
        title = _strip_date_tokens(normalized) or normalized
        # Cap title length defensively
        if len(title) > 200:
            title = title[:200].rstrip() + "…"

        # Confidence blend: kind classification + date-resolution success.
        # Date resolution adds confidence for both task and deadline cases.
        conf = kind_conf
        if when is not None:
            conf = min(1.0, conf + 0.05)

        if kind == "deadline":
            # Deadlines REQUIRE a when. If we couldn't parse one, demote
            # to a task — better to schedule it than reject it.
            if when is None:
                kind = "task"
                conf = max(0.40, conf - 0.20)

        if kind == "task":
            # Duration precedence: extracted (explicit user value) >
            # default (30 min). Clamp to schema bounds [1, 720].
            duration = derived_duration if derived_duration is not None else 30
            duration = max(1, min(720, duration))
            if when is None:
                when = _default_when_for_task(now_local, task_default_index)
                task_default_index += 1
                conf = max(0.35, conf - 0.10)
            items.append(BrainDumpParsedItem(
                item_id=str(uuid4()),
                kind="task",
                title=title,
                when_local=when,
                duration_minutes=duration,
                confidence=round(conf, 2),
            ))
        else:
            items.append(BrainDumpParsedItem(
                item_id=str(uuid4()),
                kind="deadline",
                title=title,
                when_local=when,
                duration_minutes=None,
                confidence=round(conf, 2),
            ))

    # Binding suggestions: for each task, score against parsed deadlines
    # using deadline_heuristic.score_deadlines. Build mock Deadline rows
    # with stable ids so we can map back to item_ids.
    parsed_deadlines = [i for i in items if i.kind == "deadline"]
    parsed_tasks = [i for i in items if i.kind == "task"]

    bindings: list[BrainDumpBindingSuggestion] = []
    if parsed_deadlines:
        # Build mock Deadline objects compatible with score_deadlines.
        # Only fields the heuristic reads: deadline_id + title.
        mock_deadlines = []
        item_id_for_deadline_id: dict[str, str] = {}
        for d in parsed_deadlines:
            mock = Deadline(
                deadline_id=d.item_id,  # reuse item_id as deadline_id for mapping
                title=d.title,
                user_id=0,  # not used by heuristic
                due_at_utc=d.when_local or now_local,
                state="planned",
            )
            mock_deadlines.append(mock)
            item_id_for_deadline_id[d.item_id] = d.item_id

        for t in parsed_tasks:
            match = score_deadlines(
                title=t.title,
                description=None,
                deadlines=mock_deadlines,
            )
            if not match.candidates:
                continue
            top = match.candidates[0]
            tier = _binding_tier(top.score)
            if tier == "tier3_skip":
                continue  # don't surface low-confidence bindings
            bindings.append(BrainDumpBindingSuggestion(
                task_item_id=t.item_id,
                deadline_item_id=top.deadline_id,
                deadline_title=top.title,
                confidence=top.score,
                tier=tier,
                source=top.source,
            ))

    return BrainDumpParseResponse(
        items=items,
        bindings=bindings,
        parser_status="heuristic_parsed",
    )
