# PROJECT.md — supernote-utils

Plans, architecture decisions, progress, and next steps.

---

## Current State (v0.3.0)

The CLI is feature-complete for the core use case: transcribing handwritten notes from Supernote tablets (and other image sources) to Markdown using LLM vision APIs.

### What works
- `supernote transcribe` — unified command with auto-format detection (.note, .pdf, .png, .jpg, .webp)
- Multi-file input with `-d` (output directory) or `-o` (combined output file)
- `-t` flag for output type: `markdown`, `plain-text`, `pdf`
- Providers: Anthropic (Claude), Google (Gemini, via `google-genai`), OpenAI (Responses API, optional `[openai]` extra), Ollama (local)
- Batch processing (default: 5 pages per API call); configurable with `--batch-size`
- `supernote convert input.note [-o output.pdf]` for visual PDF rendering from .note files
- `supernote list-models` queries all providers for available models
- Offline unit test suite in `test/` (provider SDK clients are mocked; no API keys needed)
- `misc/calibrate.py` scores transcription quality against a reference (WER, CER, BLEU, Levenshtein, semantic similarity)

### Known limitations
- Proper nouns with diacritics: 5-10% error rate depending on model
- Cyrillic content: higher error rates, model-dependent
- PDF text extraction falls back to image rendering when no embedded images exist
- Handwritten date headers: models misread year digits (2026 as 2020/2024) and may then shift the day or weekday to make the wrong date consistent. Mitigated by the date rule, the filename date hint, and the header check (below); not eliminated

