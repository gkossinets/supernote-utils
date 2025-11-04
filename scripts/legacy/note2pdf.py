#!/usr/bin/env python3
"""
Convert a Supernote .note file to a PDF file.
"""

import argparse
import sys
from supernotelib import parser
from supernotelib import converter

def main():
    """Main function"""
    # Create the parser
    arg_parser = argparse.ArgumentParser(description='Convert a Supernote .note file to a PDF file.')

    # Add the arguments
    arg_parser.add_argument('input_file',
                           metavar='input_file',
                           type=str,
                           help='the input .note file')
    arg_parser.add_argument('output_file',
                           metavar='output_file',
                           type=str,
                           help='the output .pdf file')

    # Execute the parse_args() method
    args = arg_parser.parse_args()

    input_file = args.input_file
    output_file = args.output_file

    try:
        with open(input_file, 'rb') as f:
            metadata = parser.parse_metadata(f)
            notebook = parser.load(f, metadata)

        pdf_converter = converter.PdfConverter(notebook)
        pdf_data = pdf_converter.convert(-1) # -1 means all pages

        with open(output_file, 'wb') as f:
            f.write(pdf_data)

        print(f"Successfully converted '{input_file}' to '{output_file}'")

    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_file}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
