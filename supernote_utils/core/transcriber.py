"""Unified transcription engine for all input types"""

import re
import sys
from pathlib import Path
from typing import TextIO

from PIL import Image

from supernote_utils.config import TranscriptionConfig
from supernote_utils.core.image_processor import ImageProcessor
from supernote_utils.core.prompts import get_prompt
from supernote_utils.providers.base import VisionProvider

# A line holding only a page marker such as "<!-- page 2 -->". Batched requests ask the
# model to start each page with one so that a silently dropped page can be detected.
_PAGE_MARKER = re.compile(r"^\s*<!--\s*page\s+(\d+)\s*-->\s*$", re.IGNORECASE | re.MULTILINE)


class Transcriber:
    """Unified transcription engine that works with any provider and source"""

    def __init__(self, provider: VisionProvider, config: TranscriptionConfig | None = None):
        """
        Initialize transcriber.

        Args:
            provider: Vision provider to use for transcription
            config: Transcription configuration (uses defaults if None)
        """
        self.provider = provider
        self.config = config or TranscriptionConfig()

        # Build prompt with the date hint (if any) and any additional instructions
        self.prompt = get_prompt(self.config.additional_prompt, self.config.expected_date)

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
- Transcribe every one of the {num_pages} pages, in order. Do not skip any page, even one that looks like a continuation of another
- Start each page's transcription with a marker line holding only the page's position in this request: `<!-- page 1 -->` for the first image, `<!-- page 2 -->` for the second, and so on up to `<!-- page {num_pages} -->`
- If a page is blank, output its marker line with nothing after it
- Do NOT add any other page numbers, headers, or separators (e.g., no "Page 1:", "---", etc.)
- Ensure consistency in style and formatting across all pages

"""
        return batch_instruction + self.prompt

    def transcribe_images(
        self,
        images: list[Image.Image],
        output: TextIO | None = None,
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
        images: list[Image.Image],
        output: TextIO | None = None,
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
        images: list[Image.Image],
        output: TextIO | None = None,
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

        for batch_start in range(0, len(images), batch_size):
            batch_end = min(batch_start + batch_size, len(images))
            batch_images = images[batch_start:batch_end]
            batch_page_nums = list(range(batch_start + 1, batch_end + 1))

            try:
                page_texts = self._transcribe_batch(batch_images, batch_page_nums)
            except Exception as e:
                print(
                    f"\nBatch processing failed for pages {batch_page_nums[0]}-{batch_page_nums[-1]}: {e}",
                    file=sys.stderr
                )
                print("Falling back to single-page mode for this batch...", file=sys.stderr)
                page_texts = self._transcribe_batch_fallback(batch_images, batch_page_nums)

            for page_num, text in zip(batch_page_nums, page_texts):
                if plain_text:
                    text = ImageProcessor.strip_markdown_formatting(text)
                text = text.strip()

                if output is None:
                    # A blank page adds nothing, not an empty paragraph.
                    if text:
                        all_parts.append(text)
                    continue

                if page_num > 1:
                    output.write("\n\n")
                if self.config.page_separator:
                    output.write(f"---- Page {page_num} ----\n")
                output.write(text)
                output.flush()

        if output is None:
            return "\n\n".join(all_parts)
        else:
            output.write("\n")
            return ""

    def _transcribe_batch(self, batch_images: list[Image.Image], page_nums: list[int]) -> list[str]:
        """
        Transcribe a batch of images in one request and check that every page came back.

        Pages the model left out are transcribed again one at a time.

        Args:
            batch_images: List of PIL Images to transcribe
            page_nums: Document page numbers of the images, for logging

        Returns:
            One transcribed text per image, in order
        """
        if len(batch_images) == 1:
            return [self._transcribe_single_page(batch_images[0], page_nums[0])]

        print(
            f"Processing pages {page_nums[0]}-{page_nums[-1]} "
            f"({len(batch_images)} pages in batch)...",
            file=sys.stderr
        )

        batch_prompt = self._get_batch_prompt(len(batch_images))
        text = self.provider.transcribe_images_batch(batch_images, batch_prompt)
        text = ImageProcessor.strip_markdown_code_blocks(text)

        pages = self._split_pages(text, page_nums)
        if not pages:
            print(
                f"Warning: no page markers in the response for pages {page_nums[0]}-{page_nums[-1]}, "
                "so missing pages can't be detected. Transcribing each page on its own.",
                file=sys.stderr,
            )
            return self._transcribe_batch_fallback(batch_images, page_nums)

        page_texts = []
        for index, (image, page_num) in enumerate(zip(batch_images, page_nums), start=1):
            if index in pages:
                page_texts.append(pages[index])
            else:
                print(
                    f"Warning: the response left out page {page_num}. Transcribing it on its own.",
                    file=sys.stderr,
                )
                page_texts.append(self._transcribe_single_page(image, page_num))
        return page_texts

    @staticmethod
    def _split_pages(text: str, page_nums: list[int]) -> dict[int, str]:
        """
        Split a batched response at its page markers.

        Text before the first marker is kept with the first page found, and a marker
        numbered outside the batch is dropped with its text kept on the preceding page,
        so no transcribed text is lost. Both are reported on stderr.

        Args:
            text: The model's response
            page_nums: Document page numbers of the batch, for warnings

        Returns:
            Text for each page position (1-based) that has a marker; empty if there are none
        """
        num_pages = len(page_nums)
        markers = [m for m in _PAGE_MARKER.finditer(text) if 1 <= int(m.group(1)) <= num_pages]
        for m in _PAGE_MARKER.finditer(text):
            position = int(m.group(1))
            if not 1 <= position <= num_pages:
                print(
                    f"Warning: the response has a marker for page {position}, but the request "
                    f"for pages {page_nums[0]}-{page_nums[-1]} had only {num_pages}. "
                    "Its text is kept with the page before it.",
                    file=sys.stderr,
                )
        if not markers:
            return {}

        pages: dict[int, str] = {}
        for i, m in enumerate(markers):
            end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
            segment = _PAGE_MARKER.sub("", text[m.end():end]).strip()
            position = int(m.group(1))
            # A repeated marker continues the same page rather than replacing it.
            pages[position] = f"{pages[position]}\n\n{segment}".strip() if position in pages else segment

        leading = text[:markers[0].start()].strip()
        if leading:
            print(
                f"Warning: the response had text before the first page marker for pages "
                f"{page_nums[0]}-{page_nums[-1]}; it is kept with the first page.",
                file=sys.stderr,
            )
            first = int(markers[0].group(1))
            pages[first] = f"{leading}\n{pages[first]}".strip()
        return pages

    def _transcribe_batch_fallback(self, batch_images: list[Image.Image], page_nums: list[int]) -> list[str]:
        """
        Transcribe each image of a batch on its own.

        Args:
            batch_images: List of PIL Images to transcribe
            page_nums: Document page numbers of the images, for logging

        Returns:
            One transcribed text per image, in order
        """
        return [
            self._transcribe_single_page(image, page_num)
            for image, page_num in zip(batch_images, page_nums)
        ]

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
        images: list[Image.Image],
        output_path: Path | None = None,
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
                print(f"Transcription saved to: {output_path}\n", file=sys.stderr)

        finally:
            if output_path:
                output_stream.close()
