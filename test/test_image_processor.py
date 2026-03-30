"""Tests for ImageProcessor utilities."""

import pytest
from PIL import Image

from supernote_utils.core.image_processor import ImageProcessor


class TestStripMarkdownCodeBlocks:
    def test_removes_markdown_wrapper(self):
        text = "```markdown\n# Hello\n```"
        assert ImageProcessor.strip_markdown_code_blocks(text) == "# Hello"

    def test_removes_plain_code_block_wrapper(self):
        text = "```\nsome text\n```"
        assert ImageProcessor.strip_markdown_code_blocks(text) == "some text"

    def test_leaves_plain_text_unchanged(self):
        text = "# Hello\nNo wrapper here."
        assert ImageProcessor.strip_markdown_code_blocks(text) == text

    def test_multiline_content_preserved(self):
        text = "```markdown\nLine 1\nLine 2\nLine 3\n```"
        assert ImageProcessor.strip_markdown_code_blocks(text) == "Line 1\nLine 2\nLine 3"

    def test_no_match_on_partial_wrapper(self):
        text = "```markdown\nno closing fence"
        assert ImageProcessor.strip_markdown_code_blocks(text) == text


class TestStripMarkdownFormatting:
    def test_removes_bold_asterisks(self):
        assert ImageProcessor.strip_markdown_formatting("**bold**") == "bold"

    def test_removes_bold_underscores(self):
        assert ImageProcessor.strip_markdown_formatting("__bold__") == "bold"

    def test_removes_italic_asterisk(self):
        assert ImageProcessor.strip_markdown_formatting("*italic*") == "italic"

    def test_removes_italic_underscore(self):
        assert ImageProcessor.strip_markdown_formatting("_italic_") == "italic"

    def test_removes_highlight(self):
        assert ImageProcessor.strip_markdown_formatting("==highlight==") == "highlight"

    def test_plain_text_unchanged(self):
        text = "No formatting here."
        assert ImageProcessor.strip_markdown_formatting(text) == text


class TestValidateImages:
    def _make_image(self, width=10, height=10):
        return Image.new("RGB", (width, height), color=(255, 255, 255))

    def test_valid_single_image(self):
        ImageProcessor.validate_images([self._make_image()])

    def test_valid_multiple_images(self):
        ImageProcessor.validate_images([self._make_image(), self._make_image()])

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="No images"):
            ImageProcessor.validate_images([])

    def test_non_image_item_raises(self):
        with pytest.raises(ValueError, match="not a PIL Image"):
            ImageProcessor.validate_images(["not an image"])

    def test_zero_width_image_raises(self):
        # PIL won't create a 0x10 image, so we patch dimensions via mock
        img = self._make_image()
        img._size = (0, 10)  # bypass normal size property
        with pytest.raises(ValueError, match="zero dimensions"):
            ImageProcessor.validate_images([img])
