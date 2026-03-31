#!/usr/bin/env python3
"""
Calibration script for comparing transcription quality across models and temperatures.

Runs a set of model/temperature configurations against a user-provided input file and
a ground-truth reference transcription. Produces a ranked markdown report with WER,
CER, BLEU, Levenshtein distance, and semantic similarity.

Requires the [test] extras:
    pip install -e ".[test]"
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    import Levenshtein
    import nltk
    from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError as e:
    print(f"Missing required package: {e}", file=sys.stderr)
    print("Install with: pip install -e '.[test]'", file=sys.stderr)
    sys.exit(1)

# Allow running directly from misc/ without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from supernote_utils.config import ProviderConfig, TranscriptionConfig
from supernote_utils.core.transcriber import Transcriber
from supernote_utils.providers import create_provider
from supernote_utils.providers.ollama import OllamaProvider
from supernote_utils.sources import factory

# Download NLTK tokenizer data if not already present
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class TranscriptionMetrics:
    """Calculate quality metrics between a hypothesis and a reference text."""

    def __init__(self):
        print("Loading semantic similarity model (all-mpnet-base-v2)...", file=sys.stderr)
        self._model = SentenceTransformer("all-mpnet-base-v2")

    def calculate_all(self, reference: str, hypothesis: str) -> Dict:
        """Return dict of wer, cer, bleu, levenshtein, semantic_sim."""
        if not hypothesis:
            return {
                "wer": 100.0,
                "cer": 100.0,
                "bleu": 0.0,
                "levenshtein": len(reference),
                "semantic_sim": 0.0,
            }

        ref_words = reference.split()
        hyp_words = hypothesis.split()

        wer = round(
            Levenshtein.distance(" ".join(ref_words), " ".join(hyp_words))
            / max(len(ref_words), 1)
            * 100,
            2,
        )
        cer = round(
            Levenshtein.distance(reference, hypothesis) / max(len(reference), 1) * 100,
            2,
        )

        ref_tokens = nltk.word_tokenize(reference.lower())
        hyp_tokens = nltk.word_tokenize(hypothesis.lower())
        bleu = (
            round(
                sentence_bleu(
                    [ref_tokens],
                    hyp_tokens,
                    smoothing_function=SmoothingFunction().method1,
                ),
                4,
            )
            if hyp_tokens
            else 0.0
        )

        lev = Levenshtein.distance(reference, hypothesis)

        ref_emb = self._model.encode([reference])
        hyp_emb = self._model.encode([hypothesis])
        sem = round(float(cosine_similarity(ref_emb, hyp_emb)[0][0]), 4)

        return {"wer": wer, "cer": cer, "bleu": bleu, "levenshtein": lev, "semantic_sim": sem}


# ---------------------------------------------------------------------------
# Transcription runner
# ---------------------------------------------------------------------------

def run_transcription(
    input_path: Path,
    model_spec: str,
    temperature: float,
) -> tuple[str, float, str]:
    """
    Transcribe input_path with model_spec at temperature.

    Returns:
        (text, runtime_seconds, error_message)
        error_message is "" on success.
    """
    start = time.time()
    try:
        provider_config = ProviderConfig.from_env()
        provider = create_provider(model_spec, provider_config, temperature)
        is_multipage = factory.is_multipage_format(input_path)
        images = factory.extract_images(input_path)
        transcription_config = TranscriptionConfig(
            temperature=temperature,
            batch_size=5 if is_multipage else 1,
        )
        transcriber = Transcriber(provider, transcription_config)
        text = transcriber.transcribe_images(images, output=None, plain_text=True)
        return text.strip(), time.time() - start, ""
    except Exception as e:
        return "", time.time() - start, str(e)


# ---------------------------------------------------------------------------
# Configuration builder
# ---------------------------------------------------------------------------

def build_test_configs(
    quick: bool,
    ollama_only: bool,
    extra_models: List[str],
) -> List[Dict]:
    """Return list of dicts with 'model' (model_spec string) and 'temperature'."""
    configs = []

    if not ollama_only:
        if quick:
            configs.extend([
                {"model": "claude-sonnet", "temperature": 0.7},
                {"model": "gemini-flash", "temperature": 1.0},
            ])
        else:
            configs.extend([
                # Claude — recommended default 0.7
                {"model": "claude-sonnet", "temperature": 0.2},
                {"model": "claude-sonnet", "temperature": 0.5},
                {"model": "claude-sonnet", "temperature": 0.7},
                {"model": "claude-haiku",  "temperature": 0.2},
                {"model": "claude-haiku",  "temperature": 0.5},
                {"model": "claude-haiku",  "temperature": 0.7},
                # Gemini — recommended default 1.0
                {"model": "gemini-flash",  "temperature": 0.5},
                {"model": "gemini-flash",  "temperature": 1.0},
                {"model": "gemini-pro",    "temperature": 0.5},
                {"model": "gemini-pro",    "temperature": 1.0},
            ])

    # Auto-detect locally installed Ollama vision models
    ollama_models = OllamaProvider.list_available_models()
    if ollama_models:
        print(f"Found {len(ollama_models)} Ollama vision model(s): {', '.join(ollama_models)}", file=sys.stderr)
    for model_name in ollama_models:
        model_spec = f"ollama:{model_name}"
        if quick:
            configs.append({"model": model_spec, "temperature": 0.5})
        else:
            configs.extend([
                {"model": model_spec, "temperature": 0.3},
                {"model": model_spec, "temperature": 0.5},
                {"model": model_spec, "temperature": 0.7},
            ])

    # Extra models requested on the command line
    for spec in extra_models:
        configs.append({"model": spec, "temperature": 1.0})

    return configs


def _is_available(model_spec: str) -> bool:
    """Return False if the required API key is missing for this model spec."""
    m = model_spec.lower()
    if m.startswith("anthropic") or m in ("claude", "claude-sonnet", "claude-haiku"):
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    if m.startswith("google") or m.startswith("gemini"):
        return bool(os.getenv("GOOGLE_API_KEY"))
    # Ollama: always attempt — availability was already checked at detection time
    return True


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    results: List[Dict],
    input_path: Path,
    reference_path: Path,
    output_file: Path,
) -> None:
    """Write a markdown calibration report to output_file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    successful = [r for r in results if r["error"] is None]

    lines = [
        "# Transcription Calibration Results",
        "",
        f"**Date:** {timestamp}  ",
        f"**Input:** `{input_path}`  ",
        f"**Reference:** `{reference_path}`  ",
        f"**Configurations tested:** {len(results)}  ",
        "",
    ]

    if successful:
        best_wer = min(r["wer"] for r in successful)
        best_bleu = max(r["bleu"] for r in successful)
        best_sem = max(r["semantic_sim"] for r in successful)
        bw = next(r for r in successful if r["wer"] == best_wer)
        bb = next(r for r in successful if r["bleu"] == best_bleu)
        bs = next(r for r in successful if r["semantic_sim"] == best_sem)

        lines += [
            "## Summary",
            "",
            f"- **Successful:** {len(successful)}/{len(results)}",
            f"- **Best WER:** {best_wer}% — `{bw['model']}` @ temp={bw['temperature']}",
            f"- **Best BLEU:** {best_bleu} — `{bb['model']}` @ temp={bb['temperature']}",
            f"- **Best semantic similarity:** {best_sem} — `{bs['model']}` @ temp={bs['temperature']}",
            "",
        ]

    sorted_results = sorted(
        results,
        key=lambda r: (r["error"] is not None, r["wer"] if r["wer"] is not None else 999),
    )

    lines += [
        "## Results",
        "",
        "| Model | Temp | WER (%) | CER (%) | BLEU | Levenshtein | Semantic | Runtime (s) | Error |",
        "|-------|------|---------|---------|------|-------------|----------|-------------|-------|",
    ]

    for r in sorted_results:
        wer  = f"{r['wer']:.2f}"         if r["wer"]           is not None else "N/A"
        cer  = f"{r['cer']:.2f}"         if r["cer"]           is not None else "N/A"
        bleu = f"{r['bleu']:.4f}"        if r["bleu"]          is not None else "N/A"
        lev  = str(r["levenshtein"])     if r["levenshtein"]   is not None else "N/A"
        sem  = f"{r['semantic_sim']:.4f}" if r["semantic_sim"] is not None else "N/A"
        rt   = f"{r['runtime']:.1f}"
        err  = r["error"] or "-"
        lines.append(
            f"| `{r['model']}` | {r['temperature']} | {wer} | {cer} | {bleu} | {lev} | {sem} | {rt} | {err} |"
        )

    lines += [
        "",
        "## Metric Descriptions",
        "",
        "- **WER (Word Error Rate):** Lower is better. Percentage of word-level errors.",
        "- **CER (Character Error Rate):** Lower is better. Percentage of character-level errors.",
        "- **BLEU:** Higher is better (0–1). N-gram overlap with reference.",
        "- **Levenshtein:** Lower is better. Raw character edit distance.",
        "- **Semantic Similarity:** Higher is better (0–1). Cosine similarity of sentence embeddings.",
        "",
    ]

    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Results saved to: {output_file}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    _MISC = Path(__file__).parent
    _ROOT = _MISC.parent

    parser = argparse.ArgumentParser(
        description="Compare transcription quality across models and temperatures.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Default: use built-in test fixture against misc/test-transcribed.md
  python misc/calibrate.py

  # Custom input (any supported format) and reference
  python misc/calibrate.py --input scan.pdf --reference reference.md
  python misc/calibrate.py --input photo.png --reference ground_truth.txt

  # Quick run (one temperature per model, faster)
  python misc/calibrate.py --quick

  # Ollama models only (no cloud API calls)
  python misc/calibrate.py --ollama-only

  # Add a specific model to the standard set
  python misc/calibrate.py --models anthropic:claude-3-opus-20240229
        """,
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=_ROOT / "test" / "test.note",
        metavar="FILE",
        help="Input file to transcribe (.note, .pdf, .png, .jpg, .jpeg, .webp). "
             "Default: test/test.note",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=_MISC / "test-transcribed.md",
        metavar="FILE",
        help="Ground truth transcription (.md or .txt). "
             "Default: misc/test-transcribed.md",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_MISC / "results",
        metavar="DIR",
        help="Directory where result reports are written. Default: misc/results/",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="One temperature per model (fewer API calls)",
    )
    parser.add_argument(
        "--ollama-only",
        action="store_true",
        help="Test only locally available Ollama vision models",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        metavar="MODEL_SPEC",
        default=[],
        help="Additional model specs to include (e.g., anthropic:claude-3-opus-20240229)",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not args.reference.exists():
        print(f"Error: Reference file not found: {args.reference}", file=sys.stderr)
        sys.exit(1)

    reference_text = args.reference.read_text(encoding="utf-8").strip()
    metrics_calc = TranscriptionMetrics()

    configs = build_test_configs(
        quick=args.quick,
        ollama_only=args.ollama_only,
        extra_models=args.models,
    )

    if not configs:
        print(
            "Error: No models to test. "
            "Set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or start Ollama with a vision model.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nInput:     {args.input}", file=sys.stderr)
    print(f"Reference: {args.reference}", file=sys.stderr)
    print(f"Configs:   {len(configs)}\n", file=sys.stderr)

    results = []
    for i, cfg in enumerate(configs, 1):
        model_spec = cfg["model"]
        temperature = cfg["temperature"]

        print(f"[{i}/{len(configs)}] {model_spec}  temp={temperature}", file=sys.stderr)

        if not _is_available(model_spec):
            print("  Skipped: API key not set", file=sys.stderr)
            results.append({
                "model": model_spec,
                "temperature": temperature,
                "runtime": 0.0,
                "error": "API key not set",
                "wer": None, "cer": None, "bleu": None,
                "levenshtein": None, "semantic_sim": None,
            })
            continue

        text, runtime, error = run_transcription(args.input, model_spec, temperature)

        if error:
            print(f"  Error: {error}", file=sys.stderr)
            results.append({
                "model": model_spec,
                "temperature": temperature,
                "runtime": round(runtime, 2),
                "error": error,
                "wer": None, "cer": None, "bleu": None,
                "levenshtein": None, "semantic_sim": None,
            })
            continue

        m = metrics_calc.calculate_all(reference_text, text)
        print(
            f"  WER={m['wer']}%  CER={m['cer']}%  "
            f"BLEU={m['bleu']}  Sem={m['semantic_sim']}  ({runtime:.1f}s)",
            file=sys.stderr,
        )
        results.append({
            "model": model_spec,
            "temperature": temperature,
            "runtime": round(runtime, 2),
            "error": None,
            **m,
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output_dir / f"run_{timestamp}.md"
    generate_report(results, args.input, args.reference, output_file)

    print("\nDone.", file=sys.stderr)


if __name__ == "__main__":
    main()
