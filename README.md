# Supernote Utilities

Python utilities for managing and transcribing handwritten notes from Ratta Supernote tablets.

## Features

- **Universal file transcription** with auto-format detection (.note, .pdf, .png, .jpg, .jpeg, .webp)
- **LLM vision APIs** support (Claude, Gemini, Ollama)
- **Batch processing** for multi-page documents (faster, more cost-effective)
- **Temperature control** for deterministic transcription (reduce hallucinations)
- **Local LLM support** via Ollama (privacy-focused, no API costs)
- **Model calibration scripts** for comparing transcription quality across models
- **PDF generation** from .note files

## Installation

### Requirements

- Python 3.8 or higher

### Quick Install

Install directly from the repository:

```bash
pip install git+https://github.com/gkossinets/supernote-utils.git
```

### Development Install

For local development or to use the latest code:

```bash
# Clone the repository
git clone https://github.com/gkossinets/supernote-utils.git
cd supernote-utils

# Install in editable mode
pip install -e .

# Install with testing dependencies (optional)
pip install -e ".[test]"

# Install with development tools (optional)
pip install -e ".[dev]"
```

### System Dependencies

For PDF rendering support (required for PDF transcription and PDF output):

```bash
# On macOS:
brew install poppler

# On Ubuntu/Debian:
sudo apt-get install poppler-utils

# On Windows:
# Download poppler from: https://github.com/oschwartz10612/poppler-windows/releases/
# Add the bin/ directory to your PATH
```

### Verify Installation

After installation, verify the CLI is working:

```bash
supernote --help
supernote list-models
```

## Environment Variables

Set the required API keys based on which services you'll use:

```bash
# For Claude (Anthropic)
export ANTHROPIC_API_KEY="your-key-here"

# For Gemini (Google)
export GOOGLE_API_KEY="your-key-here"

# For Ollama (local models) - no key needed, just install:
# https://ollama.ai/
```

## Usage

### Supported Formats

| Format | Extension | Multi-page | Notes |
|--------|-----------|------------|-------|
| Supernote | .note | Yes | Native Supernote format |
| PDF | .pdf | Yes | Scanned or exported PDFs |
| PNG | .png | No | Single image |
| JPEG | .jpg, .jpeg | No | Single image |
| WebP | .webp | No | Single image |

### Transcribe Files to Markdown

The `supernote transcribe` command automatically detects the file format and processes it accordingly:

```bash
# Basic usage with Gemini Flash (default) - works with any supported format
supernote transcribe input.note -o output.md
supernote transcribe input.pdf -o output.md
supernote transcribe photo.png -o output.md
supernote transcribe scan.jpg -o output.md

# Use Claude Sonnet model
supernote transcribe input.note -o output.md -m claude-sonnet

# Use Claude with recommended temperature
supernote transcribe input.pdf -o output.md -m claude-sonnet --temperature 0.7

# Use local Ollama model
supernote transcribe input.note -o output.md -m ollama:qwen2.5-vl:7b

# Use specific Anthropic model
supernote transcribe input.pdf -o output.md -m anthropic:claude-3-opus-20240229

# Output plain text (strip Markdown formatting)
supernote transcribe input.pdf -m claude --plain-text -o output.txt

# Generate both Markdown and PDF (.note files only)
supernote transcribe input.note -o output.md --pdf output.pdf

# Multiple files → individual outputs in a directory
supernote transcribe -t markdown *.note -d transcribed/

# Adjust batch size for multi-page processing (default: 5)
supernote transcribe input.pdf --batch-size 10 -o output.md

# Disable batch processing (process one page at a time)
supernote transcribe input.note --batch-size 1 --page-separator -o output.md
```

**Batch Processing:** By default, multi-page documents (.note, .pdf) are processed in batches of 5 pages in a single API call. This is faster and more cost-effective than processing pages individually. The batch size can be adjusted with `--batch-size`, or disabled entirely by setting it to 1.

### Generate PDF from .note File

```bash
supernote convert input.note -o output.pdf
supernote convert input.note          # writes input.pdf next to input.note
```

## Temperature Settings

