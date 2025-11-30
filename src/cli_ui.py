"""CLI UI components for rich terminal output."""

import re
from dataclasses import dataclass, field
from datetime import date
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich import box

from src.models import TaskOutput, PipelineResult


@dataclass
class CLITheme:
    """Defines the color scheme and styles for CLI output."""
    
    # Brand colors
    primary: str = "blue"
    secondary: str = "bright_black"
    accent: str = "blue"
    
    # Priority colors - clear hierarchy
    priority_critical: str = "bold red"
    priority_high: str = "bold yellow"
    priority_medium: str = "blue"
    priority_low: str = "bright_black"
    
    # Status colors
    success: str = "bold green"
    warning: str = "bold yellow"
    error: str = "bold red"
    muted: str = "bright_black"
    
    # Element styles
    assignee: str = "bold blue"
    deadline_overdue: str = "white"
    deadline_upcoming: str = "white"
    deadline_ok: str = "white"
    
    def get_priority_style(self, priority: str) -> str:
        """Get the style for a priority level."""
        priority_map = {
            "Critical": self.priority_critical,
            "High": self.priority_high,
            "Medium": self.priority_medium,
            "Low": self.priority_low,
        }
        return priority_map.get(priority, self.muted)


class BannerRenderer:
    """Renders the application banner."""
    
    APP_NAME = "Scribe"
    VERSION = "1.0.0"
    TAGLINE = "Your intelligent meeting assistant"
    
    ASCII_ART = """
╔═╗┌─┐┬─┐┬┌┐ ┌─┐
╚═╗│  ├┬┘│├┴┐├┤ 
╚═╝└─┘┴└─┴└─┘└─┘"""
    
    def __init__(self, theme: CLITheme = None):
        self.theme = theme or CLITheme()
    
    def render(self, console: Console) -> None:
        """Display the welcome banner."""
        from rich.align import Align
        from rich.console import Group
        
        # Create centered ASCII art
        art = Text(self.ASCII_ART, style="bold blue")
        
        # Create tagline
        tagline = Text(self.TAGLINE, style="bright_black italic")
        
        # Group everything with center alignment
        group = Group(
            Align.center(art),
            Text(),  # Empty line
            Align.center(tagline)
        )
        
        panel = Panel(
            group,
            border_style="blue",
            box=box.DOUBLE,
            padding=(1, 2),
            expand=False
        )
        console.print(panel, justify="center")
        console.print()
    
    def get_banner_text(self) -> str:
        """Returns banner text for testing."""
        return f"{self.APP_NAME} v{self.VERSION} - {self.TAGLINE}"



class ProgressRenderer:
    """Manages progress display during processing."""
    
    CHECKMARK = "✓"
    CROSS = "✗"
    
    def __init__(self, console: Console, theme: CLITheme = None):
        self.console = console
        self.theme = theme or CLITheme()
        self._progress: Optional[Progress] = None
        self._task_id = None
    
    def start_stage(self, stage_name: str) -> None:
        """Start a processing stage with spinner."""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        )
        self._progress.start()
        self._task_id = self._progress.add_task(f"[{self.theme.primary}]{stage_name}...", total=None)
    
    def complete_stage(self, stage_name: str) -> None:
        """Mark a stage as complete with checkmark."""
        if self._progress:
            self._progress.stop()
            self._progress = None
        self.console.print(f"[{self.theme.success}]{self.CHECKMARK}[/] {stage_name}")
    
    def fail_stage(self, stage_name: str, error: str) -> None:
        """Mark a stage as failed with error indicator."""
        if self._progress:
            self._progress.stop()
            self._progress = None
        self.console.print(f"[{self.theme.error}]{self.CROSS}[/] {stage_name}: {error}")
    
    def get_completion_text(self, stage_name: str) -> str:
        """Get completion text for testing."""
        return f"{self.CHECKMARK} {stage_name}"
    
    def get_failure_text(self, stage_name: str, error: str) -> str:
        """Get failure text for testing."""
        return f"{self.CROSS} {stage_name}: {error}"



