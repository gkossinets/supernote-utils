"""Configuration management for supernote-utils"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TranscriptionConfig:
    """Configuration for transcription operations"""

    temperature: float = 0.2
    page_separator: bool = False
    additional_prompt: str = ""
    batch_size: int = 3

    def __post_init__(self):
        """Validate configuration"""
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {self.temperature}")
        if self.batch_size < 1:
            raise ValueError(f"Batch size must be at least 1, got {self.batch_size}")


@dataclass
class ProviderConfig:
    """Configuration for LLM providers"""

    # API keys (can be set via environment or directly)
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    google_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY")
    )

    # Ollama configuration
    ollama_base_url: str = "http://localhost:11434"

    # Model overrides
    anthropic_model: Optional[str] = None
    google_model: Optional[str] = None
    ollama_model: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        """Create configuration from environment variables"""
        return cls()
