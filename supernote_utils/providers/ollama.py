"""Ollama local vision provider"""

import io
import sys
from typing import List, Optional

from PIL import Image

from supernote_utils.exceptions import ProviderAPIError, ProviderNotAvailableError
from supernote_utils.providers.base import VisionProvider

try:
    import ollama
except ImportError:
    ollama = None


class OllamaProvider(VisionProvider):
    """Provider for Ollama local vision models"""

    # Known vision-capable model keywords (in priority order)
    VISION_KEYWORDS = [
        "qwen2.5-vl:7b",  # Preferred default
        "qwen2.5-vl",
        "qwen",
        "llama3.2-vision",
        "llava",
        "minicpm",
        "gemma3",
        "vision",
        "ocr",
        "nanonets",
    ]

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        base_url: str = "http://localhost:11434",
    ):
        """
        Initialize Ollama provider.

        Args:
            model: Specific model name (None for auto-detection)
            temperature: Generation temperature (default 0.1 for local models)
            base_url: Ollama server URL
        """
        if ollama is None:
            raise ProviderNotAvailableError(
                "ollama package not installed. Install with: pip install ollama"
            )

        self.base_url = base_url

        # Auto-detect or validate model
        if model:
            self.actual_model = model
            print(f"Using specified Ollama model: {model}", file=sys.stderr)
        else:
            detected_model = self._detect_vision_model()
            if not detected_model:
                raise ProviderNotAvailableError(
                    "No vision models found in Ollama. "
                    "Install one with: ollama pull qwen2.5-vl:7b"
                )
            self.actual_model = detected_model
            print(f"Auto-detected Ollama model: {self.actual_model}", file=sys.stderr)

        super().__init__(model=self.actual_model, temperature=temperature)

        print(f"Using Ollama with temperature={self.temperature}", file=sys.stderr)

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """Transcribe image using Ollama local model"""
        try:
            # Convert PIL Image to bytes
            image_bytes = self._image_to_bytes(image)

            # Call Ollama chat with image
            response = ollama.chat(
                model=self.actual_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_bytes],
                    }
                ],
                options={
                    "temperature": self.temperature,
                },
            )
            return response["message"]["content"]

        except Exception as e:
            raise ProviderAPIError(f"Ollama API error: {str(e)}") from e

    def transcribe_images_batch(self, images: List[Image.Image], prompt: str) -> str:
        """Transcribe multiple images in a single API call"""
        try:
            # Convert all images to bytes
            image_bytes_list = [self._image_to_bytes(image) for image in images]

            # Call Ollama chat with multiple images
            response = ollama.chat(
                model=self.actual_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": image_bytes_list,
                    }
                ],
                options={
                    "temperature": self.temperature,
                },
            )
            return response["message"]["content"]

        except Exception as e:
            raise ProviderAPIError(f"Ollama API error: {str(e)}") from e

    def is_available(self) -> bool:
        """Check if Ollama is available"""
        if ollama is None:
            return False

        try:
            # Try to list models to check if Ollama is running
            ollama.list()
            return True
        except Exception:
            return False

    def get_display_name(self) -> str:
        """Get display name"""
        return f"Ollama ({self.actual_model})"

    def _detect_vision_model(self) -> Optional[str]:
        """Detect first available vision model from Ollama"""
        try:
            models = ollama.list()
            model_list = models.get("models", [])

            # First pass: check for preferred default
            for model in model_list:
                name = getattr(model, "model", model.get("model", ""))
                if "qwen2.5-vl:7b" in name.lower():
                    return name

            # Second pass: check other vision keywords
            for model in model_list:
                name = getattr(model, "model", model.get("model", ""))
                if any(keyword in name.lower() for keyword in self.VISION_KEYWORDS[1:]):
                    return name

        except Exception as e:
            print(f"Warning: Could not auto-detect Ollama models: {e}", file=sys.stderr)

        return None

    @staticmethod
    def _image_to_bytes(image: Image.Image) -> bytes:
        """Convert PIL Image to bytes"""
        buffered = io.BytesIO()
        # Convert RGBA/P to RGB for JPEG compatibility
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buffered, format="JPEG")
        return buffered.getvalue()

    @classmethod
    def list_available_models(cls, api_key: Optional[str] = None) -> list[str]:
        """
        List all available vision models in Ollama.

        Args:
            api_key: Not used for Ollama (local models)

        Returns:
            List of model names
        """
        if ollama is None:
            return []

        vision_models = []
        try:
            models = ollama.list()
            model_list = models.get("models", [])

            for model in model_list:
                name = getattr(model, "model", model.get("model", ""))
                if any(keyword in name.lower() for keyword in cls.VISION_KEYWORDS):
                    vision_models.append(name)

        except Exception:
            pass

        return vision_models

    @classmethod
    def detect_available_models(cls) -> list:
        """
        Deprecated: Use list_available_models() instead.

        Returns:
            List of model names
        """
        return cls.list_available_models()
