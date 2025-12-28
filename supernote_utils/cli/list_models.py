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
    """List all available models from all providers in provider:model format"""
    print("Available Models:\n", file=sys.stderr)
    print("Use these with: supernote transcribe note <file> -m <model>\n", file=sys.stderr)

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
        print("  - google-generativeai package not installed", file=sys.stderr)
        print("    Install with: pip install google-generativeai", file=sys.stderr)
    print(file=sys.stderr)

    # List Ollama models
    print("Ollama (Local):", file=sys.stderr)
    ollama_models = OllamaProvider.list_available_models()
    if ollama_models:
        for model in ollama_models:
            print(f"  ollama:{model}", file=sys.stderr)
    else:
        print("  - No vision models found", file=sys.stderr)
        print("    Install with: ollama pull qwen2.5-vl:7b", file=sys.stderr)
        print("    Make sure Ollama is running at http://localhost:11434", file=sys.stderr)
    print(file=sys.stderr)

    # Shortcuts section
    print("Shortcuts:", file=sys.stderr)
    print("  claude, claude-sonnet  → anthropic:claude-sonnet-4-5-20250929", file=sys.stderr)
    print("  claude-haiku           → anthropic:claude-haiku-4-5-20251001", file=sys.stderr)
    print("  gemini, gemini-pro     → google:gemini-2.5-pro-preview-06-05", file=sys.stderr)
    print("  gemini-flash           → google:gemini-2.5-flash-preview-05-20", file=sys.stderr)
    print("  ollama                 → ollama:<auto-detected vision model>", file=sys.stderr)
    print(file=sys.stderr)

    print("Examples:", file=sys.stderr)
    print("  supernote transcribe note input.note -m claude-sonnet", file=sys.stderr)
    print("  supernote transcribe note input.note -m anthropic:claude-3-opus-20240229", file=sys.stderr)
    print("  supernote transcribe note input.note -m google:gemini-2.5-pro", file=sys.stderr)
    print("  supernote transcribe note input.note -m ollama:qwen2.5-vl:7b", file=sys.stderr)
