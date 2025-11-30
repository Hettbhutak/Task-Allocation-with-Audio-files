"""Speech-to-Text service adapter component."""

from abc import ABC, abstractmethod
from typing import Optional

from src.models import TranscriptionResult


class STTServiceAdapter(ABC):
    """Abstract base class for speech-to-text service adapters."""
    
    @abstractmethod
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """
        Converts audio file to text.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            TranscriptionResult with transcript or error details
        """
        pass


class MockSTTAdapter(STTServiceAdapter):
    """Mock STT adapter for testing purposes."""
    
    def __init__(self, transcript: Optional[str] = None, should_fail: bool = False):
        """
        Initialize mock adapter.
        
        Args:
            transcript: Predefined transcript to return
            should_fail: Whether to simulate failure
        """
        self.transcript = transcript
        self.should_fail = should_fail
    
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """Returns predefined transcript or simulates failure."""
        if self.should_fail:
            return TranscriptionResult(
                success=False,
                error_message="Mock transcription failure"
            )
        
        return TranscriptionResult(
            success=True,
            transcript=self.transcript or "This is a mock transcript.",
            confidence=0.95
        )