Temperature controls the randomness of LLM generation. The CLI default is `1.0`, which is the recommended value for Gemini 3 models. Different providers have different optimal settings for transcription:

**Recommended defaults for transcription:**
- **Gemini 3.x:** `1.0` (the default; do not lower — [Google recommends 1.0](https://ai.google.dev/gemini-api/docs/gemini-3#temperature) for reasoning models; lower values may cause looping or degraded output)
- **Claude:** `--temperature 0.7` (balances determinism with flexibility for ambiguous handwriting)
- **Ollama:** `--temperature 0.5` (local models benefit from some flexibility to handle ambiguity)

The code auto-adjusts Gemini 3 models to temperature 1.0 unless you explicitly override it. If you do override, a warning is displayed.

For all providers, values above 1.0 increase hallucination risk and are not recommended for transcription.

## Model Calibration

The `misc/` directory contains scripts for comparing transcription quality across models and temperatures against a reference transcription:

```bash
# Run with all available models
python misc/test_transcription2.py

# Quick run (one temperature per model)
python misc/test_transcription2.py --quick

# Custom reference files
python misc/test_transcription2.py --note my_test.note --reference my_reference.md
```

Requires the test dependencies: `pip install -e ".[test]"`

Metrics calculated:
- **WER (Word Error Rate)**: Percentage of word-level errors
- **CER (Character Error Rate)**: Percentage of character-level errors
- **BLEU Score**: N-gram overlap with reference (0–1, higher is better)
- **Levenshtein Distance**: Raw edit distance
- **Semantic Similarity**: Meaning similarity using sentence embeddings (0–1, higher is better)

Results are saved to `test/results/run_TIMESTAMP.md`

## Supported Models

Run `supernote list-models` to see what's available in your environment. Use either shortcuts or explicit `provider:model` format:

**Shortcuts:**
- `gemini-flash`, `gemini-flash-latest` → Gemini Flash Latest (default — fast, free tier available)
- `gemini`, `gemini-pro` → Gemini 3 Pro (powerful, high accuracy)
- `gemini-3-flash` → Gemini 3 Flash Preview
- `claude`, `claude-sonnet` → Claude Sonnet 4.5 (powerful, high accuracy)
- `claude-haiku` → Claude Haiku 4.5 (faster, cost-effective)
- `ollama` → Auto-detected local vision model

**Explicit provider:model format:**
```bash
# Anthropic (Claude)
-m anthropic:claude-sonnet-4-5-20250929
-m anthropic:claude-haiku-4-5-20251001
-m anthropic:claude-3-5-sonnet-20241022
-m anthropic:claude-3-opus-20240229

# Google (Gemini)
-m google:gemini-3-pro-preview
-m google:gemini-3-flash-preview
-m google:gemini-flash-latest

# Ollama (Local)
-m ollama:qwen2.5-vl:7b
-m ollama:llama3.2-vision:11b
-m ollama:llava:latest
```

**Note:** Only locally installed Ollama models appear in the output.

## Project Structure

```
.
├── supernote_utils/         # Main package
│   ├── cli/                 # Command-line interface
│   ├── core/                # Transcription engine
│   ├── providers/           # LLM provider implementations
│   ├── sources/             # File source handlers
│   └── note_format/         # Supernote .note file format parser
├── test/                    # Unit tests and fixtures
│   └── test.note            # Sample handwritten note (test fixture)
├── misc/                    # Model calibration scripts and reference data
│   ├── test_transcription2.py   # Model comparison script
│   └── test-transcribed.md      # Reference transcription for calibration
└── pyproject.toml           # Package configuration
```

## Tips for Best Results

1. **Use the recommended temperature** for your provider (1.0 for Gemini, 0.7 for Claude, 0.5 for Ollama)
2. **Run the calibration script** (`misc/test_transcription2.py`) to find the best model for your handwriting
3. **For multilingual content**, Claude Sonnet and Gemini Pro tend to perform best
4. **For privacy-sensitive content**, use Ollama with local models
5. **Test multiple models** — different models excel at different handwriting styles and languages

## License

Apache License 2.0

## Credits

Built on top of [supernote-tool](https://github.com/jya-dev/supernote-tool) by jya.
