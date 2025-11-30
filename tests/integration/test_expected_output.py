"""
Integration test to validate CLI output against expected output from assignment.md.

This test ensures that the system produces output matching the expected results
defined in the project assignment specification.

Test Coverage:
--------------
1. Task Count: Verifies correct number of tasks are extracted
2. Task Descriptions: Validates task descriptions match expected output
3. Task Assignments: Ensures tasks are assigned to correct team members
4. Task Deadlines: Checks deadline extraction accuracy
5. Task Priorities: Validates priority classification (Critical/High/Medium/Low)
6. Task Dependencies: Verifies dependency relationships are identified
7. Assignment Reasoning: Ensures reasoning is provided for assignments
8. Output Structure: Validates complete JSON output structure
9. JSON Serialization: Tests output can be properly serialized
10. Assignment.md Compliance: Verifies all requirements from spec are met

Usage:
------
Run all tests:
    pytest tests/integration/test_expected_output.py -v

Run specific test:
    pytest tests/integration/test_expected_output.py::TestExpectedOutput::test_task_assignments -v

Run with coverage:
    pytest tests/integration/test_expected_output.py --cov=src --cov-report=html
"""

import json
import pytest
from pathlib import Path
from src.pipeline import MeetingTaskPipeline
from src.models import TeamMember
from src.stt_adapter import MockSTTAdapter


