# Supernote Utilities

Python utilities for managing and transcribing handwritten notes from Ratta Supernote tablets.

## Features

- **Universal file transcription** with auto-format detection (.note, .pdf, .png, .jpg, .jpeg, .webp)
- **LLM vision APIs** support (Claude, Gemini, OpenAI, Ollama)
- **Batch processing** for multi-page documents (faster, more cost-effective)
- **Temperature control** for Gemini and Ollama models
- **Local LLM support** via Ollama (privacy-focused, no API costs)
- **Model calibration scripts** for comparing transcription quality across models
- **PDF generation** from .note files

## Installation

### Requirements

- Python 3.11 or higher

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

# Add OpenAI support (optional)
pip install -e ".[openai]"
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

# For GPT (OpenAI; needs the [openai] extra)
export OPENAI_API_KEY="your-key-here"

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

# Use local Ollama model
supernote transcribe input.note -o output.md -m ollama:gemma4:26b-a4b

# Use a specific model
supernote transcribe input.pdf -o output.md -m anthropic:claude-opus-5-5

# Output plain text (strip Markdown formatting)
supernote transcribe input.pdf -m claude --plain-text -o output.txt

# Generate both Markdown and PDF (.note files only)
supernote transcribe input.note -o output.md --pdf output.pdf

# Multiple files → individual outputs in a directory
supernote transcribe -t markdown *.note -d transcribed/

# Adjust batch size for multi-page processing (default: 5; 1 for Ollama)
supernote transcribe input.pdf --batch-size 10 -o output.md

# Disable batch processing (process one page at a time)
supernote transcribe input.note --batch-size 1 --page-separator -o output.md

# Give the expected header date explicitly (default: read it from the filename)
supernote transcribe scan.pdf --date-hint 2026-09-20 -o output.md
```

**Batch Processing:** By default, multi-page documents (.note, .pdf) are processed in batches of 5 pages in a single API call. This is faster and more cost-effective than processing pages individually. The batch size can be adjusted with `--batch-size`, or disabled entirely by setting it to 1. Ollama models get one page per request unless you set `--batch-size`: small local models sometimes drop a whole page from a multi-page request without any error, and local requests cost nothing.

**Date headers:** Vision models often misread the year in a handwritten date header (e.g. "2026" as "2020" or "2024"), and may then shift the day or weekday so the wrong date looks consistent. The prompt tells the model to transcribe dates digit by digit and never reconcile a date with its weekday. When an input filename contains a date (`Pages 20260920.note`, `scan 2026-09-20.pdf`), it is also given to the model as a hint, and after transcription the first date in the output is checked against it. Mismatches, and weekdays that don't fit their date, are printed as warnings on stderr; the transcription itself is never changed, since a late-night entry may genuinely be headed with the next day. Use `--date-hint YYYY-MM-DD` to set the date for every input, or `--date-hint off` to disable both the hint and the check.

### Generate PDF from .note File

```bash
supernote convert input.note -o output.pdf
supernote convert input.note          # writes input.pdf next to input.note
```

## Temperature Settings

Temperature controls the randomness of LLM generation. The CLI default is `1.0`.

- **Gemini:** `1.0` (the default; do not lower — [Google recommends 1.0](https://ai.google.dev/gemini-api/docs/gemini-3#temperature) for Gemini 3 and later; lower values may cause looping or degraded output). The code sets Gemini 3+ models to 1.0 unless you override it, and prints a warning if you do.
- **Ollama:** `--temperature 0.5` (local models benefit from some flexibility to handle ambiguity)
- **Claude and OpenAI:** `--temperature` is ignored, with a warning. Current models from both providers use fixed sampling settings and reject the parameter.

Values above 1.0 increase hallucination risk and are not recommended for transcription.

## Model Calibration

`misc/calibrate.py` compares transcription quality across models and temperatures against a reference transcription. Provide any supported input format (`.note`, `.pdf`, `.png`, etc.) and a ground truth text file.

```bash
# Compare models on your own note against a transcription you have checked
python misc/calibrate.py --input my.note --reference reference.md
python misc/calibrate.py --input photo.png --reference ground_truth.txt

