"""Core data models for the Meeting Task Assignment System."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class PriorityLevel(Enum):
    """Task priority levels from most to least urgent."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class TeamMember:
    """Represents a team member who can be assigned tasks."""
    name: str
    role: str
    skills: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Normalize skills to lowercase and trimmed."""
        self.skills = [s.lower().strip() for s in self.skills if s.strip()]

    def normalized_skills(self) -> List[str]:
        """Returns the normalized skill list."""
        return self.skills

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "role": self.role,
            "skills": self.skills
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamMember":
        """Create TeamMember from dictionary."""
        return cls(
            name=data.get("name", ""),
            role=data.get("role", ""),
            skills=data.get("skills", [])
        )


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    error_message: Optional[str] = None
    file_format: Optional[str] = None
    missing_fields: List[str] = field(default_factory=list)


@dataclass
class AudioMetadata:
    """Metadata extracted from an audio file."""
    duration_seconds: float
    format: str
    file_size_bytes: int


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription."""
    success: bool
    transcript: Optional[str] = None
    error_message: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class ExtractedTask:
    """A task extracted from transcript text before full processing."""
    description: str
    raw_text: str
    mentioned_person: Optional[str] = None
    deadline_phrase: Optional[str] = None
    priority_indicators: List[str] = field(default_factory=list)
    dependency_phrases: List[str] = field(default_factory=list)


@dataclass
class TaskDependency:
    """Represents a dependency relationship between tasks."""
    dependent_task_index: int
    prerequisite_task_index: int
    dependency_phrase: str


@dataclass
class AssignmentResult:
    """Result of task assignment to a team member."""
    team_member: Optional[TeamMember] = None
    reasoning: str = ""
    confidence: float = 0.0


@dataclass
class Task:
    """A fully processed task with all attributes."""
    task_number: int
    description: str
    assigned_to: Optional[str] = None
    deadline: Optional[date] = None
    deadline_raw: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.MEDIUM
    dependencies: List[int] = field(default_factory=list)
    reasoning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_number": self.task_number,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "priority": self.priority.value,
            "dependencies": f"Depends on Task #{self.dependencies[0]}" if self.dependencies else None,
            "reasoning": self.reasoning
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from dictionary."""
        deadline = None
        if data.get("deadline"):
            deadline = date.fromisoformat(data["deadline"])
        
        dependencies = []
        dep_str = data.get("dependencies")
        if dep_str and "Task #" in str(dep_str):
            try:
                dep_num = int(str(dep_str).split("#")[1].split()[0])
                dependencies = [dep_num]
            except (IndexError, ValueError):
                pass
        
        priority = PriorityLevel.MEDIUM
        if data.get("priority"):
            for p in PriorityLevel:
                if p.value == data["priority"]:
                    priority = p
                    break
        
        return cls(
            task_number=data.get("task_number", 0),
            description=data.get("description", ""),
            assigned_to=data.get("assigned_to"),
            deadline=deadline,
            priority=priority,
            dependencies=dependencies,
            reasoning=data.get("reasoning")
        )


@dataclass
class TaskOutput:
    """Output format for a processed task."""
    task_number: int
    description: str
    assigned_to: Optional[str] = None
    deadline: Optional[str] = None
    priority: str = "Medium"
    dependencies: Optional[str] = None
    reasoning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_number": self.task_number,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "deadline": self.deadline,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "reasoning": self.reasoning
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskOutput":
        """Create TaskOutput from dictionary."""
        return cls(
            task_number=data.get("task_number", 0),
            description=data.get("description", ""),
            assigned_to=data.get("assigned_to"),
            deadline=data.get("deadline"),
            priority=data.get("priority", "Medium"),
            dependencies=data.get("dependencies"),
            reasoning=data.get("reasoning")
        )


@dataclass
class PipelineResult:
    """Result of the complete processing pipeline."""
    success: bool
    tasks: List[TaskOutput] = field(default_factory=list)
    transcript: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "tasks": [t.to_dict() for t in self.tasks],
            "transcript": self.transcript,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineResult":
        """Create PipelineResult from dictionary."""
        tasks = [TaskOutput.from_dict(t) for t in data.get("tasks", [])]
        return cls(
            success=data.get("success", False),
            tasks=tasks,
            transcript=data.get("transcript"),
            error_message=data.get("error_message")
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "PipelineResult":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
