#!/usr/bin/env python3
"""
CLI command to list available models from all providers.
"""

import os
import sys

from supernote_utils.providers.anthropic import AnthropicProvider
from supernote_utils.providers.google import GoogleProvider
from supernote_utils.providers.ollama import OllamaProvider


def list_available_models(args):
    """List all available models from all providers"""
    print("Available Models:\n", file=sys.stderr)

    # List Claude models
    print("Claude (Anthropic):", file=sys.stderr)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    claude_models = AnthropicProvider.list_available_models(api_key)
    if claude_models:
        for model in claude_models:
            print(f"  - {model}", file=sys.stderr)
        if not api_key:
            print("    (Set ANTHROPIC_API_KEY to use Claude models)", file=sys.stderr)
    else:
        print("  - anthropic package not installed", file=sys.stderr)
        print("    Install with: pip install anthropic", file=sys.stderr)
    print(file=sys.stderr)

    # List Gemini models
    print("Gemini (Google):", file=sys.stderr)
    api_key = os.getenv("GOOGLE_API_KEY")
    gemini_models = GoogleProvider.list_available_models(api_key)
    if gemini_models:
        for model in gemini_models:
            print(f"  - {model}", file=sys.stderr)
        if not api_key:
            print("    (Set GOOGLE_API_KEY to use Gemini models)", file=sys.stderr)
    else:
        print("  - google-generativeai package not installed", file=sys.stderr)
        print("    Install with: pip install google-generativeai", file=sys.stderr)
    print(file=sys.stderr)

    # List Ollama models
    print("Ollama (Local):", file=sys.stderr)
    ollama_models = OllamaProvider.list_available_models()
    if ollama_models:
        for model in ollama_models:
            print(f"  - {model}", file=sys.stderr)
    else:
        print("  - No vision models found", file=sys.stderr)
        print("    Install with: ollama pull qwen2.5-vl:7b", file=sys.stderr)
        print("    Make sure Ollama is running at http://localhost:11434", file=sys.stderr)
    print(file=sys.stderr)

    print("\nUsage: Use --api to select provider variant and --model to specify exact model", file=sys.stderr)
    print("Example: supernote transcribe note input.note --model claude-3-opus-20240229", file=sys.stderr)
