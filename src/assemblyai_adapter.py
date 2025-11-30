"""AssemblyAI Speech-to-Text adapter for better transcription quality."""

import os
import time
import requests
from src.models import TranscriptionResult
from src.stt_adapter import STTServiceAdapter


class AssemblyAIAdapter(STTServiceAdapter):
    """Speech-to-text adapter using AssemblyAI REST API."""
    
    BASE_URL = "https://api.assemblyai.com/v2"
    
    def __init__(self, api_key: str = None):
        """
        Initialize AssemblyAI adapter.
        
        Args:
            api_key: AssemblyAI API key (or set ASSEMBLYAI_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('ASSEMBLYAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "AssemblyAI API key required. Set ASSEMBLYAI_API_KEY environment variable "
                "or pass api_key parameter. Get a free key at https://www.assemblyai.com/"
            )
        self.headers = {"authorization": self.api_key}
    
    def _upload_file(self, audio_path: str) -> str:
        """Uploads audio file to AssemblyAI and returns the upload URL."""
        with open(audio_path, "rb") as f:
            response = requests.post(
                f"{self.BASE_URL}/upload",
                headers=self.headers,
                data=f
            )
        response.raise_for_status()
        return response.json()["upload_url"]
    
    def _create_transcript(self, audio_url: str) -> str:
        """Creates a transcription job and returns the transcript ID."""
        response = requests.post(
            f"{self.BASE_URL}/transcript",
            headers=self.headers,
            json={"audio_url": audio_url}
        )
        response.raise_for_status()
        return response.json()["id"]
    
    def _poll_transcript(self, transcript_id: str, timeout: int = 300) -> dict:
        """Polls for transcript completion."""
        polling_url = f"{self.BASE_URL}/transcript/{transcript_id}"
        start_time = time.time()
        
        while True:
            response = requests.get(polling_url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            
            status = result["status"]
            if status == "completed":
                return result
            elif status == "error":
                raise Exception(result.get("error", "Transcription failed"))
            
            if time.time() - start_time > timeout:
                raise Exception("Transcription timed out")
            
            time.sleep(3)  # Poll every 3 seconds
    
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """
        Transcribes audio file using AssemblyAI.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            TranscriptionResult with transcript or error details
        """
        try:
            # Upload the file
            upload_url = self._upload_file(audio_path)
            
            # Create transcription job
            transcript_id = self._create_transcript(upload_url)
            
            # Poll for completion
            result = self._poll_transcript(transcript_id)
            
            text = result.get("text", "")
            if not text:
                return TranscriptionResult(
                    success=False,
                    error_message="No speech detected in audio file"
                )
            
            return TranscriptionResult(
                success=True,
                transcript=text,
                confidence=result.get("confidence")
            )
            
        except FileNotFoundError:
            return TranscriptionResult(
                success=False,
                error_message=f"Audio file not found: {audio_path}"
            )
        except requests.RequestException as e:
            return TranscriptionResult(
                success=False,
                error_message=f"API request failed: {str(e)}"
            )
        except Exception as e:
            return TranscriptionResult(
                success=False,
                error_message=f"Transcription failed: {str(e)}"
            )
