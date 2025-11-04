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
        "note", help="Transcribe .note file to markdown"
    )
    note_parser.add_argument("input", help="Input .note file")
    note_parser.add_argument("-o", "--output", help="Output markdown file (stdout if not specified)")
    note_parser.add_argument(
        "--api",
        choices=["claude", "claude-haiku", "claude-sonnet", "gemini", "gemini-flash", "gemini-pro", "ollama"],
        default="claude-sonnet",
        help="LLM API provider (default: claude-sonnet)",
    )
    note_parser.add_argument(
        "--model",
        help="Specific model name (use 'supernote list-models' to see available models)"
    )
    note_parser.add_argument(
        "--temperature", type=float, default=0.2, help="Generation temperature (default: 0.2)"
    )
    note_parser.add_argument("--page-separator", action="store_true", help="Add page separators")
    note_parser.add_argument("--pdf", help="Also generate PDF output")

    # Transcribe PDF
    pdf_parser = transcribe_subparsers.add_parser(
        "pdf", help="Transcribe PDF to markdown"
    )
    pdf_parser.add_argument("input", help="Input PDF file")
    pdf_parser.add_argument("-o", "--output", help="Output markdown file (stdout if not specified)")
    pdf_parser.add_argument(
        "--api",
        choices=["claude", "claude-haiku", "claude-sonnet", "gemini", "gemini-flash", "gemini-pro", "ollama"],
        default="claude-sonnet",
        help="LLM API provider (default: claude-sonnet)",
    )
    pdf_parser.add_argument(
        "--model",
        help="Specific model name (use 'supernote list-models' to see available models)"
    )
    pdf_parser.add_argument(
        "--temperature", type=float, default=0.2, help="Generation temperature (default: 0.2)"
    )
    pdf_parser.add_argument("--page-separator", action="store_true", help="Add page separators")
    pdf_parser.add_argument("--plain-text", action="store_true", help="Strip markdown formatting")
    pdf_parser.add_argument("--force-render", action="store_true", help="Force page rendering")
    pdf_parser.add_argument("--dpi", type=int, default=150, help="DPI for rendering (default: 150)")

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert between formats")
    convert_subparsers = convert_parser.add_subparsers(
        dest="conversion_type", help="Conversion type"
    )

    # Note to PDF
    note2pdf_parser = convert_subparsers.add_parser(
        "note2pdf", help="Convert .note file to PDF"
    )
    note2pdf_parser.add_argument("input", help="Input .note file")
    note2pdf_parser.add_argument("output", help="Output PDF file")

    # List models command
    list_models_parser = subparsers.add_parser(
        "list-models", help="List available models from all providers"
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