### Repository and release (2026-11-26)
- **v0.3.0 released**: the first GitHub release, an annotated tag `v0.3.0`. Install with `pip install "git+https://github.com/gkossinets/supernote-utils.git@v0.3.0"`. Later docs-only commits on `main` aren't in the tag.
- **No CI.** GitHub Actions is turned off in the repo settings, and `.github/` is gone: the Gemini CLI workflow templates were removed first, then the short-lived `ci.yml`. Before committing, run `pytest` and `ruff check supernote_utils/` locally; all tests are offline.
- **No secrets or variables** remain in the repo settings. `GEMINI_API_KEY` and `GOOGLE_GENAI_USE_GCA` were deleted with the Gemini workflows that used them.
- **Only `main`** exists on GitHub. The four merged `claude/...` branches (PRs #5, #7, #9, #10) were deleted. Their history is in `main` and the merged PRs.
- **No examples at the top of the README**, at the owner's request: no handwriting images and no sample transcription. The removed screenshot is still in the v0.3.0 tag and in git history (commit `7612895`).

---

## Architecture Decisions

**Three-layer design** (sources → providers → core):
- Sources convert files to `List[PIL.Image]` — adding new input formats requires only a new handler in `sources/`
- Providers send images to an LLM and return text — adding a new provider requires only subclassing `VisionProvider`
- `Transcriber` in core orchestrates batching, page separators, streaming to file — format-agnostic

**BYOK (bring your own key)** — no bundled API credits. Provider keys come from env vars. Default model is the `gemini-flash` shortcut (`gemini-3.8-flash`, best free-tier option).

**Temperature default: 1.0** — set at the provider level; users can override with `--temperature`. Lower values (0.0–0.2) reduce hallucinations for transcription but add determinism tradeoffs.

**No temperature for Claude or OpenAI (2026-11-26):** current Claude models accept only default sampling, and anthropic SDK 2.x has no `temperature` parameter. Current OpenAI models return a 400 if it is sent. Both providers drop the value and warn when `--temperature` is set. Gemini (3+ pinned to 1.0 unless overridden) and Ollama still use it.

**Dependency refresh (2026-11-26):** `google-generativeai` → `google-genai`, PyPDF2 → `pypdf` (PyPDF2 missed embedded images that pypdf finds), Python floor 3.11 (numpy and google-genai require it). Model IDs were checked against each provider's live model list; the old Gemini preview IDs and `gemini-flash-latest` returned 404.

**Date headers (2026-10-29):** In a real journal corpus (~250 daily pages, Gemini Flash), about 11% of transcribed date headers had a wrong year, and in several the day or weekday had been shifted to agree with the misread year. The prompt's "Logic is Law" rule invited that reconciliation. Three changes: (1) a strict rule in the prompt to transcribe dates, times, and numbers digit by digit and never reconcile a date with its weekday, with "Logic is Law" limited to words; (2) `--date-hint` (default `auto`) passes the date from the input filename to the model as a hint, explicitly subordinate to clear handwriting; (3) after transcription, `core/dates.py` compares the first date in the output with the expected date and checks the weekday, printing warnings to stderr. The text is never corrected automatically, because late-night entries can legitimately carry the next day's date.

**Batch processing default: 5 pages** — batching images into a single API call is faster and cheaper than per-page calls. Providers that support multi-image input handle this natively; others fall back to serial calls.

---

## Model Quality Findings

From test runs on the `test/test.note` benchmark (2-page mixed-language document):

| Provider | Relative Quality | Notes |
|----------|-----------------|-------|
| Claude Sonnet | Best overall | Best for multilingual, proper nouns |
| Gemini Pro | Near-Claude | Fast, good quality, free tier shrinking |
| qwen2.5-vl:7b (Ollama) | Best local | ~85-90% vs cloud, fully private |
| llama3.2-vision (Ollama) | Good local | Q8 quantization recommended |
| minicpm-v | Decent local | Specialized in document understanding |

Recommended temperatures: Claude 0.2–0.3, Gemini 0.2, Ollama 0.1. (Historical: Claude no longer accepts a temperature, and Gemini 3+ should stay at 1.0.)

2026-11-26 spot check on `test/test.note`: Gemini 3.8 Flash was close to the reference (minor list/table formatting). Claude Sonnet 5.5 was accurate on English but misread several Russian words in the Issa poems ("Вечерний голос", "Ленечка") and the name "Pflaumm".

2026-11-26 Claude comparison on `test/test.note`, two runs each, character error rate (CER) after stripping Markdown formatting:

| Model | CER, all text | CER, Russian only | Russian errors |
|---|---|---|---|
| Claude Opus 5.5 (`claude-opus`) | 0.6%, 0.6% | 2.0%, 2.0% | Лепешка for Лепешки; Переварилась (run 1); Вечерний звон for гонг (run 2) |
| Claude Sonnet 5.5 (`claude`) | 6.3%, 1.7% | 5.2%, 4.0% | Лененька/Леночка, Переваривал, зайлусь/зайдусь, Привевкой/Привидкой |
| Gemini 3.8 Flash (one run) | 0.6% | 0.4% | none of substance |
| OpenAI `gpt` → gpt-6.2-sol (one run) | 0.7% | 0.8% | Перевариваю for Переваривая |
| OpenAI `gpt-mini` → gpt-6-luna (one run) | 3.8% | 13.9% | Скажи, Ленечке, Перевариваю, and more |

Opus also got "Pflaum" right where Sonnet wrote "Pflaumm" both times. Sonnet's 6.3% run is mostly layout: it wrote the closing table as two separate columns. Both OpenAI models read "1980" as "1960" (the Fassbinder line), the kind of digit error the date rule targets. For Cyrillic-heavy notes, Gemini Flash (the default) and `gpt` are the most accurate, `claude-opus` is the better Claude option, and `gpt-mini` is the weakest. The OpenAI runs (2026-11-26) were the first live test of the OpenAI provider; it worked end to end through the CLI.

---

## Future Direction

### Public handwriting benchmark (to check)
The author's handwriting samples stay out of the repo, so the benchmark notes can't be published. To make the benchmark reproducible, look for public-domain (or openly licensed) handwritten Russian and English pages with known transcriptions, e.g. scanned letters or manuscripts in archives, or handwriting datasets with permissive licenses. They should be similar to Supernote pages: lined, one writer per page, everyday script, and contain enough Cyrillic (all 33 letters, look-alike runs such as и/ш/т/л/м) to separate models. The reference texts in `misc/benchmark/` show what the private benchmark covers.

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

`test/test.note` — 2-page benchmark document, kept local (removed from the repo 2026-11-27 because it is the author's handwriting; it remains in older commits). Tests that need it skip when it is missing. It contains:
- Mixed languages: English, Russian, French, German proper nouns
- Formatting: highlights, stars, headers, tables, lists, poetry with specific line breaks

`misc/test-transcribed.md` — manually verified reference transcription of `test/test.note`, used by `misc/calibrate.py`.

`misc/benchmark/handwriting-ru.md`, `handwriting-en.md` — reference texts for a 2-page benchmark note (one Russian page, one English page) that covers every letter of both alphabets, look-alike letter runs, unusual names, numbers, and context-free word lists. The texts match the handwritten pages exactly, including the writer's slips ("neigbor", "щетку" without ё). The handwritten `.note` itself is kept local and gitignored, like all handwriting samples.

`misc/results/` — timestamped comparison reports written by `misc/calibrate.py` (`run_TIMESTAMP.md`).

`test/results/` — gitignored; holds old local reports from the removed `test_transcription2.py`.
