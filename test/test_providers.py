"""Tests for the LLM vision providers.

The vendor SDK clients are replaced with fakes, so no network calls are made.
"""

import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PIL import Image

from supernote_utils.exceptions import ProviderAPIError, ProviderNotAvailableError


def _image() -> Image.Image:
    return Image.new("RGB", (40, 30), color=(255, 255, 255))


# ---------------------------------------------------------------------------
# GoogleProvider (google-genai SDK)
# ---------------------------------------------------------------------------

from supernote_utils.providers import google as google_module  # noqa: E402
from supernote_utils.providers.google import GoogleProvider  # noqa: E402


def _gemini_response(text: str = "transcribed", finish_reason=None):
    if finish_reason is None:
        finish_reason = google_module.types.FinishReason.STOP
    return SimpleNamespace(
        text=text,
        candidates=[SimpleNamespace(finish_reason=finish_reason)],
    )


@pytest.fixture
def fake_genai_client(monkeypatch):
    """Replace genai.Client with a MagicMock and return the client instance."""
    client = MagicMock()
    client.models.generate_content.return_value = _gemini_response()
    client_cls = MagicMock(return_value=client)
    monkeypatch.setattr(google_module.genai, "Client", client_cls)
    client.client_cls = client_cls
    return client


class TestGoogleProvider:
    def test_module_import_emits_no_deprecation_warning(self):
        # The old google-generativeai package printed a FutureWarning on import.
        result = subprocess.run(
            [
                sys.executable,
                "-W", "error::FutureWarning",
                "-W", "error::DeprecationWarning",
                "-c", "import supernote_utils.providers.google",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_uses_google_genai_client_with_api_key(self, fake_genai_client):
        GoogleProvider(api_key="key-123")
        fake_genai_client.client_cls.assert_called_once_with(api_key="key-123")

    def test_missing_api_key_raises(self, fake_genai_client):
        with pytest.raises(ProviderNotAvailableError):
            GoogleProvider(api_key="")

    def test_default_flash_model(self, fake_genai_client):
        provider = GoogleProvider(api_key="k")
        assert provider.actual_model == GoogleProvider.DEFAULT_FLASH_MODEL

    def test_default_pro_model(self, fake_genai_client):
        provider = GoogleProvider(api_key="k", use_pro=True)
        assert provider.actual_model == GoogleProvider.DEFAULT_PRO_MODEL

    def test_batch_sends_prompt_and_all_images_in_one_call(self, fake_genai_client):
        provider = GoogleProvider(api_key="k", model="gemini-3.8-flash")
        images = [_image(), _image()]

        result = provider.transcribe_images_batch(images, "PROMPT")

        assert result == "transcribed"
        fake_genai_client.models.generate_content.assert_called_once()
        kwargs = fake_genai_client.models.generate_content.call_args.kwargs
        assert kwargs["model"] == "gemini-3.8-flash"
        assert kwargs["contents"] == ["PROMPT", *images]

    def test_temperature_and_safety_settings_in_config(self, fake_genai_client):
        provider = GoogleProvider(
            api_key="k", model="gemini-2.5-flash", temperature=0.3, temperature_was_set=True
        )
        provider.transcribe_image(_image(), "PROMPT")

        config = fake_genai_client.models.generate_content.call_args.kwargs["config"]
        assert config.temperature == 0.3
        thresholds = {s.threshold for s in config.safety_settings}
        assert thresholds == {google_module.types.HarmBlockThreshold.BLOCK_ONLY_HIGH}
        assert len(config.safety_settings) == 4

    def test_single_image_call_sends_prompt_then_image(self, fake_genai_client):
        provider = GoogleProvider(api_key="k")
        image = _image()
        provider.transcribe_image(image, "PROMPT")
        kwargs = fake_genai_client.models.generate_content.call_args.kwargs
        assert kwargs["contents"] == ["PROMPT", image]

    def test_recitation_finish_reason_raises(self, fake_genai_client):
        fake_genai_client.models.generate_content.return_value = _gemini_response(
            finish_reason=google_module.types.FinishReason.RECITATION
        )
        provider = GoogleProvider(api_key="k")
        with pytest.raises(ProviderAPIError, match="copyrighted"):
            provider.transcribe_image(_image(), "PROMPT")

    def test_safety_finish_reason_raises(self, fake_genai_client):
        fake_genai_client.models.generate_content.return_value = _gemini_response(
            finish_reason=google_module.types.FinishReason.SAFETY
        )
        provider = GoogleProvider(api_key="k")
        with pytest.raises(ProviderAPIError, match="safety"):
            provider.transcribe_image(_image(), "PROMPT")

    def test_max_tokens_finish_reason_raises(self, fake_genai_client):
        fake_genai_client.models.generate_content.return_value = _gemini_response(
            finish_reason=google_module.types.FinishReason.MAX_TOKENS
        )
        provider = GoogleProvider(api_key="k")
        with pytest.raises(ProviderAPIError, match="MAX_TOKENS"):
            provider.transcribe_image(_image(), "PROMPT")

    def test_sdk_error_is_wrapped(self, fake_genai_client):
        fake_genai_client.models.generate_content.side_effect = RuntimeError("boom")
        provider = GoogleProvider(api_key="k")
        with pytest.raises(ProviderAPIError, match="boom"):
            provider.transcribe_image(_image(), "PROMPT")

    @pytest.mark.parametrize("model", ["gemini-3.8-flash", "gemini-4-carbon"])
    def test_current_models_default_to_temperature_one(self, fake_genai_client, model):
        provider = GoogleProvider(api_key="k", model=model, temperature=0.2)
        assert provider.temperature == 1.0

    def test_older_models_keep_requested_temperature(self, fake_genai_client):
        provider = GoogleProvider(api_key="k", model="gemini-2.5-flash", temperature=0.2)
        assert provider.temperature == 0.2

    def test_list_models_filters_and_strips_prefix(self, fake_genai_client):
        fake_genai_client.models.list.return_value = [
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-embedding-2", supported_actions=["embedContent"]),
            SimpleNamespace(name="models/imagen-4", supported_actions=["generateContent"]),
        ]
        assert GoogleProvider.list_available_models(api_key="k") == ["gemini-3.8-flash"]

    def test_list_models_without_key_returns_static_list(self):
        models = GoogleProvider.list_available_models(api_key=None)
        assert GoogleProvider.DEFAULT_FLASH_MODEL in models
        assert GoogleProvider.DEFAULT_PRO_MODEL in models
