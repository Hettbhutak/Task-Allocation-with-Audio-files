#!/usr/bin/env python3
"""Command-line interface for the Meeting Task Assignment System."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import List

from rich.console import Console, Group
from rich.panel import Panel
from rich import box

from src.models import TeamMember, PipelineResult
from src.pipeline import MeetingTaskPipeline
from src.stt_adapter import MockSTTAdapter
from src.cli_ui import CLIRenderer


def load_team_members(file_path: str) -> List[TeamMember]:
    """
    Loads team members from a JSON file.
    
    Args:
        file_path: Path to JSON file with team member data
        
    Returns:
        List of TeamMember objects
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    members = []
    for item in data:
        member = TeamMember(
            name=item['name'],
            role=item['role'],
            skills=item.get('skills', [])
        )
        members.append(member)
    
    return members


def main():
    """Main entry point for the CLI."""
    # Initialize renderer
    console = Console(stderr=True)
    renderer = CLIRenderer(console)
    
    parser = argparse.ArgumentParser(
        description='Scribe - Your intelligent meeting assistant that extracts and assigns tasks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process audio file with team data (shows rich table)
  python -m src.cli audio.mp3 --team team.json
  
  # Process with transcript directly (for testing)
  python -m src.cli --transcript "We need to fix the login bug" --team team.json
  
  # Output JSON to file
  python -m src.cli audio.mp3 --team team.json --output results.json --format json
  
  # Show transcript in output
  python -m src.cli audio.mp3 --team team.json --show-transcript
'''
    )
    
    parser.add_argument(
        'audio',
        nargs='?',
        help='Path to the meeting audio file (.wav, .mp3, .m4a)'
    )
    
    parser.add_argument(
        '--team', '-t',
        required=True,
        help='Path to JSON file containing team member data'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file path (defaults to stdout)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['json', 'text', 'csv'],
        default='text',
        help='Output format: text (rich table), json, or csv (default: text)'
    )
    
    parser.add_argument(
        '--transcript',
        help='Process transcript text directly instead of audio file'
    )
    
    parser.add_argument(
        '--date',
        help='Reference date for deadline calculations (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--show-transcript',
        action='store_true',
        help='Show the transcript in the output'
    )
    
    args = parser.parse_args()
    
    # Show banner
    renderer.show_banner()
    
    # Validate inputs
    if not args.audio and not args.transcript:
        parser.error('Either audio file or --transcript must be provided')
    
    if args.audio and args.transcript:
        parser.error('Cannot specify both audio file and --transcript')
    
    # Load team members
    try:
        team_members = load_team_members(args.team)
        if not team_members:
            renderer.show_error(
                "No Team Members",
                "No team members found in team file",
                ["Check that the JSON file contains team member data"]
            )
            sys.exit(1)
    except FileNotFoundError:
        renderer.show_error(
            "File Not Found",
            f"Team file not found: {args.team}",
            ["Check the file path is correct", "Ensure the file exists"]
        )
        sys.exit(1)
    except json.JSONDecodeError as e:
        renderer.show_error(
            "Invalid JSON",
            f"Invalid JSON in team file: {e}",
            ["Check the JSON syntax", "Validate the file with a JSON linter"]
        )
        sys.exit(1)
    
    renderer.complete_processing(f"Loaded {len(team_members)} team members")
    
    # Parse reference date
    ref_date = None
    if args.date:
        try:
            ref_date = date.fromisoformat(args.date)
        except ValueError:
            renderer.show_error(
                "Invalid Date",
                f"Invalid date format: {args.date}",
                ["Use YYYY-MM-DD format (e.g., 2025-12-01)"]
            )
            sys.exit(1)
    
    # Create pipeline with AssemblyAI STT adapter
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.environ.get('ASSEMBLYAI_API_KEY'):
        # If processing audio file (not transcript), offer default transcript
        if args.audio and not args.transcript:
            renderer.show_api_key_error()
            console.print()
            
            # Prompt user to use default transcript
            from rich.prompt import Confirm
            use_default = Confirm.ask(
                "[cyan]Would you like to use the pre-transcribed sample audio instead?[/cyan]",
                default=True
            )
            
            if use_default:
                # Load default transcript
                default_transcript_path = Path("samples/default_transcript.txt")
                if default_transcript_path.exists():
                    with open(default_transcript_path, 'r') as f:
                        args.transcript = f.read()
                    args.audio = None  # Clear audio file
                    renderer.complete_processing("Using default sample transcript")
                else:
                    renderer.show_error(
                        "File Not Found",
                        "Default transcript file not found at samples/default_transcript.txt"
                    )
                    sys.exit(1)
            else:
                sys.exit(1)
        elif args.transcript:
            # User provided transcript directly, no API key needed
            pass
        else:
            renderer.show_api_key_error()
            sys.exit(1)
    
    # Only create STT adapter if we have API key and need to process audio
    if os.environ.get('ASSEMBLYAI_API_KEY') and args.audio:
        from src.assemblyai_adapter import AssemblyAIAdapter
        stt_adapter = AssemblyAIAdapter()
        pipeline = MeetingTaskPipeline(stt_adapter=stt_adapter)
    else:
        # Use mock adapter for transcript-only processing
        pipeline = MeetingTaskPipeline(stt_adapter=MockSTTAdapter())
    
    # Process
    try:
        if args.transcript:
            # Process transcript with detailed progress
            renderer.start_processing("Validating transcript")
            renderer.complete_processing("Transcript validated")
            
            renderer.start_processing("Extracting tasks")
            renderer.complete_processing("Tasks extracted")
            
            renderer.start_processing("Analyzing priorities and deadlines")
            renderer.complete_processing("Priorities and deadlines analyzed")
            
            renderer.start_processing("Assigning tasks to team members")
            result = pipeline.process_transcript(args.transcript, team_members, ref_date)
            renderer.complete_processing("Tasks assigned")
            
            renderer.start_processing("Resolving dependencies")
            renderer.complete_processing("Dependencies resolved")
        else:
            # Check if audio file exists
            if not Path(args.audio).exists():
                renderer.show_error(
                    "File Not Found",
                    f"Audio file not found: {args.audio}",
                    ["Check the file path is correct"]
                )
                sys.exit(1)
            
            # Process audio with detailed progress
            renderer.start_processing("Validating audio file")
            renderer.complete_processing("Audio file validated")
            
            renderer.start_processing("Transcribing audio")
            renderer.complete_processing("Audio transcribed")
            
            renderer.start_processing("Extracting tasks")
            renderer.complete_processing("Tasks extracted")
            
            renderer.start_processing("Analyzing priorities and deadlines")
            renderer.complete_processing("Priorities and deadlines analyzed")
            
            renderer.start_processing("Assigning tasks to team members")
            result = pipeline.process(args.audio, team_members, ref_date)
            renderer.complete_processing("Tasks assigned")
            
            renderer.start_processing("Resolving dependencies")
            renderer.complete_processing("Dependencies resolved")
            
    except Exception as e:
        renderer.fail_processing("Processing", str(e))
        renderer.show_error("Processing Error", str(e))
        sys.exit(1)
    
    # Output to stdout console
    output_console = Console()
    output_renderer = CLIRenderer(output_console)
    
    # Format output
    if args.format == 'json':
        output = pipeline.get_json_output(result)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            renderer.show_success("Output Saved", f"Results written to: {args.output}")
        else:
            print(output)
    elif args.format == 'csv':
        csv_output = pipeline.output_serializer.serialize_to_csv(result.tasks)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(csv_output)
            renderer.show_success("Output Saved", f"CSV written to: {args.output}")
        else:
            # Show rich results first, then offer to export
            output_renderer.show_results(result)
            print("\n")
            print(csv_output)
    else:
        # Rich text format
        if args.output:
            # Strip ANSI for file output
            plain_output = output_renderer.get_plain_output(result)
            with open(args.output, 'w') as f:
                f.write(plain_output)
            renderer.show_success("Output Saved", f"Results written to: {args.output}")
        else:
            # Show transcript by default, unless user explicitly disabled it
            output_renderer.show_results(result)
            
            # Prompt to export as CSV
            if result.tasks:
                console.print()
                from rich.prompt import Confirm
                export_csv = Confirm.ask(
                    "[cyan]Would you like to export the results as CSV?[/cyan]",
                    default=False
                )
                
                if export_csv:
                    from rich.prompt import Prompt
                    csv_filename = Prompt.ask(
                        "[cyan]Enter filename[/cyan]",
                        default="task_assignments.csv"
                    )
                    
                    # Ensure .csv extension
                    if not csv_filename.endswith('.csv'):
                        csv_filename += '.csv'
                    
                    csv_output = pipeline.output_serializer.serialize_to_csv(result.tasks)
                    with open(csv_filename, 'w') as f:
                        f.write(csv_output)
                    
                    renderer.show_success("CSV Exported", f"Results saved to: {csv_filename}")
    
    # Exit with appropriate code
    if not result.success:
        sys.exit(1)


if __name__ == '__main__':
    main()
