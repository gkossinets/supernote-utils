"""Google Gemini vision provider (google-genai SDK)"""

import re
import sys

from PIL import Image

from supernote_utils.exceptions import ProviderAPIError, ProviderNotAvailableError
from supernote_utils.providers.base import VisionProvider

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


# Handwritten notes trip Gemini's default safety filters far more often than they
# contain anything harmful, so only block content the API rates as high risk.
_SAFETY_CATEGORIES = (
    "HARM_CATEGORY_DANGEROUS_CONTENT",
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
)


class GoogleProvider(VisionProvider):
    """Provider for Google Gemini vision models"""

    # Default models for different tiers
    DEFAULT_PRO_MODEL = "gemini-4-hydrogen"
    DEFAULT_FLASH_MODEL = "gemini-3.8-flash"

    @staticmethod
    def _is_reasoning_model(model_name: str) -> bool:
        """Check if model is Gemini 3 or later, where Google recommends temperature 1.0.

        Args:
            model_name: Gemini model ID, e.g. "gemini-3.8-flash".

        Returns:
            True for Gemini major version 3 and above.
        """
        match = re.match(r"gemini-(\d+)", model_name.lower())
        return bool(match) and int(match.group(1)) >= 3

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        temperature: float = 1.0,
        use_pro: bool = False,
        temperature_was_set: bool = False,
    ):
        """
        Initialize Google Gemini provider.

        Args:
            api_key: Google API key
            model: Specific model name (None for default)
            temperature: Generation temperature
            use_pro: If True, use the Pro-tier default; if False, use Flash (faster)
            temperature_was_set: Whether the user set the temperature explicitly
        """
        if genai is None:
            raise ProviderNotAvailableError(
                "google-genai package not installed. Install with: pip install google-genai"
            )

        if not api_key:
            raise ProviderNotAvailableError(
                "Google API key not provided. Set GOOGLE_API_KEY environment variable."
            )

        if model:
            self.actual_model = model
        else:
            self.actual_model = self.DEFAULT_PRO_MODEL if use_pro else self.DEFAULT_FLASH_MODEL

        adjusted_temperature = temperature
        if self._is_reasoning_model(self.actual_model):
            if not temperature_was_set:
                adjusted_temperature = 1.0
                print(
                    "Note: Using temperature=1.0 for Gemini 3+ reasoning model (recommended)",
                    file=sys.stderr,
                )
            elif temperature < 1.0:
                print(
                    f"Warning: Gemini 3+ models perform best at temperature=1.0. "
                    f"Using {temperature} may cause degraded output.",
                    file=sys.stderr,
                )

        super().__init__(model=self.actual_model, temperature=adjusted_temperature)

        self.client = genai.Client(api_key=api_key)
        self._use_pro = use_pro

        print(
            f"Using {self.get_display_name()} (temperature={self.temperature})",
            file=sys.stderr,
        )

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """Transcribe a single image using the Gemini API"""
        return self.transcribe_images_batch([image], prompt)

    def transcribe_images_batch(self, images: list[Image.Image], prompt: str) -> str:
        """Transcribe multiple images in a single API call"""
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            safety_settings=[
                types.SafetySetting(
                    category=category,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                )
                for category in _SAFETY_CATEGORIES
            ],
        )

        try:
            response = self.client.models.generate_content(
                model=self.actual_model,
                contents=[prompt, *images],
                config=config,
            )
        except Exception as e:
            raise ProviderAPIError(f"Google API error: {e}") from e

        self._check_finish_reason(response)
        if not response.text:
            # A prompt-level block returns no candidates, so there is no finish reason.
            feedback = getattr(response, "prompt_feedback", None)
            reason = getattr(feedback, "block_reason", None) or "no reason given"
            raise ProviderAPIError(
                f"Gemini returned no text ({reason}). "
                "Try using a different LLM provider (e.g., -m claude-sonnet)."
            )
        return response.text

    @staticmethod
    def _check_finish_reason(response) -> None:
        """Raise a helpful error when Gemini stopped for anything but a normal finish.

        Args:
            response: GenerateContentResponse from the SDK.

        Raises:
            ProviderAPIError: If generation was blocked or cut short.
        """
        if not response.candidates:
            return
        reason = response.candidates[0].finish_reason
        finish = types.FinishReason

        if reason in (None, finish.STOP, finish.FINISH_REASON_UNSPECIFIED):
            return
        if reason == finish.RECITATION:
            raise ProviderAPIError(
                "Gemini detected potential copyrighted content. This is likely a false positive "
                "for handwritten OCR. Try: (1) using a different image section, (2) retrying the "
                "request, or (3) using a different LLM provider (e.g., -m claude-sonnet)."
            )
        if reason == finish.SAFETY:
            raise ProviderAPIError(
                "Gemini blocked the response due to safety filters. "
                "Try using a different LLM provider (e.g., -m claude-sonnet)."
            )
        name = getattr(reason, "name", str(reason))
        raise ProviderAPIError(
            f"Gemini stopped generation with finish_reason={name}. "
            "Try using a different LLM provider (e.g., -m claude-sonnet)."
        )

    def is_available(self) -> bool:
        """Check if Google Gemini is available"""
        return genai is not None

    def get_display_name(self) -> str:
        """Get display name"""
        if "flash" in self.actual_model.lower():
            return f"Gemini Flash ({self.actual_model})"
        return f"Gemini ({self.actual_model})"

    @classmethod
    def list_available_models(cls, api_key: str | None = None) -> list[str]:
        """
        List available Gemini vision models.

        Args:
            api_key: Google API key (optional; without it a static list is returned)

        Returns:
            List of available model names
        """
        if genai is None:
            return []

        if api_key:
            try:
                client = genai.Client(api_key=api_key)
                available_models = [
                    model.name.removeprefix("models/")
                    for model in client.models.list()
                    if "generateContent" in (model.supported_actions or [])
                    and model.name.startswith("models/gemini")
                ]
                if available_models:
                    return available_models
            except Exception as e:
                print(f"Could not list Gemini models from the API: {e}", file=sys.stderr)

        # Static fallback: current stable models (checked November 2026)
        return [
            "gemini-4-carbon",
            "gemini-4-neon",
            cls.DEFAULT_PRO_MODEL,
            "gemini-4-argon",
            cls.DEFAULT_FLASH_MODEL,
            "gemini-3.5-flash-lite",
        ]
