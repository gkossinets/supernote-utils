"""Tests for the source file handler factory."""

from pathlib import Path

import pytest

from supernote_utils.exceptions import FileFormatError
from supernote_utils.sources.factory import (
    get_format_name,
    get_handler,
    is_multipage_format,
)
from supernote_utils.sources.image import ImageFileHandler
from supernote_utils.sources.note import NoteFileHandler
from supernote_utils.sources.pdf import PDFFileHandler


class TestGetHandler:
    def test_note_extension(self):
        handler_cls, _ = get_handler(Path("file.note"))
        assert handler_cls is NoteFileHandler

    def test_pdf_extension(self):
        handler_cls, _ = get_handler(Path("file.pdf"))
        assert handler_cls is PDFFileHandler

    def test_png_extension(self):
        handler_cls, _ = get_handler(Path("file.png"))
        assert handler_cls is ImageFileHandler

    def test_jpg_extension(self):
        handler_cls, _ = get_handler(Path("file.jpg"))
        assert handler_cls is ImageFileHandler

    def test_jpeg_extension(self):
        handler_cls, _ = get_handler(Path("file.jpeg"))
        assert handler_cls is ImageFileHandler

    def test_webp_extension(self):
        handler_cls, _ = get_handler(Path("file.webp"))
        assert handler_cls is ImageFileHandler

    def test_uppercase_extension_is_normalised(self):
        handler_cls, _ = get_handler(Path("file.NOTE"))
        assert handler_cls is NoteFileHandler

    def test_mixed_case_extension(self):
        handler_cls, _ = get_handler(Path("file.Pdf"))
        assert handler_cls is PDFFileHandler

    def test_unsupported_extension_raises(self):
        with pytest.raises(FileFormatError, match="Unsupported file format"):
            get_handler(Path("file.docx"))

    def test_unsupported_extension_lists_supported(self):
        with pytest.raises(FileFormatError, match=r"\.note"):
            get_handler(Path("file.xyz"))


class TestIsMultipageFormat:
    def test_note_is_multipage(self):
        assert is_multipage_format(Path("file.note")) is True

    def test_pdf_is_multipage(self):
        assert is_multipage_format(Path("file.pdf")) is True

    def test_png_is_not_multipage(self):
        assert is_multipage_format(Path("file.png")) is False

    def test_jpg_is_not_multipage(self):
        assert is_multipage_format(Path("file.jpg")) is False


class TestGetFormatName:
    def test_note_format_name(self):
        assert get_format_name(Path("file.note")) == "Supernote"

    def test_pdf_format_name(self):
        assert get_format_name(Path("file.pdf")) == "PDF"

    def test_png_format_name(self):
        assert get_format_name(Path("file.png")) == "PNG image"
