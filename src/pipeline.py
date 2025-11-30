"""Main pipeline orchestrator for the Meeting Task Assignment System."""

from datetime import date
from typing import List, Optional

from src.models import (
    TeamMember, TaskOutput, PipelineResult, PriorityLevel
)
from src.audio_validator import AudioValidator
from src.stt_adapter import STTServiceAdapter, MockSTTAdapter
from src.team_store import TeamMemberStore
from src.task_extractor import TaskExtractor
from src.deadline_parser import DeadlineParser
from src.priority_classifier import PriorityClassifier
from src.assignment_engine import AssignmentEngine
from src.dependency_resolver import DependencyResolver
from src.output_serializer import OutputSerializer


class MeetingTaskPipeline:
    """Orchestrates the complete meeting task extraction and assignment pipeline."""
    
    def __init__(
        self,
        stt_adapter: Optional[STTServiceAdapter] = None
    ):
        """
        Initialize the pipeline with all components.
        
        Args:
            stt_adapter: STT adapter for audio transcription (required for audio processing)
        """
        self.audio_validator = AudioValidator()
        self.stt_adapter = stt_adapter
        self.task_extractor = TaskExtractor()
        self.deadline_parser = DeadlineParser()
        self.priority_classifier = PriorityClassifier()
        self.assignment_engine = AssignmentEngine()
        self.dependency_resolver = DependencyResolver()
        self.output_serializer = OutputSerializer()
    
    def process(
        self,
        audio_path: str,
        team_members: List[TeamMember],
        reference_date: Optional[date] = None
    ) -> PipelineResult:
        """
        Processes an audio file and returns assigned tasks.
        
        Args:
            audio_path: Path to the meeting audio file
            team_members: List of team members for assignment
            reference_date: Reference date for deadline calculations
            
        Returns:
            PipelineResult with extracted and assigned tasks
        """
        ref_date = reference_date or date.today()
        
        # Step 1: Validate audio file
        validation = self.audio_validator.validate(audio_path)
        if not validation.is_valid:
            return PipelineResult(
                success=False,
                error_message=f"Audio validation failed: {validation.error_message}"
            )
        
        # Step 2: Transcribe audio
        transcription = self.stt_adapter.transcribe(audio_path)
        if not transcription.success:
            return PipelineResult(
                success=False,
                error_message=f"Transcription failed: {transcription.error_message}"
            )
        
        transcript = transcription.transcript
        
        # Step 3: Set up team store
        team_store = TeamMemberStore()
        for member in team_members:
            team_store.add_member(member)
        
        # Update task extractor with team names
        self.task_extractor.set_team_names(team_store.get_all_names())
        
        # Step 4: Extract tasks from transcript
        extracted_tasks = self.task_extractor.extract_tasks(transcript)
        
        if not extracted_tasks:
            return PipelineResult(
                success=True,
                tasks=[],
                transcript=transcript,
                error_message="No tasks identified in the meeting transcript"
            )
        
        # Step 5: Process each task
        task_outputs = []
        for i, extracted in enumerate(extracted_tasks):
            # Parse deadline
            deadline = None
            deadline_raw = extracted.deadline_phrase
            if deadline_raw:
                deadline = self.deadline_parser.parse(deadline_raw, ref_date)
            
            # Classify priority
            priority = self.priority_classifier.classify(
                extracted, deadline, ref_date
            )
            
            # Assign to team member
            assignment = self.assignment_engine.assign(extracted, team_store)
            
            task_output = TaskOutput(
                task_number=i + 1,
                description=extracted.description,
                assigned_to=assignment.team_member.name if assignment.team_member else None,
                deadline=deadline_raw or (deadline.isoformat() if deadline else None),
                priority=priority.value,
                dependencies=None,  # Will be filled in dependency resolution
                reasoning=assignment.reasoning if assignment.team_member else None
            )
            task_outputs.append(task_output)
        
        # Step 6: Resolve dependencies
        dependencies = self.dependency_resolver.resolve(extracted_tasks)
        
        # Update task outputs with dependency info
        for dep in dependencies:
            if dep.dependent_task_index < len(task_outputs):
                prereq_num = dep.prerequisite_task_index + 1
                task_outputs[dep.dependent_task_index].dependencies = f"Depends on Task #{prereq_num}"
        
        # Check for circular dependencies
        cycles = self.dependency_resolver.detect_circular_dependencies(dependencies)
        warning = None
        if cycles:
            warning = f"Warning: Circular dependencies detected between tasks"
        
        return PipelineResult(
            success=True,
            tasks=task_outputs,
            transcript=transcript,
            error_message=warning
        )
    
    def process_transcript(
        self,
        transcript: str,
        team_members: List[TeamMember],
        reference_date: Optional[date] = None
    ) -> PipelineResult:
        """
        Processes a transcript directly (skipping audio validation and STT).
        
        Args:
            transcript: Meeting transcript text
            team_members: List of team members for assignment
            reference_date: Reference date for deadline calculations
            
        Returns:
            PipelineResult with extracted and assigned tasks
        """
        ref_date = reference_date or date.today()
        
        # Set up team store
        team_store = TeamMemberStore()
        for member in team_members:
            team_store.add_member(member)
        
        # Update task extractor with team names
        self.task_extractor.set_team_names(team_store.get_all_names())
        
        # Extract tasks from transcript
        extracted_tasks = self.task_extractor.extract_tasks(transcript)
        
        if not extracted_tasks:
            return PipelineResult(
                success=True,
                tasks=[],
                transcript=transcript,
                error_message="No tasks identified in the meeting transcript"
            )
        
        # Process each task
        task_outputs = []
        for i, extracted in enumerate(extracted_tasks):
            # Parse deadline
            deadline = None
            deadline_raw = extracted.deadline_phrase
            if deadline_raw:
                deadline = self.deadline_parser.parse(deadline_raw, ref_date)
            
            # Classify priority
            priority = self.priority_classifier.classify(
                extracted, deadline, ref_date
            )
            
            # Assign to team member
            assignment = self.assignment_engine.assign(extracted, team_store)
            
            task_output = TaskOutput(
                task_number=i + 1,
                description=extracted.description,
                assigned_to=assignment.team_member.name if assignment.team_member else None,
                deadline=deadline_raw or (deadline.isoformat() if deadline else None),
                priority=priority.value,
                dependencies=None,
                reasoning=assignment.reasoning if assignment.team_member else None
            )
            task_outputs.append(task_output)
        
        # Resolve dependencies
        dependencies = self.dependency_resolver.resolve(extracted_tasks)
        
        for dep in dependencies:
            if dep.dependent_task_index < len(task_outputs):
                prereq_num = dep.prerequisite_task_index + 1
                task_outputs[dep.dependent_task_index].dependencies = f"Depends on Task #{prereq_num}"
        
        cycles = self.dependency_resolver.detect_circular_dependencies(dependencies)
        warning = None
        if cycles:
            warning = f"Warning: Circular dependencies detected between tasks"
        
        return PipelineResult(
            success=True,
            tasks=task_outputs,
            transcript=transcript,
            error_message=warning
        )
    
    def get_json_output(self, result: PipelineResult) -> str:
        """Returns the pipeline result as JSON string."""
        return self.output_serializer.serialize_result(result)
    
    def get_display_output(self, result: PipelineResult) -> str:
        """Returns the pipeline result as formatted display string."""
        return self.output_serializer.format_for_display(result.tasks)