class TestExpectedOutput:
    """Test suite for validating output against assignment.md expectations."""
    
    @pytest.fixture
    def team_members(self):
        """Load team members from samples/team_members.json."""
        team_file = Path("samples/team_members.json")
        with open(team_file, 'r') as f:
            data = json.load(f)
        
        return [
            TeamMember(
                name=item['name'],
                role=item['role'],
                skills=item.get('skills', [])
            )
            for item in data
        ]
    
    @pytest.fixture
    def expected_output(self):
        """Load expected output from samples/expected_output.json."""
        expected_file = Path("samples/expected_output.json")
        with open(expected_file, 'r') as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_transcript(self):
        """The transcript from the assignment.md example."""
        return (
            "Hi everyone, let's discuss this week's priorities. "
            "Sakshi, we need someone to fix the critical login bug that users reported yesterday. "
            "This needs to be done by tomorrow evening since it's blocking users. "
            "Also, the database performance is really slow, Mohit you're good with backend optimization right? "
            "We should tackle this by end of this week, it's affecting the user experience. "
            "And we need to update the API documentation before Friday's release - this is high priority. "
            "Oh, and someone should design the new onboarding screens for the next sprint. "
            "Arjun, didn't you work on UI designs last month? This can wait until next Monday. "
            "One more thing - we need to write unit tests for the payment module. "
            "This depends on the login bug fix being completed first, so let's plan this for Wednesday."
        )
    
    def test_task_count(self, team_members, sample_transcript, expected_output):
        """Test that the correct number of tasks are extracted."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        assert result.success, "Pipeline should succeed"
        assert len(result.tasks) == len(expected_output['tasks']), \
            f"Expected {len(expected_output['tasks'])} tasks, got {len(result.tasks)}"
    
    def test_task_descriptions(self, team_members, sample_transcript, expected_output):
        """Test that task descriptions are correctly extracted."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        expected_descriptions = {
            task['task_number']: task['description'] 
            for task in expected_output['tasks']
        }
        
        for task in result.tasks:
            expected_desc = expected_descriptions.get(task.task_number)
            assert expected_desc is not None, f"Task #{task.task_number} not found in expected output"
            
            # Normalize for comparison (case-insensitive, ignore minor wording differences)
            actual_normalized = task.description.lower().strip()
            expected_normalized = expected_desc.lower().strip()
            
            # Check if key words match
            assert self._descriptions_match(actual_normalized, expected_normalized), \
                f"Task #{task.task_number} description mismatch:\n" \
                f"  Expected: {expected_desc}\n" \
                f"  Got: {task.description}"
    
    def test_task_assignments(self, team_members, sample_transcript, expected_output):
        """Test that tasks are assigned to the correct team members."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        expected_assignments = {
            task['task_number']: task['assigned_to']
            for task in expected_output['tasks']
        }
        
        for task in result.tasks:
            expected_assignee = expected_assignments.get(task.task_number)
            assert task.assigned_to == expected_assignee, \
                f"Task #{task.task_number} assignment mismatch:\n" \
                f"  Expected: {expected_assignee}\n" \
                f"  Got: {task.assigned_to}"
    
    def test_task_deadlines(self, team_members, sample_transcript, expected_output):
        """Test that deadlines are correctly extracted."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        expected_deadlines = {
            task['task_number']: task['deadline']
            for task in expected_output['tasks']
        }
        
        for task in result.tasks:
            expected_deadline = expected_deadlines.get(task.task_number)
            
            # Normalize deadline strings for comparison
            actual_deadline = self._normalize_deadline(task.deadline)
            expected_deadline_norm = self._normalize_deadline(expected_deadline)
            
            assert actual_deadline == expected_deadline_norm, \
                f"Task #{task.task_number} deadline mismatch:\n" \
                f"  Expected: {expected_deadline}\n" \
                f"  Got: {task.deadline}"
    
    def test_task_priorities(self, team_members, sample_transcript, expected_output):
        """Test that priorities are correctly classified."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        expected_priorities = {
            task['task_number']: task['priority']
            for task in expected_output['tasks']
        }
        
        for task in result.tasks:
            expected_priority = expected_priorities.get(task.task_number)
            assert task.priority == expected_priority, \
                f"Task #{task.task_number} priority mismatch:\n" \
                f"  Expected: {expected_priority}\n" \
                f"  Got: {task.priority}"
    
    def test_task_dependencies(self, team_members, sample_transcript, expected_output):
        """Test that task dependencies are correctly identified."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        expected_dependencies = {
            task['task_number']: task['dependencies']
            for task in expected_output['tasks']
        }
        
        for task in result.tasks:
            expected_dep = expected_dependencies.get(task.task_number)
            assert task.dependencies == expected_dep, \
                f"Task #{task.task_number} dependency mismatch:\n" \
                f"  Expected: {expected_dep}\n" \
                f"  Got: {task.dependencies}"
    
    def test_assignment_reasoning(self, team_members, sample_transcript, expected_output):
        """Test that assignment reasoning is provided."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        for task in result.tasks:
            assert task.reasoning is not None, \
                f"Task #{task.task_number} should have assignment reasoning"
            assert len(task.reasoning) > 0, \
                f"Task #{task.task_number} reasoning should not be empty"
    
    def test_complete_output_structure(self, team_members, sample_transcript, expected_output):
        """Test that the complete output structure matches expectations."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        # Verify result structure
        assert result.success == expected_output['success']
        assert result.transcript is not None
        assert len(result.tasks) == len(expected_output['tasks'])
        
        # Verify each task has all required fields
        for task in result.tasks:
            assert task.task_number is not None
            assert task.description is not None
            assert task.assigned_to is not None
            assert task.deadline is not None
            assert task.priority is not None
            # dependencies can be None
            assert task.reasoning is not None
    
    def test_json_serialization(self, team_members, sample_transcript):
        """Test that output can be serialized to JSON matching expected format."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        # Get JSON output
        json_output = pipeline.get_json_output(result)
        
        # Verify it's valid JSON
        parsed = json.loads(json_output)
        
        # Verify structure
        assert 'success' in parsed
        assert 'tasks' in parsed
        assert 'transcript' in parsed
        assert 'error_message' in parsed
        
        # Verify tasks structure
        for task in parsed['tasks']:
            assert 'task_number' in task
            assert 'description' in task
            assert 'assigned_to' in task
            assert 'deadline' in task
            assert 'priority' in task
            assert 'dependencies' in task
            assert 'reasoning' in task
    
    # Helper methods
    
    def _descriptions_match(self, actual: str, expected: str) -> bool:
        """
        Check if two task descriptions match, allowing for minor variations.
        
        Args:
            actual: Actual description from system
            expected: Expected description from spec
            
        Returns:
            True if descriptions match closely enough
        """
        # Extract key words (ignore articles, prepositions)
        stop_words = {'the', 'a', 'an', 'for', 'to', 'of', 'in', 'on', 'at'}
        
        actual_words = set(actual.split()) - stop_words
        expected_words = set(expected.split()) - stop_words
        
        # Check if most key words match
        if not expected_words:
            return actual == expected
        
        overlap = len(actual_words & expected_words)
        similarity = overlap / len(expected_words)
        
        return similarity >= 0.7  # 70% word overlap
    
    def _normalize_deadline(self, deadline: str) -> str:
        """
        Normalize deadline string for comparison.
        
        Args:
            deadline: Deadline string
            
        Returns:
            Normalized deadline string
        """
        if deadline is None:
            return None
        
        # Convert to lowercase and strip whitespace
        normalized = deadline.lower().strip()
        
        # Normalize common variations
        replacements = {
            'end of this week': 'end of week',
            'this week': 'end of week',
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized


class TestAssignmentMdCompliance:
    """Test that output complies with all requirements from assignment.md."""
    
    @pytest.fixture
    def team_members(self):
        """Load team members."""
        team_file = Path("samples/team_members.json")
        with open(team_file, 'r') as f:
            data = json.load(f)
        
        return [
            TeamMember(
                name=item['name'],
                role=item['role'],
                skills=item.get('skills', [])
            )
            for item in data
        ]
    
    @pytest.fixture
    def sample_transcript(self):
        """Sample transcript."""
        return (
            "Hi everyone, let's discuss this week's priorities. "
            "Sakshi, we need someone to fix the critical login bug that users reported yesterday. "
            "This needs to be done by tomorrow evening since it's blocking users. "
            "Also, the database performance is really slow, Mohit you're good with backend optimization right? "
            "We should tackle this by end of this week, it's affecting the user experience. "
            "And we need to update the API documentation before Friday's release - this is high priority. "
            "Oh, and someone should design the new onboarding screens for the next sprint. "
            "Arjun, didn't you work on UI designs last month? This can wait until next Monday. "
            "One more thing - we need to write unit tests for the payment module. "
            "This depends on the login bug fix being completed first, so let's plan this for Wednesday."
        )
    
    def test_minimum_required_fields(self, team_members, sample_transcript):
        """Test that minimum required output fields are present."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        # Per assignment.md: Minimum Required
        # 1. List of Identified Tasks - each task extracted from meeting
        assert len(result.tasks) > 0, "Should identify at least one task"
        
        for task in result.tasks:
            # 2. Clear description of what needs to be done
            assert task.description is not None
            assert len(task.description) > 0
            
            # 3. Task Assignments - which team member is assigned
            assert task.assigned_to is not None
    
    def test_additional_extractable_information(self, team_members, sample_transcript):
        """Test that additional extractable information is present."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        # Per assignment.md: Additional Extractable Information
        has_deadline = False
        has_priority = False
        has_dependency = False
        
        for task in result.tasks:
            # Deadlines / Timeline
            if task.deadline is not None:
                has_deadline = True
            
            # Priority Levels
            if task.priority is not None:
                has_priority = True
            
            # Dependencies
            if task.dependencies is not None:
                has_dependency = True
        
        assert has_deadline, "Should extract at least one deadline"
        assert has_priority, "Should classify priorities"
        assert has_dependency, "Should identify at least one dependency"
    
    def test_reasoning_provided(self, team_members, sample_transcript):
        """Test that reasoning for assignments is provided (optional but recommended)."""
        pipeline = MeetingTaskPipeline()
        result = pipeline.process_transcript(sample_transcript, team_members)
        
        # Per assignment.md: Include reasoning if mentioned or inferred
        for task in result.tasks:
            if task.assigned_to is not None:
                assert task.reasoning is not None, \
                    f"Task #{task.task_number} should have reasoning for assignment"
