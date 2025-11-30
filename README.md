# Scribe

An intelligent meeting assistant that automatically extracts and assigns tasks from meeting audio recordings to team members based on their skills and roles.

## Features

- **Audio Processing**: Supports WAV, MP3, and M4A audio formats with validation
- **Speech-to-Text**: AssemblyAI transcription service
- **Task Extraction**: Identifies actionable tasks from meeting discussions using custom NLP logic
- **Smart Assignment**: Matches tasks to team members based on:
  - Explicit mentions in the meeting
  - Skill-based matching
  - Role relevance
- **Deadline Parsing**: Understands natural language deadlines like "tomorrow", "next week", "by Friday"
- **Priority Classification**: Automatically determines task priority (Critical, High, Medium, Low)
- **Dependency Detection**: Identifies task dependencies and detects circular dependencies
- **Multiple Output Formats**: JSON, CSV, and rich terminal display
- **Interactive CLI**: Beautiful terminal interface with progress indicators and error handling

## Installation

### Prerequisites

- Python 3.10+

### Setup

1. Clone the repository

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure API key (for AssemblyAI transcription):
```bash
cp env.example .env
# Edit .env and add your AssemblyAI API key
```

Note: If no API key is provided, the system will offer to use a pre-transcribed sample or you can provide transcript text directly.


## Quick Start

Run the demo with sample data:

```bash
python3 run_demo.py
```

This will process the sample meeting audio and display task assignments in a rich terminal interface.

## Usage

### Command Line Interface

Process an audio file:
```bash
python -m src.cli samples/sample-meeting2.mp3 --team samples/team_members.json
```

Process with transcript directly (useful for testing without audio):
```bash
python -m src.cli --transcript "We need to fix the login bug by tomorrow" --team samples/team_members.json
```

Export results to CSV:
```bash
python -m src.cli samples/sample-meeting2.mp3 --team samples/team_members.json --format csv --output results.csv
```

### CLI Options

| Option | Description |
|--------|-------------|
| `audio` | Path to meeting audio file (.wav, .mp3, .m4a) |
| `--team, -t` | Path to JSON file with team member data (required) |
| `--output, -o` | Output file path (defaults to stdout) |
| `--format, -f` | Output format: `text` (rich table), `json`, or `csv` (default: text) |
| `--transcript` | Process transcript text directly instead of audio |
| `--date` | Reference date for deadline calculations (YYYY-MM-DD format) |
| `--show-transcript` | Include the full transcript in the output |

### Team Member JSON Format

```json
[
  {
    "name": "Sakshi",
    "role": "Frontend Developer",
    "skills": ["React", "JavaScript", "UI bugs", "CSS"]
  },
  {
    "name": "Mohit",
    "role": "Backend Engineer",
    "skills": ["Database", "APIs", "Performance optimization"]
  }
]
```

### Python API

```python
from src.models import TeamMember
from src.pipeline import MeetingTaskPipeline
from src.assemblyai_adapter import AssemblyAIAdapter

# Create team members
team = [
    TeamMember(name="Sakshi", role="Frontend Developer", skills=["React", "JavaScript", "UI bugs"]),
    TeamMember(name="Mohit", role="Backend Engineer", skills=["Database", "APIs", "Performance optimization"]),
]

# Create pipeline with AssemblyAI adapter
stt_adapter = AssemblyAIAdapter()  # Reads ASSEMBLYAI_API_KEY from environment
pipeline = MeetingTaskPipeline(stt_adapter=stt_adapter)

# Process audio file
result = pipeline.process("samples/sample-meeting2.mp3", team)

# Or process transcript directly (no STT needed)
result = pipeline.process_transcript("We need to fix the login bug by tomorrow", team)

# Get JSON output
json_output = pipeline.get_json_output(result)
print(json_output)

# Get formatted display output
display_output = pipeline.get_display_output(result)
print(display_output)

# Access individual tasks
for task in result.tasks:
    print(f"Task {task.task_number}: {task.description}")
    print(f"  Assigned to: {task.assigned_to}")
    print(f"  Priority: {task.priority}")
```

