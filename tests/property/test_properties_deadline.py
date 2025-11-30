"""Property-based tests for deadline parsing."""

from datetime import date, timedelta
from hypothesis import given, strategies as st, settings

from src.deadline_parser import DeadlineParser


# Strategy for relative deadline phrases
deadline_phrase_strategy = st.sampled_from([
    'tomorrow', 'today', 'tonight', 'next week',
    'next monday', 'next tuesday', 'next wednesday', 'next thursday', 'next friday',
    'end of week', 'end of this week', 'this week',
    'end of month', 'end of this month',
    'by friday', 'by monday', 'by wednesday',
    'in 3 days', 'in 1 week', 'in 2 weeks'
])

# Strategy for reference dates (within reasonable range)
reference_date_strategy = st.dates(
    min_value=date(2020, 1, 1),
    max_value=date(2030, 12, 31)
)


# Feature: meeting-task-assignment, Property 7: Deadline parsing correctness
# For any relative deadline phrase and a reference date, parsing the phrase SHALL
# produce a date that is after or equal to the reference date and within a
# reasonable range (not more than 1 year ahead).
# **Validates: Requirements 5.1, 5.2, 5.4**
@settings(max_examples=100)
@given(
    phrase=deadline_phrase_strategy,
    ref_date=reference_date_strategy
)
def test_deadline_parsing_correctness(phrase, ref_date):
    """Property 7: Parsed deadlines are valid and within reasonable range."""
    parser = DeadlineParser()
    
    parsed = parser.parse(phrase, reference_date=ref_date)
    
    # Should successfully parse known phrases
    assert parsed is not None, f"Failed to parse known phrase: {phrase}"
    
    # Parsed date should be on or after reference date
    assert parsed >= ref_date, f"Parsed date {parsed} is before reference {ref_date}"
    
    # Parsed date should be within 1 year of reference
    max_date = ref_date + timedelta(days=365)
    assert parsed <= max_date, f"Parsed date {parsed} is more than 1 year from {ref_date}"


# Test that "tomorrow" always returns reference_date + 1 day
@settings(max_examples=50)
@given(ref_date=reference_date_strategy)
def test_tomorrow_is_next_day(ref_date):
    """Tomorrow should always be exactly one day after reference."""
    parser = DeadlineParser()
    
    parsed = parser.parse('tomorrow', reference_date=ref_date)
    expected = ref_date + timedelta(days=1)
    
    assert parsed == expected, f"Tomorrow from {ref_date} should be {expected}, got {parsed}"


# Test that "today" returns the reference date
@settings(max_examples=50)
@given(ref_date=reference_date_strategy)
def test_today_is_reference_date(ref_date):
    """Today should return the reference date."""
    parser = DeadlineParser()
    
    parsed = parser.parse('today', reference_date=ref_date)
    
    assert parsed == ref_date, f"Today should be {ref_date}, got {parsed}"


# Test that "in N days" returns reference + N days
@settings(max_examples=50)
@given(
    ref_date=reference_date_strategy,
    days=st.integers(min_value=1, max_value=30)
)
def test_in_n_days_correctness(ref_date, days):
    """'In N days' should return reference + N days."""
    parser = DeadlineParser()
    
    phrase = f"in {days} days"
    parsed = parser.parse(phrase, reference_date=ref_date)
    expected = ref_date + timedelta(days=days)
    
    assert parsed == expected, f"'{phrase}' from {ref_date} should be {expected}, got {parsed}"
