"""Property-based tests for priority classification."""

from datetime import date, timedelta
from hypothesis import given, strategies as st, settings

from src.models import ExtractedTask, PriorityLevel
from src.priority_classifier import PriorityClassifier


# Strategy for task descriptions
task_text_strategy = st.text(min_size=10, max_size=200)

# Strategy for priority indicators
priority_indicator_strategy = st.lists(
    st.text(min_size=1, max_size=30),
    min_size=0, max_size=5
)


# Feature: meeting-task-assignment, Property 8: Priority classification validity
# For any ExtractedTask, the PriorityClassifier SHALL return exactly one of the
# four valid PriorityLevel values: Critical, High, Medium, or Low.
# **Validates: Requirements 6.1, 6.5**
@settings(max_examples=100)
@given(
    description=task_text_strategy,
    raw_text=task_text_strategy,
    indicators=priority_indicator_strategy
)
def test_priority_classification_validity(description, raw_text, indicators):
    """Property 8: Classification always returns a valid PriorityLevel."""
    classifier = PriorityClassifier()
    
    task = ExtractedTask(
        description=description,
        raw_text=raw_text,
        priority_indicators=indicators
    )
    
    result = classifier.classify(task)
    
    # Result must be a valid PriorityLevel
    assert isinstance(result, PriorityLevel), f"Result should be PriorityLevel, got {type(result)}"
    assert result in list(PriorityLevel), f"Result {result} is not a valid PriorityLevel"
    
    # Verify it's one of the four expected values
    valid_values = {PriorityLevel.CRITICAL, PriorityLevel.HIGH, PriorityLevel.MEDIUM, PriorityLevel.LOW}
    assert result in valid_values, f"Result {result} is not in valid values"


# Feature: meeting-task-assignment, Property 9: Urgency indicator priority boost
# For any task description containing critical indicators ("critical", "blocking", "urgent"),
# the classified priority SHALL be Critical or High (never Medium or Low).
# **Validates: Requirements 6.2, 6.3**
@settings(max_examples=100)
@given(
    base_text=st.text(min_size=5, max_size=100),
    critical_indicator=st.sampled_from(['critical', 'urgent', 'asap', 'immediately', 'blocking', 'blocker'])
)
def test_urgency_indicator_priority_boost(base_text, critical_indicator):
    """Property 9: Critical indicators result in Critical or High priority."""
    classifier = PriorityClassifier()
    
    # Create task with critical indicator in text
    raw_text = f"{base_text} This is {critical_indicator}."
    task = ExtractedTask(
        description=raw_text,
        raw_text=raw_text,
        priority_indicators=[critical_indicator]
    )
    
    result = classifier.classify(task)
    
    # Should be Critical or High, never Medium or Low
    high_priorities = {PriorityLevel.CRITICAL, PriorityLevel.HIGH}
    assert result in high_priorities, f"Task with '{critical_indicator}' should be Critical or High, got {result}"


# Test that short deadlines boost priority
@settings(max_examples=50)
@given(
    base_text=st.text(min_size=5, max_size=100),
    days_until=st.integers(min_value=0, max_value=1)
)
def test_short_deadline_boosts_priority(base_text, days_until):
    """Very short deadlines (0-1 days) should result in Critical priority."""
    classifier = PriorityClassifier()
    
    ref_date = date.today()
    deadline = ref_date + timedelta(days=days_until)
    
    task = ExtractedTask(
        description=base_text,
        raw_text=base_text,
        priority_indicators=[]
    )
    
    result = classifier.classify(task, deadline=deadline, reference_date=ref_date)
    
    # Should be Critical due to imminent deadline
    assert result == PriorityLevel.CRITICAL, f"Task due in {days_until} days should be Critical, got {result}"


# Test that no indicators defaults to Medium
@settings(max_examples=50)
@given(base_text=st.text(min_size=5, max_size=100, alphabet='abcdefghijklmnopqrstuvwxyz '))
def test_no_indicators_defaults_to_medium(base_text):
    """Tasks without indicators or urgent deadlines default to Medium."""
    classifier = PriorityClassifier()
    
    # Filter out any text that accidentally contains indicators
    text_lower = base_text.lower()
    has_indicator = any(
        ind in text_lower 
        for ind in classifier.CRITICAL_INDICATORS + classifier.HIGH_INDICATORS + classifier.LOW_INDICATORS
    )
    
    if has_indicator:
        return  # Skip this case
    
    task = ExtractedTask(
        description=base_text,
        raw_text=base_text,
        priority_indicators=[]
    )
    
    # No deadline, no indicators
    result = classifier.classify(task, deadline=None)
    
    assert result == PriorityLevel.MEDIUM, f"Task without indicators should be Medium, got {result}"
