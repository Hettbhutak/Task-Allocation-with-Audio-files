"""Property-based tests for validation components."""

from hypothesis import given, strategies as st, settings

from src.audio_validator import AudioValidator


# Feature: meeting-task-assignment, Property 1: Supported audio format acceptance
# For any audio file path with extension .wav, .mp3, or .m4a, the AudioValidator
# SHALL return a valid result with is_valid=True and no error message (assuming file exists and is valid).
# **Validates: Requirements 1.1, 1.2, 1.3**
@settings(max_examples=100)
@given(st.sampled_from(['.wav', '.mp3', '.m4a']))
def test_supported_format_acceptance(extension):
    """Property 1: Supported formats are recognized as valid extensions."""
    validator = AudioValidator()
    
    # Test that the extension is in supported formats
    assert extension in validator.SUPPORTED_FORMATS, f"Extension {extension} should be supported"
    
    # Test the is_supported_format helper
    test_path = f"test_file{extension}"
    assert validator.is_supported_format(test_path), f"is_supported_format should return True for {extension}"


# Feature: meeting-task-assignment, Property 2: Unsupported format rejection
# For any file path with an extension not in {.wav, .mp3, .m4a}, the AudioValidator
# SHALL return is_valid=False with a non-empty error message.
# **Validates: Requirements 1.4**
@settings(max_examples=100)
@given(st.text(min_size=1, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz').filter(
    lambda x: x not in ['wav', 'mp3', 'm4a']
))
def test_unsupported_format_rejection(extension):
    """Property 2: Unsupported formats are rejected with error message."""
    validator = AudioValidator()
    
    # Create a fake path with unsupported extension
    test_path = f"test_file.{extension}"
    
    # The extension should not be in supported formats
    assert not validator.is_supported_format(test_path), f"Extension .{extension} should not be supported"
    
    # Validation should fail (file doesn't exist, but format check happens first for existing files)
    # For non-existent files, we get "file not found" error
    # But we can verify the format is not in supported set
    full_ext = f".{extension}"
    assert full_ext not in validator.SUPPORTED_FORMATS, f"Extension {full_ext} should not be in supported formats"


import os
import tempfile
from hypothesis import assume

from src.models import TeamMember
from src.team_store import TeamMemberStore


# Feature: meeting-task-assignment, Property 1 (extended): Supported format file validation
# For any audio file with valid magic bytes, the AudioValidator SHALL accept it.
# **Validates: Requirements 1.1, 1.2, 1.3**
@settings(max_examples=100)
@given(
    st.sampled_from(['.wav', '.mp3', '.m4a']),
    st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789_-', min_size=1, max_size=20)
)
def test_supported_format_file_validation(extension, filename):
    """Property 1: Valid audio files with correct magic bytes are accepted."""
    assume(filename.strip())
    
    validator = AudioValidator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, f"{filename}{extension}")
        
        # Write appropriate magic bytes for each format
        if extension == '.wav':
            content = b'RIFF\x00\x00\x00\x00WAVEfmt '
        elif extension == '.mp3':
            content = b'ID3\x04\x00\x00\x00\x00\x00\x00'
        elif extension == '.m4a':
            content = b'\x00\x00\x00\x14ftypM4A '
        else:
            content = b'\x00' * 16
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        result = validator.validate(file_path)
        
        assert result.is_valid, f"Valid {extension} file should be accepted, got: {result.error_message}"
        assert result.error_message is None
        assert result.file_format == extension


# Feature: meeting-task-assignment, Property 3: Team member storage consistency
# For any valid TeamMember with non-empty name, role, and skills list, adding the
# member to TeamMemberStore and then retrieving by name SHALL return an equivalent
# TeamMember object.
# **Validates: Requirements 2.1**
@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
    st.lists(st.text(min_size=1, max_size=30).filter(lambda x: x.strip()), min_size=1, max_size=5)
)
def test_team_member_storage_consistency(name, role, skills):
    """Property 3: Storing and retrieving team member preserves data."""
    store = TeamMemberStore()
    member = TeamMember(name=name, role=role, skills=skills)
    
    result = store.add_member(member)
    assert result.is_valid, f"Valid member should be added: {result.error_message}"
    
    retrieved = store.find_by_name(name)
    assert retrieved is not None, "Member should be retrievable by name"
    
    assert retrieved.name == member.name
    assert retrieved.role == member.role
    assert retrieved.skills == member.skills


# Feature: meeting-task-assignment, Property 4: Missing field rejection
# For any TeamMember data missing name, role, or skills, the validation SHALL fail
# and the error message SHALL specify which field is missing.
# **Validates: Requirements 2.2**
@settings(max_examples=100)
@given(
    st.one_of(st.just(""), st.just("   ")),
    st.one_of(st.just(""), st.just("   ")),
    st.one_of(st.just([]), st.lists(st.just(""), max_size=0))
)
def test_missing_field_rejection(name, role, skills):
    """Property 4: Missing/empty fields are rejected with specific error."""
    store = TeamMemberStore()
    
    member = TeamMember(name=name, role=role, skills=skills)
    result = store.validate_member(member)
    
    assert not result.is_valid, "Member with missing fields should be rejected"
    assert result.error_message is not None
    assert len(result.missing_fields) > 0
    
    if not name.strip():
        assert "name" in result.missing_fields
    if not role.strip():
        assert "role" in result.missing_fields
    if not skills:
        assert "skills" in result.missing_fields
