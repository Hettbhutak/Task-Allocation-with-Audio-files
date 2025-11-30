"""Property-based tests for data models."""

import json
from hypothesis import given, strategies as st, settings

from src.models import (
    TeamMember, Task, TaskOutput, PipelineResult, PriorityLevel
)


# Feature: meeting-task-assignment, Property 5: Skill normalization consistency
# For any list of skills with varying case and whitespace, normalizing the skills
# SHALL produce lowercase trimmed strings, and normalizing twice SHALL produce
# the same result as normalizing once (idempotence).
# **Validates: Requirements 2.4**
@settings(max_examples=100)
@given(st.lists(st.text(min_size=0, max_size=50), min_size=0, max_size=10))
def test_skill_normalization_consistency(skills):
    """Property 5: Skills are normalized to lowercase and trimmed, idempotently."""
    member = TeamMember(name="Test", role="Developer", skills=skills)
    
    # All skills should be lowercase and trimmed
    for skill in member.skills:
        assert skill == skill.lower(), f"Skill '{skill}' is not lowercase"
        assert skill == skill.strip(), f"Skill '{skill}' is not trimmed"
    
    # Normalizing again should produce the same result (idempotence)
    member2 = TeamMember(name="Test", role="Developer", skills=member.skills)
    assert member.skills == member2.skills, "Normalization is not idempotent"


# Feature: meeting-task-assignment, Property 15: Serialization round-trip
# For any valid list of TaskOutput objects, serializing to JSON and then
# deserializing SHALL produce a list equivalent to the original.
# **Validates: Requirements 9.4, 9.5**
@settings(max_examples=100)
@given(
    st.lists(
        st.builds(
            TaskOutput,
            task_number=st.integers(min_value=1, max_value=1000),
            description=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
            assigned_to=st.one_of(st.none(), st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
            deadline=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
            priority=st.sampled_from(["Critical", "High", "Medium", "Low"]),
            dependencies=st.one_of(st.none(), st.text(min_size=0, max_size=50)),
            reasoning=st.one_of(st.none(), st.text(min_size=0, max_size=200))
        ),
        min_size=0,
        max_size=10
    )
)
def test_serialization_round_trip(tasks):
    """Property 15: Serializing and deserializing TaskOutput preserves all data."""
    # Create a PipelineResult with the tasks
    original = PipelineResult(
        success=True,
        tasks=tasks,
        transcript="Test transcript",
        error_message=None
    )
    
    # Serialize to JSON
    json_str = original.to_json()
    
    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict), "Serialized output is not a valid JSON object"
    
    # Deserialize back
    restored = PipelineResult.from_json(json_str)
    
    # Verify equivalence
    assert restored.success == original.success
    assert restored.transcript == original.transcript
    assert restored.error_message == original.error_message
    assert len(restored.tasks) == len(original.tasks)
    
    for orig_task, rest_task in zip(original.tasks, restored.tasks):
        assert rest_task.task_number == orig_task.task_number
        assert rest_task.description == orig_task.description
        assert rest_task.assigned_to == orig_task.assigned_to
        assert rest_task.deadline == orig_task.deadline
        assert rest_task.priority == orig_task.priority
        assert rest_task.dependencies == orig_task.dependencies
        assert rest_task.reasoning == orig_task.reasoning
