"""Dependency resolution component for task relationships."""

import re
from typing import Dict, List, Optional, Set, Tuple

from src.models import ExtractedTask, TaskDependency


class DependencyResolver:
    """Identifies and resolves dependencies between tasks."""
    
    # Patterns for detecting dependency phrases
    DEPENDENCY_PATTERNS = [
        r'depends on (.+?)(?:\.|,|$)',
        r'after (.+?) is (?:done|completed|finished)',
        r'once (.+?) is (?:done|completed|finished)',
        r'blocked by (.+?)(?:\.|,|$)',
        r'waiting for (.+?)(?:\.|,|$)',
        r'requires (.+?) (?:to be |first|completed)',
        r'needs (.+?) (?:to be |first|completed)',
        r'can\'t start until (.+?)(?:\.|,|$)',
        r'prerequisite[s]?: (.+?)(?:\.|,|$)',
    ]
    
    def resolve(
        self,
        tasks: List[ExtractedTask]
    ) -> List[TaskDependency]:
        """
        Identifies dependencies between tasks.
        
        Args:
            tasks: List of extracted tasks
            
        Returns:
            List of TaskDependency objects
        """
        dependencies = []
        
        # Build a map of task descriptions for matching
        task_descriptions = [t.description.lower() for t in tasks]
        
        for i, task in enumerate(tasks):
            # Check dependency phrases from extraction
            for phrase in task.dependency_phrases:
                prereq_idx = self._find_matching_task(phrase, task_descriptions, exclude_idx=i)
                if prereq_idx is not None:
                    dependencies.append(TaskDependency(
                        dependent_task_index=i,
                        prerequisite_task_index=prereq_idx,
                        dependency_phrase=phrase
                    ))
            
            # Also scan raw text for dependency patterns
            text_deps = self._extract_dependencies_from_text(task.raw_text)
            for phrase in text_deps:
                if phrase not in task.dependency_phrases:
                    prereq_idx = self._find_matching_task(phrase, task_descriptions, exclude_idx=i)
                    if prereq_idx is not None:
                        dependencies.append(TaskDependency(
                            dependent_task_index=i,
                            prerequisite_task_index=prereq_idx,
                            dependency_phrase=phrase
                        ))
        
        return dependencies
    
    def _extract_dependencies_from_text(self, text: str) -> List[str]:
        """Extracts dependency phrases from text."""
        found = []
        text_lower = text.lower()
        
        for pattern in self.DEPENDENCY_PATTERNS:
            matches = re.findall(pattern, text_lower)
            found.extend(matches)
        
        return found
    
    def _find_matching_task(
        self,
        phrase: str,
        task_descriptions: List[str],
        exclude_idx: int
    ) -> Optional[int]:
        """
        Finds a task that matches the dependency phrase.
        
        Args:
            phrase: The dependency phrase to match
            task_descriptions: List of task descriptions (lowercase)
            exclude_idx: Index to exclude (the dependent task itself)
            
        Returns:
            Index of matching task or None
        """
        phrase_lower = phrase.lower().strip()
        
        # Try to find a task that contains key words from the phrase
        phrase_words = set(phrase_lower.split())
        
        # Remove common filler words
        filler_words = {'the', 'a', 'an', 'is', 'are', 'being', 'completed', 'done', 'finished', 'first'}
        phrase_words = phrase_words - filler_words
        
        best_match_idx = None
        best_match_score = 0
        
        for i, desc in enumerate(task_descriptions):
            if i == exclude_idx:
                continue
            
            # Check for phrase containment
            if phrase_lower in desc or desc in phrase_lower:
                return i
            
            # Check for key term matches (login, bug, database, etc.)
            desc_words = set(desc.split()) - filler_words
            
            # Check for partial word matches (e.g., "login" matches "login bug")
            for phrase_word in phrase_words:
                for desc_word in desc_words:
                    if phrase_word in desc_word or desc_word in phrase_word:
                        # Strong match on key terms
                        if phrase_word in ['login', 'bug', 'database', 'api', 'test', 'payment', 'onboarding']:
                            return i
            
            # Check for word overlap
            overlap = len(phrase_words & desc_words)
            
            if overlap > best_match_score and overlap >= 1:
                best_match_score = overlap
                best_match_idx = i
        
        return best_match_idx
    
    def detect_circular_dependencies(
        self,
        dependencies: List[TaskDependency]
    ) -> List[Tuple[int, int]]:
        """
        Detects circular dependency chains.
        
        Args:
            dependencies: List of task dependencies
            
        Returns:
            List of (task_a, task_b) tuples forming cycles
        """
        # Build adjacency list
        graph: Dict[int, Set[int]] = {}
        for dep in dependencies:
            if dep.dependent_task_index not in graph:
                graph[dep.dependent_task_index] = set()
            graph[dep.dependent_task_index].add(dep.prerequisite_task_index)
        
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: int, path: List[int]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor, path + [neighbor]):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycles.append((node, neighbor))
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                dfs(node, [node])
        
        return cycles
    
    def has_dependency_phrase(self, text: str) -> bool:
        """Checks if text contains any dependency phrases."""
        text_lower = text.lower()
        
        for pattern in self.DEPENDENCY_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def get_dependency_order(
        self,
        num_tasks: int,
        dependencies: List[TaskDependency]
    ) -> List[int]:
        """
        Returns tasks in dependency order (topological sort).
        
        Args:
            num_tasks: Total number of tasks
            dependencies: List of dependencies
            
        Returns:
            List of task indices in execution order
        """
        # Build adjacency list and in-degree count
        graph: Dict[int, Set[int]] = {i: set() for i in range(num_tasks)}
        in_degree = {i: 0 for i in range(num_tasks)}
        
        for dep in dependencies:
            graph[dep.prerequisite_task_index].add(dep.dependent_task_index)
            in_degree[dep.dependent_task_index] += 1
        
        # Kahn's algorithm
        queue = [i for i in range(num_tasks) if in_degree[i] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If result doesn't contain all tasks, there's a cycle
        if len(result) != num_tasks:
            # Return partial order
            remaining = [i for i in range(num_tasks) if i not in result]
            result.extend(remaining)
        
        return result
