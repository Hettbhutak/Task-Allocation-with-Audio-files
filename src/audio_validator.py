"""Audio file validation component."""

import os
from pathlib import Path
from typing import Optional

from src.models import ValidationResult, AudioMetadata


class AudioValidator:
    """Validates audio files for format and integrity."""
    
    SUPPORTED_FORMATS = {'.wav', '.mp3', '.m4a'}
    
    def validate(self, file_path: str) -> ValidationResult:
        """
        Validates an audio file for format and basic integrity.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            ValidationResult with is_valid status and any error message
        """
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"File not found: {file_path}"
            )
        
        # Check if it's a file (not directory)
        if not path.is_file():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path is not a file: {file_path}"
            )
        
        # Check file extension
        extension = path.suffix.lower()
        if extension not in self.SUPPORTED_FORMATS:
            return ValidationResult(
                is_valid=False,
                error_message=f"Unsupported audio format: {extension}. Supported formats: {', '.join(sorted(self.SUPPORTED_FORMATS))}",
                file_format=extension
            )
        
        # Check if file is empty
        if path.stat().st_size == 0:
            return ValidationResult(
                is_valid=False,
                error_message="Audio file is empty",
                file_format=extension
            )
        
        # Basic integrity check - try to read file header
        try:
            with open(path, 'rb') as f:
                header = f.read(12)
                if len(header) < 4:
                    return ValidationResult(
                        is_valid=False,
                        error_message="Audio file appears to be corrupted (too small)",
                        file_format=extension
                    )
                
                # Basic format validation based on magic bytes
                if not self._validate_magic_bytes(header, extension):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"File content does not match {extension} format",
                        file_format=extension
                    )
        except IOError as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Cannot read audio file: {str(e)}",
                file_format=extension
            )
        
        return ValidationResult(
            is_valid=True,
            file_format=extension
        )
    
    def _validate_magic_bytes(self, header: bytes, extension: str) -> bool:
        """
        Validates file magic bytes match expected format.
        
        Args:
            header: First 12 bytes of the file
            extension: Expected file extension
            
        Returns:
            True if magic bytes match expected format
        """
        if extension == '.wav':
            # WAV files start with "RIFF" and contain "WAVE"
            return header[:4] == b'RIFF' and header[8:12] == b'WAVE'
        
        elif extension == '.mp3':
            # MP3 files start with ID3 tag or frame sync
            return (header[:3] == b'ID3' or 
                    header[:2] == b'\xff\xfb' or
                    header[:2] == b'\xff\xfa' or
                    header[:2] == b'\xff\xf3' or
                    header[:2] == b'\xff\xf2')
        
        elif extension == '.m4a':
            # M4A files have 'ftyp' at offset 4
            return header[4:8] == b'ftyp'
        
        return False
    
    def get_audio_metadata(self, file_path: str) -> Optional[AudioMetadata]:
        """
        Extracts metadata from an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            AudioMetadata if successful, None if file is invalid
        """
        validation = self.validate(file_path)
        if not validation.is_valid:
            return None
        
        path = Path(file_path)
        file_size = path.stat().st_size
        
        # For now, return basic metadata without duration
        # Duration calculation would require pydub or similar
        return AudioMetadata(
            duration_seconds=0.0,  # Would need audio library to calculate
            format=validation.file_format or path.suffix.lower(),
            file_size_bytes=file_size
        )
    
    def is_supported_format(self, file_path: str) -> bool:
        """
        Quick check if file extension is supported.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if extension is supported
        """
        extension = Path(file_path).suffix.lower()
        return extension in self.SUPPORTED_FORMATS
