#!/usr/bin/env python3
"""
Unified transcribe command handler
"""

import sys
from pathlib import Path

from supernote_utils.config import ProviderConfig, TranscriptionConfig
from supernote_utils.core.transcriber import Transcriber
from supernote_utils.providers import create_provider
from supernote_utils.sources import factory
from supernote_utils.sources.note import NoteFileHandler


def transcribe_file(args):
    """Handle unified transcription from CLI args"""
    try:
        input_path = Path(args.input)
        output_path = Path(args.output) if args.output else None

        # Validate file exists
        if not input_path.exists():
            print(f"Error: File not found: {input_path}", file=sys.stderr)
            sys.exit(1)

        # Detect format and get handler
        try:
            _, format_name = factory.get_handler(input_path)
            print(f"Detected format: {format_name}", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Validate format-specific options
        is_multipage = factory.is_multipage_format(input_path)
        ext = input_path.suffix.lower()

        # --dpi and --force-render only valid for PDF
        if ext != ".pdf":
            if hasattr(args, 'force_render') and args.force_render:
                print("Warning: --force-render only applies to PDF files, ignoring", file=sys.stderr)
            if hasattr(args, 'dpi') and args.dpi != 150:  # 150 is default
                print("Warning: --dpi only applies to PDF files, ignoring", file=sys.stderr)

        # --pdf output only valid for .note input
        if ext != ".note" and hasattr(args, 'pdf') and args.pdf:
            print("Error: --pdf output only supported for .note input files", file=sys.stderr)
            sys.exit(1)

        # Create provider configuration
        provider_config = ProviderConfig.from_env()

        # Check if temperature was explicitly set
        temperature_was_set = hasattr(args, '_temperature_was_set') and args._temperature_was_set

        # Create provider
        provider = create_provider(
            model_spec=args.model,
            config=provider_config,
            temperature=args.temperature,
            temperature_was_set=temperature_was_set,
        )

        # Create transcription config
        batch_size = args.batch_size if hasattr(args, 'batch_size') else 3
        if not is_multipage and batch_size > 1:
            # Silently treat as 1 for single images
            batch_size = 1

        transcription_config = TranscriptionConfig(
            temperature=args.temperature,
            page_separator=args.page_separator if hasattr(args, 'page_separator') and is_multipage else False,
            batch_size=batch_size,
        )

        # Extract images using appropriate handler
        extract_kwargs = {}
        if ext == ".pdf":
            extract_kwargs = {
                'force_render': args.force_render if hasattr(args, 'force_render') else False,
                'dpi': args.dpi if hasattr(args, 'dpi') else 150,
            }

        images = factory.extract_images(input_path, **extract_kwargs)

        # Create transcriber and process
        transcriber = Transcriber(provider, transcription_config)
        plain_text = args.plain_text if hasattr(args, 'plain_text') else False
        transcriber.transcribe_file(images, output_path, plain_text=plain_text)

        # Generate PDF if requested (only for .note files)
        if ext == ".note" and hasattr(args, 'pdf') and args.pdf:
            pdf_path = Path(args.pdf)
            print(f"\nGenerating PDF: {pdf_path}", file=sys.stderr)
            NoteFileHandler.generate_pdf(input_path, pdf_path)

    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
