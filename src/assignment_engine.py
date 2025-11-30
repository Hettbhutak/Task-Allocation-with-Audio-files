"""Assignment engine component for matching tasks to team members."""

from typing import Dict, List, Optional, Set

from src.models import ExtractedTask, TeamMember, AssignmentResult
from src.team_store import TeamMemberStore


class AssignmentEngine:
    """Matches tasks to team members based on skills and explicit mentions."""
    
    # Mapping of skill domains to related keywords
    SKILL_KEYWORDS: Dict[str, List[str]] = {
        'frontend': [
            'ui', 'react', 'javascript', 'css', 'html', 'login bug', 'button',
            'screen', 'page', 'form', 'component', 'interface', 'vue', 'angular',
            'frontend', 'front-end', 'client', 'browser', 'responsive', 'fix login'
        ],
        'backend': [
            'api', 'database', 'server', 'performance', 'optimization', 'backend',
            'back-end', 'endpoint', 'rest', 'graphql', 'microservice', 'cache',
            'query', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql',
            'api documentation', 'documentation', 'optimize database'
        ],
        'design': [
            'design', 'figma', 'onboarding', 'ux', 'ui/ux', 'screens', 'mockup',
            'wireframe', 'prototype', 'user flow', 'sketch', 'adobe', 'visual',
            'layout', 'typography', 'color', 'branding'
        ],
        'qa': [
            'test', 'testing', 'quality', 'automation', 'unit test', 'qa',
            'write test', 'write unit test', 'regression', 'integration test', 
            'e2e', 'selenium', 'cypress', 'jest', 'pytest', 'coverage',
            'payment module', 'test for'
        ],
        'devops': [
            'deploy', 'deployment', 'ci', 'cd', 'pipeline', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'infrastructure', 'monitoring', 'logging'
        ],
        'documentation': [
            'documentation', 'docs', 'readme', 'api docs', 'swagger', 'openapi',
            'wiki', 'guide', 'tutorial', 'comment'
        ]
    }
    
    # Role to skill domain mapping
    ROLE_DOMAINS: Dict[str, List[str]] = {
        'frontend': ['frontend', 'front-end', 'ui developer', 'react developer'],
        'backend': ['backend', 'back-end', 'server', 'api developer'],
        'design': ['designer', 'ui/ux', 'ux', 'ui designer'],
        'qa': ['qa', 'quality', 'tester', 'test engineer'],
        'devops': ['devops', 'sre', 'infrastructure', 'platform'],
    }
    
    def __init__(self):
        self._keyword_to_domain: Dict[str, str] = {}
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """Builds reverse index from keywords to domains."""
        for domain, keywords in self.SKILL_KEYWORDS.items():
            for keyword in keywords:
                self._keyword_to_domain[keyword.lower()] = domain
    
    def assign(
        self,
        task: ExtractedTask,
        team_store: TeamMemberStore
    ) -> AssignmentResult:
        """
        Assigns a task to the most suitable team member.
        
        Args:
            task: The extracted task to assign
            team_store: Store containing team members
            
        Returns:
            AssignmentResult with assigned member and reasoning
        """
        # First, check for explicit mention
        explicit_result = self._match_by_explicit_mention(task, team_store)
        if explicit_result and explicit_result.team_member:
            return explicit_result
        
        # Fall back to skill-based matching
        skill_result = self._match_by_skills(task, team_store)
        if skill_result and skill_result.team_member:
            return skill_result
        
        # No suitable match found
        return AssignmentResult(
            team_member=None,
            reasoning="No suitable team member found for this task",
            confidence=0.0
        )
    
    def _match_by_explicit_mention(
        self,
        task: ExtractedTask,
        team_store: TeamMemberStore
    ) -> Optional[AssignmentResult]:
        """Checks for explicit team member mention in task."""
        if not task.mentioned_person:
            return None
        
        member = team_store.find_by_name(task.mentioned_person)
        if member:
            return AssignmentResult(
                team_member=member,
                reasoning=f"Explicitly mentioned in task: '{task.mentioned_person}'",
                confidence=1.0
            )
        
        return None
    
    def _match_by_skills(
        self,
        task: ExtractedTask,
        team_store: TeamMemberStore
    ) -> Optional[AssignmentResult]:
        """Matches task to team member based on skill keywords."""
        # Extract domains from task description
        task_text = (task.description + " " + task.raw_text).lower()
        task_domains = self._extract_domains(task_text)
        
        if not task_domains:
            return None
        
        # Determine primary domain based on task keywords
        primary_domain = None
        if 'unit test' in task_text or 'write test' in task_text or 'testing' in task_text:
            primary_domain = 'qa'
        elif 'database' in task_text or 'api' in task_text or 'backend' in task_text or 'documentation' in task_text:
            primary_domain = 'backend'
        elif 'design' in task_text or 'onboarding' in task_text or 'screen' in task_text:
            primary_domain = 'design'
        elif 'login' in task_text or 'bug' in task_text or 'ui' in task_text:
            primary_domain = 'frontend'
        
        # Score each team member
        best_member: Optional[TeamMember] = None
        best_score = 0.0
        matched_skills: List[str] = []
        
        for member in team_store.get_all_members():
            score, skills = self._calculate_skill_score(task_domains, member)
            
            # Boost score if member's role matches primary domain
            if primary_domain:
                role_lower = member.role.lower()
                if primary_domain == 'qa' and 'qa' in role_lower:
                    score += 2.0
                elif primary_domain == 'backend' and 'backend' in role_lower:
                    score += 1.5
                elif primary_domain == 'design' and 'design' in role_lower:
                    score += 1.5
                elif primary_domain == 'frontend' and 'frontend' in role_lower:
                    score += 1.5
            
            if score > best_score:
                best_score = score
                best_member = member
                matched_skills = skills
        
        if best_member and best_score > 0:
            reasoning = self._generate_skill_reasoning(best_member, matched_skills, task_domains)
            return AssignmentResult(
                team_member=best_member,
                reasoning=reasoning,
                confidence=min(best_score, 1.0)
            )
        
        return None
    
    def _extract_domains(self, text: str) -> Set[str]:
        """Extracts skill domains from text based on keywords."""
        text_lower = text.lower()
        domains = set()
        
        for keyword, domain in self._keyword_to_domain.items():
            if keyword in text_lower:
                domains.add(domain)
        
        return domains
    
    def _calculate_skill_score(
        self,
        task_domains: Set[str],
        member: TeamMember
    ) -> tuple[float, List[str]]:
        """
        Calculates match score between task domains and member skills.
        
        Returns:
            Tuple of (score, list of matched skills)
        """
        matched_skills = []
        score = 0.0
        
        # Check member skills against task domains
        for skill in member.skills:
            skill_lower = skill.lower()
            
            # Direct skill match
            for domain in task_domains:
                if domain in skill_lower or skill_lower in domain:
                    matched_skills.append(skill)
                    score += 0.5
                    break
                
                # Check if skill matches domain keywords
                domain_keywords = self.SKILL_KEYWORDS.get(domain, [])
                for keyword in domain_keywords:
                    if keyword in skill_lower or skill_lower in keyword:
                        matched_skills.append(skill)
                        score += 0.3
                        break
        
        # Check role relevance
        role_lower = member.role.lower()
        for domain in task_domains:
            role_keywords = self.ROLE_DOMAINS.get(domain, [])
            for keyword in role_keywords:
                if keyword in role_lower:
                    score += 0.4
                    break
        
        return score, matched_skills
    
    def _generate_skill_reasoning(
        self,
        member: TeamMember,
        matched_skills: List[str],
        task_domains: Set[str]
    ) -> str:
        """Generates reasoning string for skill-based assignment."""
        parts = []
        
        if matched_skills:
            skills_str = ", ".join(set(matched_skills))
            parts.append(f"Matched skills: {skills_str}")
        
        if task_domains:
            domains_str = ", ".join(task_domains)
            parts.append(f"Task domains: {domains_str}")
        
        parts.append(f"Role: {member.role}")
        
        return "; ".join(parts)
