#!/usr/bin/env python3
"""
Quick demo script to run Scribe with sample data.
This uses the sample audio file and team members for easy testing.
""" 

import subprocess
import sys
from pathlib import Path

def main():
    # Check if sample files exist
    audio_file = Path("samples/sample-meeting2.mp3")
    team_file = Path("samples/team_members.json")
    
    if not audio_file.exists():
        print(f"Error: Sample audio file not found at {audio_file}")
        sys.exit(1)
    
    if not team_file.exists():
        print(f"Error: Team members file not found at {team_file}")
        sys.exit(1)
    
    # Run the CLI with sample files
    cmd = [
        sys.executable,
        "-m",
        "src.cli",
        str(audio_file),
        "--team",
        str(team_file)
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)

if __name__ == "__main__":
    main()
