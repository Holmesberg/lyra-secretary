"""Natural language task parser."""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import dateparser

from app.schemas.parse import ParseResponse
from app.schemas.task import TaskParseResponse
from app.db.session import SessionLocal
from app.db.models import CategoryMapping


class TaskParser:
    """Parse natural language into structured task data."""
    
    def __init__(self, *, use_db_categories: bool = True):
        self.db = SessionLocal() if use_db_categories else None
    
    def parse(self, text: str) -> TaskParseResponse:
        """
        Parse natural language text into task components.
        
        Args:
            text: Natural language task description
            
        Returns:
            TaskParseResponse with extracted data and confidence score
        """
        text = text.strip()
        ambiguities = []
        
        # Extract title (everything before time indicators)
        title, remaining = self._extract_title(text)
        
        # Extract time components
        start, end, duration_minutes, time_confidence = self._extract_time(
            remaining or text
        )
        
        # If no time found, try full text
        if start is None:
            start, end, duration_minutes, time_confidence = self._extract_time(text)
            if start is not None:
                title, _ = self._extract_title(
                    re.sub(r'\b(at|from|@)\b.*', '', text, flags=re.IGNORECASE)
                )
        
        # Handle missing end time
        if start and end is None and duration_minutes is None:
            ambiguities.append("duration_missing")
        
        # Infer category (from static mappings)
        category = self._infer_category(title)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            title, start, end, duration_minutes, time_confidence
        )
        
        # If end is missing but duration exists, calculate end
        if start and end is None and duration_minutes:
            end = start + timedelta(minutes=duration_minutes)
        
        # Return raw parsed times (no timezone awareness)
        start_raw = start if start else datetime.now()
        end_raw = end if end else None
        
        return TaskParseResponse(
            title=title or "Untitled Task",
            start=start_raw,
            end=end_raw,
            duration_minutes=duration_minutes,
            category=category,
            confidence=confidence,
            ambiguities=ambiguities
        )
    
    def parse_chained(self, text: str) -> list[TaskParseResponse]:
        """
        Parse a compound request containing multiple tasks separated by "then".

        Each segment after the first inherits the end time of the previous task
        as its start time when no explicit start is given.

        Returns a list of TaskParseResponse objects in order.
        Single-task inputs return a one-element list.
        """
        segments = [s.strip() for s in re.split(r'\s+then\s+', text, flags=re.IGNORECASE) if s.strip()]
        if len(segments) == 1:
            return [self.parse(text)]

        results = []
        prev_end: Optional[datetime] = None

        for segment in segments:
            title, remaining = self._extract_title(segment)
            start, end, duration_minutes, time_confidence = self._extract_time(remaining or segment)
            if start is None:
                start, end, duration_minutes, time_confidence = self._extract_time(segment)

            # Chain: if no explicit start time, pick up where the previous task ended
            if start is None and prev_end is not None:
                start = prev_end
                if duration_minutes:
                    end = start + timedelta(minutes=duration_minutes)

            ambiguities = []
            if start and end is None and duration_minutes is None:
                ambiguities.append("duration_missing")

            if start and end is None and duration_minutes:
                end = start + timedelta(minutes=duration_minutes)

            category = self._infer_category(title or "")
            confidence = self._calculate_confidence(title, start, end, duration_minutes, time_confidence)
            start_raw = start if start else datetime.now()

            results.append(TaskParseResponse(
                title=title or "Untitled Task",
                start=start_raw,
                end=end,
                duration_minutes=duration_minutes,
                category=category,
                confidence=confidence,
                ambiguities=ambiguities,
            ))
            prev_end = end  # carry forward for next segment

        return results

    def _extract_title(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract task title from text.
        
        Returns:
            (title, remaining_text)
        """
        time_indicators = r'\b(at|from|@|tomorrow|today|tonight|in|next|this)\b|\bfor\b(?=\s*\d)'
        
        match = re.search(time_indicators, text, re.IGNORECASE)
        if match:
            title = text[:match.start()].strip()
            remaining = text[match.start():].strip()
            return title, remaining
        
        return text, None
    
    def _extract_time(
        self, text: str
    ) -> Tuple[Optional[datetime], Optional[datetime], Optional[int], float]:
        """
        Extract time components from text.
        
        Returns:
            (start, end, duration_minutes, confidence)
        """
        if not text:
            return None, None, None, 0.0
        
        # Use dateparser with no timezone awareness
        settings_dict = {
            'PREFER_DATES_FROM': 'future',
        }
        
        duration_minutes = self._extract_duration(text)
        
        # Clean text of duration strings before passing to dateparser
        duration_pattern = r'\b(?:for\s+)?(?:\d+(?:\.\d+)?|\d+\s*[-–]\s*\d+)\s*(?:hours?|hrs?|h|minutes?|mins?|m)\b'
        clean_text = re.sub(duration_pattern, '', text, flags=re.IGNORECASE).strip()
        # Strip trailing/leading artifacts that duration extraction might leave behind
        clean_text = re.sub(r'^\s*(for|and)\b\s*', '', clean_text, flags=re.IGNORECASE).strip()
        clean_text = re.sub(r'\s*\b(for|and)\b\s*$', '', clean_text, flags=re.IGNORECASE).strip()
        
        parsed = None
        if clean_text:
            parsed = dateparser.parse(clean_text, settings=settings_dict)
            
        if parsed:
            # If time is in past (same day), adjust to tomorrow
            now = datetime.now()
            if parsed.date() == now.date() and parsed.time() < now.time():
                parsed = parsed + timedelta(days=1)
            
            end = self._extract_end_time(text, parsed)
            
            return parsed, end, duration_minutes, 0.85
            
        if duration_minutes is not None:
            return None, None, duration_minutes, 0.5
            
        return None, None, None, 0.0
    
    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract duration in minutes from text."""
        # Range pattern (e.g., "2-3 hours") → use MAX
        range_pattern = r'(\d+)\s*[-–]\s*(\d+)\s*(hours?|hrs?|h|minutes?|mins?|m)'
        match = re.search(range_pattern, text, re.IGNORECASE)
        if match:
            max_val = int(match.group(2))
            unit = match.group(3).lower()
            
            if 'h' in unit:
                return max_val * 60
            else:
                return max_val
        
        # Single duration
        single_pattern = r'(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)'
        match = re.search(single_pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            if 'h' in unit:
                return int(value * 60)
            else:
                return int(value)
        
        return None
    
    def _extract_end_time(
        self, text: str, start: datetime
    ) -> Optional[datetime]:
        """Try to extract explicit end time."""
        patterns = [
            r'(?:to|until|till|-|–)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
            r'(?:ends?\s+at)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                end_str = match.group(1)
                end = dateparser.parse(
                    end_str,
                    settings={'RELATIVE_BASE': start}
                )
                if end and end > start:
                    return end
        
        return None
    
    def _infer_category(self, title: str) -> Optional[str]:
        """Infer category from static keyword mappings."""
        if self.db is None:
            return None
        title_lower = title.lower()
        
        # Query database for matching keywords
        for word in title_lower.split():
            mapping = self.db.query(CategoryMapping).filter(
                CategoryMapping.keyword == word
            ).first()
            
            if mapping:
                return mapping.category
        
        return None
    
    def _calculate_confidence(
        self,
        title: Optional[str],
        start: Optional[datetime],
        end: Optional[datetime],
        duration: Optional[int],
        time_confidence: float
    ) -> float:
        """Calculate overall parsing confidence."""
        confidence = 0.0
        
        if title and len(title) > 1:
            confidence += 0.3
        
        if start:
            confidence += 0.3
        
        if end or duration:
            confidence += 0.2

        confidence += time_confidence * 0.2

        return min(confidence, 1.0)


# ──────────────────────────────────────────────────────────────────────
# Loop 11 — scope-bullet counter (alembic 033, 2026-04-26).
# Counts bullet markers in `task.description` to populate
# `task.scope_bullet_count_at_plan` (at create) and
# `scope_bullet_count_at_execute` (at complete). Operationalizes
# `scope_density` per MANIFESTO Rule 12 amendment.
# Pattern: line starts with optional whitespace then one of [-*•·].
# Matches markdown-style bullets, asterisk-bullets, and unicode bullets.
# Known false positive: dashes inside fenced code blocks (e.g.
# ```bash\n- ls\n```) are counted. Documented as v1 instrument
# approximation — not fixed.
# ──────────────────────────────────────────────────────────────────────

BULLET_PATTERN = re.compile(r"^\s*[-*•·]", re.MULTILINE)


def extract_scope_bullets(description: Optional[str]) -> Optional[int]:
    """Count bullet markers in task description.

    None or empty description → None (distinguishable from 0, which
    means "description present but has no bullets").

    Bullet rule: line starts with optional whitespace, then one of
    `-`, `*`, `•` (U+2022), or `·` (U+00B7). Mid-line dashes do NOT
    count (e.g., "task - urgent" is 0 bullets).

    See MANIFESTO Rule 12 amendment (2026-04-26) for the research
    interpretation: this count is the operational definition of
    `description_item_count` in the scope_density formula.
    """
    if not description:
        return None
    return len(BULLET_PATTERN.findall(description))


# ──────────────────────────────────────────────────────────────────────
# Loop 11 Phase G — parser Pass 2 keyword-overlap deadline inference
# (alembic 033, 2026-04-26).
#
# When a user creates a task without an explicit deadline_id, attempt
# to bind the task to one of the user's active/planned deadlines based
# on keyword overlap between the task title and the deadline
# title+description.
#
# This is Pass 2 of the binding strategy from
# `docs/deadline_mechanism_design.md §"Inference mechanism"`. Pass 3
# (semantic similarity) is deferred to a later commit.
#
# Threshold: overlap_ratio ≥ 0.5 AND ≥ 1 non-stoplist token shared.
# Source: 'parser_auto'. Confidence: the overlap_ratio itself.
#
# Stoplist intentionally short — common scheduling words ("today",
# "tomorrow", time-of-day terms) and ultra-common short tokens. The
# parser already strips date/time tokens upstream, so by the time we
# get the title here it should be mostly content words.
# ──────────────────────────────────────────────────────────────────────

# Keep this list short. Overly aggressive stop-listing would zero out
# overlaps for short user titles.
_DEADLINE_BINDING_STOPLIST = frozenset({
    "the", "a", "an", "and", "or", "but", "of", "to", "for", "in", "on",
    "at", "by", "from", "with", "about", "as",
    "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "i", "me", "my", "you", "your", "we", "our", "they", "their",
    "task", "todo", "thing", "stuff",
    # Common scheduling fillers — parser strips most date/time but
    # leftover words like "today" / "tomorrow" can still slip through
    # in titles like "study today".
    "today", "tomorrow", "tonight", "morning", "afternoon", "evening",
    "now", "later", "soon", "asap",
})


_TOKENIZE_RE = re.compile(r"[A-Za-z0-9]+", re.UNICODE)


def _tokenize_for_binding(text: Optional[str]) -> set[str]:
    """Lowercase, strip stop-listed and short tokens, return as a set."""
    if not text:
        return set()
    tokens = _TOKENIZE_RE.findall(text.lower())
    return {
        t for t in tokens
        if len(t) >= 3 and t not in _DEADLINE_BINDING_STOPLIST
    }


def infer_deadline_binding(
    task_title: str,
    candidate_deadlines: list,
    threshold: float = 0.5,
) -> Optional[tuple[object, float]]:
    """Pass 2 keyword-overlap inference.

    Args:
        task_title: the title of the task being created.
        candidate_deadlines: a list of Deadline ORM rows that are
            bindable for this user (state ∈ {planned, active}, voided_at
            IS NULL). Caller is responsible for the filter.
        threshold: minimum overlap_ratio for a binding to fire. Default
            0.5 per design spec.

    Returns:
        (deadline, confidence) of the BEST match if any candidate
        meets the threshold, else None. Confidence equals the
        overlap_ratio.

    Algorithm:
        For each candidate deadline:
          deadline_tokens = tokenize(title + " " + description)
          task_tokens = tokenize(task_title)
          if not task_tokens or not deadline_tokens: skip (no signal)
          shared = task_tokens ∩ deadline_tokens
          ratio = len(shared) / len(task_tokens)
          require: ratio ≥ threshold AND len(shared) ≥ 1
        Pick the candidate with highest ratio; ties broken by earliest
        due_at_utc (urgency wins).

    The asymmetric ratio (over task_tokens, NOT deadline_tokens) is
    deliberate: a task whose title is fully contained in the deadline
    description should match strongly, even if the deadline has lots
    of unrelated words.
    """
    task_tokens = _tokenize_for_binding(task_title)
    if not task_tokens:
        return None

    best: Optional[tuple[object, float]] = None
    for deadline in candidate_deadlines:
        deadline_text = " ".join(
            x for x in [deadline.title, deadline.description] if x
        )
        deadline_tokens = _tokenize_for_binding(deadline_text)
        if not deadline_tokens:
            continue
        shared = task_tokens & deadline_tokens
        if len(shared) < 1:
            continue
        ratio = len(shared) / len(task_tokens)
        if ratio < threshold:
            continue
        # Tie-break: among equal ratios, prefer the deadline with the
        # earliest due_at_utc.
        if best is None or ratio > best[1] or (
            ratio == best[1] and deadline.due_at_utc < best[0].due_at_utc
        ):
            best = (deadline, round(ratio, 3))
    return best
