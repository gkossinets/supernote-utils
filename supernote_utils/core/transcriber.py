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

    def _get_batch_prompt(self, num_pages: int) -> str:
        """
        Get prompt for batch processing multiple pages.

        Args:
            num_pages: Number of pages in the batch

        Returns:
            Modified prompt for batch processing
        """
        batch_instruction = f"""You are transcribing {num_pages} consecutive pages from a personal handwritten document. The pages are provided in order.

**CRITICAL: Output Format Requirements:**
- Transcribe all {num_pages} pages as continuous flowing text
- Preserve page boundaries by maintaining natural paragraph breaks between pages
- Do NOT add page numbers, headers, or separators (e.g., no "Page 1:", "---", etc.)
- Ensure consistency in style and formatting across all pages
- If a sentence or thought continues across pages, maintain continuity

"""
        return batch_instruction + self.prompt

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

        # Use batch processing if batch_size > 1
        if self.config.batch_size > 1:
            return self._transcribe_with_batching(images, output, plain_text)
        else:
            return self._transcribe_single_pages(images, output, plain_text)

    def _transcribe_single_pages(
        self,
        images: List[Image.Image],
        output: Optional[TextIO] = None,
        plain_text: bool = False,
    ) -> str:
        """
        Transcribe images one at a time (original behavior).

        Args:
            images: List of PIL Images to transcribe
            output: Output stream (None for string return, sys.stdout for console)
            plain_text: If True, strip markdown formatting from output

        Returns:
            Transcribed text (empty string if output stream provided)
        """
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

    def _transcribe_with_batching(
        self,
        images: List[Image.Image],
        output: Optional[TextIO] = None,
        plain_text: bool = False,
    ) -> str:
        """
        Transcribe images in batches.

        Args:
            images: List of PIL Images to transcribe
            output: Output stream (None for string return, sys.stdout for console)
            plain_text: If True, strip markdown formatting from output

        Returns:
            Transcribed text (empty string if output stream provided)
        """
        batch_size = self.config.batch_size
        all_parts = []

        # Process in batches
        for batch_start in range(0, len(images), batch_size):
            batch_end = min(batch_start + batch_size, len(images))
            batch_images = images[batch_start:batch_end]
            batch_page_nums = list(range(batch_start + 1, batch_end + 1))

            try:
                text = self._transcribe_batch(batch_images, batch_page_nums)
            except Exception as e:
                # Fallback to single-page processing on error
                print(
                    f"\nBatch processing failed for pages {batch_page_nums[0]}-{batch_page_nums[-1]}: {e}",
                    file=sys.stderr
                )
                print("Falling back to single-page mode for this batch...", file=sys.stderr)
                text = self._transcribe_batch_fallback(batch_images, batch_page_nums)

            if plain_text:
                text = ImageProcessor.strip_markdown_formatting(text)

            if output is None:
                all_parts.append(text.strip())
            else:
                # Add spacing and separator
                if batch_start > 0:
                    output.write("\n\n")

                # Add page separators if requested
                if self.config.page_separator:
                    if len(batch_page_nums) == 1:
                        output.write(f"---- Page {batch_page_nums[0]} ----\n")
                    else:
                        output.write(f"---- Pages {batch_page_nums[0]}-{batch_page_nums[-1]} ----\n")

                output.write(text.strip())
                output.flush()

        if output is None:
            return "\n\n".join(all_parts)
        else:
            output.write("\n")
            return ""

    def _transcribe_batch(self, batch_images: List[Image.Image], page_nums: List[int]) -> str:
        """
        Transcribe a batch of images.

        Args:
            batch_images: List of PIL Images to transcribe
            page_nums: List of page numbers for logging

        Returns:
            Transcribed text
        """
        if len(batch_images) == 1:
            return self._transcribe_single_page(batch_images[0], page_nums[0])

        # Log batch processing
        print(
            f"Processing pages {page_nums[0]}-{page_nums[-1]} "
            f"({len(batch_images)} pages in batch)...",
            file=sys.stderr
        )

        # Get batch prompt
        batch_prompt = self._get_batch_prompt(len(batch_images))

        # Call provider with batch
        text = self.provider.transcribe_images_batch(batch_images, batch_prompt)

        # Clean up code block wrappers
        text = ImageProcessor.strip_markdown_code_blocks(text)

        return text

    def _transcribe_batch_fallback(self, batch_images: List[Image.Image], page_nums: List[int]) -> str:
        """
        Fallback to single-page processing for a batch.

        Args:
            batch_images: List of PIL Images to transcribe
            page_nums: List of page numbers for logging

        Returns:
            Transcribed text
        """
        parts = []
        for image, page_num in zip(batch_images, page_nums):
            text = self._transcribe_single_page(image, page_num)
            parts.append(text.strip())
        return "\n\n".join(parts)

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
