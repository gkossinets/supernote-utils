"""Unified source file handler factory"""

from pathlib import Path
from typing import Dict, List, Tuple, Type

from PIL import Image

from supernote_utils.exceptions import FileFormatError
from supernote_utils.sources.image import ImageFileHandler
from supernote_utils.sources.note import NoteFileHandler
from supernote_utils.sources.pdf import PDFFileHandler


# Mapping of file extensions to handler classes
SUPPORTED_EXTENSIONS: Dict[str, Tuple[Type, str]] = {
    ".note": (NoteFileHandler, "Supernote"),
    ".pdf": (PDFFileHandler, "PDF"),
    ".png": (ImageFileHandler, "PNG image"),
    ".jpg": (ImageFileHandler, "JPEG image"),
    ".jpeg": (ImageFileHandler, "JPEG image"),
    ".webp": (ImageFileHandler, "WebP image"),
}


def get_handler(path: Path) -> Tuple[Type, str]:
    """
    Get appropriate handler class for file format.

    Args:
        path: Path to input file

    Returns:
        Tuple of (handler_class, format_name)

    Raises:
        FileFormatError: If file extension is not supported
    """
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        supported_list = ", ".join(sorted(SUPPORTED_EXTENSIONS.keys()))
        raise FileFormatError(
            f"Unsupported file format: {ext}\n"
            f"Supported formats: {supported_list}"
        )

    return SUPPORTED_EXTENSIONS[ext]


def extract_images(path: Path, **kwargs) -> List[Image.Image]:
    """
    Extract images from file using appropriate handler.

    Args:
        path: Path to input file
        **kwargs: Format-specific options (force_render, dpi, etc.)

    Returns:
        List of PIL Images

    Raises:
        FileFormatError: If file format is unsupported or file cannot be read
    """
    handler_class, _ = get_handler(path)
    return handler_class.extract_images(path, **kwargs)


def is_multipage_format(path: Path) -> bool:
    """Check if file format supports multiple pages"""
    ext = path.suffix.lower()
    return ext in {".note", ".pdf"}


def get_format_name(path: Path) -> str:
    """Get human-readable format name"""
    _, format_name = get_handler(path)
    return format_name
