"""LLM vision provider implementations and factory"""

from supernote_utils.config import ProviderConfig
from supernote_utils.exceptions import ConfigurationError
from supernote_utils.providers.anthropic import AnthropicProvider
from supernote_utils.providers.base import VisionProvider
from supernote_utils.providers.google import GoogleProvider
from supernote_utils.providers.ollama import OllamaProvider
from supernote_utils.providers.openai import OpenAIProvider

__all__ = [
    "VisionProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "SHORTCUTS",
    "create_provider",
    "describe_shortcuts",
    "parse_model_spec",
]

VALID_PROVIDERS = ["anthropic", "google", "openai", "ollama"]

# Shortcut -> (provider, model, options). Models come from the provider classes'
# constants (None means the provider picks its tier default), so each class stays
# the single source of truth for its model IDs.
SHORTCUTS: dict[str, tuple[str, str | None, dict]] = {
    "claude": ("anthropic", None, {"use_sonnet": True}),
    "claude-sonnet": ("anthropic", None, {"use_sonnet": True}),
    "claude-haiku": ("anthropic", None, {"use_sonnet": False}),
    "claude-opus": ("anthropic", AnthropicProvider.DEFAULT_OPUS_MODEL, {"use_sonnet": True}),
    "gemini": ("google", None, {"use_pro": True}),
    "gemini-pro": ("google", None, {"use_pro": True}),
    "gemini-flash": ("google", None, {"use_pro": False}),
    "gpt": ("openai", None, {"use_mini": False}),
    "openai": ("openai", None, {"use_mini": False}),
    "gpt-mini": ("openai", None, {"use_mini": True}),
    "ollama": ("ollama", None, {}),
}


def parse_model_spec(model_spec: str) -> tuple[str, str | None, dict]:
    """
    Parse model specification into (provider, model_name, options).

    Accepts formats:
    - Explicit: "anthropic:claude-opus-5-5", "google:gemini-4-carbon",
      "openai:gpt-6.2-astra", "ollama:qwen2.5-vl:7b"
    - Shortcuts: see SHORTCUTS

    Args:
        model_spec: Model specification string

    Returns:
        Tuple of (provider_name, model_name, options_dict)
        - provider_name: one of VALID_PROVIDERS
        - model_name: Specific model or None for provider default
        - options_dict: Additional options like {"use_sonnet": True}

    Raises:
        ConfigurationError: If model_spec format is invalid
    """
    model_spec_lower = model_spec.lower()

    if model_spec_lower in SHORTCUTS:
        return SHORTCUTS[model_spec_lower]

    if ":" in model_spec:
        # Split only on first colon (ollama models can have colons like "qwen2.5-vl:7b")
        provider, _, model = model_spec.partition(":")
        provider = provider.lower()

        if provider not in VALID_PROVIDERS:
            raise ConfigurationError(
                f"Unknown provider: '{provider}'. "
                f"Valid providers: {', '.join(VALID_PROVIDERS)}"
            )

        options = {}
        if provider == "anthropic":
            options["use_sonnet"] = True
        elif provider == "google":
            options["use_pro"] = "pro" in model.lower()

        return (provider, model or None, options)

    raise ConfigurationError(
        f"Invalid model specification: '{model_spec}'. "
        f"Use 'provider:model' format (e.g., 'anthropic:claude-opus-5-5', "
        f"'google:gemini-4-carbon', 'openai:gpt-6.2-astra', 'ollama:qwen2.5-vl:7b') "
        f"or a shortcut: {', '.join(SHORTCUTS)}"
    )


def describe_shortcuts() -> dict[str, str]:
    """Map each shortcut to the concrete "provider:model" it currently selects.

    Returns:
        Dict of shortcut name to "provider:model" string.
    """
    defaults = {
        ("anthropic", "use_sonnet", True): AnthropicProvider.DEFAULT_SONNET_MODEL,
        ("anthropic", "use_sonnet", False): AnthropicProvider.DEFAULT_HAIKU_MODEL,
        ("google", "use_pro", True): GoogleProvider.DEFAULT_PRO_MODEL,
        ("google", "use_pro", False): GoogleProvider.DEFAULT_FLASH_MODEL,
        ("openai", "use_mini", False): OpenAIProvider.DEFAULT_MODEL,
        ("openai", "use_mini", True): OpenAIProvider.DEFAULT_MINI_MODEL,
    }
    described = {}
    for name, (provider, model, options) in SHORTCUTS.items():
        if provider == "ollama":
            described[name] = "ollama:<auto-detected vision model>"
            continue
        ((option, value),) = options.items()
        described[name] = f"{provider}:{model or defaults[(provider, option, value)]}"
    return described


def create_provider(
    model_spec: str,
    config: ProviderConfig | None = None,
    temperature: float = 1.0,
    temperature_was_set: bool = False,
) -> VisionProvider:
    """
    Factory function to create appropriate vision provider.

    Args:
        model_spec: Model specification in "provider:model" format or shortcut
                   Examples: "anthropic:claude-opus-5-5", "google:gemini-4-carbon",
                            "ollama:qwen2.5-vl:7b", "claude-sonnet", "gemini-flash"
        config: Provider configuration (uses defaults if None)
        temperature: Generation temperature
        temperature_was_set: Whether temperature was explicitly set by user (vs using default)

    Returns:
        Configured VisionProvider instance

    Raises:
        ConfigurationError: If provider is not supported or not configured
    """
    if config is None:
        config = ProviderConfig.from_env()

    provider_name, model, options = parse_model_spec(model_spec)

    if provider_name == "anthropic":
        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=model,
            temperature=temperature,
            use_sonnet=options.get("use_sonnet", True),
            temperature_was_set=temperature_was_set,
        )

    if provider_name == "google":
        return GoogleProvider(
            api_key=config.google_api_key,
            model=model,
            temperature=temperature,
            use_pro=options.get("use_pro", False),
            temperature_was_set=temperature_was_set,
        )

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=config.openai_api_key,
            model=model,
            temperature=temperature,
            use_mini=options.get("use_mini", False),
            temperature_was_set=temperature_was_set,
        )

    if provider_name == "ollama":
        return OllamaProvider(
            model=model,
            temperature=temperature,
            base_url=config.ollama_base_url,
        )

    # This shouldn't happen if parse_model_spec validates correctly
    raise ConfigurationError(f"Unsupported provider: {provider_name}")
