# Supernote Utilities

Python utilities for managing and transcribing handwritten notes from Ratta Supernote tablets.

## Features

- **Universal file transcription** with auto-format detection (.note, .pdf, .png, .jpg, .jpeg, .webp)
- **LLM vision APIs** support (Claude, Gemini, Ollama)
- **Batch processing** for multi-page documents (faster, more cost-effective)
- **Temperature control** for deterministic transcription (reduce hallucinations)
- **Local LLM support** via Ollama (privacy-focused, no API costs)
- **Comprehensive test suite** for comparing transcription quality across models
- **PDF generation** from .note files

## Installation

### Requirements

- Python 3.8 or higher
- pip (Python package installer)

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

### List Available Models

```bash
# List all available models from all providers
supernote list-models

# This will show available models from Claude, Gemini, and Ollama
```

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

# Use specific Gemini model with custom temperature
supernote transcribe input.pdf -o output.md -m google:gemini-3-pro-preview --temperature 0.2

# Use local Ollama model
supernote transcribe input.note -o output.md -m ollama:qwen2.5-vl:7b

# Use specific Anthropic model
supernote transcribe input.pdf -o output.md -m anthropic:claude-3-opus-20240229

# Output plain text (strip Markdown formatting)
supernote transcribe input.pdf -m claude --plain-text -o output.txt

# Generate both Markdown and PDF (.note files only)
supernote transcribe input.note -o output.md --pdf output.pdf

# Adjust batch size for multi-page processing (default: 3)
supernote transcribe input.pdf --batch-size 5 -o output.md

# Disable batch processing (process one page at a time)
supernote transcribe input.note --batch-size 1 --page-separator -o output.md
```

**Batch Processing:** By default, multi-page documents (.note, .pdf) are processed in batches of 3 pages in a single API call. This is faster and more cost-effective than processing pages individually. The batch size can be adjusted with `--batch-size`, or disabled entirely by setting it to 1.

### Generate PDF from .note File

```bash
supernote convert note2pdf input.note output.pdf
```

## Temperature Settings

Temperature controls the randomness of LLM generation. For transcription:

- **0.0-0.2**: Very deterministic, minimal hallucinations (recommended for transcription)
- **0.2-0.5**: Balanced, some flexibility for ambiguous handwriting
- **0.5-1.0**: More creative, higher risk of hallucinations

**Recommended defaults:**
- Claude: 0.3
- Gemini: 0.2
- Ollama: 0.1

## Test Suite

Compare transcription quality across different models and temperature settings:

```bash
# Run full test suite
python test_transcription.py

# Quick test with default configurations
python test_transcription.py --quick

# Custom test files
python test_transcription.py --note my_test.note --reference my_reference.md
```

The test suite calculates:
- **WER (Word Error Rate)**: Percentage of word-level errors
- **CER (Character Error Rate)**: Percentage of character-level errors
- **BLEU Score**: N-gram overlap with reference (0-1, higher is better)
- **Levenshtein Distance**: Raw edit distance
- **Semantic Similarity**: Meaning similarity using sentence embeddings (0-1, higher is better)

Results are saved to `test/results/run_TIMESTAMP.md`

## Supported Models

**To see all available models, run:**
```bash
supernote list-models
```

### Model Selection Format

Use either shortcuts or explicit `provider:model` format:

**Shortcuts:**
- `gemini-flash` → Gemini 3 Flash (default - fast, free tier available)
- `gemini`, `gemini-pro` → Gemini 3 Pro (powerful, high accuracy)
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
-m google:gemini-2.0-flash-exp
-m google:gemini-1.5-pro

# Ollama (Local)
-m ollama:qwen2.5-vl:7b
-m ollama:llama3.2-vision:11b
-m ollama:llava:latest
```

**Note:** Only models installed locally will be shown by `supernote list-models`

## Project Structure

```
.
├── supernote_utils/         # Main package
│   ├── cli/                 # Command-line interface
│   ├── core/                # Transcription engine
│   ├── providers/           # LLM provider implementations
│   ├── sources/             # File source handlers
│   └── note_format/         # Supernote .note file format parser
├── test/                    # Test files
│   ├── test.note            # Sample handwritten note
│   ├── test-transcribed.md  # Reference transcription
│   └── results/             # Test results
└── pyproject.toml           # Package configuration
```

## Tips for Best Results

1. **Use deterministic temperature** (0.0-0.2) for consistent transcription
2. **Test multiple models** - different models excel at different handwriting styles
3. **Use the test suite** to find the best model/temperature for your handwriting
4. **For multilingual content**, Claude Sonnet and Gemini Pro tend to perform best
5. **For privacy-sensitive content**, use Ollama with local models
6. **For scientific notation**, add custom instructions via `--add-prompt`

## License

Apache License 2.0

## Credits

Built on top of [supernote-tool](https://github.com/jya-dev/supernote-tool) by jya.