## Project Structure

```
scribe/
├── src/
│   ├── models.py                  # Core data models (TeamMember, Task, PipelineResult)
│   ├── pipeline.py                # Main pipeline orchestrator
│   ├── cli.py                     # Command-line interface
│   ├── cli_ui.py                  # Rich terminal UI components
│   ├── audio_validator.py         # Audio file validation
│   ├── stt_adapter.py             # STT adapter base class
│   ├── assemblyai_adapter.py      # AssemblyAI STT implementation
│   ├── team_store.py              # Team member storage and lookup
│   ├── task_extractor.py          # Task extraction from transcript
│   ├── deadline_parser.py         # Natural language deadline parsing
│   ├── priority_classifier.py     # Priority classification logic
│   ├── assignment_engine.py       # Task-to-member assignment logic
│   ├── dependency_resolver.py     # Dependency detection and cycle checking
│   └── output_serializer.py       # JSON and CSV serialization
├── tests/
│   ├── property/                  # Property-based tests using Hypothesis
│   ├── unit/                      # Unit tests for individual components
│   └── integration/               # End-to-end integration tests
├── samples/
│   ├── team_members.json          # Sample team data
│   ├── sample-meeting.mp3         # Sample audio file
│   ├── sample-meeting2.mp3        # Another sample audio file
│   ├── default_transcript.txt     # Pre-transcribed sample
│   ├── sample_transcript.txt      # Sample transcript text
│   └── expected_output.json       # Expected output for validation
├── .env                           # Environment variables (API keys)
├── env.example                    # Environment template
├── requirements.txt               # Python dependencies
├── pytest.ini                     # Test configuration
├── run_demo.py                    # Quick demo script
└── README.md
```

## Sample Output

### Terminal Display (Rich Format)
When running with default settings, you'll see a beautiful terminal table with color-coded priorities and clear task information.

### JSON Format
```json
{
  "success": true,
  "tasks": [
    {
      "task_number": 1,
      "description": "Fix critical login bug",
      "assigned_to": "Sakshi",
      "deadline": "tomorrow evening",
      "priority": "Critical",
      "dependencies": null,
      "reasoning": "Explicitly mentioned in task: 'Sakshi'"
    },
    {
      "task_number": 2,
      "description": "Optimize database performance",
      "assigned_to": "Mohit",
      "deadline": "end of this week",
      "priority": "High",
      "dependencies": null,
      "reasoning": "Matched skills: database, performance optimization; Role: Backend Engineer"
    },
    {
      "task_number": 3,
      "description": "Update API documentation",
      "assigned_to": "Mohit",
      "deadline": "Friday",
      "priority": "High",
      "dependencies": null,
      "reasoning": "Matched skills: apis; Role: Backend Engineer"
    },
    {
      "task_number": 4,
      "description": "Design new onboarding screens",
      "assigned_to": "Arjun",
      "deadline": "next Monday",
      "priority": "Medium",
      "dependencies": null,
      "reasoning": "Explicitly mentioned in task: 'Arjun'"
    },
    {
      "task_number": 5,
      "description": "Write unit tests for payment module",
      "assigned_to": "Lata",
      "deadline": "Wednesday",
      "priority": "Medium",
      "dependencies": "Depends on Task #1",
      "reasoning": "Matched skills: testing; Role: QA Engineer"
    }
  ],
  "transcript": "Hi everyone, let's discuss this week's priorities...",
  "error_message": null
}
```

