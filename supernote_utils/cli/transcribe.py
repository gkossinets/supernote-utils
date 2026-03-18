#!/usr/bin/env python3
"""
Unified transcribe command handler
"""

import sys
from pathlib import Path
from typing import List, Optional

from supernote_utils.config import ProviderConfig, TranscriptionConfig
from supernote_utils.core.transcriber import Transcriber
from supernote_utils.providers import create_provider
from supernote_utils.sources import factory
from supernote_utils.sources.note import NoteFileHandler


FORMAT_EXTENSIONS = {
    'markdown': '.md',
    'plain-text': '.txt',
    'pdf': '.pdf',
}


def _build_provider(args):
    """Create a provider instance from CLI args."""
    provider_config = ProviderConfig.from_env()
    temperature_was_set = hasattr(args, '_temperature_was_set') and args._temperature_was_set
    return create_provider(
        model_spec=args.model,
        config=provider_config,
        temperature=args.temperature,
        temperature_was_set=temperature_was_set,
    )


def _build_transcription_config(args, is_multipage: bool) -> TranscriptionConfig:
    """Create a TranscriptionConfig from CLI args."""
    batch_size = args.batch_size if hasattr(args, 'batch_size') else 3
    if not is_multipage and batch_size > 1:
        batch_size = 1
    return TranscriptionConfig(
        temperature=args.temperature,
        page_separator=args.page_separator if hasattr(args, 'page_separator') and is_multipage else False,
        batch_size=batch_size,
    )


def _get_extract_kwargs(args, input_path: Path) -> dict:
    """Return kwargs for factory.extract_images based on file type."""
    if input_path.suffix.lower() == '.pdf':
        return {
            'force_render': args.force_render if hasattr(args, 'force_render') else False,
            'dpi': args.dpi if hasattr(args, 'dpi') else 150,
        }
    return {}


def _warn_format_specific(args, input_path: Path) -> None:
    """Emit warnings for format-specific flags used with wrong file types."""
    ext = input_path.suffix.lower()
    if ext != '.pdf':
        if hasattr(args, 'force_render') and args.force_render:
            print("Warning: --force-render only applies to PDF files, ignoring", file=sys.stderr)
        if hasattr(args, 'dpi') and args.dpi != 150:
            print("Warning: --dpi only applies to PDF files, ignoring", file=sys.stderr)


def _generate_pdf(input_path: Path, output_path: Path) -> None:
    """Generate a visual PDF from a .note file."""
    if input_path.suffix.lower() != '.note':
        raise ValueError(f"PDF output only supported for .note files, got: {input_path.suffix}")
    print(f"Generating PDF: {output_path}", file=sys.stderr)
    NoteFileHandler.generate_pdf(input_path, output_path)


def _determine_target_format(args) -> str:
    """Resolve the effective target format from args."""
    target_format = getattr(args, 'format', 'markdown') or 'markdown'
    # --plain-text is a backward-compat alias for -t plain-text
    if getattr(args, 'plain_text', False) and target_format == 'markdown':
        target_format = 'plain-text'
    return target_format


def _transcribe_combined(
    args,
    input_paths: List[Path],
    output_path: Path,
    target_format: str,
    plain_text: bool,
) -> None:
    """Transcribe all inputs and write combined result to a single output file."""
    if target_format == 'pdf':
        if len(input_paths) > 1:
            print(
                "Error: PDF format does not support combining multiple inputs into a single output file.",
                file=sys.stderr,
            )
            sys.exit(1)
        # Single .note → single PDF
        _generate_pdf(input_paths[0], output_path)
        return

    # Validate all files exist before starting any API calls
    for p in input_paths:
        if not p.exists():
            print(f"Error: File not found: {p}", file=sys.stderr)
            sys.exit(1)

    provider = _build_provider(args)
    all_texts: List[str] = []

    for input_path in input_paths:
        try:
            _, format_name = factory.get_handler(input_path)
            print(f"Processing {input_path} (format: {format_name})...", file=sys.stderr)
            _warn_format_specific(args, input_path)
            is_multipage = factory.is_multipage_format(input_path)
            transcription_config = _build_transcription_config(args, is_multipage)
            extract_kwargs = _get_extract_kwargs(args, input_path)
            images = factory.extract_images(input_path, **extract_kwargs)
            transcriber = Transcriber(provider, transcription_config)
            text = transcriber.transcribe_images(images, output=None, plain_text=plain_text)
            all_texts.append(text.strip())
        except Exception as e:
            # Abort: output would be incomplete without every file
            print(f"Error processing {input_path}: {e}", file=sys.stderr)
            sys.exit(1)

    combined = "\n\n---\n\n".join(all_texts)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(combined)
        f.write('\n')
    print(f"Transcription saved to: {output_path}", file=sys.stderr)


