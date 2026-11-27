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

    def test_pro_default_is_hydrogen(self, fake_genai_client):
        # Google's recommended general-purpose Gemini 4 model.
        provider = GoogleProvider(api_key="k", use_pro=True)
        assert provider.actual_model == "gemini-4-hydrogen"

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

    def test_blocked_prompt_with_no_text_raises(self, fake_genai_client):
        # A prompt-level block returns no candidates and text=None.
        fake_genai_client.models.generate_content.return_value = SimpleNamespace(
            text=None,
            candidates=[],
            prompt_feedback=SimpleNamespace(block_reason="PROHIBITED_CONTENT"),
        )
        provider = GoogleProvider(api_key="k")
        with pytest.raises(ProviderAPIError, match="PROHIBITED_CONTENT"):
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


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------

from supernote_utils.providers import anthropic as anthropic_module  # noqa: E402
from supernote_utils.providers.anthropic import AnthropicProvider  # noqa: E402


def _claude_response(text: str = "transcribed", stop_reason: str = "end_turn", thinking=True):
    blocks = []
    if thinking:
        # Current models think by default; the thinking block comes before the text.
        blocks.append(SimpleNamespace(type="thinking", thinking=""))
    blocks.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(content=blocks, stop_reason=stop_reason, stop_details=None)


@pytest.fixture
def fake_anthropic_client(monkeypatch):
    client = MagicMock()
    client.beta.messages.create.return_value = _claude_response()
    client_cls = MagicMock(return_value=client)
    monkeypatch.setattr(anthropic_module.anthropic, "Anthropic", client_cls)
    client.client_cls = client_cls
    return client


class TestAnthropicProvider:
    def test_default_models_are_current(self, fake_anthropic_client):
        assert AnthropicProvider(api_key="k").actual_model == "claude-sonnet-5-5"
        assert AnthropicProvider(api_key="k", use_sonnet=False).actual_model == "claude-haiku-5-5"

    def test_missing_api_key_raises(self, fake_anthropic_client):
        with pytest.raises(ProviderNotAvailableError):
            AnthropicProvider(api_key="")

    def test_returns_text_block_after_thinking_block(self, fake_anthropic_client):
        provider = AnthropicProvider(api_key="k")
        assert provider.transcribe_image(_image(), "PROMPT") == "transcribed"

    def test_does_not_send_temperature(self, fake_anthropic_client):
        # Current Claude models accept only the default sampling settings.
        provider = AnthropicProvider(api_key="k", temperature=0.7, temperature_was_set=True)
        provider.transcribe_image(_image(), "PROMPT")
        kwargs = fake_anthropic_client.beta.messages.create.call_args.kwargs
        assert "temperature" not in kwargs

    def test_warns_when_temperature_set_explicitly(self, fake_anthropic_client, capsys):
        AnthropicProvider(api_key="k", temperature=0.7, temperature_was_set=True)
        assert "ignored" in capsys.readouterr().err

    def test_batch_sends_all_images_in_one_call(self, fake_anthropic_client):
        provider = AnthropicProvider(api_key="k")
        provider.transcribe_images_batch([_image(), _image(), _image()], "PROMPT")

        fake_anthropic_client.beta.messages.create.assert_called_once()
        content = fake_anthropic_client.beta.messages.create.call_args.kwargs["messages"][0]["content"]
        assert content[0] == {"type": "text", "text": "PROMPT"}
        assert [block["type"] for block in content[1:]] == ["image"] * 3

    def test_sonnet_requests_server_side_refusal_fallback(self, fake_anthropic_client):
        AnthropicProvider(api_key="k").transcribe_image(_image(), "PROMPT")
        kwargs = fake_anthropic_client.beta.messages.create.call_args.kwargs
        assert kwargs["fallbacks"] == "default"
        assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]

    def test_opus_shortcut_creates_opus_provider_with_fallback(self, fake_anthropic_client):
        config = ProviderConfig(anthropic_api_key="k", google_api_key=None)
        provider = create_provider("claude-opus", config)
        assert provider.actual_model == "claude-opus-5-5"
        assert provider.get_display_name() == "Claude Opus 5.5"

        provider.transcribe_image(_image(), "PROMPT")
        assert fake_anthropic_client.beta.messages.create.call_args.kwargs["fallbacks"] == "default"

    def test_haiku_does_not_request_fallback(self, fake_anthropic_client):
        # Haiku has no server-side fallback; sending the parameter would be rejected.
        AnthropicProvider(api_key="k", use_sonnet=False).transcribe_image(_image(), "PROMPT")
        kwargs = fake_anthropic_client.beta.messages.create.call_args.kwargs
        assert "fallbacks" not in kwargs
        assert "betas" not in kwargs

    def test_refusal_raises(self, fake_anthropic_client):
        fake_anthropic_client.beta.messages.create.return_value = _claude_response(
            text="", stop_reason="refusal"
        )
        with pytest.raises(ProviderAPIError, match="declined"):
            AnthropicProvider(api_key="k").transcribe_image(_image(), "PROMPT")

    def test_max_tokens_raises(self, fake_anthropic_client):
        fake_anthropic_client.beta.messages.create.return_value = _claude_response(
            stop_reason="max_tokens"
        )
        with pytest.raises(ProviderAPIError, match="max_tokens"):
            AnthropicProvider(api_key="k").transcribe_image(_image(), "PROMPT")

    def test_sdk_error_is_wrapped(self, fake_anthropic_client):
        fake_anthropic_client.beta.messages.create.side_effect = RuntimeError("boom")
        with pytest.raises(ProviderAPIError, match="boom"):
            AnthropicProvider(api_key="k").transcribe_image(_image(), "PROMPT")


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

