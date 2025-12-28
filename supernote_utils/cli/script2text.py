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
            model_spec=args.model,
            config=provider_config,
            temperature=args.temperature,
        )

        # Create transcription config
        transcription_config = TranscriptionConfig(
            temperature=args.temperature,
            page_separator=args.page_separator if hasattr(args, 'page_separator') else False,
            batch_size=args.batch_size if hasattr(args, 'batch_size') else 3,
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
  # Process with Gemini Flash (default)
  %(prog)s input.pdf -o output.md

  # Process with Claude Sonnet
  %(prog)s input.pdf -m claude-sonnet -o result.md

  # Process with specific Google model
  %(prog)s input.pdf -m google:gemini-3-pro-preview --temperature 0.3 -o result.md

  # Process with Ollama local model
  %(prog)s input.pdf -m ollama:llama3.2-vision:11b -o result.md

  # Output plain text
  %(prog)s input.pdf -m claude --plain-text -o result.txt
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

    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Number of pages to process in a single API call (default: 3, use 1 to disable batching)",
    )

    args = parser.parse_args()
    transcribe_pdf_file(args)


if __name__ == "__main__":
    main()
