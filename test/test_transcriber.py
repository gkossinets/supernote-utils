"""Tests for Transcriber batching and orchestration logic.

All tests use a deterministic mock provider — no LLM calls.
"""

import io
from typing import List
from unittest.mock import MagicMock, call, patch

import pytest
from PIL import Image

from supernote_utils.config import TranscriptionConfig
from supernote_utils.core.transcriber import Transcriber
from supernote_utils.providers.base import VisionProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_image(width=10, height=10) -> Image.Image:
    return Image.new("RGB", (width, height), color=(200, 200, 200))


def make_images(n: int) -> List[Image.Image]:
    return [make_image() for _ in range(n)]


class FixedProvider(VisionProvider):
    """Mock provider that returns a predictable string per image."""

    def __init__(self, response: str = "transcribed text"):
        super().__init__(temperature=1.0)
        self.response = response
        self.single_call_count = 0
        self.batch_call_count = 0

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        self.single_call_count += 1
        return self.response

    def transcribe_images_batch(self, images: List[Image.Image], prompt: str) -> str:
        self.batch_call_count += 1
        return self.response

    def is_available(self) -> bool:
        return True

    def get_display_name(self) -> str:
        return "FixedProvider"


# ---------------------------------------------------------------------------
# Single-page mode (batch_size=1)
# ---------------------------------------------------------------------------

class TestTranscriberSinglePageMode:
    def test_single_image_returns_text(self):
        provider = FixedProvider("hello")
        t = Transcriber(provider, TranscriptionConfig(batch_size=1))
        result = t.transcribe_images(make_images(1))
        assert result == "hello"

    def test_multiple_images_joined(self):
        provider = FixedProvider("page")
        t = Transcriber(provider, TranscriptionConfig(batch_size=1))
        result = t.transcribe_images(make_images(3))
        assert result == "page\n\npage\n\npage"

    def test_single_page_calls_transcribe_image_not_batch(self):
        provider = FixedProvider()
        t = Transcriber(provider, TranscriptionConfig(batch_size=1))
        t.transcribe_images(make_images(2))
        assert provider.single_call_count == 2
        assert provider.batch_call_count == 0

    def test_plain_text_strips_markdown(self):
        provider = FixedProvider("**bold** text")
        t = Transcriber(provider, TranscriptionConfig(batch_size=1))
        result = t.transcribe_images(make_images(1), plain_text=True)
        assert "**" not in result
        assert "bold text" in result


# ---------------------------------------------------------------------------
# Batch mode (batch_size > 1)
# ---------------------------------------------------------------------------

class TestTranscriberBatchMode:
    def test_batch_calls_transcribe_images_batch(self):
        provider = FixedProvider("batch result")
        t = Transcriber(provider, TranscriptionConfig(batch_size=3))
        result = t.transcribe_images(make_images(3))
        assert provider.batch_call_count == 1
        assert provider.single_call_count == 0

    def test_six_images_with_batch_size_3_makes_two_calls(self):
        provider = FixedProvider("batch")
        t = Transcriber(provider, TranscriptionConfig(batch_size=3))
        t.transcribe_images(make_images(6))
        assert provider.batch_call_count == 2

    def test_single_image_with_batch_mode_uses_single_call(self):
        """A batch of 1 should use single-page path (optimisation in _transcribe_batch)."""
        provider = FixedProvider("single")
        t = Transcriber(provider, TranscriptionConfig(batch_size=3))
        t.transcribe_images(make_images(1))
        assert provider.single_call_count == 1
        assert provider.batch_call_count == 0

    def test_batch_failure_falls_back_to_single_pages(self):
        """When batch transcription raises, it falls back to per-page calls."""
        provider = FixedProvider("fallback")
        provider.transcribe_images_batch = MagicMock(side_effect=RuntimeError("API error"))
        t = Transcriber(provider, TranscriptionConfig(batch_size=3))
        result = t.transcribe_images(make_images(3))
        # Fallback should produce concatenated single-page results
        assert "fallback" in result

    def test_batch_plain_text_strips_markdown(self):
        provider = FixedProvider("**bold**")
        t = Transcriber(provider, TranscriptionConfig(batch_size=3))
        result = t.transcribe_images(make_images(2), plain_text=True)
        assert "**" not in result


# ---------------------------------------------------------------------------
# Output streaming
# ---------------------------------------------------------------------------

class TestTranscriberOutputStream:
    def test_writes_to_stream(self):
        provider = FixedProvider("streamed")
        t = Transcriber(provider, TranscriptionConfig(batch_size=1))
        buf = io.StringIO()
        return_val = t.transcribe_images(make_images(1), output=buf)
        assert return_val == ""
        assert "streamed" in buf.getvalue()

    def test_page_separator_inserted_in_stream(self):
        provider = FixedProvider("text")
        t = Transcriber(provider, TranscriptionConfig(batch_size=1, page_separator=True))
        buf = io.StringIO()
        t.transcribe_images(make_images(2), output=buf)
        assert "Page" in buf.getvalue()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestTranscriberEdgeCases:
    def test_empty_image_list_raises(self):
        provider = FixedProvider()
        t = Transcriber(provider, TranscriptionConfig())
        with pytest.raises(ValueError, match="No images"):
            t.transcribe_images([])

    def test_code_block_wrapper_stripped(self):
        provider = FixedProvider("```markdown\nclean text\n```")
        t = Transcriber(provider, TranscriptionConfig(batch_size=1))
        result = t.transcribe_images(make_images(1))
        assert result == "clean text"
