#!/usr/bin/env python3
"""
Main CLI entry point for supernote-utils

Provides unified interface with subcommands for different operations.
"""

import argparse
import sys

from supernote_utils.__version__ import __version__


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

  # Transcribe a .note file (uses Gemini Flash by default)
  supernote transcribe note input.note -o output.md

  # Transcribe a PDF with Claude Sonnet and custom batch size
  supernote transcribe pdf input.pdf -o output.md -m claude-sonnet --batch-size 10

  # Convert .note to PDF
  supernote convert note2pdf input.note output.pdf

for more help on a specific command:
  supernote transcribe note --help
  supernote transcribe pdf --help
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
        "transcribe", help="Transcribe handwritten notes to text"
    )
    transcribe_subparsers = transcribe_parser.add_subparsers(
        dest="source_type", help="Input source type"
    )

    # Transcribe note
    note_parser = transcribe_subparsers.add_parser(
        "note",
        help="Transcribe .note file to markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Basic usage with default Gemini Flash model
  supernote transcribe note input.note -o output.md

  # Use Claude Sonnet model
  supernote transcribe note input.note -o output.md -m claude-sonnet

  # Use specific model with custom temperature and batch size
  supernote transcribe note input.note -o output.md -m anthropic:claude-3-opus-20240229 --temperature 0.1 --batch-size 10

  # Generate both markdown and PDF output
  supernote transcribe note input.note -o output.md --pdf output.pdf

  # Process one page at a time (disable batching)
  supernote transcribe note input.note -o output.md --batch-size 1 --page-separator
        """
    )
    note_parser.add_argument(
        "input",
        help="Path to input Supernote .note file"
    )
    note_parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Path to output markdown file (writes to stdout if not specified)"
    )
    note_parser.add_argument(
        "-m", "--model",
        default="gemini-flash",
        metavar="MODEL",
        help="Model to use for transcription (default: gemini-flash). "
             "Format: 'provider:model' (e.g., anthropic:claude-3-opus-20240229, "
             "google:gemini-3-pro-preview, ollama:qwen2.5-vl:7b) or use shortcuts: "
             "claude, claude-sonnet, claude-haiku, gemini, gemini-flash, gemini-pro, ollama. "
             "Run 'supernote list-models' to see all available models"
    )
    note_parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        metavar="FLOAT",
        help="LLM generation temperature controlling randomness (default: 0.2). "
             "Lower values (0.0-0.2) are more deterministic and reduce hallucinations. "
             "Range: 0.0 to 2.0"
    )
    note_parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        metavar="N",
        help="Number of pages to process in a single API call (default: 10). "
             "Larger batches are faster and more cost-effective. "
             "Use 1 to disable batching and process pages individually"
    )
    note_parser.add_argument(
        "--page-separator",
        action="store_true",
        help="Insert page separator markers (---) between pages in the output"
    )
    note_parser.add_argument(
        "--pdf",
        metavar="FILE",
        help="Also generate a PDF output file at the specified path"
    )

    # Transcribe PDF
    pdf_parser = transcribe_subparsers.add_parser(
        "pdf",
        help="Transcribe PDF to markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Basic usage with default Gemini Flash model
  supernote transcribe pdf input.pdf -o output.md

  # Use Claude Sonnet model
  supernote transcribe pdf input.pdf -o output.md -m claude-sonnet

  # Output plain text instead of markdown
  supernote transcribe pdf input.pdf -o output.txt --plain-text

  # Force rendering with custom DPI (for PDFs without embedded images)
  supernote transcribe pdf input.pdf -o output.md --force-render --dpi 200

  # Process one page at a time (disable batching)
  supernote transcribe pdf input.pdf -o output.md --batch-size 1
        """
    )
    pdf_parser.add_argument(
        "input",
        help="Path to input PDF file"
    )
    pdf_parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Path to output markdown file (writes to stdout if not specified)"
    )
    pdf_parser.add_argument(
        "-m", "--model",
        default="gemini-flash",
        metavar="MODEL",
        help="Model to use for transcription (default: gemini-flash). "
             "Format: 'provider:model' (e.g., anthropic:claude-3-opus-20240229, "
             "google:gemini-3-pro-preview, ollama:qwen2.5-vl:7b) or use shortcuts: "
             "claude, claude-sonnet, claude-haiku, gemini, gemini-flash, gemini-pro, ollama. "
             "Run 'supernote list-models' to see all available models"
    )
    pdf_parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        metavar="FLOAT",
        help="LLM generation temperature controlling randomness (default: 0.2). "
             "Lower values (0.0-0.2) are more deterministic and reduce hallucinations. "
             "Range: 0.0 to 2.0"
    )
    pdf_parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        metavar="N",
        help="Number of pages to process in a single API call (default: 10). "
             "Larger batches are faster and more cost-effective. "
             "Use 1 to disable batching and process pages individually"
    )
    pdf_parser.add_argument(
        "--page-separator",
        action="store_true",
        help="Insert page separator markers (---) between pages in the output"
    )
    pdf_parser.add_argument(
        "--plain-text",
        action="store_true",
        help="Output plain text by stripping all markdown formatting from the result"
    )
    pdf_parser.add_argument(
        "--force-render",
        action="store_true",
        help="Force rendering of PDF pages to images instead of extracting embedded images. "
             "Useful for PDFs that don't have embedded images or have poor quality images"
    )
    pdf_parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        metavar="N",
        help="DPI (dots per inch) to use when rendering PDF pages to images (default: 150). "
             "Higher values produce better quality but larger images. "
             "Only used when --force-render is specified or when PDF has no embedded images. "
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
        if args.source_type == "note":
            from supernote_utils.cli.note2text import transcribe_note_file
            transcribe_note_file(args)
        elif args.source_type == "pdf":
            from supernote_utils.cli.script2text import transcribe_pdf_file
            transcribe_pdf_file(args)
        else:
            transcribe_parser.print_help()
            sys.exit(1)

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
