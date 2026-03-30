"""Tests for file source handlers."""

import io
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from supernote_utils.exceptions import FileFormatError
from supernote_utils.sources.image import ImageFileHandler

TEST_NOTE = Path(__file__).parent / "test.note"


# ---------------------------------------------------------------------------
# ImageFileHandler
# ---------------------------------------------------------------------------

class TestImageFileHandler:
    def _write_png(self, path: Path, size=(20, 20)):
        img = Image.new("RGB", size, color=(128, 64, 32))
        img.save(path, format="PNG")

    def test_extract_png_returns_single_image(self, tmp_path):
        png = tmp_path / "test.png"
        self._write_png(png)
        images = ImageFileHandler.extract_images(png)
        assert len(images) == 1
        assert isinstance(images[0], Image.Image)

    def test_extracted_image_has_correct_size(self, tmp_path):
        png = tmp_path / "test.png"
        self._write_png(png, size=(30, 50))
        images = ImageFileHandler.extract_images(png)
        assert images[0].size == (30, 50)

    def test_rgba_image_converted_to_rgb(self, tmp_path):
        png = tmp_path / "rgba.png"
        img = Image.new("RGBA", (10, 10), color=(0, 0, 0, 128))
        img.save(png)
        images = ImageFileHandler.extract_images(png)
        assert images[0].mode == "RGB"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileFormatError, match="not found"):
            ImageFileHandler.extract_images(tmp_path / "nonexistent.png")

    def test_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "file.bmp"
        f.touch()
        with pytest.raises(FileFormatError, match="Unsupported image format"):
            ImageFileHandler.extract_images(f)

    def test_corrupt_file_raises(self, tmp_path):
        f = tmp_path / "bad.png"
        f.write_bytes(b"not a valid image")
        with pytest.raises(FileFormatError, match="Failed to load"):
            ImageFileHandler.extract_images(f)

    def test_is_supported_returns_true_for_png(self):
        assert ImageFileHandler.is_supported(Path("x.png")) is True

    def test_is_supported_returns_false_for_docx(self):
        assert ImageFileHandler.is_supported(Path("x.docx")) is False


# ---------------------------------------------------------------------------
# NoteFileHandler — deterministic binary parsing, no LLM
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not TEST_NOTE.exists(), reason="test.note fixture not found")
class TestNoteFileHandler:
    def test_extract_images_returns_list(self):
        from supernote_utils.sources.note import NoteFileHandler
        images = NoteFileHandler.extract_images(TEST_NOTE)
        assert isinstance(images, list)

    def test_extract_images_returns_at_least_one_page(self):
        from supernote_utils.sources.note import NoteFileHandler
        images = NoteFileHandler.extract_images(TEST_NOTE)
        assert len(images) >= 1

    def test_extracted_images_are_pil_images(self):
        from supernote_utils.sources.note import NoteFileHandler
        images = NoteFileHandler.extract_images(TEST_NOTE)
        for img in images:
            assert isinstance(img, Image.Image)
            assert img.width > 0 and img.height > 0

    def test_missing_file_raises(self, tmp_path):
        from supernote_utils.sources.note import NoteFileHandler
        from supernote_utils.exceptions import FileFormatError
        with pytest.raises((FileFormatError, Exception)):
            NoteFileHandler.extract_images(tmp_path / "missing.note")
