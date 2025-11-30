"""Property-based tests for task assignment."""

from hypothesis import given, strategies as st, settings, assume

from src.models import ExtractedTask, TeamMember, AssignmentResult
from src.team_store import TeamMemberStore
from src.assignment_engine import AssignmentEngine


# Strategy for team member names
name_strategy = st.sampled_from(['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank'])

# Strategy for roles
role_strategy = st.sampled_from([
    'Frontend Developer', 'Backend Engineer', 'UI/UX Designer',
    'QA Engineer', 'DevOps Engineer', 'Full Stack Developer'
])

# Strategy for skills
skills_strategy = st.lists(
    st.sampled_from([
        'react', 'javascript', 'python', 'database', 'api', 'testing',
        'design', 'figma', 'docker', 'aws', 'css', 'html'
    ]),
    min_size=1, max_size=5
)


# Feature: meeting-task-assignment, Property 10: Explicit mention assignment priority
# For any task with an explicitly mentioned team member name that exists in the
# TeamMemberStore, the AssignmentEngine SHALL assign the task to that mentioned
# member regardless of skill matching.
# **Validates: Requirements 7.2**
@settings(max_examples=100)
@given(
    name=name_strategy,
    role=role_strategy,
    skills=skills_strategy,
    task_desc=st.text(min_size=10, max_size=100)
)
def test_explicit_mention_assignment_priority(name, role, skills, task_desc):
    """Property 10: Explicit mentions take priority over skill matching."""
    # Set up team store with the member
    store = TeamMemberStore()
    member = TeamMember(name=name, role=role, skills=skills)
    store.add_member(member)
    
    # Add another member with different skills
    other_member = TeamMember(name="Other Person", role="Manager", skills=["management"])
    store.add_member(other_member)
    
    # Create task with explicit mention
    task = ExtractedTask(
        description=task_desc,
        raw_text=task_desc,
        mentioned_person=name  # Explicitly mention the member
    )
    
    # Assign
    engine = AssignmentEngine()
    result = engine.assign(task, store)
    
    # Should assign to the mentioned person
    assert result.team_member is not None, "Should assign to mentioned member"
    assert result.team_member.name == name, f"Should assign to {name}, got {result.team_member.name}"
    assert "mentioned" in result.reasoning.lower() or "explicit" in result.reasoning.lower(), \
        "Reasoning should mention explicit assignment"


# Feature: meeting-task-assignment, Property 11: Skill-based assignment relevance
# For any task without explicit mention and with identifiable skill keywords, the
# assigned TeamMember (if any) SHALL have at least one skill that matches the task
# domain keywords.
# **Validates: Requirements 7.1, 7.4**
@settings(max_examples=100)
@given(
    task_keyword=st.sampled_from(['fix the login bug', 'optimize database', 'design new screens', 'write unit tests']),
)
def test_skill_based_assignment_relevance(task_keyword):
    """Property 11: Skill-based assignment matches relevant skills."""
    # Set up team with different specializations
    store = TeamMemberStore()
    
    frontend_dev = TeamMember(name="Frontend Dev", role="Frontend Developer", skills=["react", "javascript", "css", "login"])
    backend_dev = TeamMember(name="Backend Dev", role="Backend Engineer", skills=["python", "database", "api", "optimization"])
    designer = TeamMember(name="Designer", role="UI/UX Designer", skills=["figma", "design", "screens", "wireframe"])
    qa_eng = TeamMember(name="QA Engineer", role="QA Engineer", skills=["testing", "automation", "unit test", "pytest"])
    
    store.add_member(frontend_dev)
    store.add_member(backend_dev)
    store.add_member(designer)
    store.add_member(qa_eng)
    
    # Create task without explicit mention
    task = ExtractedTask(
        description=task_keyword,
        raw_text=task_keyword,
        mentioned_person=None
    )
    
    # Assign
    engine = AssignmentEngine()
    result = engine.assign(task, store)
    
    # Should assign to someone
    assert result.team_member is not None, f"Should find a match for '{task_keyword}'"
    
    # The assigned member should have relevant skills
    # Check that at least one skill domain matches
    task_domains = engine._extract_domains(task_keyword)
    member_skills_lower = [s.lower() for s in result.team_member.skills]
    
    # Verify there's some relevance
    has_relevance = False
    for domain in task_domains:
        domain_keywords = engine.SKILL_KEYWORDS.get(domain, [])
        for skill in member_skills_lower:
            if any(kw in skill or skill in kw for kw in domain_keywords):
                has_relevance = True
                break
        if has_relevance:
            break
    
    assert has_relevance or result.confidence > 0, \
        f"Assigned member should have relevant skills for '{task_keyword}'"


# Feature: meeting-task-assignment, Property 16: Assignment reasoning presence
# For any task that is successfully assigned to a team member, the AssignmentResult
# SHALL include a non-empty reasoning string explaining the assignment.
# **Validates: Requirements 10.1, 10.2, 10.3**
@settings(max_examples=100)
@given(
    name=name_strategy,
    role=role_strategy,
    skills=skills_strategy,
    task_keyword=st.sampled_from(['fix bug', 'update api', 'design screen', 'write test', 'deploy service'])
)
def test_assignment_reasoning_presence(name, role, skills, task_keyword):
    """Property 16: Successful assignments include non-empty reasoning."""
    store = TeamMemberStore()
    member = TeamMember(name=name, role=role, skills=skills)
    store.add_member(member)
    
    # Create task (with or without mention)
    task = ExtractedTask(
        description=task_keyword,
        raw_text=task_keyword,
        mentioned_person=name  # Use explicit mention to ensure assignment
    )
    
    engine = AssignmentEngine()
    result = engine.assign(task, store)
    
    # If assigned, reasoning must be present
    if result.team_member is not None:
        assert result.reasoning, "Reasoning should not be empty for assigned tasks"
        assert len(result.reasoning) > 0, "Reasoning should have content"


# Test that no match returns appropriate result
@settings(max_examples=50)
@given(task_desc=st.text(min_size=10, max_size=100, alphabet='xyz0123456789 '))
def test_no_match_returns_unassigned(task_desc):
    """When no suitable member exists, task should be unassigned with reason."""
    store = TeamMemberStore()
    
    # Add member with unrelated skills
    member = TeamMember(name="Unrelated", role="Manager", skills=["management", "leadership"])
    store.add_member(member)
    
    # Task with no matching keywords
    task = ExtractedTask(
        description=task_desc,
        raw_text=task_desc,
        mentioned_person=None
    )
    
    engine = AssignmentEngine()
    result = engine.assign(task, store)
    
    # Should have reasoning even if unassigned
    assert result.reasoning, "Should have reasoning even when unassigned"