# Quick run (one temperature per model, fewer API calls)
python misc/calibrate.py --input my.note --reference reference.md --quick

# Ollama models only (no cloud API calls)
python misc/calibrate.py --input my.note --reference reference.md --ollama-only
```

Requires the test dependencies: `pip install -e ".[test]"`

Metrics calculated:
- **WER (Word Error Rate)**: Percentage of word-level errors
- **CER (Character Error Rate)**: Percentage of character-level errors
- **BLEU Score**: N-gram overlap with reference (0–1, higher is better)
- **Levenshtein Distance**: Raw edit distance
- **Semantic Similarity**: Meaning similarity using sentence embeddings (0–1, higher is better)

Results are saved to `misc/results/run_TIMESTAMP.md`

### Benchmark on your own handwriting

`misc/benchmark/` holds two texts to copy by hand, one Russian (`handwriting-ru.md`) and one English (`handwriting-en.md`). Each uses every letter of its alphabet, plus letter shapes that are easy to confuse in handwriting, unusual names, numbers, and lists of unrelated words that a model can't guess from context.

1. Write each text in its own note on your tablet and copy the `.note` files to your computer.
2. If your page differs from the text (a skipped word, a slip, ё written as е), edit a copy of the reference to match the page. The model is scored against what is written, not against what was meant.
3. Run the calibration script on each note:

```bash
python misc/calibrate.py --input ru.note --reference misc/benchmark/handwriting-ru.md
python misc/calibrate.py --input en.note --reference misc/benchmark/handwriting-en.md
```

`.note` files are gitignored, so your handwriting stays out of the repository.

## Supported Models

Run `supernote list-models` to see what's available in your environment (it prints the same shortcut table as below). Use either shortcuts or explicit `provider:model` format:

**Shortcuts:**

| Shortcut | Model |
|---|---|
| `gemini-flash` (default) | `google:gemini-3.8-flash` — fast, free tier available |
| `gemini`, `gemini-pro` | `google:gemini-4-hydrogen` — Google's recommended general-purpose model |
| `claude`, `claude-sonnet` | `anthropic:claude-sonnet-5-5` |
| `claude-haiku` | `anthropic:claude-haiku-5-5` — faster, cheaper |
| `claude-opus` | `anthropic:claude-opus-5-5` — most capable Claude, about 2× Sonnet's price |
| `gpt`, `openai` | `openai:gpt-6.2-sol` |
| `gpt-mini` | `openai:gpt-6-luna` — faster, cheaper |
| `ollama` | Auto-detected local vision model, preferring `gemma4:26b-a4b` |

**Explicit provider:model format:**
```bash
-m anthropic:claude-opus-5-5
-m google:gemini-4-carbon
-m openai:gpt-6.2-astra
-m ollama:gemma4:26b-a4b
```

**Note:** Only locally installed Ollama models appear in the output.

Ollama requests are sent one page at a time, with thinking turned off. Current local vision models (Gemma 4, Qwen 3.x) think by default, which made them several times slower on handwriting with no gain in accuracy.

## Project Structure

```
.
├── supernote_utils/         # Main package
│   ├── cli/                 # Command-line interface
│   ├── core/                # Transcription engine
│   ├── providers/           # LLM provider implementations
│   ├── sources/             # File source handlers
│   └── note_format/         # Supernote .note file format parser
├── test/                    # Unit tests (tests that need a .note fixture skip without one)
├── misc/                    # Model calibration
│   ├── calibrate.py             # Model comparison script
│   └── benchmark/               # Texts to copy by hand for a benchmark
└── pyproject.toml           # Package configuration
```

## Tips for Best Results

1. **Use the recommended temperature** for your provider (1.0 for Gemini, 0.5 for Ollama)
2. **Run the calibration script** (`misc/calibrate.py`) to find the best model for your handwriting
3. **For multilingual content**, Claude Sonnet and Gemini Pro tend to perform best
4. **For privacy-sensitive content**, use Ollama with local models
5. **Test multiple models** — different models excel at different handwriting styles and languages

## License

Apache License 2.0

## Credits

Built on top of [supernote-tool](https://github.com/jya-dev/supernote-tool) by jya.
