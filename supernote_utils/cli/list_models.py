#!/usr/bin/env python3
"""
CLI command to list available models from all providers.
"""

import os
import sys

from supernote_utils.providers import describe_shortcuts
from supernote_utils.providers.anthropic import AnthropicProvider
from supernote_utils.providers.google import GoogleProvider
from supernote_utils.providers.ollama import OllamaProvider
from supernote_utils.providers.openai import OpenAIProvider


def list_available_models(args):
    """List all available models from all providers in provider:model format"""
    print("Available Models:\n", file=sys.stderr)
    print("Use these with: supernote transcribe <file> -m <model>\n", file=sys.stderr)

    # List Claude models
    print("Anthropic (Claude):", file=sys.stderr)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    claude_models = AnthropicProvider.list_available_models(api_key)
    if claude_models:
        for model in claude_models:
            print(f"  anthropic:{model}", file=sys.stderr)
        if not api_key:
            print("    (Set ANTHROPIC_API_KEY to use Anthropic models)", file=sys.stderr)
    else:
        print("  - anthropic package not installed", file=sys.stderr)
        print("    Install with: pip install anthropic", file=sys.stderr)
    print(file=sys.stderr)

    # List Gemini models
    print("Google (Gemini):", file=sys.stderr)
    api_key = os.getenv("GOOGLE_API_KEY")
    gemini_models = GoogleProvider.list_available_models(api_key)
    if gemini_models:
        for model in gemini_models:
            print(f"  google:{model}", file=sys.stderr)
        if not api_key:
            print("    (Set GOOGLE_API_KEY to use Google models)", file=sys.stderr)
    else:
        print("  - google-genai package not installed", file=sys.stderr)
        print("    Install with: pip install google-genai", file=sys.stderr)
    print(file=sys.stderr)

    # List OpenAI models
    print("OpenAI (GPT):", file=sys.stderr)
    api_key = os.getenv("OPENAI_API_KEY")
    openai_models = OpenAIProvider.list_available_models(api_key)
    if openai_models:
        for model in openai_models:
            print(f"  openai:{model}", file=sys.stderr)
        if not api_key:
            print("    (Set OPENAI_API_KEY to use OpenAI models)", file=sys.stderr)
    else:
        print("  - openai package not installed (optional)", file=sys.stderr)
        print("    Install with: pip install 'supernote-utils[openai]'", file=sys.stderr)
    print(file=sys.stderr)

    # List Ollama models
    print("Ollama (Local):", file=sys.stderr)
    ollama_models = OllamaProvider.list_available_models()
    if ollama_models:
        for model in ollama_models:
            print(f"  ollama:{model}", file=sys.stderr)
    else:
        print("  - No vision models found", file=sys.stderr)
        print("    Install with: ollama pull gemma4:26b-a4b", file=sys.stderr)
        print("    Make sure Ollama is running at http://localhost:11434", file=sys.stderr)
    print(file=sys.stderr)

    # Shortcuts section, generated from the factory so it can't drift from it
    print("Shortcuts:", file=sys.stderr)
    shortcuts = describe_shortcuts()
    width = max(len(name) for name in shortcuts)
    for name, target in shortcuts.items():
        print(f"  {name:<{width}}  → {target}", file=sys.stderr)
    print(file=sys.stderr)

    print("Examples:", file=sys.stderr)
    print("  supernote transcribe input.note -m claude-sonnet", file=sys.stderr)
    print("  supernote transcribe input.note -m anthropic:claude-opus-5-5", file=sys.stderr)
    print("  supernote transcribe input.note -m google:gemini-4-carbon", file=sys.stderr)
    print("  supernote transcribe input.note -m openai:gpt-6.2-astra", file=sys.stderr)
    print("  supernote transcribe input.note -m ollama:gemma4:26b-a4b", file=sys.stderr)
    print("  supernote transcribe *.note -d transcribed/", file=sys.stderr)