class TaskTableRenderer:
    """Renders tasks as a rich table."""
    
    DEPENDENCY_ICON = "->"
    
    def __init__(self, theme: CLITheme = None):
        self.theme = theme or CLITheme()
    
    def render(self, tasks: List[TaskOutput], console: Console) -> None:
        """Render tasks as a formatted table."""
        table = Table(
            title="Task Assignments",
            box=box.ROUNDED,
            header_style="bold white",
            border_style="bright_black",
            show_lines=True,
        )
        
        table.add_column("#", style="dim", width=4)
        table.add_column("Description", min_width=30)
        table.add_column("Assignee", min_width=12)
        table.add_column("Deadline", min_width=12)
        table.add_column("Priority", min_width=10)
        table.add_column("Dependencies", min_width=15)
        table.add_column("Reasoning", min_width=20)
        
        for task in tasks:
            table.add_row(
                str(task.task_number),
                task.description,
                self.format_assignee(task.assigned_to),
                self.format_deadline(task.deadline),
                self.format_priority(task.priority),
                self.format_dependencies(task.dependencies),
                self.format_reasoning(task.reasoning),
            )
        
        console.print(table)
    
    def format_priority(self, priority: str) -> Text:
        """Format priority with appropriate color."""
        style = self.theme.get_priority_style(priority)
        return Text(priority, style=style)
    
    def format_assignee(self, name: Optional[str]) -> Text:
        """Format assignee name with highlighting."""
        if name:
            return Text(name, style=self.theme.assignee)
        return Text("Unassigned", style=self.theme.muted)
    
    def format_deadline(self, deadline: Optional[str], reference_date: date = None) -> Text:
        """Format deadline with default color and capitalize first letter."""
        if not deadline:
            return Text("Not set", style=self.theme.muted)
        
        # Capitalize first letter
        formatted_deadline = deadline[0].upper() + deadline[1:] if deadline else deadline
        
        # Return deadline with default color (no special styling)
        return Text(formatted_deadline)
    
    def format_dependencies(self, deps: Optional[str]) -> Text:
        """Format dependencies with icon."""
        if deps:
            return Text(f"{self.DEPENDENCY_ICON} {deps}", style=self.theme.warning)
        return Text("-", style=self.theme.muted)
    
    def format_reasoning(self, reasoning: Optional[str]) -> Text:
        """Format reasoning text with better formatting and highlighted labels."""
        if not reasoning:
            return Text("-", style=self.theme.muted)
        
        # Split reasoning into parts
        text = Text()
        
        # Handle "Matched skills:"
        if "Matched skills:" in reasoning:
            parts = reasoning.split("Matched skills:", 1)
            if parts[0]:
                text.append(parts[0], style=self.theme.muted)
            text.append("Matched skills:", style="white")
            remaining = parts[1]
        else:
            remaining = reasoning
        
        # Handle "Task domains:"
        if "Task domains:" in remaining:
            parts = remaining.split("Task domains:", 1)
            text.append(parts[0].replace("; Task domains:", ""), style=self.theme.muted)
            text.append("\nTask domains:", style="white")
            remaining = parts[1]
        else:
            text.append(remaining, style=self.theme.muted)
            return text
        
        # Handle "Role:"
        if "Role:" in remaining:
            parts = remaining.split("Role:", 1)
            text.append(parts[0].replace("; ", ""), style=self.theme.muted)
            text.append("\nRole:", style="white")
            text.append(parts[1], style=self.theme.muted)
        else:
            text.append(remaining, style=self.theme.muted)
        
        return text
    
    def get_table_text(self, tasks: List[TaskOutput]) -> str:
        """Get table as plain text for testing."""
        console = Console(force_terminal=True, file=StringIO())
        self.render(tasks, console)
        return console.file.getvalue()



