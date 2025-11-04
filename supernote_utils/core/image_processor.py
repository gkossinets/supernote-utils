"""Image processing utilities for transcription"""

import re
from typing import List

from PIL import Image


class ImageProcessor:
    """Handles image processing for transcription"""

    @staticmethod
    def strip_markdown_code_blocks(text: str) -> str:
        """
        Remove markdown code block wrapper if present.

        Args:
            text: Text that may be wrapped in ```markdown...```

        Returns:
            Text with wrapper removed
        """
        pattern = r"^```(?:markdown)?\n(.*?)\n```$"
        match = re.match(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return text

    @staticmethod
    def strip_markdown_formatting(text: str) -> str:
        """
        Remove common Markdown syntax from text.

        Args:
            text: Markdown formatted text

        Returns:
            Plain text with Markdown syntax removed
        """
        # Remove highlight syntax
        text = re.sub(r"==(.*?)==", r"\1", text)
        # Remove bold syntax
        text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
        # Remove italic syntax
        text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
        return text

    @staticmethod
    def validate_images(images: List[Image.Image]) -> None:
        """
        Validate list of images.

        Args:
            images: List of PIL Images

        Raises:
            ValueError: If images list is empty or contains invalid images
        """
        if not images:
            raise ValueError("No images provided for processing")

        for i, img in enumerate(images):
            if not isinstance(img, Image.Image):
                raise ValueError(f"Item {i} is not a PIL Image")
            if img.width == 0 or img.height == 0:
                raise ValueError(f"Image {i} has zero dimensions")
