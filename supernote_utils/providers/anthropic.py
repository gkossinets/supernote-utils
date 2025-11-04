"""Anthropic Claude vision provider"""

import base64
import io
import sys
from typing import Optional

from PIL import Image

from supernote_utils.exceptions import ProviderAPIError, ProviderNotAvailableError
from supernote_utils.providers.base import VisionProvider

try:
    import anthropic
except ImportError:
    anthropic = None


class AnthropicProvider(VisionProvider):
    """Provider for Anthropic Claude vision models"""

    # Default models for different tiers
    DEFAULT_SONNET_MODEL = "claude-sonnet-4-5-20250929"
    DEFAULT_HAIKU_MODEL = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        use_sonnet: bool = True,
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Specific model name (None for default)
            temperature: Generation temperature
            use_sonnet: If True, use Sonnet (more powerful); if False, use Haiku (faster)
        """
        if anthropic is None:
            raise ProviderNotAvailableError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

        if not api_key:
            raise ProviderNotAvailableError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable."
            )

        # Determine model
        if model:
            self.actual_model = model
        else:
            self.actual_model = (
                self.DEFAULT_SONNET_MODEL if use_sonnet else self.DEFAULT_HAIKU_MODEL
            )

        super().__init__(model=self.actual_model, temperature=temperature)

        self.client = anthropic.Anthropic(api_key=api_key)
        self._use_sonnet = use_sonnet

        print(
            f"Using {self.get_display_name()} (temperature={self.temperature})",
            file=sys.stderr,
        )

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """Transcribe image using Claude API"""
        base64_image = self._image_to_base64(image)

        try:
            response = self.client.messages.create(
                model=self.actual_model,
                max_tokens=4096,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image,
                                },
                            },
                        ],
                    }
                ],
            )
            return response.content[0].text

        except Exception as e:
            raise ProviderAPIError(f"Anthropic API error: {str(e)}") from e

    def is_available(self) -> bool:
        """Check if Anthropic is available"""
        return anthropic is not None

    def get_display_name(self) -> str:
        """Get display name"""
        if "sonnet" in self.actual_model.lower():
            return "Claude Sonnet 4.5"
        elif "haiku" in self.actual_model.lower():
            return "Claude Haiku 4.5"
        else:
            return f"Claude ({self.actual_model})"

    @staticmethod
    def _image_to_base64(image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        # Convert RGBA/P to RGB for JPEG compatibility
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
