"""OpenAI GPT-4o vision provider"""

import base64
import io
import sys
from typing import List, Optional

from PIL import Image

from supernote_utils.exceptions import ProviderAPIError, ProviderNotAvailableError
from supernote_utils.providers.base import VisionProvider

try:
    import openai
except ImportError:
    openai = None


class OpenAIProvider(VisionProvider):
    """Provider for OpenAI GPT-4o vision models"""

    # Default models
    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_MINI_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        use_mini: bool = False,
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Specific model name (None for default)
            temperature: Generation temperature
            use_mini: If True, use gpt-4o-mini (faster, cheaper); if False, use gpt-4o
        """
        if openai is None:
            raise ProviderNotAvailableError(
                "openai package not installed. Install with: pip install openai"
            )

        if not api_key:
            raise ProviderNotAvailableError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."
            )

        # Determine model
        if model:
            self.actual_model = model
        else:
            self.actual_model = self.DEFAULT_MINI_MODEL if use_mini else self.DEFAULT_MODEL

        super().__init__(model=self.actual_model, temperature=temperature)

        self.client = openai.OpenAI(api_key=api_key)
        self._use_mini = use_mini

        print(
            f"Using {self.get_display_name()} (temperature={self.temperature})",
            file=sys.stderr,
        )

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """Transcribe image using OpenAI API"""
        base64_image = self._image_to_base64(image)

        try:
            response = self.client.chat.completions.create(
                model=self.actual_model,
                max_tokens=4096,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
            )
            return response.choices[0].message.content

        except Exception as e:
            raise ProviderAPIError(f"OpenAI API error: {str(e)}") from e

    def transcribe_images_batch(self, images: List[Image.Image], prompt: str) -> str:
        """Transcribe multiple images in a single API call"""
        try:
            # Build content array with prompt and all images
            content = [{"type": "text", "text": prompt}]

            for image in images:
                base64_image = self._image_to_base64(image)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high",
                    },
                })

            response = self.client.chat.completions.create(
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
            return response.choices[0].message.content

        except Exception as e:
            raise ProviderAPIError(f"OpenAI API error: {str(e)}") from e

    def is_available(self) -> bool:
        """Check if OpenAI is available"""
        return openai is not None

    def get_display_name(self) -> str:
        """Get display name"""
        if self.actual_model == self.DEFAULT_MODEL:
            return "GPT-4o"
        elif self.actual_model == self.DEFAULT_MINI_MODEL:
            return "GPT-4o Mini"
        else:
            return f"OpenAI ({self.actual_model})"

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
        List available OpenAI vision models.

        Args:
            api_key: OpenAI API key (optional)

        Returns:
            List of available model names
        """
        if openai is None:
            return []

        # Try to dynamically fetch models if API key is available
        if api_key:
            try:
                client = openai.OpenAI(api_key=api_key)
                available_models = []
                for model in client.models.list():
                    # Filter for vision-capable models (gpt-4o variants)
                    if "gpt-4o" in model.id or "gpt-4-vision" in model.id:
                        available_models.append(model.id)
                if available_models:
                    return sorted(available_models)
            except Exception:
                pass  # Fall back to static list

        # Return known OpenAI vision models (static fallback)
        return [
            cls.DEFAULT_MODEL,       # gpt-4o
            cls.DEFAULT_MINI_MODEL,  # gpt-4o-mini
            "gpt-4o-2024-11-20",
            "gpt-4o-2024-08-06",
            "gpt-4o-2024-05-13",
            "gpt-4o-mini-2024-07-18",
        ]
