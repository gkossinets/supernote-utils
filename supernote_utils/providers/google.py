"""Google Gemini vision provider"""

import sys
from typing import Optional

from PIL import Image

from supernote_utils.exceptions import ProviderAPIError, ProviderNotAvailableError
from supernote_utils.providers.base import VisionProvider

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class GoogleProvider(VisionProvider):
    """Provider for Google Gemini vision models"""

    # Default models for different tiers
    DEFAULT_PRO_MODEL = "gemini-2.5-pro"
    DEFAULT_FLASH_MODEL = "gemini-2.5-flash"

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        use_pro: bool = False,
    ):
        """
        Initialize Google Gemini provider.

        Args:
            api_key: Google API key
            model: Specific model name (None for default)
            temperature: Generation temperature
            use_pro: If True, use Pro (more powerful); if False, use Flash (faster)
        """
        if genai is None:
            raise ProviderNotAvailableError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )

        if not api_key:
            raise ProviderNotAvailableError(
                "Google API key not provided. Set GOOGLE_API_KEY environment variable."
            )

        # Determine model
        if model:
            self.actual_model = model
        else:
            self.actual_model = self.DEFAULT_PRO_MODEL if use_pro else self.DEFAULT_FLASH_MODEL

        super().__init__(model=self.actual_model, temperature=temperature)

        # Configure and create client
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(self.actual_model)
        self._use_pro = use_pro

        print(
            f"Using {self.get_display_name()} (temperature={self.temperature})",
            file=sys.stderr,
        )

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        """Transcribe image using Gemini API"""
        try:
            # Configure safety settings to reduce false positives for OCR tasks
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
            ]

            response = self.client.generate_content(
                [prompt, image],
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                ),
                safety_settings=safety_settings,
            )

            # Check finish_reason before accessing text
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason

                # finish_reason values: 0=UNSPECIFIED, 1=STOP, 2=MAX_TOKENS, 3=SAFETY, 4=RECITATION, 5=OTHER
                if finish_reason == 4:  # RECITATION
                    raise ProviderAPIError(
                        "Gemini detected potential copyrighted content. This is likely a false positive "
                        "for handwritten OCR. Try: (1) using a different image section, (2) retrying the "
                        "request, or (3) using a different LLM provider (e.g., --api claude-sonnet)."
                    )
                elif finish_reason == 3:  # SAFETY
                    raise ProviderAPIError(
                        "Gemini blocked the response due to safety filters. "
                        "Try using a different LLM provider (e.g., --api claude-sonnet)."
                    )
                elif finish_reason not in [0, 1]:  # Not UNSPECIFIED or STOP
                    raise ProviderAPIError(
                        f"Gemini stopped generation with finish_reason={finish_reason}. "
                        "Try using a different LLM provider (e.g., --api claude-sonnet)."
                    )

            return response.text

        except ProviderAPIError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            raise ProviderAPIError(f"Google API error: {str(e)}") from e

    def is_available(self) -> bool:
        """Check if Google Gemini is available"""
        return genai is not None

    def get_display_name(self) -> str:
        """Get display name"""
        if "pro" in self.actual_model.lower():
            return f"Gemini Pro ({self.actual_model})"
        elif "flash" in self.actual_model.lower():
            return f"Gemini Flash ({self.actual_model})"
        else:
            return f"Gemini ({self.actual_model})"

    @classmethod
    def list_available_models(cls, api_key: Optional[str] = None) -> list[str]:
        """
        List available Gemini vision models.

        Args:
            api_key: Google API key (optional, reads from env if not provided)

        Returns:
            List of available model names
        """
        if genai is None:
            return []

        # Try to dynamically fetch models if API key is available
        if api_key:
            try:
                genai.configure(api_key=api_key)
                available_models = []
                for model in genai.list_models():
                    # Only include vision-capable models
                    if "vision" in model.supported_generation_methods or \
                       "generateContent" in model.supported_generation_methods:
                        available_models.append(model.name.replace("models/", ""))
                if available_models:
                    return available_models
            except Exception:
                pass  # Fall back to static list

        # Return known Gemini vision models (static fallback)
        return [
            cls.DEFAULT_PRO_MODEL,
            cls.DEFAULT_FLASH_MODEL,
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
        ]