def _transcribe_per_file(
    args,
    input_paths: List[Path],
    target_format: str,
    target_dir: Optional[Path],
    plain_text: bool,
) -> None:
    """Transcribe each input file to its own output, continuing past errors."""
    # Check all files exist before starting
    missing = [p for p in input_paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"Error: File not found: {p}", file=sys.stderr)
        sys.exit(1)

    # Warn about --pdf flag in multi-file mode (it targets a single fixed path)
    multi = len(input_paths) > 1
    if multi and getattr(args, 'pdf', None):
        print("Warning: --pdf is not supported with multiple input files, ignoring.", file=sys.stderr)

    # Build provider once; not needed for PDF-only output
    provider = _build_provider(args) if target_format != 'pdf' else None

    ext = FORMAT_EXTENSIONS[target_format]
    errors: List[Path] = []

    for input_path in input_paths:
        out_path = (target_dir if target_dir else input_path.parent) / (input_path.stem + ext)
        try:
            _, format_name = factory.get_handler(input_path)
            print(f"Processing {input_path} (format: {format_name}) → {out_path}", file=sys.stderr)

            if target_format == 'pdf':
                _generate_pdf(input_path, out_path)
            else:
                _warn_format_specific(args, input_path)
                is_multipage = factory.is_multipage_format(input_path)
                transcription_config = _build_transcription_config(args, is_multipage)
                extract_kwargs = _get_extract_kwargs(args, input_path)
                images = factory.extract_images(input_path, **extract_kwargs)
                transcriber = Transcriber(provider, transcription_config)
                transcriber.transcribe_file(images, out_path, plain_text=plain_text)

                # --pdf side-effect: also generate visual PDF (single-file mode only)
                if not multi and input_path.suffix.lower() == '.note' and getattr(args, 'pdf', None):
                    pdf_path = Path(args.pdf)
                    print(f"Generating PDF: {pdf_path}", file=sys.stderr)
                    NoteFileHandler.generate_pdf(input_path, pdf_path)

        except Exception as e:
            print(f"Error processing {input_path}: {e}", file=sys.stderr)
            errors.append(input_path)

    if errors:
        print(f"\nFailed to process {len(errors)} file(s):", file=sys.stderr)
        for p in errors:
            print(f"  {p}", file=sys.stderr)
        sys.exit(1)


def transcribe_file(args):
    """Handle transcription from CLI args, supporting multiple inputs."""
    try:
        input_paths = [Path(p) for p in args.input]
        output_path = Path(args.output) if args.output else None
        target_dir = Path(args.directory) if getattr(args, 'directory', None) else None
        target_format = _determine_target_format(args)
        plain_text = (target_format == 'plain-text')

        if output_path and target_dir:
            print("Error: -o/--output and -d/--directory are mutually exclusive.", file=sys.stderr)
            sys.exit(1)

        if target_dir:
            target_dir.mkdir(parents=True, exist_ok=True)

        if output_path:
            _transcribe_combined(args, input_paths, output_path, target_format, plain_text)
        else:
            _transcribe_per_file(args, input_paths, target_format, target_dir, plain_text)

    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
