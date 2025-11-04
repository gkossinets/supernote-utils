#!/usr/bin/env python3
"""
CLI handler for note to PDF conversion
"""

import argparse
import sys
from pathlib import Path

from supernote_utils.sources.note import NoteFileHandler


def convert_note_to_pdf(args):
    """Handle note to PDF conversion from CLI args"""
    try:
        input_path = Path(args.input)
        output_path = Path(args.output)

        NoteFileHandler.generate_pdf(input_path, output_path)
        print(f"Successfully converted '{input_path}' to '{output_path}'")

    except KeyboardInterrupt:
        print("\nConversion interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for standalone note2pdf command"""
    parser = argparse.ArgumentParser(
        description="Convert a Supernote .note file to a PDF file."
    )

    parser.add_argument("input", metavar="input_file", type=str, help="Input .note file")

    parser.add_argument("output", metavar="output_file", type=str, help="Output .pdf file")

    args = parser.parse_args()
    convert_note_to_pdf(args)


if __name__ == "__main__":
    main()
