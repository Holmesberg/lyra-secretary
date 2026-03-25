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
    
    def __init__(self):
        self.db = SessionLocal()
    
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
