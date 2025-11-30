"""Priority classification component for task urgency determination."""

from datetime import date, timedelta
from typing import List, Optional

from src.models import ExtractedTask, PriorityLevel


class PriorityClassifier:
    """Classifies task priority based on urgency indicators and deadlines."""
    
    # Words/phrases indicating critical priority
    CRITICAL_INDICATORS = [
        'critical', 'urgent', 'asap', 'immediately', 'emergency',
        'right away', 'right now', 'drop everything'
    ]
    
    # Words/phrases indicating high priority
    HIGH_INDICATORS = [
        'high priority', 'important', 'blocking', 'blocker',
        'affecting users', 'affecting the user', 'user experience',
        'affecting the user experience', "it's affecting",
        'before release', 'production issue',
        'customer impact', 'deadline', 'must have',
        'really slow', 'is slow'
    ]
    
    # Words/phrases indicating low priority
    LOW_INDICATORS = [
        'when possible', 'nice to have', 'low priority',
        'backlog', 'eventually', 'no rush',
        'whenever', 'if time permits'
    ]
    
    # Words/phrases indicating medium priority (not urgent but has deadline)
    MEDIUM_INDICATORS = [
        'can wait', 'next sprint', 'next week'
    ]
    
    def classify(
        self,
        task: ExtractedTask,
        deadline: Optional[date] = None,
        reference_date: Optional[date] = None
    ) -> PriorityLevel:
        """
        Classifies task priority based on indicators and deadline.
        
        Args:
            task: The extracted task to classify
            deadline: Parsed deadline date (if any)
            reference_date: Reference date for deadline urgency calculation
            
        Returns:
            PriorityLevel enum value
        """
        text_lower = task.raw_text.lower()
        indicators = task.priority_indicators
        
        # Check for "can wait" first - this explicitly indicates lower priority
        if 'can wait' in text_lower:
            return PriorityLevel.MEDIUM
        
        # Check for critical indicators
        if self._has_critical_indicators(text_lower, indicators):
            return PriorityLevel.CRITICAL
        
        # Check deadline urgency - very short deadlines override other indicators
        deadline_priority = self._check_deadline_urgency(deadline, reference_date)
        if deadline_priority == PriorityLevel.CRITICAL:
            return PriorityLevel.CRITICAL
        
        # Check for high indicators
        if self._has_high_indicators(text_lower, indicators):
            return PriorityLevel.HIGH
        
        # Apply non-critical deadline priority
        if deadline_priority:
            return deadline_priority
        
        # Check for low indicators
        if self._has_low_indicators(text_lower, indicators):
            return PriorityLevel.LOW
        
        # Default to medium
        return PriorityLevel.MEDIUM
    
    def _has_critical_indicators(self, text: str, indicators: List[str]) -> bool:
        """Checks for critical priority indicators."""
        # Check in provided indicators
        for ind in indicators:
            if ind.lower() in [c.lower() for c in self.CRITICAL_INDICATORS]:
                return True
        
        # Check in text
        for indicator in self.CRITICAL_INDICATORS:
            if indicator in text:
                return True
        
        return False
    
    def _has_high_indicators(self, text: str, indicators: List[str]) -> bool:
        """Checks for high priority indicators."""
        # Check in provided indicators
        for ind in indicators:
            if ind.lower() in [h.lower() for h in self.HIGH_INDICATORS]:
                return True
        
        # Check in text
        for indicator in self.HIGH_INDICATORS:
            if indicator in text:
                return True
        
        return False
    
    def _has_low_indicators(self, text: str, indicators: List[str]) -> bool:
        """Checks for low priority indicators."""
        # Check in provided indicators
        for ind in indicators:
            if ind.lower() in [l.lower() for l in self.LOW_INDICATORS]:
                return True
        
        # Check in text
        for indicator in self.LOW_INDICATORS:
            if indicator in text:
                return True
        
        return False
    
    def _check_deadline_urgency(
        self,
        deadline: Optional[date],
        reference_date: Optional[date] = None
    ) -> Optional[PriorityLevel]:
        """
        Determines priority based on deadline proximity.
        
        Args:
            deadline: The task deadline
            reference_date: Reference date for comparison
            
        Returns:
            PriorityLevel if deadline affects priority, None otherwise
        """
        if not deadline:
            return None
        
        ref_date = reference_date or date.today()
        days_until = (deadline - ref_date).days
        
        # Very urgent: due today or tomorrow
        if days_until <= 1:
            return PriorityLevel.CRITICAL
        
        # Urgent: due within 2 days
        if days_until <= 2:
            return PriorityLevel.HIGH
        
        # Within a week - don't override, let other indicators decide
        return None
    
    def classify_from_text(
        self,
        text: str,
        deadline: Optional[date] = None,
        reference_date: Optional[date] = None
    ) -> PriorityLevel:
        """
        Convenience method to classify priority directly from text.
        
        Args:
            text: Task description text
            deadline: Parsed deadline date
            reference_date: Reference date for calculations
            
        Returns:
            PriorityLevel enum value
        """
        # Create a minimal ExtractedTask
        task = ExtractedTask(
            description=text,
            raw_text=text,
            priority_indicators=[]
        )
        return self.classify(task, deadline, reference_date)
