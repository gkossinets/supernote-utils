#!/usr/bin/env python3
"""
Main CLI entry point for supernote-utils

Provides unified interface with subcommands for different operations.
"""

import argparse
import sys

from supernote_utils.__version__ import __version__


class TemperatureAction(argparse.Action):
    """Custom action to track when temperature is explicitly set"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        setattr(namespace, '_temperature_was_set', True)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="supernote",
        description="Python utilities for Supernote tablet handwriting transcription",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
environment variables:
  ANTHROPIC_API_KEY    API key for Claude models (required for Anthropic)
  GOOGLE_API_KEY       API key for Gemini models (required for Google)
  OLLAMA_BASE_URL      Base URL for Ollama server (default: http://localhost:11434)

examples:
  # List available models
  supernote list-models

  # Transcribe files (auto-detects format, uses Gemini Flash by default)
  supernote transcribe input.note -o output.md
  supernote transcribe input.pdf -o output.md
  supernote transcribe photo.png -o output.md

  # Transcribe with Claude Sonnet and custom batch size
  supernote transcribe input.pdf -o output.md -m claude-sonnet --batch-size 5

  # Convert .note to PDF
  supernote convert note2pdf input.note output.pdf

for more help on a specific command:
  supernote transcribe --help
  supernote convert note2pdf --help
        """
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Transcribe command
    transcribe_parser = subparsers.add_parser(
        "transcribe",
        help="Transcribe handwritten notes to text (auto-detects format)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
supported formats:
  .note          Supernote native format
  .pdf           Scanned or exported PDFs
  .png, .jpg     Single images
  .jpeg, .webp   Single images

examples:
  # Basic usage with default Gemini Flash model (auto-detects format)
  supernote transcribe input.note -o output.md
  supernote transcribe input.pdf -o output.md
  supernote transcribe photo.png -o output.md

  # Use Claude Sonnet model
  supernote transcribe input.pdf -o output.md -m claude-sonnet

  # Use specific model with custom temperature and batch size
  supernote transcribe input.note -o output.md -m anthropic:claude-3-opus-20240229 --temperature 0.1 --batch-size 5

  # Generate both markdown and PDF output (.note files only)
  supernote transcribe input.note -o output.md --pdf output.pdf

  # Output plain text instead of markdown
  supernote transcribe input.pdf -o output.txt --plain-text

  # Force rendering with custom DPI (PDF files only)
  supernote transcribe input.pdf -o output.md --force-render --dpi 200

  # Process one page at a time (disable batching)
  supernote transcribe input.note -o output.md --batch-size 1 --page-separator
        """
    )
    transcribe_parser.add_argument(
        "input",
        help="Path to input file (.note, .pdf, .png, .jpg, .jpeg, .webp)"
    )
    transcribe_parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Path to output markdown file (writes to stdout if not specified)"
    )
    transcribe_parser.add_argument(
        "-m", "--model",
        default="gemini-flash",
        metavar="MODEL",
        help="Model to use for transcription (default: gemini-flash). "
             "Format: 'provider:model' (e.g., anthropic:claude-3-opus-20240229, "
             "google:gemini-3-pro-preview, ollama:qwen2.5-vl:7b) or use shortcuts: "
             "claude, claude-sonnet, claude-haiku, gemini, gemini-flash, gemini-pro, ollama. "
             "Run 'supernote list-models' to see all available models"
    )
    transcribe_parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        metavar="FLOAT",
        action=TemperatureAction,
        help="LLM generation temperature controlling randomness (default: 0.2, but 1.0 for Gemini 3 models). "
             "Lower values (0.0-0.2) are more deterministic and reduce hallucinations. "
             "Range: 0.0 to 2.0"
    )
    transcribe_parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        metavar="N",
        help="Number of pages to process in a single API call (default: 3). "
             "Larger batches are faster and more cost-effective. "
             "Use 1 to disable batching and process pages individually. "
             "Only applies to multi-page formats (.note, .pdf)"
    )
    transcribe_parser.add_argument(
        "--page-separator",
        action="store_true",
        help="Insert page separator markers (---) between pages in the output. "
             "Only applies to multi-page formats (.note, .pdf)"
    )
    transcribe_parser.add_argument(
        "--plain-text",
        action="store_true",
        help="Output plain text by stripping all markdown formatting from the result"
    )
    transcribe_parser.add_argument(
        "--pdf",
        metavar="FILE",
        help="Also generate a PDF output file at the specified path. "
             "Only supported for .note input files"
    )
    transcribe_parser.add_argument(
        "--force-render",
        action="store_true",
        help="Force rendering of PDF pages to images instead of extracting embedded images. "
             "Useful for PDFs that don't have embedded images or have poor quality images. "
             "Only applies to PDF input files"
    )
    transcribe_parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        metavar="N",
        help="DPI (dots per inch) to use when rendering PDF pages to images (default: 150). "
             "Higher values produce better quality but larger images. "
             "Only used when --force-render is specified or when PDF has no embedded images. "
             "Only applies to PDF input files. "
             "Recommended values: 150 (default), 200 (high quality), 300 (very high quality)"
    )

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert between formats")
    convert_subparsers = convert_parser.add_subparsers(
        dest="conversion_type", help="Conversion type"
    )

    # Note to PDF
    note2pdf_parser = convert_subparsers.add_parser(
        "note2pdf",
        help="Convert .note file to PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Convert .note file to PDF
  supernote convert note2pdf input.note output.pdf
        """
    )
    note2pdf_parser.add_argument(
        "input",
        help="Path to input Supernote .note file"
    )
    note2pdf_parser.add_argument(
        "output",
        help="Path to output PDF file"
    )

    # List models command
    list_models_parser = subparsers.add_parser(
        "list-models",
        help="List available models from all providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # List all available models with shortcuts
  supernote list-models
        """
    )

    # Parse arguments
    args = parser.parse_args()

    # Handle no command
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate handler
    if args.command == "transcribe":
        from supernote_utils.cli.transcribe import transcribe_file
        transcribe_file(args)

    elif args.command == "convert":
        if args.conversion_type == "note2pdf":
            from supernote_utils.cli.note2pdf import convert_note_to_pdf
            convert_note_to_pdf(args)
        else:
            convert_parser.print_help()
            sys.exit(1)

    elif args.command == "list-models":
        from supernote_utils.cli.list_models import list_available_models
        list_available_models(args)


if __name__ == "__main__":
    main()
