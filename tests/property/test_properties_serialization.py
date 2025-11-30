"""Property-based tests for output serialization."""

import json
from hypothesis import given, strategies as st, settings

from src.models import TaskOutput, PipelineResult
from src.output_serializer import OutputSerializer


# Strategy for task outputs
task_output_strategy = st.builds(
    TaskOutput,
    task_number=st.integers(min_value=1, max_value=100),
    description=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    assigned_to=st.one_of(st.none(), st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
    deadline=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
    priority=st.sampled_from(['Critical', 'High', 'Medium', 'Low']),
    dependencies=st.one_of(st.none(), st.text(min_size=0, max_size=50)),
    reasoning=st.one_of(st.none(), st.text(min_size=0, max_size=100))
)


# Feature: meeting-task-assignment, Property 14: Output field completeness
# For any TaskOutput object, serialization SHALL include all required fields:
# task_number, description, and priority. Optional fields (assigned_to, deadline,
# dependencies, reasoning) SHALL be present as null if not set.
# **Validates: Requirements 9.2, 9.3**
@settings(max_examples=100)
@given(task=task_output_strategy)
def test_output_field_completeness(task):
    """Property 14: Serialized output contains all required and optional fields."""
    serializer = OutputSerializer()
    
    # Serialize to dict
    task_dict = serializer.to_dict(task)
    
    # Check required fields are present
    assert 'task_number' in task_dict, "task_number is required"
    assert 'description' in task_dict, "description is required"
    assert 'priority' in task_dict, "priority is required"
    
    # Check optional fields are present (even if null)
    assert 'assigned_to' in task_dict, "assigned_to should be present"
    assert 'deadline' in task_dict, "deadline should be present"
    assert 'dependencies' in task_dict, "dependencies should be present"
    assert 'reasoning' in task_dict, "reasoning should be present"
    
    # Verify values match
    assert task_dict['task_number'] == task.task_number
    assert task_dict['description'] == task.description
    assert task_dict['priority'] == task.priority


# Test JSON serialization produces valid JSON
@settings(max_examples=100)
@given(tasks=st.lists(task_output_strategy, min_size=0, max_size=10))
def test_serialization_produces_valid_json(tasks):
    """Serialization produces valid, parseable JSON."""
    serializer = OutputSerializer()
    
    json_str = serializer.serialize(tasks)
    
    # Should be valid JSON
    parsed = json.loads(json_str)
    assert isinstance(parsed, list), "Should serialize to JSON array"
    assert len(parsed) == len(tasks), "Should have same number of items"


# Test round-trip serialization
@settings(max_examples=100)
@given(tasks=st.lists(task_output_strategy, min_size=1, max_size=5))
def test_serialization_round_trip(tasks):
    """Serializing and deserializing preserves all data."""
    serializer = OutputSerializer()
    
    # Serialize
    json_str = serializer.serialize(tasks)
    
    # Deserialize
    restored = serializer.deserialize(json_str)
    
    # Verify
    assert len(restored) == len(tasks)
    for orig, rest in zip(tasks, restored):
        assert rest.task_number == orig.task_number
        assert rest.description == orig.description
        assert rest.priority == orig.priority
        assert rest.assigned_to == orig.assigned_to
        assert rest.deadline == orig.deadline
        assert rest.dependencies == orig.dependencies
        assert rest.reasoning == orig.reasoning


# Test PipelineResult serialization
@settings(max_examples=50)
@given(
    success=st.booleans(),
    tasks=st.lists(task_output_strategy, min_size=0, max_size=5),
    transcript=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
    error_message=st.one_of(st.none(), st.text(min_size=1, max_size=100))
)
def test_pipeline_result_serialization(success, tasks, transcript, error_message):
    """PipelineResult serialization preserves all fields."""
    serializer = OutputSerializer()
    
    original = PipelineResult(
        success=success,
        tasks=tasks,
        transcript=transcript,
        error_message=error_message
    )
    
    # Serialize and deserialize
    json_str = serializer.serialize_result(original)
    restored = serializer.deserialize_result(json_str)
    
    # Verify
    assert restored.success == original.success
    assert restored.transcript == original.transcript
    assert restored.error_message == original.error_message
    assert len(restored.tasks) == len(original.tasks)
