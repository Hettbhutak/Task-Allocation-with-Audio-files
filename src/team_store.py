"""Team member storage and management component."""

from typing import Dict, List, Optional

from src.models import TeamMember, ValidationResult


class TeamMemberStore:
    """Manages team member data with validation and search capabilities."""
    
    def __init__(self):
        self._members: Dict[str, TeamMember] = {}
    
    def validate_member(self, member: TeamMember) -> ValidationResult:
        """
        Validates team member data for completeness.
        
        Args:
            member: TeamMember to validate
            
        Returns:
            ValidationResult with validation status and missing fields
        """
        missing_fields = []
        
        if not member.name or not member.name.strip():
            missing_fields.append("name")
        
        if not member.role or not member.role.strip():
            missing_fields.append("role")
        
        if not member.skills:
            missing_fields.append("skills")
        
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required fields: {', '.join(missing_fields)}",
                missing_fields=missing_fields
            )
        
        return ValidationResult(is_valid=True)
    
    def add_member(self, member: TeamMember) -> ValidationResult:
        """
        Adds a team member after validation.
        
        Args:
            member: TeamMember to add
            
        Returns:
            ValidationResult indicating success or failure
        """
        validation = self.validate_member(member)
        if not validation.is_valid:
            return validation
        
        # Check for duplicates (case-insensitive name match)
        name_key = member.name.lower().strip()
        if name_key in self._members:
            return ValidationResult(
                is_valid=False,
                error_message=f"Duplicate team member: {member.name}"
            )
        
        self._members[name_key] = member
        return ValidationResult(is_valid=True)
    
    def get_member(self, name: str) -> Optional[TeamMember]:
        """
        Retrieves a team member by name (case-insensitive).
        
        Args:
            name: Name of the team member
            
        Returns:
            TeamMember if found, None otherwise
        """
        return self._members.get(name.lower().strip())
    
    def find_by_name(self, name: str) -> Optional[TeamMember]:
        """
        Finds a team member by name (case-insensitive, partial match).
        
        Args:
            name: Name or partial name to search for
            
        Returns:
            TeamMember if found, None otherwise
        """
        search_name = name.lower().strip()
        
        # Exact match first
        if search_name in self._members:
            return self._members[search_name]
        
        # Partial match
        for key, member in self._members.items():
            if search_name in key or key in search_name:
                return member
        
        return None
    
    def find_by_skill(self, skill: str) -> List[TeamMember]:
        """
        Finds all team members with a matching skill.
        
        Args:
            skill: Skill to search for (case-insensitive)
            
        Returns:
            List of TeamMembers with the matching skill
        """
        search_skill = skill.lower().strip()
        matches = []
        
        for member in self._members.values():
            for member_skill in member.skills:
                if search_skill in member_skill or member_skill in search_skill:
                    matches.append(member)
                    break
        
        return matches
    
    def find_by_role(self, role: str) -> List[TeamMember]:
        """
        Finds all team members with a matching role.
        
        Args:
            role: Role to search for (case-insensitive, partial match)
            
        Returns:
            List of TeamMembers with the matching role
        """
        search_role = role.lower().strip()
        matches = []
        
        for member in self._members.values():
            if search_role in member.role.lower():
                matches.append(member)
        
        return matches
    
    def get_all_members(self) -> List[TeamMember]:
        """Returns all team members."""
        return list(self._members.values())
    
    def get_all_names(self) -> List[str]:
        """Returns all team member names."""
        return [m.name for m in self._members.values()]
    
    def clear(self):
        """Removes all team members."""
        self._members.clear()
    
    def __len__(self) -> int:
        return len(self._members)
    
    def __contains__(self, name: str) -> bool:
        return name.lower().strip() in self._members
