"""Deadline parsing component for natural language date expressions."""

import re
from datetime import date, timedelta
from typing import Callable, Dict, Optional


def _next_weekday(from_date: date, weekday: int) -> date:
    """Returns the next occurrence of a weekday (0=Monday, 6=Sunday)."""
    days_ahead = weekday - from_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return from_date + timedelta(days=days_ahead)


def _end_of_week(from_date: date) -> date:
    """Returns the Friday of the current week."""
    days_until_friday = 4 - from_date.weekday()  # 4 = Friday
    if days_until_friday < 0:
        days_until_friday += 7
    return from_date + timedelta(days=days_until_friday)


def _end_of_month(from_date: date) -> date:
    """Returns the last day of the current month."""
    if from_date.month == 12:
        next_month = date(from_date.year + 1, 1, 1)
    else:
        next_month = date(from_date.year, from_date.month + 1, 1)
    return next_month - timedelta(days=1)


class DeadlineParser:
    """Parses natural language deadline expressions into concrete dates."""
    
    # Mapping of weekday names to weekday numbers (0=Monday)
    WEEKDAYS = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    # Relative deadline patterns with their date calculation functions
    RELATIVE_PATTERNS: Dict[str, Callable[[date], date]] = {
        'today': lambda d: d,
        'tonight': lambda d: d,
        'tomorrow': lambda d: d + timedelta(days=1),
        'tomorrow evening': lambda d: d + timedelta(days=1),
        'tomorrow morning': lambda d: d + timedelta(days=1),
        'next week': lambda d: d + timedelta(weeks=1),
        'next monday': lambda d: _next_weekday(d, 0),
        'next tuesday': lambda d: _next_weekday(d, 1),
        'next wednesday': lambda d: _next_weekday(d, 2),
        'next thursday': lambda d: _next_weekday(d, 3),
        'next friday': lambda d: _next_weekday(d, 4),
        'next saturday': lambda d: _next_weekday(d, 5),
        'next sunday': lambda d: _next_weekday(d, 6),
        'end of week': lambda d: _end_of_week(d),
        'end of this week': lambda d: _end_of_week(d),
        'this week': lambda d: _end_of_week(d),
        'end of month': lambda d: _end_of_month(d),
        'end of this month': lambda d: _end_of_month(d),
    }
    
    def parse(self, phrase: str, reference_date: Optional[date] = None) -> Optional[date]:
        """
        Parses a deadline phrase into a concrete date.
        
        Args:
            phrase: Natural language deadline phrase
            reference_date: Reference date for relative calculations (defaults to today)
            
        Returns:
            Parsed date or None if phrase cannot be parsed
        """
        if not phrase:
            return None
        
        ref_date = reference_date or date.today()
        phrase_lower = phrase.lower().strip()
        
        # Try exact matches first
        if phrase_lower in self.RELATIVE_PATTERNS:
            return self.RELATIVE_PATTERNS[phrase_lower](ref_date)
        
        # Try "by <weekday>" pattern
        by_match = re.match(r'by\s+(\w+)', phrase_lower)
        if by_match:
            day_name = by_match.group(1)
            if day_name in self.WEEKDAYS:
                return _next_weekday(ref_date, self.WEEKDAYS[day_name])
        
        # Try standalone weekday names
        for day_name, day_num in self.WEEKDAYS.items():
            if day_name in phrase_lower:
                return _next_weekday(ref_date, day_num)
        
        # Try "in N days/weeks" pattern
        in_match = re.match(r'in\s+(\d+)\s+(day|days|week|weeks)', phrase_lower)
        if in_match:
            num = int(in_match.group(1))
            unit = in_match.group(2)
            if 'week' in unit:
                return ref_date + timedelta(weeks=num)
            else:
                return ref_date + timedelta(days=num)
        
        # Try "N days" pattern
        days_match = re.match(r'(\d+)\s+days?', phrase_lower)
        if days_match:
            num = int(days_match.group(1))
            return ref_date + timedelta(days=num)
        
        return None
    
    def extract_deadline_phrase(self, text: str) -> Optional[str]:
        """
        Extracts a deadline phrase from text.
        
        Args:
            text: Text to search for deadline phrases
            
        Returns:
            Extracted deadline phrase or None
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Patterns to search for
        patterns = [
            r'by\s+(tomorrow|today|tonight|next\s+\w+|end\s+of\s+(?:this\s+)?\w+|\w+day)',
            r'before\s+(tomorrow|today|tonight|next\s+\w+|\w+day)',
            r'(tomorrow\s*(?:evening|morning|afternoon)?)',
            r'(today|tonight)',
            r'(next\s+(?:week|monday|tuesday|wednesday|thursday|friday|saturday|sunday))',
            r'(end\s+of\s+(?:this\s+)?(?:week|month))',
            r'(this\s+week)',
            r'in\s+(\d+\s+(?:day|days|week|weeks))',
            r'(\w+day)\s+(?:evening|morning|afternoon)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def is_valid_deadline(self, parsed_date: date, reference_date: Optional[date] = None) -> bool:
        """
        Checks if a parsed deadline is valid (in the future and within reasonable range).
        
        Args:
            parsed_date: The parsed deadline date
            reference_date: Reference date for comparison
            
        Returns:
            True if deadline is valid
        """
        ref_date = reference_date or date.today()
        
        # Deadline should be on or after reference date
        if parsed_date < ref_date:
            return False
        
        # Deadline should be within 1 year
        max_date = ref_date + timedelta(days=365)
        if parsed_date > max_date:
            return False
        
        return True