from supernote_utils.config import ProviderConfig  # noqa: E402
from supernote_utils.providers import create_provider, parse_model_spec  # noqa: E402


class TestCreateProvider:
    def test_passes_temperature_was_set_to_anthropic(self, fake_anthropic_client, capsys):
        config = ProviderConfig(anthropic_api_key="k", google_api_key=None)
        create_provider("claude", config, temperature=0.5, temperature_was_set=True)
        assert "ignored" in capsys.readouterr().err

    def test_creates_openai_provider(self, fake_openai_client):
        config = ProviderConfig(anthropic_api_key=None, google_api_key=None, openai_api_key="k")
        provider = create_provider("gpt", config)
        assert isinstance(provider, OpenAIProvider)
        assert provider.actual_model == OpenAIProvider.DEFAULT_MODEL

    def test_openai_without_key_raises(self, fake_openai_client):
        config = ProviderConfig(anthropic_api_key=None, google_api_key=None, openai_api_key=None)
        with pytest.raises(ProviderNotAvailableError, match="OPENAI_API_KEY"):
            create_provider("openai", config)


class TestParseModelSpec:
    @pytest.mark.parametrize(
        "spec, provider",
        [
            ("claude", "anthropic"),
            ("claude-sonnet", "anthropic"),
            ("claude-haiku", "anthropic"),
            ("claude-opus", "anthropic"),
            ("gemini", "google"),
            ("gemini-pro", "google"),
            ("gemini-flash", "google"),
            ("gpt", "openai"),
            ("gpt-mini", "openai"),
            ("openai", "openai"),
            ("ollama", "ollama"),
        ],
    )
    def test_shortcuts(self, spec, provider):
        assert parse_model_spec(spec)[0] == provider

    def test_explicit_openai_model(self):
        assert parse_model_spec("openai:gpt-6.2-astra") == ("openai", "gpt-6.2-astra", {})

    def test_explicit_ollama_model_keeps_tag_colon(self):
        assert parse_model_spec("ollama:qwen2.5-vl:7b")[1] == "qwen2.5-vl:7b"

    @pytest.mark.parametrize("spec", ["gemini-flash-latest", "gemini-3-flash"])
    def test_retired_shortcuts_are_rejected(self, spec):
        # These pointed at model IDs the Gemini API no longer serves.
        with pytest.raises(ConfigurationError):
            parse_model_spec(spec)

    def test_unknown_provider_lists_openai(self):
        with pytest.raises(ConfigurationError, match="openai"):
            parse_model_spec("mistral:large")


class TestDescribeShortcuts:
    def test_every_shortcut_resolves_to_a_concrete_model(self):
        described = describe_shortcuts()
        assert described["claude"] == "anthropic:claude-sonnet-5-5"
        assert described["claude-haiku"] == "anthropic:claude-haiku-5-5"
        assert described["claude-opus"] == "anthropic:claude-opus-5-5"
        assert described["gemini-flash"] == f"google:{GoogleProvider.DEFAULT_FLASH_MODEL}"
        assert described["gemini-pro"] == f"google:{GoogleProvider.DEFAULT_PRO_MODEL}"
        assert described["gpt"] == f"openai:{OpenAIProvider.DEFAULT_MODEL}"
        assert described["gpt-mini"] == f"openai:{OpenAIProvider.DEFAULT_MINI_MODEL}"
        assert described["ollama"] == "ollama:<auto-detected vision model>"


# ---------------------------------------------------------------------------
# OpenAIProvider (Responses API)
# ---------------------------------------------------------------------------

from supernote_utils.exceptions import ConfigurationError  # noqa: E402
from supernote_utils.providers import describe_shortcuts  # noqa: E402
from supernote_utils.providers import openai as openai_module  # noqa: E402
from supernote_utils.providers.openai import OpenAIProvider  # noqa: E402


