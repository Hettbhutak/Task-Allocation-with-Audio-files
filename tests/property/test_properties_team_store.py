"""Property-based tests for team member storage."""

from hypothesis import given, strategies as st, settings, assume

from src.models import TeamMember
from src.team_store import TeamMemberStore


# Strategy for generating valid team member names
valid_name_strategy = st.text(
    min_size=1, max_size=50,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))
).filter(lambda x: x.strip())

# Strategy for generating valid roles
valid_role_strategy = st.sampled_from([
    'Developer', 'Frontend Developer', 'Backend Engineer',
    'UI/UX Designer', 'QA Engineer', 'DevOps', 'Manager'
])

# Strategy for generating valid skills
valid_skills_strategy = st.lists(
    st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
    min_size=1, max_size=10
)


# Feature: meeting-task-assignment, Property 3: Team member storage consistency
# For any valid TeamMember with non-empty name, role, and skills list, adding the
# member to TeamMemberStore and then retrieving by name SHALL return an equivalent
# TeamMember object.
# **Validates: Requirements 2.1**
@settings(max_examples=100)
@given(
    name=valid_name_strategy,
    role=valid_role_strategy,
    skills=valid_skills_strategy
)
def test_team_member_storage_consistency(name, role, skills):
    """Property 3: Adding and retrieving a team member preserves data."""
    store = TeamMemberStore()
    member = TeamMember(name=name, role=role, skills=skills)
    
    # Add member
    result = store.add_member(member)
    assert result.is_valid, f"Failed to add valid member: {result.error_message}"
    
    # Retrieve by name
    retrieved = store.get_member(name)
    assert retrieved is not None, f"Could not retrieve member by name: {name}"
    
    # Verify equivalence
    assert retrieved.name == member.name, "Name mismatch"
    assert retrieved.role == member.role, "Role mismatch"
    assert retrieved.skills == member.skills, "Skills mismatch (after normalization)"


# Feature: meeting-task-assignment, Property 4: Missing field rejection
# For any TeamMember data missing name, role, or skills, the validation SHALL fail
# and the error message SHALL specify which field is missing.
# **Validates: Requirements 2.2**
@settings(max_examples=100)
@given(
    has_name=st.booleans(),
    has_role=st.booleans(),
    has_skills=st.booleans()
)
def test_missing_field_rejection(has_name, has_role, has_skills):
    """Property 4: Missing required fields are detected and reported."""
    # Skip if all fields are present (that's a valid case)
    assume(not (has_name and has_role and has_skills))
    
    store = TeamMemberStore()
    
    name = "Test User" if has_name else ""
    role = "Developer" if has_role else ""
    skills = ["python", "testing"] if has_skills else []
    
    member = TeamMember(name=name, role=role, skills=skills)
    result = store.validate_member(member)
    
    # Validation should fail
    assert not result.is_valid, "Validation should fail for incomplete data"
    assert result.error_message, "Error message should be present"
    
    # Check that missing fields are reported
    if not has_name:
        assert "name" in result.missing_fields, "Missing 'name' should be reported"
    if not has_role:
        assert "role" in result.missing_fields, "Missing 'role' should be reported"
    if not has_skills:
        assert "skills" in result.missing_fields, "Missing 'skills' should be reported"
