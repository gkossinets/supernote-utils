"""Tests for .note → PDF conversion."""

import tempfile
from pathlib import Path

import pytest

from supernote_utils.sources.note import NoteFileHandler

TEST_NOTE = Path(__file__).parent / "test.note"


@pytest.mark.skipif(not TEST_NOTE.exists(), reason="test.note fixture not found")
def test_note_to_pdf_creates_file():
    """NoteFileHandler.generate_pdf writes a non-empty PDF."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output = Path(f.name)

    try:
        NoteFileHandler.generate_pdf(TEST_NOTE, output)
        assert output.exists(), "PDF file was not created"
        assert output.stat().st_size > 0, "PDF file is empty"
    finally:
        output.unlink(missing_ok=True)


@pytest.mark.skipif(not TEST_NOTE.exists(), reason="test.note fixture not found")
def test_note_extract_images_returns_pil_images():
    """NoteFileHandler.extract_images returns at least one PIL Image."""
    from PIL import Image
    images = NoteFileHandler.extract_images(TEST_NOTE)
    assert len(images) >= 1, "Expected at least one page"
    for img in images:
        assert isinstance(img, Image.Image)
        assert img.width > 0 and img.height > 0
