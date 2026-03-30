# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable mode with test dependencies
pip install -e ".[test]"

# Run tests
pytest test/

# Run a single test file
pytest test/test_note2pdf.py

# Run with coverage
pytest test/ --cov=supernote_utils --cov-report=term-missing

# Lint
ruff check supernote_utils/

# CLI entry point (after install)
supernote --help
supernote list-models
```

Note: `pytest.ini_options` sets `testpaths = ["tests"]` (plural) but test files live in `test/` (singular). Run pytest with an explicit path: `pytest test/`.

System dependency: `brew install poppler` is required for PDF rendering (`pdf2image` won't work without it).

## Architecture

The package is structured as three independent layers that compose at the CLI layer:

**Sources** (`supernote_utils/sources/`) — Convert files to lists of PIL Images:
- `factory.py` dispatches by file extension to the right handler
- `NoteFileHandler` — parses Supernote `.note` binary format (via `note_format/`)
- `PDFFileHandler` — renders PDF pages to images using `pdf2image`
- `ImageFileHandler` — wraps single images directly

**Providers** (`supernote_utils/providers/`) — Send images to an LLM and return text:
- `VisionProvider` (base) defines `transcribe_image(image, prompt)` and `transcribe_images_batch(images, prompt)`
- Concrete providers: `AnthropicProvider`, `GoogleProvider`, `OllamaProvider`, `OpenAIProvider`
- `transcribe_images_batch` defaults to serial single-image calls; providers can override for true batching

**Core** (`supernote_utils/core/`) — Orchestrates sources → providers:
- `Transcriber` wraps a provider and a `TranscriptionConfig`; handles batching logic and page separator insertion
- `ImageProcessor` — image validation and markdown post-processing utilities
- `prompts.py` — the transcription prompt template

**Note format** (`supernote_utils/note_format/`) — Vendored/adapted code from `supernote-tool` for parsing the proprietary Supernote binary format. Avoid modifying unless you understand the format spec.

**CLI** (`supernote_utils/cli/`) — Thin wrappers over the above:
- `main.py` — argparse dispatch to `transcribe`, `convert`, `list-models`
- `transcribe.py` — resolves model shortcut strings → provider instances → `Transcriber`
- `list_models.py` — queries each provider for available models

## Keeping README.md current

After any change to CLI behaviour, defaults, flags, supported formats, or model shortcuts, update `README.md` to match. Specifically check: command examples, the Temperature Settings section, Model Calibration paths, the Supported Models shortcuts table, and the Project Structure tree.

## Provider/model string format

The CLI accepts `provider:model` strings (e.g., `anthropic:claude-3-opus-20240229`) or shortcuts (`claude`, `gemini-flash`, `ollama`). Resolution logic lives in `transcribe.py`. When adding new models, update both the shortcut map there and `list_models.py`.

## Adding a new provider

1. Subclass `VisionProvider` in `supernote_utils/providers/`
2. Implement `transcribe_image`, `is_available`, `get_display_name`
3. Optionally override `transcribe_images_batch` for efficiency
4. Register the prefix in `transcribe.py` and `list_models.py`
5. Add the dependency to `pyproject.toml`

## Environment variables

- `ANTHROPIC_API_KEY` — required for Claude models
- `GOOGLE_API_KEY` — required for Gemini models
- `OLLAMA_BASE_URL` — Ollama server (default `http://localhost:11434`)
