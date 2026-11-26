"""Anthropic Claude vision provider"""

import base64
import io
import sys

from PIL import Image

from supernote_utils.exceptions import ProviderAPIError, ProviderNotAvailableError
from supernote_utils.providers.base import VisionProvider

try:
    import anthropic
except ImportError:
    anthropic = None


# Models that accept the server-side refusal fallback. If a safety classifier
# declines a page, the API retries it on a fallback model within the same call
# instead of returning nothing. Haiku has no server-side fallback.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"
_FALLBACK_MODELS = {
    "claude-sonnet-5-5",
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-fable-5-1",
    "claude-fable-5-2",
}

# Room for adaptive thinking plus several pages of transcription, while staying
# under the SDK's non-streaming request timeout.
_MAX_TOKENS = 16000


class AnthropicProvider(VisionProvider):
    """Provider for Anthropic Claude vision models"""

    DEFAULT_SONNET_MODEL = "claude-sonnet-5-5"
    DEFAULT_HAIKU_MODEL = "claude-haiku-5-5"
    # Not a tier default; selected by the claude-opus shortcut.
    DEFAULT_OPUS_MODEL = "claude-opus-5-5"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        temperature: float = 1.0,
        use_sonnet: bool = True,
        temperature_was_set: bool = False,
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Specific model name (None for default)
            temperature: Accepted for interface compatibility; not sent to the API
            use_sonnet: If True, use Sonnet (more capable); if False, use Haiku (faster)
            temperature_was_set: Whether the user set the temperature explicitly
        """
        if anthropic is None:
            raise ProviderNotAvailableError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

        if not api_key:
            raise ProviderNotAvailableError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable."
            )

        if model:
            self.actual_model = model
        else:
            self.actual_model = (
                self.DEFAULT_SONNET_MODEL if use_sonnet else self.DEFAULT_HAIKU_MODEL
            )

        super().__init__(model=self.actual_model, temperature=temperature)

        # Current Claude models reject non-default sampling settings, and the
        # anthropic SDK 2.x no longer has a temperature parameter at all.
        if temperature_was_set:
            print(
                f"Warning: --temperature {temperature} is ignored for Claude models "
                "(current models use fixed sampling settings).",
                file=sys.stderr,
            )

        self.client = anthropic.Anthropic(api_key=api_key)
        self._use_sonnet = use_sonnet

        print(f"Using {self.get_display_name()}", file=sys.stderr)

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """Transcribe a single image using the Claude API"""
        return self.transcribe_images_batch([image], prompt)

    def transcribe_images_batch(self, images: list[Image.Image], prompt: str) -> str:
        """Transcribe multiple images in a single API call"""
        content = [{"type": "text", "text": prompt}]
        for image in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": self._image_to_base64(image),
                },
            })

        request = {
            "model": self.actual_model,
            "max_tokens": _MAX_TOKENS,
            "messages": [{"role": "user", "content": content}],
        }
        if self.actual_model in _FALLBACK_MODELS:
            request["betas"] = [_FALLBACK_BETA]
            request["fallbacks"] = "default"

        try:
            response = self.client.beta.messages.create(**request)
        except Exception as e:
            raise ProviderAPIError(f"Anthropic API error: {e}") from e

        return self._extract_text(response)

    @staticmethod
    def _extract_text(response) -> str:
        """Return the response's text, or raise if Claude did not finish normally.

        Args:
            response: Message returned by the SDK.

        Returns:
            Concatenated text blocks (thinking blocks are skipped).

        Raises:
            ProviderAPIError: On a refusal or when the output was truncated.
        """
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None)
            raise ProviderAPIError(
                f"Claude declined to transcribe this page (category: {category}). "
                "Try a different provider (e.g., -m gemini-flash)."
            )
        if response.stop_reason == "max_tokens":
            raise ProviderAPIError(
                f"Claude hit the max_tokens limit ({_MAX_TOKENS}) before finishing. "
                "Try a smaller --batch-size."
            )
        return "".join(block.text for block in response.content if block.type == "text")

    def is_available(self) -> bool:
        """Check if Anthropic is available"""
        return anthropic is not None

    def get_display_name(self) -> str:
        """Get display name"""
        if self.actual_model == self.DEFAULT_SONNET_MODEL:
            return "Claude Sonnet 5.5"
        if self.actual_model == self.DEFAULT_HAIKU_MODEL:
            return "Claude Haiku 5.5"
        if self.actual_model == self.DEFAULT_OPUS_MODEL:
            return "Claude Opus 5.5"
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
    def list_available_models(cls, api_key: str | None = None) -> list[str]:
        """
        List available Claude vision models.

        Args:
            api_key: Anthropic API key (optional; without it a static list is returned)

        Returns:
            List of available model names
        """
        if anthropic is None:
            return []

        if api_key:
            try:
                client = anthropic.Anthropic(api_key=api_key)
                # All Claude models accept image input
                available_models = [model.id for model in client.models.list()]
                if available_models:
                    return available_models
            except Exception as e:
                print(f"Could not list Claude models from the API: {e}", file=sys.stderr)

        # Static fallback: current models (checked November 2026)
        return [
            cls.DEFAULT_OPUS_MODEL,
            cls.DEFAULT_SONNET_MODEL,
            cls.DEFAULT_HAIKU_MODEL,
            "claude-fable-5-2",
        ]
