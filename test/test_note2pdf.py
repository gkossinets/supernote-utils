"""Tests for .note → PDF conversion."""

import argparse
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from supernote_utils.cli.note2pdf import convert_note_to_pdf
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
def test_convert_with_explicit_output(tmp_path):
    """`-o output.pdf` writes to the specified path."""
    output = tmp_path / "out.pdf"
    args = SimpleNamespace(input=str(TEST_NOTE), output=str(output))
    convert_note_to_pdf(args)
    assert output.exists() and output.stat().st_size > 0


@pytest.mark.skipif(not TEST_NOTE.exists(), reason="test.note fixture not found")
def test_convert_derives_output_from_input(tmp_path):
    """When output is None, the PDF is written next to the input as <stem>.pdf."""
    import shutil
    note_copy = tmp_path / "mynotes.note"
    shutil.copy(TEST_NOTE, note_copy)
    args = SimpleNamespace(input=str(note_copy), output=None)
    convert_note_to_pdf(args)
    expected = tmp_path / "mynotes.pdf"
    assert expected.exists() and expected.stat().st_size > 0


@pytest.mark.skipif(not TEST_NOTE.exists(), reason="test.note fixture not found")
def test_note_extract_images_returns_pil_images():
    """NoteFileHandler.extract_images returns at least one PIL Image."""
    from PIL import Image
    images = NoteFileHandler.extract_images(TEST_NOTE)
    assert len(images) >= 1, "Expected at least one page"
    for img in images:
        assert isinstance(img, Image.Image)
        assert img.width > 0 and img.height > 0