def _openai_response(text: str = "transcribed", status: str = "completed", reason=None):
    return SimpleNamespace(
        output_text=text,
        status=status,
        incomplete_details=SimpleNamespace(reason=reason) if reason else None,
    )


@pytest.fixture
def fake_openai_client(monkeypatch):
    client = MagicMock()
    client.responses.create.return_value = _openai_response()
    client_cls = MagicMock(return_value=client)
    monkeypatch.setattr(openai_module.openai, "OpenAI", client_cls)
    client.client_cls = client_cls
    return client


class TestOpenAIProvider:
    def test_default_models(self, fake_openai_client):
        assert OpenAIProvider(api_key="k").actual_model == "gpt-6.2-sol"
        assert OpenAIProvider(api_key="k", use_mini=True).actual_model == "gpt-6-luna"

    def test_missing_api_key_raises(self, fake_openai_client):
        with pytest.raises(ProviderNotAvailableError):
            OpenAIProvider(api_key="")

    def test_batch_uses_responses_api_with_all_images(self, fake_openai_client):
        provider = OpenAIProvider(api_key="k")
        result = provider.transcribe_images_batch([_image(), _image()], "PROMPT")

        assert result == "transcribed"
        fake_openai_client.responses.create.assert_called_once()
        kwargs = fake_openai_client.responses.create.call_args.kwargs
        content = kwargs["input"][0]["content"]
        assert content[0] == {"type": "input_text", "text": "PROMPT"}
        assert [part["type"] for part in content[1:]] == ["input_image", "input_image"]
        assert content[1]["image_url"].startswith("data:image/jpeg;base64,")

    def test_does_not_send_temperature(self, fake_openai_client):
        # Current OpenAI models reject the temperature parameter.
        provider = OpenAIProvider(api_key="k", temperature=0.4, temperature_was_set=True)
        provider.transcribe_image(_image(), "PROMPT")
        assert "temperature" not in fake_openai_client.responses.create.call_args.kwargs

    def test_warns_when_temperature_set_explicitly(self, fake_openai_client, capsys):
        OpenAIProvider(api_key="k", temperature=0.4, temperature_was_set=True)
        assert "ignored" in capsys.readouterr().err

    def test_incomplete_response_raises(self, fake_openai_client):
        fake_openai_client.responses.create.return_value = _openai_response(
            status="incomplete", reason="max_output_tokens"
        )
        with pytest.raises(ProviderAPIError, match="max_output_tokens"):
            OpenAIProvider(api_key="k").transcribe_image(_image(), "PROMPT")

    def test_empty_output_raises(self, fake_openai_client):
        fake_openai_client.responses.create.return_value = _openai_response(text="")
        with pytest.raises(ProviderAPIError, match="no text"):
            OpenAIProvider(api_key="k").transcribe_image(_image(), "PROMPT")

    def test_sdk_error_is_wrapped(self, fake_openai_client):
        fake_openai_client.responses.create.side_effect = RuntimeError("boom")
        with pytest.raises(ProviderAPIError, match="boom"):
            OpenAIProvider(api_key="k").transcribe_image(_image(), "PROMPT")


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------

from supernote_utils.providers import ollama as ollama_module  # noqa: E402
from supernote_utils.providers.ollama import OllamaProvider  # noqa: E402


@pytest.fixture
def fake_ollama(monkeypatch):
    fake = MagicMock()
    fake.chat.return_value = {"message": {"content": "transcribed"}}
    monkeypatch.setattr(ollama_module, "ollama", fake)
    return fake


class TestOllamaProvider:
    def test_single_image_disables_thinking(self, fake_ollama):
        # Thinking made local vision models several times slower with no gain in accuracy.
        OllamaProvider(model="gemma4:latest").transcribe_image(_image(), "PROMPT")
        assert fake_ollama.chat.call_args.kwargs["think"] is False

    def test_batch_disables_thinking(self, fake_ollama):
        OllamaProvider(model="gemma4:latest").transcribe_images_batch([_image(), _image()], "PROMPT")
        kwargs = fake_ollama.chat.call_args.kwargs
        assert kwargs["think"] is False
        assert len(kwargs["messages"][0]["images"]) == 2

    def test_sends_temperature(self, fake_ollama):
        OllamaProvider(model="gemma4:latest", temperature=0.5).transcribe_image(_image(), "PROMPT")
        assert fake_ollama.chat.call_args.kwargs["options"]["temperature"] == 0.5

    def test_returns_message_content(self, fake_ollama):
        assert OllamaProvider(model="m").transcribe_image(_image(), "PROMPT") == "transcribed"

    def test_sdk_error_is_wrapped(self, fake_ollama):
        fake_ollama.chat.side_effect = RuntimeError("boom")
        with pytest.raises(ProviderAPIError, match="boom"):
            OllamaProvider(model="m").transcribe_image(_image(), "PROMPT")
