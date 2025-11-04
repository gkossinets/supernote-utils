"""Unified transcription engine for all input types"""

import sys
from pathlib import Path
from typing import List, Optional, TextIO

from PIL import Image

from supernote_utils.config import TranscriptionConfig
from supernote_utils.core.image_processor import ImageProcessor
from supernote_utils.core.prompts import get_prompt
from supernote_utils.providers.base import VisionProvider


class Transcriber:
    """Unified transcription engine that works with any provider and source"""

    def __init__(self, provider: VisionProvider, config: Optional[TranscriptionConfig] = None):
        """
        Initialize transcriber.

        Args:
            provider: Vision provider to use for transcription
            config: Transcription configuration (uses defaults if None)
        """
        self.provider = provider
        self.config = config or TranscriptionConfig()

        # Build prompt with any additional instructions
        self.prompt = get_prompt(self.config.additional_prompt)

    def transcribe_images(
        self,
        images: List[Image.Image],
        output: Optional[TextIO] = None,
        plain_text: bool = False,
    ) -> str:
        """
        Transcribe multiple images to markdown.

        Args:
            images: List of PIL Images to transcribe
            output: Output stream (None for string return, sys.stdout for console)
            plain_text: If True, strip markdown formatting from output

        Returns:
            Transcribed text (empty string if output stream provided)

        Raises:
            ImageProcessingError: If images are invalid
            ProviderAPIError: If transcription fails
        """
        # Validate images
        ImageProcessor.validate_images(images)

        # Prepare output
        if output is None:
            # Return as string
            parts = []
            for i, image in enumerate(images, start=1):
                text = self._transcribe_single_page(image, i)
                if plain_text:
                    text = ImageProcessor.strip_markdown_formatting(text)
                parts.append(text.strip())
            return "\n\n".join(parts)
        else:
            # Stream to output
            for i, image in enumerate(images, start=1):
                text = self._transcribe_single_page(image, i)
                if plain_text:
                    text = ImageProcessor.strip_markdown_formatting(text)

                # Add spacing and separator
                if i > 1:
                    output.write("\n\n")
                if self.config.page_separator:
                    output.write(f"---- Page {i} ----\n")

                output.write(text.strip())
                output.flush()

            output.write("\n")
            return ""

    def _transcribe_single_page(self, image: Image.Image, page_num: int) -> str:
        """
        Transcribe a single page image.

        Args:
            image: PIL Image to transcribe
            page_num: Page number for logging

        Returns:
            Transcribed text
        """
        print(f"Processing page {page_num} (size: {image.size})...", file=sys.stderr)

        # Call provider
        text = self.provider.transcribe_image(image, self.prompt)

        # Clean up code block wrappers
        text = ImageProcessor.strip_markdown_code_blocks(text)

        return text

    def transcribe_file(
        self,
        images: List[Image.Image],
        output_path: Optional[Path] = None,
        plain_text: bool = False,
    ) -> None:
        """
        Transcribe images and write to file or stdout.

        Args:
            images: List of PIL Images to transcribe
            output_path: Output file path (None for stdout)
            plain_text: If True, strip markdown formatting

        Raises:
            ImageProcessingError: If images are invalid
            ProviderAPIError: If transcription fails
        """
        # Set up output with proper UTF-8 encoding
        if output_path:
            output_stream = open(output_path, "w", encoding="utf-8")
        else:
            # Ensure stdout uses UTF-8 encoding
            if sys.stdout.encoding != "utf-8":
                output_stream = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
            else:
                output_stream = sys.stdout

        try:
            self.transcribe_images(images, output=output_stream, plain_text=plain_text)

            if output_path:
                print(f"\nTranscription saved to: {output_path}", file=sys.stderr)

        finally:
            if output_path:
                output_stream.close()
