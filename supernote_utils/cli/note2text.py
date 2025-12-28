#!/usr/bin/env python3
"""
CLI handler for note to text conversion
"""

import argparse
import sys
from pathlib import Path

from supernote_utils.config import ProviderConfig, TranscriptionConfig
from supernote_utils.core.transcriber import Transcriber
from supernote_utils.providers import create_provider
from supernote_utils.sources.note import NoteFileHandler


class TemperatureAction(argparse.Action):
    """Custom action to track when temperature is explicitly set"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        setattr(namespace, '_temperature_was_set', True)


def transcribe_note_file(args):
    """Handle note transcription from CLI args"""
    try:
        input_path = Path(args.input)
        output_path = Path(args.output) if args.output else None
        pdf_path = Path(args.pdf) if hasattr(args, 'pdf') and args.pdf else None

        # Create provider configuration
        provider_config = ProviderConfig.from_env()

        # Check if temperature was explicitly set (not default 0.2)
        temperature_was_set = hasattr(args, '_temperature_was_set') and args._temperature_was_set

        # Create provider
        provider = create_provider(
            model_spec=args.model,
            config=provider_config,
            temperature=args.temperature,
            temperature_was_set=temperature_was_set,
        )

        # Create transcription config
        transcription_config = TranscriptionConfig(
            temperature=args.temperature,
            page_separator=args.page_separator if hasattr(args, 'page_separator') else False,
            batch_size=args.batch_size if hasattr(args, 'batch_size') else 3,
        )

        # Extract images from note file
        images = NoteFileHandler.extract_images(input_path)

        # Create transcriber and process
        transcriber = Transcriber(provider, transcription_config)
        transcriber.transcribe_file(images, output_path, plain_text=False)

        # Generate PDF if requested
        if pdf_path:
            print(f"\nGenerating PDF: {pdf_path}", file=sys.stderr)
            NoteFileHandler.generate_pdf(input_path, pdf_path)

    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for standalone note2text command"""
    parser = argparse.ArgumentParser(
        description="Convert Supernote .note files to Markdown using LLM vision APIs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  ANTHROPIC_API_KEY - Required for Claude models
  GOOGLE_API_KEY    - Required for Gemini models
  (Ollama requires local installation at http://localhost:11434)

Examples:
  # Basic usage with Gemini Flash (default)
  %(prog)s input.note --output output.md

  # Use Claude Sonnet model
  %(prog)s input.note -o output.md -m claude-sonnet

  # Use specific Anthropic model
  %(prog)s input.note -o output.md -m anthropic:claude-3-opus-20240229

  # Use specific Gemini model
  %(prog)s input.note -o output.md -m google:gemini-3-pro-preview

  # Use local Ollama model
  %(prog)s input.note -o output.md -m ollama:qwen2.5-vl:7b

  # Generate both Markdown and PDF
  %(prog)s input.note -o output.md --pdf output.pdf
        """,
    )

    parser.add_argument("input", type=str, help="Input .note file from Supernote")

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output Markdown file (prints to stdout if not specified)",
    )

    parser.add_argument(
        "--pdf", type=str, default=None, help="Output PDF file (optional)"
    )

    parser.add_argument(
        "-m", "--model",
        default="gemini-flash",
        help="Model to use (default: gemini-flash). Format: 'provider:model' (e.g., anthropic:claude-3-opus-20240229, "
             "google:gemini-3-pro-preview, ollama:qwen2.5-vl:7b) or shortcuts: "
             "claude, claude-sonnet, claude-haiku, gemini, gemini-flash, gemini-pro, ollama"
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        action=TemperatureAction,
        help="Temperature for generation (default: 0.2, but 1.0 for Gemini 3 models). Range: 0.0-2.0",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Number of pages to process in a single API call (default: 3, use 1 to disable batching)",
    )

    parser.add_argument(
        "--page-separator", action="store_true", help="Add page separator markers in output"
    )

    args = parser.parse_args()
    transcribe_note_file(args)


if __name__ == "__main__":
    main()
