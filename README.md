# Supernote Utilities

Python utilities for managing and transcribing handwritten notes from Ratta Supernote tablets.

## Features

- **Direct .note to Markdown transcription** using LLM vision APIs (Claude, Gemini, Ollama)
- **PDF to Markdown transcription** for scanned handwritten documents
- **Temperature control** for deterministic transcription (reduce hallucinations)
- **Local LLM support** via Ollama (privacy-focused, no API costs)
- **Comprehensive test suite** for comparing transcription quality across models
- **PDF generation** from .note files using supernotelib

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# For PDF rendering support (optional)
# On macOS:
brew install poppler

# On Ubuntu/Debian:
sudo apt-get install poppler-utils
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

### Convert .note Files to Markdown

```bash
# Basic usage with Claude Sonnet
python note2text.py input.note --md output.md

# Use Gemini with custom temperature
python note2text.py input.note --md output.md --api gemini-flash --temperature 0.2

# Use local Ollama model (privacy-focused, no API costs)
python note2text.py input.note --md output.md --api ollama --temperature 0.1

# Generate both Markdown and PDF
python note2text.py input.note --md output.md --pdf output.pdf

# Add page separators
python note2text.py input.note --md output.md --page-separator
```

### Convert PDF to Markdown

```bash
# Transcribe scanned PDF
python script2text.py input.pdf --out output.md

# Use different model and temperature
python script2text.py input.pdf --api gemini-pro --temperature 0.3 --out output.md

# Output plain text (strip Markdown formatting)
python script2text.py input.pdf --plain-text --out output.txt
```

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

### Claude (Anthropic)
- `claude-sonnet`: Claude Sonnet 4.5 (powerful, high accuracy)
- `claude-haiku`: Claude Haiku 4.5 (faster, cost-effective)

### Gemini (Google)
- `gemini-pro`: Gemini 2.5 Pro (powerful, high accuracy)
- `gemini-flash`: Gemini 2.5 Flash (fast, free tier available)

### Ollama (Local)
- `ollama`: Auto-detects available vision models
- Supports: qwen2.5-vl, llama3.2-vision, llava, minicpm
- Specify model: `--model llama3.2-vision:11b`

## Project Structure

```
.
├── note2text.py              # Convert .note to Markdown
├── script2text.py            # Convert PDF to Markdown
├── note2pdf.py               # Convert .note to PDF
├── transcription_prompt.py   # Shared transcription prompt
├── test_transcription.py     # Test suite
├── requirements.txt          # Python dependencies
├── supernotelib/            # Supernote file format library
└── test/                    # Test files
    ├── test.note            # Sample handwritten note
    ├── test-transcribed.md  # Reference transcription
    └── results/             # Test results
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
