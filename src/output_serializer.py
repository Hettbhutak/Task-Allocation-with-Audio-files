"""Output serialization component for JSON formatting."""

import csv
import json
from io import StringIO
from typing import Any, Dict, List

from src.models import TaskOutput, PipelineResult


class OutputSerializer:
    """Serializes task results to JSON format."""
    
    REQUIRED_FIELDS = ['task_number', 'description', 'priority']
    OPTIONAL_FIELDS = ['assigned_to', 'deadline', 'dependencies', 'reasoning']
    
    def serialize(self, tasks: List[TaskOutput]) -> str:
        """
        Serializes a list of tasks to JSON string.
        
        Args:
            tasks: List of TaskOutput objects
            
        Returns:
            JSON string representation
        """
        task_dicts = [self.to_dict(task) for task in tasks]
        return json.dumps(task_dicts, indent=2)
    
    def deserialize(self, json_str: str) -> List[TaskOutput]:
        """
        Deserializes JSON string to list of TaskOutput objects.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            List of TaskOutput objects
        """
        data = json.loads(json_str)
        
        if isinstance(data, list):
            return [TaskOutput.from_dict(item) for item in data]
        elif isinstance(data, dict) and 'tasks' in data:
            return [TaskOutput.from_dict(item) for item in data['tasks']]
        else:
            raise ValueError("Invalid JSON format: expected list or object with 'tasks' key")
    
    def to_dict(self, task: TaskOutput) -> Dict[str, Any]:
        """
        Converts TaskOutput to dictionary with all fields.
        
        Args:
            task: TaskOutput object
            
        Returns:
            Dictionary representation
        """
        return {
            'task_number': task.task_number,
            'description': task.description,
            'assigned_to': task.assigned_to,
            'deadline': task.deadline,
            'priority': task.priority,
            'dependencies': task.dependencies,
            'reasoning': task.reasoning
        }
    
    def from_dict(self, data: Dict[str, Any]) -> TaskOutput:
        """
        Creates TaskOutput from dictionary.
        
        Args:
            data: Dictionary with task data
            
        Returns:
            TaskOutput object
        """
        return TaskOutput.from_dict(data)
    
    def serialize_result(self, result: PipelineResult) -> str:
        """
        Serializes a complete pipeline result to JSON.
        
        Args:
            result: PipelineResult object
            
        Returns:
            JSON string representation
        """
        return result.to_json()
    
    def deserialize_result(self, json_str: str) -> PipelineResult:
        """
        Deserializes JSON string to PipelineResult.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            PipelineResult object
        """
        return PipelineResult.from_json(json_str)
    
    def validate_task_dict(self, data: Dict[str, Any]) -> bool:
        """
        Validates that a task dictionary has all required fields.
        
        Args:
            data: Dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                return False
        return True
    
    def get_missing_fields(self, data: Dict[str, Any]) -> List[str]:
        """
        Returns list of missing required fields.
        
        Args:
            data: Dictionary to check
            
        Returns:
            List of missing field names
        """
        return [f for f in self.REQUIRED_FIELDS if f not in data]
    
    def format_for_display(self, tasks: List[TaskOutput]) -> str:
        """
        Formats tasks for human-readable display using rich formatting.
        
        Args:
            tasks: List of TaskOutput objects
            
        Returns:
            Formatted string for display
        """
        from io import StringIO
        from rich.console import Console
        from src.cli_ui import CLIRenderer, strip_ansi
        from src.models import PipelineResult
        
        # Create a result object for the renderer
        result = PipelineResult(success=True, tasks=tasks)
        
        # Use CLIRenderer to get rich output
        string_io = StringIO()
        console = Console(force_terminal=True, file=string_io)
        renderer = CLIRenderer(console)
        renderer.show_results(result)
        
        # Return plain text (ANSI stripped) for compatibility
        return strip_ansi(string_io.getvalue())

    def serialize_to_csv(self, tasks: List[TaskOutput]) -> str:
        """
        Serializes a list of tasks to CSV format.
        
        Args:
            tasks: List of TaskOutput objects
            
        Returns:
            CSV string representation
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Task Number',
            'Description',
            'Assigned To',
            'Deadline',
            'Priority',
            'Dependencies',
            'Reasoning'
        ])
        
        # Write task rows
        for task in tasks:
            writer.writerow([
                task.task_number,
                task.description,
                task.assigned_to or '',
                task.deadline or '',
                task.priority,
                task.dependencies or '',
                task.reasoning or ''
            ])
        
        return output.getvalue()
