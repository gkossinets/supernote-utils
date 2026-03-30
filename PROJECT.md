# PROJECT.md — supernote-utils

Plans, architecture decisions, progress, and next steps.

---

## Current State (v0.2.0)

The CLI is feature-complete for the core use case: transcribing handwritten notes from Supernote tablets (and other image sources) to Markdown using LLM vision APIs.

### What works
- `supernote transcribe` — unified command with auto-format detection (.note, .pdf, .png, .jpg, .webp)
- Multi-file input with `-d` (output directory) or `-o` (combined output file)
- `-t` flag for output type: `markdown`, `plain-text`, `pdf`
- Providers: Anthropic (Claude), Google (Gemini), Ollama (local), OpenAI-compatible
- Batch processing (default: 3 pages per API call); configurable with `--batch-size`
- `supernote convert note2pdf` for visual PDF rendering from .note files
- `supernote list-models` queries all providers for available models
- Test suite in `test/` with NLP metrics (WER, CER, BLEU, semantic similarity)

### Known limitations
- Proper nouns with diacritics: 5-10% error rate depending on model
- Cyrillic content: higher error rates, model-dependent
- PDF text extraction falls back to image rendering when no embedded images exist

---

## Architecture Decisions

**Three-layer design** (sources → providers → core):
- Sources convert files to `List[PIL.Image]` — adding new input formats requires only a new handler in `sources/`
- Providers send images to an LLM and return text — adding a new provider requires only subclassing `VisionProvider`
- `Transcriber` in core orchestrates batching, page separators, streaming to file — format-agnostic

**BYOK (bring your own key)** — no bundled API credits. Provider keys come from env vars. Default model is `gemini-flash-latest` (best free-tier option).

**Temperature default: 1.0** — set at the provider level; users can override with `--temperature`. Lower values (0.0–0.2) reduce hallucinations for transcription but add determinism tradeoffs.

**Batch processing default: 3 pages** — batching images into a single API call is faster and cheaper than per-page calls. Providers that support multi-image input handle this natively; others fall back to serial calls.

---

## Model Quality Findings

From test runs on the `test/test.note` benchmark (3-page mixed-language document):

| Provider | Relative Quality | Notes |
|----------|-----------------|-------|
| Claude Sonnet | Best overall | Best for multilingual, proper nouns |
| Gemini Pro | Near-Claude | Fast, good quality, free tier shrinking |
| qwen2.5-vl:7b (Ollama) | Best local | ~85-90% vs cloud, fully private |
| llama3.2-vision (Ollama) | Good local | Q8 quantization recommended |
| minicpm-v | Decent local | Specialized in document understanding |

Recommended temperatures: Claude 0.2–0.3, Gemini 0.2, Ollama 0.1.

---

## Future Direction

### Near-term CLI improvements
- Resume/checkpoint support for large documents (partial transcription on failure)
- HTML report output from test suite
- Cost estimation per transcription run
- Two-pass verification (run two models, highlight differences)

### Desktop app (planned, not started)
A GUI application targeting non-technical Supernote users. Key decisions made:

- **Stack**: Tauri + React (cross-platform, small bundle, App Store ready)
- **Backend**: Rust (port Python logic for clean distribution)
- **Distribution**: Mac App Store + Microsoft Store + direct GitHub releases
- **Pricing**: Free + tip jar (Calibre model — fully functional, optional donations)
- **API model**: BYOK with a guided onboarding wizard; Gemini recommended as default
- **Input formats**: .note, PDF, PNG, JPEG from v1.0
- **Target users**: Supernote owners who don't want to use a CLI

The Python CLI (`supernote-utils`) would remain as the reference implementation and developer tool; the desktop app would ship a bundled Rust port of the core logic.

---

## Test Files

`test/test.note` — 3-page benchmark document containing:
- Mixed languages: English, Russian, French, German proper nouns
- Formatting: highlights, stars, headers, tables, lists, poetry with specific line breaks

`test/test-transcribed.md` — manually verified reference transcription used for metric calculation.

`test/outputs/` — per-model transcription outputs from benchmark runs.
`test/results/` — timestamped comparison reports from `test_transcription2.py`.