### CSV Format
```csv
Task #,Description,Assigned To,Deadline,Priority,Dependencies,Reasoning
1,Fix critical login bug,Sakshi,tomorrow evening,Critical,,Explicitly mentioned in task: 'Sakshi'
2,Optimize database performance,Mohit,end of this week,High,,Matched skills: database, performance optimization; Role: Backend Engineer
3,Update API documentation,Mohit,Friday,High,,Matched skills: apis; Role: Backend Engineer
4,Design new onboarding screens,Arjun,next Monday,Medium,,Explicitly mentioned in task: 'Arjun'
5,Write unit tests for payment module,Lata,Wednesday,Medium,Depends on Task #1,Matched skills: testing; Role: QA Engineer
```

## Running Tests

The project includes comprehensive test coverage using multiple testing strategies.

### Run All Tests

```bash
# Activate virtual environment first
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
```

### Test Categories

#### 1. Integration Tests
End-to-end tests that validate the complete system against expected outputs:

```bash
pytest tests/integration/ -v
```

These tests verify:
- Correct number of tasks extracted from sample meetings
- Task descriptions match expected output
- Tasks assigned to correct team members
- Deadline extraction accuracy
- Priority classification (Critical, High, Medium, Low)
- Dependency identification and circular dependency detection
- Assignment reasoning provided
- Complete JSON output structure
- Full compliance with assignment requirements

#### 2. Property-Based Tests
Tests using Hypothesis framework to verify correctness properties across many randomly generated inputs:

```bash
pytest tests/property/ -v
```

Property tests cover:
- Task extraction properties
- Deadline parsing consistency
- Priority classification rules
- Assignment engine logic
- Dependency resolution
- Data model serialization round-trips
- Team store operations
- Output serialization formats

#### 3. Unit Tests
Tests for individual components (if needed):

```bash
pytest tests/unit/ -v
```

### Test Results

All tests pass successfully. The system correctly:
- Extracts all 5 tasks from the sample meeting transcript
- Assigns tasks to the appropriate team members (Sakshi, Mohit, Arjun, Lata)
- Identifies deadlines in natural language ("tomorrow evening", "end of this week", "Friday", "next Monday", "Wednesday")
- Classifies priorities accurately (Critical, High, Medium)
- Detects task dependencies (Task 5 depends on Task 1)
- Provides clear reasoning for each assignment decision

## Architecture

The system follows a modular pipeline architecture:

1. **Audio Validation**: Validates audio file format and integrity
2. **Speech-to-Text**: Converts audio to text using STT adapter
3. **Task Extraction**: Identifies tasks from transcript using custom NLP logic
4. **Deadline Parsing**: Extracts and normalizes deadline information
5. **Priority Classification**: Determines task priority based on keywords and urgency
6. **Assignment Engine**: Matches tasks to team members using skill-based and mention-based logic
7. **Dependency Resolution**: Identifies task dependencies and checks for circular dependencies
8. **Output Serialization**: Formats results as JSON, CSV, or rich terminal display

## Technical Implementation

- **Speech-to-Text**: AssemblyAI adapter for audio transcription
- **Task Classification**: Custom NLP logic without external AI APIs
- **Assignment Logic**: Custom skill-matching algorithm based on explicit mentions, skill overlap, and role relevance
- **Testing**: Comprehensive test suite using pytest and Hypothesis for property-based testing
- **CLI**: Rich terminal interface using the Rich library for beautiful output

## Design Decisions

- Custom logic for task extraction and assignment ensures full control and transparency
- Property-based testing validates correctness across a wide range of inputs
- Graceful fallback when API keys are not available (uses pre-transcribed samples)
- Interactive CLI with progress indicators and error handling for better user experience

## Assignment Requirements

This project is built to meet specific requirements:

### Allowed
- External APIs for Speech-to-Text conversion (AssemblyAI)
- Any library for parsing, NLP, or logic building
- Custom logic for task identification and assignment

### Not Allowed
- External APIs or pre-trained models for task classification
- External APIs or pre-trained models for assignment logic
- External automation tools for core decision-making

### Implementation
- Speech-to-Text uses AssemblyAI external service
- Task extraction, classification, and assignment use custom logic implemented in Python
- No external AI APIs are used for the core task processing logic
- All decision-making is transparent and based on explicit rules