class PanelRenderer:
    """Renders styled panels for various content types."""
    
    def __init__(self, theme: CLITheme = None):
        self.theme = theme or CLITheme()
    
    def error_panel(self, title: str, message: str, suggestions: List[str] = None) -> Panel:
        """Create an error panel with optional suggestions."""
        content = Text()
        content.append(message, style=self.theme.error)
        
        if suggestions:
            content.append("\n\nSuggestions:\n", style=self.theme.warning)
            for suggestion in suggestions:
                content.append(f"   • {suggestion}\n", style=self.theme.muted)
        
        return Panel(
            content,
            title=f"ERROR: {title}",
            border_style=self.theme.error,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    
    def success_panel(self, title: str, message: str) -> Panel:
        """Create a success panel."""
        content = Text(message, style=self.theme.success)
        return Panel(
            content,
            title=f"SUCCESS: {title}",
            border_style=self.theme.success,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    
    def warning_panel(self, title: str, message: str) -> Panel:
        """Create a warning panel."""
        content = Text(message, style=self.theme.warning)
        return Panel(
            content,
            title=f"WARNING: {title}",
            border_style=self.theme.warning,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    
    def info_panel(self, title: str, content: str) -> Panel:
        """Create an info panel."""
        text = Text(content, style=self.theme.muted)
        return Panel(
            text,
            title=f"INFO: {title}",
            border_style=self.theme.secondary,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    
    def get_error_text(self, title: str, message: str) -> str:
        """Get error panel as text for testing."""
        console = Console(force_terminal=True, file=StringIO())
        console.print(self.error_panel(title, message))
        return console.file.getvalue()


    def api_key_error_panel(self) -> Panel:
        """Create API key missing error panel with setup instructions."""
        content = Text()
        content.append("AssemblyAI API Key Not Found\n\n", style="bold red")
        content.append("To use this application, you need an AssemblyAI API key.\n\n", style="white")
        content.append("Steps to get your API key:\n", style="bold yellow")
        content.append("  1. Sign up at: ", style="white")
        content.append("https://www.assemblyai.com/dashboard/signup\n", style="blue underline")
        content.append("  2. Get your API key from the dashboard\n", style="white")
        content.append("  3. Create a .env file in the project root with:\n", style="white")
        content.append("     ASSEMBLYAI_API_KEY=your_api_key_here\n", style="green")
        
        return Panel(
            content,
            title="API Key Required",
            border_style="red",
            box=box.DOUBLE,
            padding=(1, 2),
        )



@dataclass
class SummaryStats:
    """Statistics for the summary display."""
    total_tasks: int
    assigned_count: int
    unassigned_count: int
    priority_counts: Dict[str, int]
    has_warnings: bool
    warning_message: Optional[str]


class SummaryRenderer:
    """Renders the processing summary."""
    
    def __init__(self, theme: CLITheme = None):
        self.theme = theme or CLITheme()
    
    def calculate_stats(self, tasks: List[TaskOutput]) -> SummaryStats:
        """Calculate summary statistics."""
        total = len(tasks)
        assigned = sum(1 for t in tasks if t.assigned_to)
        unassigned = total - assigned
        
        priority_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for task in tasks:
            if task.priority in priority_counts:
                priority_counts[task.priority] += 1
        
        return SummaryStats(
            total_tasks=total,
            assigned_count=assigned,
            unassigned_count=unassigned,
            priority_counts=priority_counts,
            has_warnings=False,
            warning_message=None,
        )
    
    def render(self, result: PipelineResult, console: Console) -> None:
        """Render the summary panel."""
        stats = self.calculate_stats(result.tasks)
        
        content = Text()
        content.append(f"Total Tasks: ", style="bold")
        content.append(f"{stats.total_tasks}\n", style=self.theme.primary)
        
        content.append(f"Assigned: ", style="bold")
        content.append(f"{stats.assigned_count}  ", style=self.theme.success)
        content.append(f"Unassigned: ", style="bold")
        content.append(f"{stats.unassigned_count}\n\n", style=self.theme.warning if stats.unassigned_count > 0 else self.theme.muted)
        
        content.append("Priority Breakdown:\n", style="bold")
        for priority, count in stats.priority_counts.items():
            if count > 0:
                style = self.theme.get_priority_style(priority)
                content.append(f"  • {priority}: {count}\n", style=style)
        
        # Success message if all assigned
        if stats.assigned_count == stats.total_tasks and stats.total_tasks > 0:
            content.append("\n", style="bold")
            content.append("All tasks have been assigned!", style=self.theme.success)
        
        # Warning if present
        if result.error_message:
            content.append(f"\n\nWARNING: {result.error_message}", style=self.theme.warning)
        
        panel = Panel(
            content,
            title="Summary",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2),
        )
        console.print(panel)
    
    def get_summary_text(self, result: PipelineResult) -> str:
        """Get summary as text for testing."""
        console = Console(force_terminal=True, file=StringIO())
        self.render(result, console)
        return console.file.getvalue()



class TranscriptRenderer:
    """Renders transcript display."""
    
    MAX_DISPLAY_LENGTH = 500
    
    def __init__(self, theme: CLITheme = None):
        self.theme = theme or CLITheme()
    
    def truncate_text(self, text: str, max_length: int = None) -> Tuple[str, bool]:
        """Truncate text if needed, return (text, was_truncated)."""
        max_len = max_length or self.MAX_DISPLAY_LENGTH
        if len(text) <= max_len:
            return text, False
        return text[:max_len] + "...", True
    
    def render(self, transcript: str, console: Console, truncate: bool = True) -> None:
        """Render transcript in a panel."""
        if truncate:
            display_text, was_truncated = self.truncate_text(transcript)
        else:
            display_text = transcript
            was_truncated = False
        
        content = Text(display_text, style=self.theme.muted)
        
        if was_truncated:
            content.append(f"\n\n[{len(transcript)} characters total]", style="dim italic")
        
        panel = Panel(
            content,
            title="Transcript",
            border_style=self.theme.muted,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        console.print(panel)
    
    def get_transcript_text(self, transcript: str, truncate: bool = True) -> str:
        """Get transcript panel as text for testing."""
        console = Console(force_terminal=True, file=StringIO())
        self.render(transcript, console, truncate)
        return console.file.getvalue()



def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_pattern.sub('', text)


class CLIRenderer:
    """Main CLI rendering facade."""
    
    def __init__(self, console: Console = None, theme: CLITheme = None):
        self.console = console or Console()
        self.theme = theme or CLITheme()
        self.banner = BannerRenderer(self.theme)
        self.progress = ProgressRenderer(self.console, self.theme)
        self.tasks = TaskTableRenderer(self.theme)
        self.panels = PanelRenderer(self.theme)
        self.summary = SummaryRenderer(self.theme)
        self.transcript = TranscriptRenderer(self.theme)
        self._content_buffer = []  # Buffer to collect content for boxing
    
    def show_banner(self) -> None:
        """Display welcome banner."""
        self.banner.render(self.console)
    
    def show_error(self, title: str, message: str, suggestions: List[str] = None) -> None:
        """Display error panel."""
        panel = self.panels.error_panel(title, message, suggestions)
        self.console.print(panel)
    
    def show_success(self, title: str, message: str) -> None:
        """Display success panel."""
        panel = self.panels.success_panel(title, message)
        self.console.print(panel)
    
    def show_warning(self, title: str, message: str) -> None:
        """Display warning panel."""
        panel = self.panels.warning_panel(title, message)
        self.console.print(panel)
    
    def show_api_key_error(self) -> None:
        """Display API key missing error with setup instructions."""
        panel = self.panels.api_key_error_panel()
        self.console.print(panel)
    
    def show_results(self, result: PipelineResult, show_transcript: bool = True, boxed: bool = True) -> None:
        """Display complete results with transcript, tasks and summary."""
        if boxed:
            # Create renderables list for Group
            from rich.console import Group
            from rich.panel import Panel
            from rich import box
            from rich.text import Text
            
            renderables = []
            
            # Add transcript if available
            if show_transcript and result.transcript:
                transcript_text, was_truncated = self.transcript.truncate_text(result.transcript)
                content = Text(transcript_text, style=self.theme.muted)
                if was_truncated:
                    content.append(f"\n\n[{len(result.transcript)} characters total]", style="dim italic")
                
                renderables.append(Panel(
                    content,
                    title="Transcript",
                    border_style=self.theme.muted,
                    box=box.ROUNDED,
                    padding=(1, 2),
                ))
                renderables.append(Text())  # Spacing
            
            # Add tasks table
            if result.tasks:
                renderables.append(self._create_task_table(result.tasks))
                renderables.append(Text())  # Spacing
            
            # Add summary
            renderables.append(self._create_summary_panel(result))
            
            # Group all content
            group = Group(*renderables)
            
            # Wrap in outer panel
            outer_panel = Panel(
                group,
                border_style="blue",
                box=box.DOUBLE,
                padding=(1, 2),
                title="[bold blue]Scribe Results[/bold blue]",
                title_align="center"
            )
            self.console.print(outer_panel)
        else:
            # Show transcript first if available
            if show_transcript and result.transcript:
                self.transcript.render(result.transcript, self.console)
                self.console.print()
            
            # Then show tasks
            if result.tasks:
                self.tasks.render(result.tasks, self.console)
                self.console.print()
            
            # Finally show summary
            self.summary.render(result, self.console)
    
    def _create_task_table(self, tasks: List[TaskOutput]) -> Table:
        """Create a task table renderable."""
        table = Table(
            title="Task Assignments",
            box=box.ROUNDED,
            header_style="bold white",
            border_style="bright_black",
            show_lines=True,
        )
        
        table.add_column("#", style="dim", width=4)
        table.add_column("Description", min_width=30)
        table.add_column("Assignee", min_width=12)
        table.add_column("Deadline", min_width=12)
        table.add_column("Priority", min_width=10)
        table.add_column("Dependencies", min_width=15)
        table.add_column("Reasoning", min_width=20)
        
        for task in tasks:
            table.add_row(
                str(task.task_number),
                task.description,
                self.tasks.format_assignee(task.assigned_to),
                self.tasks.format_deadline(task.deadline),
                self.tasks.format_priority(task.priority),
                self.tasks.format_dependencies(task.dependencies),
                self.tasks.format_reasoning(task.reasoning),
            )
        
        return table
    
    def _create_summary_panel(self, result: PipelineResult) -> Panel:
        """Create a summary panel renderable."""
        from rich.panel import Panel
        from rich import box
        from rich.text import Text
        
        stats = self.summary.calculate_stats(result.tasks)
        
        content = Text()
        content.append(f"Total Tasks: ", style="bold")
        content.append(f"{stats.total_tasks}\n", style=self.theme.primary)
        
        content.append(f"Assigned: ", style="bold")
        content.append(f"{stats.assigned_count}  ", style=self.theme.success)
        content.append(f"Unassigned: ", style="bold")
        content.append(f"{stats.unassigned_count}\n\n", style=self.theme.warning if stats.unassigned_count > 0 else self.theme.muted)
        
        content.append("Priority Breakdown:\n", style="bold")
        for priority, count in stats.priority_counts.items():
            if count > 0:
                style = self.theme.get_priority_style(priority)
                content.append(f"  • {priority}: {count}\n", style=style)
        
        # Success message if all assigned
        if stats.assigned_count == stats.total_tasks and stats.total_tasks > 0:
            content.append("\n", style="bold")
            content.append("All tasks have been assigned!", style=self.theme.success)
        
        # Warning if present
        if result.error_message:
            content.append(f"\n\nWARNING: {result.error_message}", style=self.theme.warning)
        
        return Panel(
            content,
            title="Summary",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    
    def show_transcript(self, transcript: str) -> None:
        """Display transcript panel."""
        self.transcript.render(transcript, self.console)
    
    def start_processing(self, stage: str) -> None:
        """Start a processing stage with spinner."""
        self.progress.start_stage(stage)
    
    def complete_processing(self, stage: str) -> None:
        """Complete a processing stage."""
        self.progress.complete_stage(stage)
    
    def fail_processing(self, stage: str, error: str) -> None:
        """Fail a processing stage."""
        self.progress.fail_stage(stage, error)
    
    def get_rich_output(self, result: PipelineResult) -> str:
        """Get rich formatted output as string."""
        string_io = StringIO()
        temp_console = Console(force_terminal=True, file=string_io)
        
        if result.tasks:
            self.tasks.render(result.tasks, temp_console)
            temp_console.print()
        
        self.summary.render(result, temp_console)
        
        return string_io.getvalue()
    
    def get_plain_output(self, result: PipelineResult) -> str:
        """Get plain text output (ANSI stripped) for file output."""
        rich_output = self.get_rich_output(result)
        return strip_ansi(rich_output)
