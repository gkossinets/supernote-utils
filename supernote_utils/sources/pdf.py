"""Handler for PDF file format"""

import io
import sys
from pathlib import Path
from typing import List

from PIL import Image

from supernote_utils.exceptions import FileFormatError

try:
    import PyPDF2
    from pdf2image import convert_from_path
except ImportError:
    PyPDF2 = None
    convert_from_path = None


class PDFFileHandler:
    """Handles extraction of images from PDF files"""

    @staticmethod
    def extract_embedded_images(pdf_path: Path) -> List[Image.Image]:
        """
        Extract embedded images directly from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of PIL Images extracted from PDF
        """
        if PyPDF2 is None:
            raise FileFormatError(
                "PyPDF2 not installed. Install with: pip install PyPDF2"
            )

        images = []
        try:
            with open(pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    if page.images:
                        for image_file_object in page.images:
                            try:
                                img = Image.open(io.BytesIO(image_file_object.data))
                                # Filter out small images (likely icons/decorations)
                                if img.width > 100 and img.height > 100:
                                    images.append(img)
                            except Exception:
                                continue

            if images:
                print(
                    f"Successfully extracted {len(images)} embedded images",
                    file=sys.stderr,
                )

        except Exception as e:
            print(f"Could not extract embedded images: {str(e)}", file=sys.stderr)

        return images

    @staticmethod
    def render_pages(pdf_path: Path, dpi: int = 150) -> List[Image.Image]:
        """
        Render PDF pages to images.

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for rendering (default 150)

        Returns:
            List of PIL Images (one per page)

        Raises:
            FileFormatError: If rendering fails
        """
        if convert_from_path is None:
            raise FileFormatError(
                "pdf2image not installed. Install with: pip install pdf2image"
            )

        print(f"Rendering PDF pages at {dpi} DPI...", file=sys.stderr)

        try:
            images = convert_from_path(pdf_path, dpi=dpi)
            print(f"Rendered {len(images)} pages", file=sys.stderr)
            return images

        except Exception as e:
            raise FileFormatError(f"Error rendering PDF: {e}") from e

    @staticmethod
    def extract_images(
        pdf_path: Path, force_render: bool = False, dpi: int = 150
    ) -> List[Image.Image]:
        """
        Get images from PDF, either by extraction or rendering.

        Args:
            pdf_path: Path to PDF file
            force_render: If True, always render pages instead of extracting
            dpi: Resolution for rendering if needed

        Returns:
            List of PIL Images

        Raises:
            FileFormatError: If extraction/rendering fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Try embedded image extraction first (unless forced to render)
        if not force_render:
            images = PDFFileHandler.extract_embedded_images(pdf_path)
            if images:
                return images
            print(
                "No suitable embedded images found, rendering pages instead...",
                file=sys.stderr,
            )

        # Render pages
        return PDFFileHandler.render_pages(pdf_path, dpi)
