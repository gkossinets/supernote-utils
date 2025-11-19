"""Anthropic Claude vision provider"""

import base64
import io
import sys
from typing import List, Optional

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

    def transcribe_images_batch(self, images: List[Image.Image], prompt: str) -> str:
        """Transcribe multiple images in a single API call"""
        try:
            # Build content array with prompt and all images
            content = [{"type": "text", "text": prompt}]

            for i, image in enumerate(images, start=1):
                base64_image = self._image_to_base64(image)
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64_image,
                    },
                })

            response = self.client.messages.create(
                model=self.actual_model,
                max_tokens=8192,  # Increased for multiple pages
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": content,
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
        # If using default models, show friendly names
        if self.actual_model == self.DEFAULT_SONNET_MODEL:
            return "Claude Sonnet 4.5"
        elif self.actual_model == self.DEFAULT_HAIKU_MODEL:
            return "Claude Haiku 4.5"
        # For custom models, show the actual model name
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

    @classmethod
    def list_available_models(cls, api_key: Optional[str] = None) -> list[str]:
        """
        List available Claude vision models.

        Args:
            api_key: Anthropic API key (optional, reads from env if not provided)

        Returns:
            List of available model names
        """
        if anthropic is None:
            return []

        # Try to dynamically fetch models if API key is available
        if api_key:
            try:
                client = anthropic.Anthropic(api_key=api_key)
                available_models = []
                for model in client.models.list():
                    # All Claude models support vision, so include all
                    available_models.append(model.id)
                if available_models:
                    return available_models
            except Exception:
                pass  # Fall back to static list

        # Return known Claude vision models (static fallback)
        # List matches API response as of November 2025
        return [
            # Claude 4.5 (latest)
            cls.DEFAULT_HAIKU_MODEL,   # claude-haiku-4-5-20251001
            cls.DEFAULT_SONNET_MODEL,  # claude-sonnet-4-5-20250929
            # Claude 4.1 / 4
            "claude-opus-4-1-20250805",
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            # Claude 3.7 / 3.5
            "claude-3-7-sonnet-20250219",
            "claude-3-5-haiku-20241022",
            # Claude 3
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229",
        ]
