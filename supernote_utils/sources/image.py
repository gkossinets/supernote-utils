"""Image file handler for PNG, JPEG, WEBP formats"""

from pathlib import Path
from typing import List

from PIL import Image

from supernote_utils.exceptions import FileFormatError


class ImageFileHandler:
    """Handler for image files (PNG, JPEG, WEBP)"""

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

    @classmethod
    def extract_images(cls, path: Path, **kwargs) -> List[Image.Image]:
        """
        Load image file and return as single-item list.

        Args:
            path: Path to image file
            **kwargs: Ignored (for compatibility with other handlers)

        Returns:
            List containing single PIL Image

        Raises:
            FileFormatError: If file doesn't exist or isn't a valid image
        """
        if not path.exists():
            raise FileFormatError(f"Image file not found: {path}")

        if path.suffix.lower() not in cls.SUPPORTED_EXTENSIONS:
            raise FileFormatError(
                f"Unsupported image format: {path.suffix}. "
                f"Supported: {', '.join(sorted(cls.SUPPORTED_EXTENSIONS))}"
            )

        try:
            image = Image.open(path)
            # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            return [image]
        except Exception as e:
            raise FileFormatError(f"Failed to load image {path}: {str(e)}") from e

    @classmethod
    def is_supported(cls, path: Path) -> bool:
        """Check if file extension is supported"""
        return path.suffix.lower() in cls.SUPPORTED_EXTENSIONS
