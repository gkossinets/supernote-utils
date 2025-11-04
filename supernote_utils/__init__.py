"""
Supernote Utils - Python utilities for Supernote tablet handwriting transcription

This package provides tools for transcribing handwritten notes from Ratta Supernote
tablets to text/markdown using LLM vision APIs (Claude, Gemini, Ollama).
"""

from supernote_utils.__version__ import __version__
from supernote_utils.config import ProviderConfig, TranscriptionConfig
from supernote_utils.exceptions import (
    ConfigurationError,
    FileFormatError,
    ImageProcessingError,
    ProviderAPIError,
    ProviderError,
    ProviderNotAvailableError,
    SupernoteUtilsError,
)

__all__ = [
    "__version__",
    "ProviderConfig",
    "TranscriptionConfig",
    "SupernoteUtilsError",
    "ProviderError",
    "ProviderNotAvailableError",
    "ProviderAPIError",
    "ImageProcessingError",
    "FileFormatError",
    "ConfigurationError",
]
