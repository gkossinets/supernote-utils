"""LLM vision provider implementations and factory"""

from typing import Optional

from supernote_utils.config import ProviderConfig
from supernote_utils.exceptions import ConfigurationError
from supernote_utils.providers.anthropic import AnthropicProvider
from supernote_utils.providers.base import VisionProvider
from supernote_utils.providers.google import GoogleProvider
from supernote_utils.providers.ollama import OllamaProvider

__all__ = [
    "VisionProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "OllamaProvider",
    "create_provider",
    "parse_model_spec",
]


def parse_model_spec(model_spec: str) -> tuple[str, Optional[str], dict]:
    """
    Parse model specification into (provider, model_name, options).

    Accepts formats:
    - Explicit: "anthropic:claude-3-opus-20240229", "google:gemini-2.5-pro", "ollama:qwen2.5-vl:7b"
    - Shortcuts: "claude", "claude-sonnet", "claude-haiku", "gemini", "gemini-flash", "gemini-pro", "ollama"

    Args:
        model_spec: Model specification string

    Returns:
        Tuple of (provider_name, model_name, options_dict)
        - provider_name: "anthropic", "google", or "ollama"
        - model_name: Specific model or None for provider default
        - options_dict: Additional options like {"use_sonnet": True}

    Raises:
        ConfigurationError: If model_spec format is invalid
    """
    # Shortcuts mapping: shortcut -> (provider, model, options)
    shortcuts = {
        "claude": ("anthropic", None, {"use_sonnet": True}),
        "claude-sonnet": ("anthropic", None, {"use_sonnet": True}),
        "claude-haiku": ("anthropic", None, {"use_sonnet": False}),
        "gemini": ("google", "gemini-3-pro-preview", {"use_pro": True}),
        "gemini-flash": ("google", "gemini-3-flash-preview", {"use_pro": False}),
        "gemini-pro": ("google", "gemini-3-pro-preview", {"use_pro": True}),
        "ollama": ("ollama", None, {}),
    }

    model_spec_lower = model_spec.lower()

    # Check for shortcut first
    if model_spec_lower in shortcuts:
        return shortcuts[model_spec_lower]

    # Check for explicit provider:model format
    if ":" in model_spec:
        # Split only on first colon (ollama models can have colons like "qwen2.5-vl:7b")
        parts = model_spec.split(":", 1)
        provider = parts[0].lower()
        model = parts[1] if len(parts) > 1 and parts[1] else None

        # Validate provider
        valid_providers = ["anthropic", "google", "ollama"]
        if provider not in valid_providers:
            raise ConfigurationError(
                f"Unknown provider: '{provider}'. "
                f"Valid providers: {', '.join(valid_providers)}"
            )

        # Set default options based on provider
        options = {}
        if provider == "anthropic":
            options["use_sonnet"] = True  # Default to sonnet behavior
        elif provider == "google":
            options["use_pro"] = "pro" in (model or "").lower()

        return (provider, model, options)

    # No colon and not a shortcut - invalid format
    raise ConfigurationError(
        f"Invalid model specification: '{model_spec}'. "
        f"Use 'provider:model' format (e.g., 'anthropic:claude-3-opus-20240229', "
        f"'google:gemini-2.5-pro', 'ollama:qwen2.5-vl:7b') "
        f"or a shortcut: claude, claude-sonnet, claude-haiku, gemini, gemini-flash, gemini-pro, ollama"
    )


def create_provider(
    model_spec: str,
    config: Optional[ProviderConfig] = None,
    temperature: float = 0.2,
) -> VisionProvider:
    """
    Factory function to create appropriate vision provider.

    Args:
        model_spec: Model specification in "provider:model" format or shortcut
                   Examples: "anthropic:claude-3-opus-20240229", "google:gemini-2.5-pro",
                            "ollama:qwen2.5-vl:7b", "claude-sonnet", "gemini-flash"
        config: Provider configuration (uses defaults if None)
        temperature: Generation temperature

    Returns:
        Configured VisionProvider instance

    Raises:
        ConfigurationError: If provider is not supported or not configured
    """
    if config is None:
        config = ProviderConfig.from_env()

    # Parse the model specification
    provider_name, model, options = parse_model_spec(model_spec)

    # Create appropriate provider
    if provider_name == "anthropic":
        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=model,
            temperature=temperature,
            use_sonnet=options.get("use_sonnet", True),
        )

    elif provider_name == "google":
        return GoogleProvider(
            api_key=config.google_api_key,
            model=model,
            temperature=temperature,
            use_pro=options.get("use_pro", False),
        )

    elif provider_name == "ollama":
        return OllamaProvider(
            model=model,
            temperature=temperature,
            base_url=config.ollama_base_url,
        )

    else:
        # This shouldn't happen if parse_model_spec validates correctly
        raise ConfigurationError(f"Unsupported provider: {provider_name}")
