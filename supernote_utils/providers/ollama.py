"""Ollama local vision provider"""

import io
import sys

from PIL import Image

from supernote_utils.exceptions import ProviderAPIError, ProviderNotAvailableError
from supernote_utils.providers.base import VisionProvider

try:
    import ollama
except ImportError:
    ollama = None


class OllamaProvider(VisionProvider):
    """Provider for Ollama local vision models"""

    # Auto-detection picks the first of these that is installed, else the first
    # installed model that reports the vision capability. Order comes from a
    # benchmark on English/Russian handwriting (2026-11-27): gemma4:26b-a4b ran
    # as fast as the small models with about half their Cyrillic errors; 31b is
    # slightly more accurate but 7x slower; the 8-bit e4b beat the default 4-bit one.
    PREFERRED_MODELS = [
        "gemma4:26b-a4b",
        "gemma4:26b",
        "gemma4:31b",
        "gemma4:e4b-it-q8_0",
        "gemma4:latest",
    ]

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 1.0,
        base_url: str = "http://localhost:11434",
    ):
        """
        Initialize Ollama provider.

        Args:
            model: Specific model name (None for auto-detection)
            temperature: Generation temperature (default 1.0 for local models)
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
                    "Install one with: ollama pull gemma4:26b-a4b"
                )
            self.actual_model = detected_model
            print(f"Auto-detected Ollama model: {self.actual_model}", file=sys.stderr)

        super().__init__(model=self.actual_model, temperature=temperature)

        print(f"Using Ollama with temperature={self.temperature}", file=sys.stderr)

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """Transcribe image using Ollama local model"""
        return self.transcribe_images_batch([image], prompt)

    def transcribe_images_batch(self, images: list[Image.Image], prompt: str) -> str:
        """Transcribe multiple images in a single API call"""
        try:
            response = ollama.chat(
                model=self.actual_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [self._image_to_bytes(image) for image in images],
                    }
                ],
                options={
                    "temperature": self.temperature,
                },
                # Current local vision models (Gemma 4, Qwen 3.x) think by default. On a
                # 2-page test note thinking made them several times slower with no gain
                # in accuracy.
                think=False,
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

    def _detect_vision_model(self) -> str | None:
        """Pick a vision model: a preferred one if installed, else the first available.

        Returns:
            Model name, or None if no installed model can read images.
        """
        vision_models = self.list_available_models()
        for preferred in self.PREFERRED_MODELS:
            if preferred in vision_models:
                return preferred
        return vision_models[0] if vision_models else None

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
    def list_available_models(cls, api_key: str | None = None) -> list[str]:
        """List installed models that Ollama reports as able to read images.

        Uses each model's reported capabilities rather than its name, so new model
        families are found without a code change.

        Args:
            api_key: Not used for Ollama (local models)

        Returns:
            Model names in the order Ollama lists them (most recently changed first);
            empty if Ollama is not installed or not running.
        """
        if ollama is None:
            return []

        try:
            names = [model.model for model in ollama.list().models]
        except Exception as e:
            print(f"Warning: could not reach Ollama: {e}", file=sys.stderr)
            return []

        vision_models = []
        for name in names:
            try:
                capabilities = ollama.show(name).capabilities or []
            except Exception as e:
                print(f"Warning: could not inspect Ollama model {name}: {e}", file=sys.stderr)
                continue
            if "vision" in capabilities:
                vision_models.append(name)
        return vision_models
