# Supernote Utilities

Python utilities for managing and transcribing handwritten notes from Ratta Supernote tablets.

## Features

- **Direct .note to Markdown transcription** using LLM vision APIs (Claude, Gemini, Ollama)
- **PDF to Markdown transcription** for scanned handwritten documents
- **Batch processing** for multi-page PDFs (faster, more cost-effective)
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

For PDF rendering support (required for `script2text` and PDF output):

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

### Convert .note Files to Markdown

```bash
# Basic usage with Claude Sonnet
python note2text.py input.note --md output.md

# Use Gemini with custom temperature
python note2text.py input.note --md output.md --api gemini-flash --temperature 0.2

# Use local Ollama model (privacy-focused, no API costs)
python note2text.py input.note --md output.md --api ollama --temperature 0.1

# Specify exact model name
supernote transcribe note input.note --model claude-3-opus-20240229

# Generate both Markdown and PDF
python note2text.py input.note --md output.md --pdf output.pdf

# Add page separators
python note2text.py input.note --md output.md --page-separator
```

### Convert PDF to Markdown

```bash
# Transcribe scanned PDF (batch processing enabled by default)
python script2text.py input.pdf --out output.md

# Use different model and temperature
python script2text.py input.pdf --api gemini-pro --temperature 0.3 --out output.md

# Output plain text (strip Markdown formatting)
python script2text.py input.pdf --plain-text --out output.txt

# Adjust batch size for multi-page processing (default: 10)
python script2text.py input.pdf --batch-size 5 --out output.md

# Disable batch processing (process one page at a time)
python script2text.py input.pdf --batch-size 1 --out output.md
```

**Batch Processing:** By default, `script2text` processes multiple pages in a single API call (10 pages per batch). This is faster and more cost-effective than processing pages individually. The batch size can be adjusted with `--batch-size`, or disabled entirely by setting it to 1.

### Generate PDF from .note File

```bash
python note2pdf.py input.note output.pdf
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

### Claude (Anthropic)
- `claude-sonnet`: Claude Sonnet 4.5 (powerful, high accuracy)
- `claude-haiku`: Claude Haiku 4.5 (faster, cost-effective)
- Specific models:
  - `claude-sonnet-4-5-20250929` (latest Sonnet)
  - `claude-haiku-4-5-20251001` (latest Haiku)
  - `claude-3-5-sonnet-20241022`
  - `claude-3-5-haiku-20241022`
  - `claude-3-opus-20240229`
  - And more (use `supernote list-models` to see all)

### Gemini (Google)
- `gemini-pro`: Gemini 2.5 Pro (powerful, high accuracy)
- `gemini-flash`: Gemini 2.5 Flash (fast, free tier available)
- Specific models:
  - `gemini-2.5-pro` (latest Pro)
  - `gemini-2.5-flash` (latest Flash)
  - `gemini-2.0-flash-exp`
  - `gemini-1.5-pro`
  - `gemini-1.5-flash`
  - `gemini-1.5-flash-8b`

### Ollama (Local)
- `ollama`: Auto-detects available vision models
- Supports: qwen2.5-vl, llama3.2-vision, llava, minicpm
- Specify model: `--model llama3.2-vision:11b`
- **Note:** Only models installed locally will be shown by `supernote list-models`

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
