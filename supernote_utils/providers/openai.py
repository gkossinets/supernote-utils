"""OpenAI vision provider (Responses API)"""

import base64
import io
import sys

from PIL import Image

from supernote_utils.exceptions import ProviderAPIError, ProviderNotAvailableError
from supernote_utils.providers.base import VisionProvider

try:
    import openai
except ImportError:
    openai = None


# Room for reasoning plus several pages of transcription.
_MAX_OUTPUT_TOKENS = 16000

# Model ID fragments for OpenAI models that are not general image-to-text models.
_NON_VISION_MARKERS = ("search", "codex", "audio", "realtime", "tts", "transcribe", "image")


class OpenAIProvider(VisionProvider):
    """Provider for OpenAI GPT vision models"""

    DEFAULT_MODEL = "gpt-6.2-sol"
    DEFAULT_MINI_MODEL = "gpt-6-luna"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        temperature: float = 1.0,
        use_mini: bool = False,
        temperature_was_set: bool = False,
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Specific model name (None for default)
            temperature: Accepted for interface compatibility; not sent to the API
            use_mini: If True, use the small, cheaper default model
            temperature_was_set: Whether the user set the temperature explicitly
        """
        if openai is None:
            raise ProviderNotAvailableError(
                "openai package not installed. Install with: pip install 'supernote-utils[openai]'"
            )

        if not api_key:
            raise ProviderNotAvailableError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."
            )

        if model:
            self.actual_model = model
        else:
            self.actual_model = self.DEFAULT_MINI_MODEL if use_mini else self.DEFAULT_MODEL

        super().__init__(model=self.actual_model, temperature=temperature)

        # Current OpenAI models reject the temperature parameter outright.
        if temperature_was_set:
            print(
                f"Warning: --temperature {temperature} is ignored for OpenAI models "
                "(current models do not accept it).",
                file=sys.stderr,
            )

        self.client = openai.OpenAI(api_key=api_key)
        self._use_mini = use_mini

        print(f"Using {self.get_display_name()}", file=sys.stderr)

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """Transcribe a single image using the OpenAI API"""
        return self.transcribe_images_batch([image], prompt)

    def transcribe_images_batch(self, images: list[Image.Image], prompt: str) -> str:
        """Transcribe multiple images in a single API call"""
        content = [{"type": "input_text", "text": prompt}]
        for image in images:
            content.append({
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{self._image_to_base64(image)}",
                "detail": "high",
            })

        try:
            response = self.client.responses.create(
                model=self.actual_model,
                input=[{"role": "user", "content": content}],
                max_output_tokens=_MAX_OUTPUT_TOKENS,
            )
        except Exception as e:
            raise ProviderAPIError(f"OpenAI API error: {e}") from e

        if response.status == "incomplete":
            reason = getattr(response.incomplete_details, "reason", "unknown")
            raise ProviderAPIError(
                f"OpenAI stopped before finishing (reason: {reason}). "
                "Try a smaller --batch-size."
            )
        if not response.output_text:
            # A refusal comes back as a completed response with no output text.
            raise ProviderAPIError(
                "OpenAI returned no text for this page. "
                "Try a different provider (e.g., -m gemini-flash)."
            )
        return response.output_text

    def is_available(self) -> bool:
        """Check if OpenAI is available"""
        return openai is not None

    def get_display_name(self) -> str:
        """Get display name"""
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
    def list_available_models(cls, api_key: str | None = None) -> list[str]:
        """
        List available OpenAI vision models.

        Args:
            api_key: OpenAI API key (optional; without it a static list is returned)

        Returns:
            List of available model names
        """
        if openai is None:
            return []

        if api_key:
            try:
                client = openai.OpenAI(api_key=api_key)
                available_models = sorted(
                    model.id
                    for model in client.models.list()
                    if model.id.startswith("gpt-")
                    and not any(marker in model.id for marker in _NON_VISION_MARKERS)
                )
                if available_models:
                    return available_models
            except Exception as e:
                print(f"Could not list OpenAI models from the API: {e}", file=sys.stderr)

        # Static fallback: current models (checked November 2026)
        return [
            "gpt-6.2-astra",
            cls.DEFAULT_MODEL,
            "gpt-6.1-terra",
            cls.DEFAULT_MINI_MODEL,
        ]
