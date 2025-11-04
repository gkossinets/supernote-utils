#!/usr/bin/env python3
"""
CLI handler for PDF to text conversion
"""

import argparse
import sys
from pathlib import Path

from supernote_utils.config import ProviderConfig, TranscriptionConfig
from supernote_utils.core.transcriber import Transcriber
from supernote_utils.providers import create_provider
from supernote_utils.sources.pdf import PDFFileHandler


def transcribe_pdf_file(args):
    """Handle PDF transcription from CLI args"""
    try:
        input_path = Path(args.input)
        output_path = Path(args.output) if args.output else None

        # Create provider configuration
        provider_config = ProviderConfig.from_env()

        # Create provider
        provider = create_provider(
            provider_name=args.api,
            config=provider_config,
            model=args.model if hasattr(args, 'model') and args.model else None,
            temperature=args.temperature,
        )

        # Create transcription config
        transcription_config = TranscriptionConfig(
            temperature=args.temperature,
            page_separator=args.page_separator if hasattr(args, 'page_separator') else False,
        )

        # Extract images from PDF
        force_render = args.force_render if hasattr(args, 'force_render') else False
        dpi = args.dpi if hasattr(args, 'dpi') else 150
        images = PDFFileHandler.extract_images(input_path, force_render=force_render, dpi=dpi)

        # Create transcriber and process
        transcriber = Transcriber(provider, transcription_config)
        plain_text = args.plain_text if hasattr(args, 'plain_text') else False
        transcriber.transcribe_file(images, output_path, plain_text=plain_text)

    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for standalone script2text command"""
    parser = argparse.ArgumentParser(
        description="Extract handwritten text from PDF using LLM APIs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  ANTHROPIC_API_KEY - Required for Claude models
  GOOGLE_API_KEY    - Required for Gemini models
  (Ollama requires local installation at http://localhost:11434)

Examples:
  # Process with Claude Sonnet
  %(prog)s input.pdf --api claude-sonnet --temperature 0.2

  # Process with Gemini and save as plain text
  %(prog)s input.pdf --api gemini --plain-text -o result.txt

  # Process with Ollama local model
  %(prog)s input.pdf --api ollama --model llama3.2-vision:11b -o result.md
        """,
    )

    parser.add_argument("input", type=str, help="Input PDF file to process")

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (prints to stdout if not specified)",
    )

    parser.add_argument(
        "--api",
        choices=[
            "claude",
            "claude-haiku",
            "claude-sonnet",
            "gemini",
            "gemini-flash",
            "gemini-pro",
            "ollama",
        ],
        default="claude-sonnet",
        help="LLM API service to use (default: claude-sonnet)",
    )

    parser.add_argument(
        "--model", type=str, default=None, help="Specific model name to use (optional)"
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Temperature for generation (0.0-2.0, default: 0.2)",
    )

    parser.add_argument(
        "--page-separator", action="store_true", help="Add a separator between pages"
    )

    parser.add_argument(
        "--plain-text",
        action="store_true",
        help="Output plain text by stripping Markdown formatting",
    )

    parser.add_argument(
        "--force-render",
        action="store_true",
        help="Force rendering of pages instead of extracting embedded images",
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI to use when rendering pages (default: 150)",
    )

    args = parser.parse_args()
    transcribe_pdf_file(args)


if __name__ == "__main__":
    main()
