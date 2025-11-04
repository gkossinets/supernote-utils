"""Abstract base class for LLM vision providers"""

from abc import ABC, abstractmethod
from typing import Optional

from PIL import Image


class VisionProvider(ABC):
    """Abstract base class for vision LLM providers"""

    def __init__(self, model: Optional[str] = None, temperature: float = 0.2):
        """
        Initialize provider.

        Args:
            model: Specific model name to use (None for provider default)
            temperature: Generation temperature (0.0-2.0, lower = more deterministic)
        """
        self.model = model
        self.temperature = temperature
        self._validate_temperature()

    def _validate_temperature(self):
        """Validate temperature is in valid range"""
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {self.temperature}")

    @abstractmethod
    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """
        Transcribe handwritten content from image.

        Args:
            image: PIL Image containing handwritten content
            prompt: Transcription prompt with instructions

        Returns:
            Transcribed text as markdown

        Raises:
            ProviderAPIError: If API call fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is configured and available.

        Returns:
            True if provider can be used, False otherwise
        """
        pass

    @abstractmethod
    def get_display_name(self) -> str:
        """
        Get human-readable name for this provider.

        Returns:
            Display name (e.g., "Claude Sonnet 4.5")
        """
        pass
