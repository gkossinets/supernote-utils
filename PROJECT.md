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
- qwen3-vl:8b ignores Ollama's `think=False` and reasons anyway (17–21K characters per request), so it is slow; the provider can't turn that off
- PDF text extraction falls back to image rendering when no embedded images exist
- Handwritten date headers: models misread year digits (2026 as 2020/2024) and may then shift the day or weekday to make the wrong date consistent. Mitigated by the date rule, the filename date hint, and the header check (below); not eliminated

### Repository and release (2026-11-26)
- **v0.3.0 released**: the first GitHub release, an annotated tag `v0.3.0`. Install with `pip install "git+https://github.com/gkossinets/supernote-utils.git@v0.3.0"`. Later docs-only commits on `main` aren't in the tag.
- **No CI.** GitHub Actions is turned off in the repo settings, and `.github/` is gone: the Gemini CLI workflow templates were removed first, then the short-lived `ci.yml`. Before committing, run `pytest` and `ruff check supernote_utils/` locally; all tests are offline.
- **No secrets or variables** remain in the repo settings. `GEMINI_API_KEY` and `GOOGLE_GENAI_USE_GCA` were deleted with the Gemini workflows that used them.
- **Only `main`** exists on GitHub. The four merged `claude/...` branches (PRs #5, #7, #9, #10) were deleted. Their history is in `main` and the merged PRs.
- **No examples at the top of the README.**

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

**Ollama (2026-11-27):** requests are sent with `think=False`. Current local vision models (Gemma 4, Qwen 3.x) think by default; on the test note, thinking made them 5–12x slower with no gain in accuracy (gemma4:31b: 563 s → 47 s for two pages). Auto-detection (`-m ollama`, `list-models`) uses each model's reported `vision` capability instead of matching names, and prefers `gemma4:26b-a4b` (speed), then `gemma4:26b`, `gemma4:31b-mlx` (best Cyrillic accuracy, ~3x slower), `gemma4:e4b-it-q8_0`, `gemma4:latest`, else the first vision model. Ollama sends one page per request unless `--batch-size` is given (`DEFAULT_BATCH_SIZE` on the provider class; cloud providers keep 5): gemma4:latest and qwen3.5:9b each silently dropped a whole page in 2 of 4 two-page requests, while single-page requests lost nothing and were no slower for the larger models. The `ollama` client floor is 0.5.0, the first release with `think`.

**Batch processing default: 5 pages** — batching images into a single API call is faster and cheaper than per-page calls. Providers that support multi-image input handle this natively; others fall back to serial calls.

---

## Model Quality Findings

The test note referred to below is a 2-page document in English and Russian (prose, a short poem, a name table, highlights and stars).

2026-11-26 spot check on the test note: Gemini 3.8 Flash was close to the reference (minor list/table formatting). Claude Sonnet 5.5 was accurate on English but misread several Russian words in the Issa poems ("Вечерний голос", "Ленечка") and the name "Pflaumm".

2026-11-26 Claude comparison on the test note, two runs each, character error rate (CER) after stripping Markdown formatting:

| Model | CER, all text | CER, Russian only | Russian errors |
|---|---|---|---|
| Claude Opus 5.5 (`claude-opus`) | 0.6%, 0.6% | 2.0%, 2.0% | Лепешка for Лепешки; Переварилась (run 1); Вечерний звон for гонг (run 2) |
| Claude Sonnet 5.5 (`claude`) | 6.3%, 1.7% | 5.2%, 4.0% | Лененька/Леночка, Переваривал, зайлусь/зайдусь, Привевкой/Привидкой |
| Gemini 3.8 Flash (one run) | 0.6% | 0.4% | none of substance |
| OpenAI `gpt` → gpt-6.2-sol (one run) | 0.7% | 0.8% | Перевариваю for Переваривая |
| OpenAI `gpt-mini` → gpt-6-luna (one run) | 3.8% | 13.9% | Скажи, Ленечке, Перевариваю, and more |

Opus also got "Pflaum" right where Sonnet wrote "Pflaumm" both times. Sonnet's 6.3% run is mostly layout: it wrote the closing table as two separate columns. Both OpenAI models read "1980" as "1960" (the Fassbinder line), the kind of digit error the date rule targets. For Cyrillic-heavy notes, Gemini Flash (the default) and `gpt` are the most accurate, `claude-opus` is the better Claude option, and `gpt-mini` is the weakest. The OpenAI runs (2026-11-26) were the first live test of the OpenAI provider; it worked end to end through the CLI.

2026-11-27 local models via Ollama 0.40.17 on an M1 Max, thinking off, CER after stripping Markdown. Ranges span 2–4 runs; times exclude the first run, which includes loading the model.

| Model | Time, 2 pages | CER, all text | CER, Russian only |
|---|---|---|---|
| gemma4:26b-a4b (MoE, ~4B active, nvfp4) | 7 s | 2.3–2.7% | 7.0–8.5% |
| gemma4:31b (older Q4_K_M build) | 47 s | 1.6–2.2% | 4.5–5.5% |
| gemma4:e4b-it-q8_0 | 10 s | 5.6–6.0% | 13.6–15.1% |
| gemma4:latest (e4b, nvfp4) | 6 s | 5.5–8.3% | 16.6–25.1% |
| qwen3.5:9b | 9 s | 5.6–8.9% | 22–33% |
| muse-glimmer:30b-mlx | ~200 s | 4.8–6.6% | 15–27% |
| qwen3.8:27b | 25 s | 9.1–12.1% | 23–30% |
| gemma4:12b | 15 s | 9.1–11.5% | 40–46% |
| qwen3-vl:8b (thinks regardless) | 224–345 s | 16–18% | 47–54% |

- **Default:** gemma4:26b-a4b runs as fast as the 4–9B models with about half their Russian errors. gemma4:31b is slightly more accurate but 7x slower.
- **No measurable effect:** temperature (0.1, 0.5, 1.0); a prompt paragraph on Russian and look-alike Cyrillic letters; one page per request instead of two.
- **Quantization:** on the test note the 8-bit e4b looked better than the 4-bit default, but on the larger benchmark (one page per request) the two were the same.
- **Image tokens:** current Gemma 4 builds get ~1100 tokens per page. The older gemma4:31b build was capped at 512 by llama.cpp's batch size (`cap image_max_tokens ... to 512` in the server log); `num_batch: 2048` lifts the cap, with no clear accuracy gain. Ollama ignores an `image_max_tokens` option.
- **Caveat:** the Russian part of the test note has only 28 words (199 characters), so one misread word moves the Russian CER by about 3 points.

2026-11-27 larger benchmark: the two `misc/benchmark/` texts written out by hand (one Russian page with ~580 letters, one English page), one page per request, thinking off, temperature 1.0, 4 runs each:

| Model | Time, 2 pages | CER, Russian | CER, English |
|---|---|---|---|
| gemma4:31b-mlx | 30 s | 3.9–4.9% | 1.0–1.3% |
| gemma4:26b-a4b | 10.5 s | 7.1–9.1% | 1.0–1.1% |
| qwen3.5:9b | 12.7 s | 13.4–18.9% | 1.1–1.8% |
| gemma4:e4b-it-q8_0 | 14.5 s | 19.0–21.0% | 2.0–2.4% |
| gemma4:latest | 8.5 s | 19.7–21.3% | 3.0–4.2% |

- **Both pages in one request inflates Russian scores** on this benchmark: the pages are translations of each other, and models used the English page to fill in Russian words (gemma4:26b-a4b: 3.7–5.9% Russian CER with both pages, 7.1–9.1% alone). Score one page per request.
- **gemma4:31b-mlx vs the older gemma4:31b build** (two-page requests): 3.7–3.9% vs 5.5–6.8% Russian CER, 30 s vs 72 s.
- **Still no measurable effect** on gemma4:26b-a4b from temperature 0.5 vs 1.0 or from the Russian prompt paragraph; the paragraph also did nothing for e4b.
- **Dropped pages:** see the Ollama decision above. gemma4:26b-a4b and both 31b builds never dropped a page in 24 two-page requests.

---

## Future Direction

### Public handwriting benchmark (to check)
The repo ships no handwriting, so nobody can rerun the benchmarks as they are. To make them reproducible, look for public-domain (or openly licensed) handwritten Russian and English pages with known transcriptions, e.g. scanned letters or manuscripts in archives, or handwriting datasets with permissive licenses. They should be similar to Supernote pages: lined, one writer per page, everyday script, and contain enough Cyrillic (all 33 letters, look-alike runs such as и/ш/т/л/м) to separate models. The texts in `misc/benchmark/` show what such pages should cover.

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

Tests that parse `.note` files look for `test/test.note`. No `.note` file is distributed with the repository, so on a fresh clone those tests skip; everything else runs offline.

`misc/benchmark/handwriting-ru.md`, `handwriting-en.md` — texts to copy by hand for a benchmark (one Russian page, one English page). They cover every letter of both alphabets, look-alike letter runs, unusual names, numbers, and lists of unrelated words that can't be guessed from context. To score a model, the reference must match the handwritten page exactly, slips included; keep such page-matched copies and the `.note` files in `misc/benchmark/local/` (gitignored). See README, "Benchmark on your own handwriting".

`misc/results/` — timestamped comparison reports written by `misc/calibrate.py` (`run_TIMESTAMP.md`).

`test/results/` — gitignored; holds old local reports from the removed `test_transcription2.py`.
