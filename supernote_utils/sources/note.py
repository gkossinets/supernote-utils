"""Handler for Supernote .note file format"""

import sys
from pathlib import Path
from typing import List

from PIL import Image

from supernote_utils.exceptions import FileFormatError

try:
    from supernotelib import parser
    from supernotelib.converter import ImageConverter
except ImportError:
    parser = None
    ImageConverter = None


class NoteFileHandler:
    """Handles extraction of images from Supernote .note files"""

    @staticmethod
    def extract_images(note_path: Path) -> List[Image.Image]:
        """
        Extract page images directly from .note file.

        Args:
            note_path: Path to .note file

        Returns:
            List of PIL Images (one per page)

        Raises:
            FileFormatError: If file cannot be read or is invalid format
        """
        if parser is None or ImageConverter is None:
            raise FileFormatError(
                "supernotelib not installed. Install with: pip install supernotelib"
            )

        if not note_path.exists():
            raise FileNotFoundError(f"Note file not found: {note_path}")

        print(f"Loading .note file: {note_path}", file=sys.stderr)

        try:
            # Load the notebook using supernotelib
            notebook = parser.load_notebook(str(note_path))

            # Create image converter
            converter = ImageConverter(notebook)

            # Extract images for all pages
            images = []
            total_pages = notebook.get_total_pages()
            print(f"Found {total_pages} pages in note file", file=sys.stderr)

            for i in range(total_pages):
                img = converter.convert(i)
                images.append(img)

            return images

        except Exception as e:
            raise FileFormatError(f"Error loading .note file: {e}") from e

    @staticmethod
    def generate_pdf(note_path: Path, output_path: Path) -> None:
        """
        Generate PDF from .note file using supernotelib.

        Args:
            note_path: Path to input .note file
            output_path: Path for output PDF file

        Raises:
            FileFormatError: If conversion fails
        """
        if parser is None:
            raise FileFormatError(
                "supernotelib not installed. Install with: pip install supernotelib"
            )

        try:
            with open(note_path, "rb") as f:
                metadata = parser.parse_metadata(f)
                notebook = parser.load(f, metadata)

            from supernotelib.converter import PdfConverter

            pdf_converter = PdfConverter(notebook)
            pdf_data = pdf_converter.convert(-1)  # -1 means all pages

            with open(output_path, "wb") as f:
                f.write(pdf_data)

            print(f"PDF saved to: {output_path}", file=sys.stderr)

        except Exception as e:
            raise FileFormatError(f"Error generating PDF: {e}") from e
