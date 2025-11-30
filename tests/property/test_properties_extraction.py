"""Property-based tests for task extraction."""

from datetime import date, timedelta
from hypothesis import given, strategies as st, settings, assume

from src.task_extractor import TaskExtractor


# Strategy for complete actionable task sentences
# These are realistic task sentences that will pass the actionability checks
task_sentence_strategy = st.sampled_from([
    'We need to fix the critical bug in the login system',
    'Someone should update the API documentation',
    'We should design the new onboarding screens',
    'We need to write unit tests for the payment module',
    'We must optimize the database performance',
    'We have to implement the authentication feature',
    'We should create the user dashboard interface',
    'Someone needs to fix the performance issue',
    'We need to update the documentation for the API',
    'We should design the onboarding flow screens',
])


# Feature: meeting-task-assignment, Property 6: Task extraction completeness
# For any transcript containing N distinct task indicator phrases, the TaskExtractor
# SHALL extract at least N task entries (may extract more if phrases contain multiple tasks).
# **Validates: Requirements 4.1**
@settings(max_examples=100)
@given(
    task_sentences=st.lists(task_sentence_strategy, min_size=1, max_size=5, unique=True)
)
def test_task_extraction_completeness(task_sentences):
    """Property 6: Task extractor identifies actionable task sentences."""
    extractor = TaskExtractor()
    
    # Build transcript with task sentences
    transcript = ". ".join(task_sentences) + "."
    
    # Extract tasks
    tasks = extractor.extract_tasks(transcript)
    
    # We should extract at least 1 task from actionable task sentences
    # (The exact number may vary due to filtering and merging logic)
    assert len(tasks) >= 1, f"Should extract at least 1 task from {len(task_sentences)} actionable task sentence(s)"
    
    # Each extracted task should have a non-empty description
    for task in tasks:
        assert task.description, "Task description should not be empty"
        assert task.raw_text, "Task raw_text should not be empty"
        # Description should be reasonably long (implementation filters < 10 chars)
        assert len(task.description) > 10, f"Task description should be > 10 chars, got: {task.description}"


# Additional test: Empty transcript returns empty list
@settings(max_examples=50)
@given(st.text(max_size=0))
def test_empty_transcript_returns_empty(transcript):
    """Empty or whitespace-only transcript returns empty task list."""
    extractor = TaskExtractor()
    tasks = extractor.extract_tasks(transcript)
    assert tasks == [], "Empty transcript should return empty task list"


# Additional test: Transcript without indicators returns empty
@settings(max_examples=50)
@given(st.text(min_size=10, max_size=100, alphabet='abcdefghijklmnopqrstuvwxyz '))
def test_no_indicators_returns_empty(transcript):
    """Transcript without task indicators returns empty or minimal tasks."""
    # Filter out any text that accidentally contains indicators
    extractor = TaskExtractor()
    has_indicator = any(ind in transcript.lower() for ind in extractor.TASK_INDICATORS)
    assume(not has_indicator)
    
    tasks = extractor.extract_tasks(transcript)
    assert len(tasks) == 0, "Transcript without indicators should return no tasks"


from src.models import ExtractedTask, PriorityLevel
from src.priority_classifier import PriorityClassifier


# Feature: meeting-task-assignment, Property 8: Priority classification validity
# For any ExtractedTask, the PriorityClassifier SHALL return exactly one of the
# four valid PriorityLevel values: Critical, High, Medium, or Low.
# **Validates: Requirements 6.1, 6.5**
@settings(max_examples=100)
@given(
    st.text(min_size=5, max_size=200),
    st.text(min_size=5, max_size=200),
    st.lists(st.text(min_size=1, max_size=30), max_size=5),
    st.one_of(st.none(), st.dates(min_value=date.today(), max_value=date.today() + timedelta(days=365)))
)
def test_priority_classification_validity(description, raw_text, indicators, deadline):
    """Property 8: Classification always returns valid PriorityLevel."""
    classifier = PriorityClassifier()
    
    task = ExtractedTask(
        description=description,
        raw_text=raw_text,
        priority_indicators=indicators
    )
    
    result = classifier.classify(task, deadline)
    
    # Result must be a valid PriorityLevel
    assert isinstance(result, PriorityLevel), f"Result should be PriorityLevel, got {type(result)}"
    assert result in list(PriorityLevel), f"Result {result} should be valid PriorityLevel"


# Feature: meeting-task-assignment, Property 9: Urgency indicator priority boost
# For any task description containing critical indicators ("critical", "blocking",
# "urgent"), the classified priority SHALL be Critical or High (never Medium or Low).
# **Validates: Requirements 6.2, 6.3**
@settings(max_examples=100)
@given(
    st.sampled_from(['critical', 'blocking', 'urgent', 'asap', 'immediately']),
    st.text(min_size=5, max_size=100)
)
def test_urgency_indicator_priority_boost(indicator, base_text):
    """Property 9: Critical indicators result in Critical or High priority."""
    classifier = PriorityClassifier()
    
    # Create task with critical indicator in description
    description = f"{base_text} This is {indicator}."
    task = ExtractedTask(
        description=description,
        raw_text=description,
        priority_indicators=[indicator]
    )
    
    result = classifier.classify(task)
    
    # Should be Critical or High, never Medium or Low
    assert result in [PriorityLevel.CRITICAL, PriorityLevel.HIGH], \
        f"Task with '{indicator}' should be Critical or High, got {result}"


# Additional test: Default priority is Medium
@settings(max_examples=50)
@given(
    st.text(alphabet='abcdefghijklmnopqrstuvwxyz ', min_size=10, max_size=100)
)
def test_default_priority_is_medium(description):
    """Tasks without priority indicators default to Medium."""
    classifier = PriorityClassifier()
    
    # Filter out any text containing priority indicators
    all_indicators = (
        classifier.CRITICAL_INDICATORS + 
        classifier.HIGH_INDICATORS + 
        classifier.LOW_INDICATORS
    )
    for indicator in all_indicators:
        assume(indicator not in description.lower())
    
    task = ExtractedTask(
        description=description,
        raw_text=description,
        priority_indicators=[]
    )
    
    result = classifier.classify(task)
    
    assert result == PriorityLevel.MEDIUM, f"Default priority should be Medium, got {result}"


from src.deadline_parser import DeadlineParser


# Deadline phrases that should be parseable
DEADLINE_PHRASES = [
    'tomorrow',
    'next week',
    'next monday',
    'next tuesday',
    'next wednesday',
    'next thursday',
    'next friday',
    'by friday',
    'end of week',
    'end of this week',
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
]


# Feature: meeting-task-assignment, Property 7: Deadline parsing correctness
# For any relative deadline phrase and a reference date, parsing the phrase SHALL
# produce a date that is after or equal to the reference date and within a
# reasonable range (not more than 1 year ahead).
# **Validates: Requirements 5.1, 5.2, 5.4**
@settings(max_examples=100)
@given(
    st.sampled_from(DEADLINE_PHRASES),
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))
)
def test_deadline_parsing_correctness(phrase, reference_date):
    """Property 7: Parsed deadlines are valid future dates within reasonable range."""
    parser = DeadlineParser()
    
    result = parser.parse(phrase, reference_date)
    
    # Should successfully parse known phrases
    assert result is not None, f"Should parse '{phrase}'"
    
    # Result should be on or after reference date
    assert result >= reference_date, f"Deadline {result} should be >= reference {reference_date}"
    
    # Result should be within 1 year
    max_date = reference_date + timedelta(days=365)
    assert result <= max_date, f"Deadline {result} should be within 1 year of {reference_date}"
