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
]


def create_provider(
    provider_name: str,
    config: Optional[ProviderConfig] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
) -> VisionProvider:
    """
    Factory function to create appropriate vision provider.

    Args:
        provider_name: Name of provider (claude, claude-haiku, claude-sonnet,
                      gemini, gemini-flash, gemini-pro, ollama)
        config: Provider configuration (uses defaults if None)
        model: Specific model override
        temperature: Generation temperature

    Returns:
        Configured VisionProvider instance

    Raises:
        ConfigurationError: If provider is not supported or not configured
    """
    if config is None:
        config = ProviderConfig.from_env()

    provider_name = provider_name.lower()

    # Anthropic providers
    if provider_name in ["claude", "claude-haiku", "claude-sonnet"]:
        use_sonnet = provider_name == "claude-sonnet"
        model_override = model or config.anthropic_model

        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=model_override,
            temperature=temperature,
            use_sonnet=use_sonnet,
        )

    # Google providers
    elif provider_name in ["gemini", "gemini-flash", "gemini-pro"]:
        use_pro = provider_name == "gemini-pro"
        model_override = model or config.google_model

        return GoogleProvider(
            api_key=config.google_api_key,
            model=model_override,
            temperature=temperature,
            use_pro=use_pro,
        )

    # Ollama provider
    elif provider_name == "ollama":
        model_override = model or config.ollama_model

        return OllamaProvider(
            model=model_override,
            temperature=temperature,
            base_url=config.ollama_base_url,
        )

    else:
        raise ConfigurationError(
            f"Unsupported provider: {provider_name}. "
            f"Supported: claude, claude-haiku, claude-sonnet, "
            f"gemini, gemini-flash, gemini-pro, ollama"
        )
