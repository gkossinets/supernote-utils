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
        provider = FixedProvider("A page.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=1))
        result = t.transcribe_images(make_images(3))
        assert result == "A page.\n\nA page.\n\nA page."

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
        provider = FixedProvider("<!-- page 1 -->\nA.\n<!-- page 2 -->\nB.\n<!-- page 3 -->\nC.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=3))
        result = t.transcribe_images(make_images(3))
        assert result == "A.\n\nB.\n\nC."
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


# ---------------------------------------------------------------------------
# Page check in batched requests
# ---------------------------------------------------------------------------

class ScriptedProvider(FixedProvider):
    """Returns a fixed batch response and a numbered text for each single-page call."""

    def __init__(self, batch_response: str):
        super().__init__()
        self.batch_response = batch_response

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        self.single_call_count += 1
        return f"Redo {self.single_call_count}."

    def transcribe_images_batch(self, images: List[Image.Image], prompt: str) -> str:
        self.batch_call_count += 1
        self.last_batch_prompt = prompt
        return self.batch_response


class TestBatchPageCheck:
    def test_batch_prompt_asks_for_page_markers(self):
        provider = ScriptedProvider("<!-- page 1 -->\nA.\n<!-- page 2 -->\nB.")
        Transcriber(provider, TranscriptionConfig(batch_size=2)).transcribe_images(make_images(2))
        assert "<!-- page 1 -->" in provider.last_batch_prompt
        assert "<!-- page 2 -->" in provider.last_batch_prompt

    def test_markers_are_removed_from_output(self):
        provider = ScriptedProvider("<!-- page 1 -->\nFirst.\n\n<!-- page 2 -->\nSecond.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=2))
        assert t.transcribe_images(make_images(2)) == "First.\n\nSecond."
        assert provider.single_call_count == 0

    def test_missing_page_is_redone_alone(self, capsys):
        provider = ScriptedProvider("<!-- page 1 -->\nFirst.\n<!-- page 3 -->\nThird.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=3))
        assert t.transcribe_images(make_images(3)) == "First.\n\nRedo 1.\n\nThird."
        assert provider.single_call_count == 1
        assert "page 2" in capsys.readouterr().err

    def test_page_numbers_are_relative_to_the_batch(self):
        # Pages 4-5 of a document are pages 1-2 of the second batch.
        provider = ScriptedProvider("<!-- page 1 -->\nX.\n<!-- page 2 -->\nY.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=3))
        result = t.transcribe_images(make_images(5))
        assert provider.single_call_count == 1  # page 3 of the first batch is missing
        assert result == "X.\n\nY.\n\nRedo 1.\n\nX.\n\nY."

    def test_no_markers_redoes_every_page(self, capsys):
        provider = ScriptedProvider("unmarked text")
        t = Transcriber(provider, TranscriptionConfig(batch_size=2))
        assert t.transcribe_images(make_images(2)) == "Redo 1.\n\nRedo 2."
        assert "no page markers" in capsys.readouterr().err

    def test_empty_page_counts_as_present(self):
        provider = ScriptedProvider("<!-- page 1 -->\n<!-- page 2 -->\nSecond.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=2))
        assert t.transcribe_images(make_images(2)) == "Second."
        assert provider.single_call_count == 0

    def test_text_before_first_marker_is_kept(self, capsys):
        provider = ScriptedProvider("Stray.\n<!-- page 1 -->\nA.\n<!-- page 2 -->\nB.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=2))
        assert t.transcribe_images(make_images(2)) == "Stray.\nA.\n\nB."
        assert "before the first page marker" in capsys.readouterr().err

    def test_marker_spacing_and_case_are_tolerated(self):
        provider = ScriptedProvider("<!--Page 1-->\nA.\n  <!--  PAGE 2  -->  \nB.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=2))
        assert t.transcribe_images(make_images(2)) == "A.\n\nB."

    def test_out_of_range_marker_is_reported(self, capsys):
        provider = ScriptedProvider("<!-- page 1 -->\nA.\n<!-- page 2 -->\nB.\n<!-- page 7 -->\nC.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=2))
        assert t.transcribe_images(make_images(2)) == "A.\n\nB.\n\nC."
        assert "page 7" in capsys.readouterr().err

    def test_page_separators_are_per_page_in_batch_mode(self):
        provider = ScriptedProvider("<!-- page 1 -->\nA.\n<!-- page 2 -->\nB.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=2, page_separator=True))
        buf = io.StringIO()
        t.transcribe_images(make_images(2), output=buf)
        assert buf.getvalue() == "---- Page 1 ----\nA.\n\n---- Page 2 ----\nB.\n"

    def test_markers_are_stripped_before_plain_text_conversion(self):
        provider = ScriptedProvider("<!-- page 1 -->\n**A.**\n<!-- page 2 -->\nB.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=2))
        assert t.transcribe_images(make_images(2), plain_text=True) == "A.\n\nB."


# ---------------------------------------------------------------------------
# Stitching pages: a sentence that runs across a page boundary stays one paragraph
# ---------------------------------------------------------------------------

class PagesProvider(FixedProvider):
    """Returns the given page texts in order, one per single-page call."""

    def __init__(self, pages: List[str]):
        super().__init__()
        self.pages = list(pages)

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        self.single_call_count += 1
        return self.pages.pop(0)


def stitch(*pages: str, **config) -> str:
    provider = PagesProvider(list(pages))
    t = Transcriber(provider, TranscriptionConfig(batch_size=1, **config))
    return t.transcribe_images(make_images(len(pages)))


class TestPageJoinRule:
    @pytest.mark.parametrize("prev, nxt, expected", [
        # Sentence continues: join with a space
        ("We walked to the", "river and back.", "We walked to the river and back."),
        ("Мы шли к", "реке и обратно.", "Мы шли к реке и обратно."),
        ("apples, pears,", "and plums.", "apples, pears, and plums."),
        ("it was 1980", "or so.", "it was 1980 or so."),
        ("and then —", "nothing.", "and then — nothing."),
        # Word hyphenated across the break: join without the hyphen
        ("a long transcrip-", "tion here.", "a long transcription here."),
        ("перено-", "сы слов.", "переносы слов."),
        # Page ends a sentence: keep the paragraph break
        ("The end.", "next page.", "The end.\n\nnext page."),
        ("Really?", "yes.", "Really?\n\nyes."),
        ('He said "go."', "then left.", 'He said "go."\n\nthen left.'),
        # Next page starts with a capital, list, header or symbol: keep the break
        ("We walked to the", "River Thames.", "We walked to the\n\nRiver Thames."),
        ("Shopping", "- milk", "Shopping\n\n- milk"),
        ("notes", "**Header**", "notes\n\n**Header**"),
        ("notes", "==marked== text", "notes\n\n==marked== text"),
        # Page ends with a list item, table row, quote, bold header or highlight: keep it
        ("- buy bread", "and milk", "- buy bread\n\nand milk"),
        ("1. first item", "continued", "1. first item\n\ncontinued"),
        ("| a | b |", "after", "| a | b |\n\nafter"),
        ("> quoted line", "after", "> quoted line\n\nafter"),
        ("**Header**", "text", "**Header**\n\ntext"),
        ("a ==highlight==", "text", "a ==highlight==\n\ntext"),
        # A spaced hyphen or dash is not a hyphenation
        ("a - b -", "c", "a - b - c"),
    ])
    def test_join(self, prev, nxt, expected):
        assert stitch(prev, nxt) == expected

    def test_only_the_last_paragraph_and_first_paragraph_merge(self):
        assert stitch("Para one.\n\nPara two runs", "on here.\n\nPara three.") == (
            "Para one.\n\nPara two runs on here.\n\nPara three."
        )

    def test_three_pages_chain(self):
        assert stitch("one", "two", "three.") == "one two three."

    def test_blank_page_breaks_the_chain(self):
        assert stitch("We walked to the", "", "river.") == "We walked to the\n\nriver."

    def test_page_separator_disables_joining(self):
        buf = io.StringIO()
        provider = PagesProvider(["We walked to the", "river."])
        t = Transcriber(provider, TranscriptionConfig(batch_size=1, page_separator=True))
        t.transcribe_images(make_images(2), output=buf)
        assert buf.getvalue() == "---- Page 1 ----\nWe walked to the\n\n---- Page 2 ----\nriver.\n"


class TestPageJoinModes:
    def test_stream_output_matches_string_output(self):
        pages = ["We walked to the", "river and transcrip-", "tion.", "Done."]
        buf = io.StringIO()
        t = Transcriber(PagesProvider(pages), TranscriptionConfig(batch_size=1))
        t.transcribe_images(make_images(4), output=buf)
        assert buf.getvalue() == stitch(*pages) + "\n"
        assert buf.getvalue() == "We walked to the river and transcription.\n\nDone.\n"

    def test_join_within_a_batch(self):
        provider = ScriptedProvider("<!-- page 1 -->\nWe walked to the\n<!-- page 2 -->\nriver.")
        t = Transcriber(provider, TranscriptionConfig(batch_size=2))
        assert t.transcribe_images(make_images(2)) == "We walked to the river."

    def test_join_across_batches(self):
        provider = ScriptedProvider("")
        responses = iter([
            "<!-- page 1 -->\nOne.\n<!-- page 2 -->\nWe walked to the",
            "<!-- page 1 -->\nriver.\n<!-- page 2 -->\nTwo.",
        ])
        provider.transcribe_images_batch = lambda images, prompt: next(responses)
        t = Transcriber(provider, TranscriptionConfig(batch_size=2))
        assert t.transcribe_images(make_images(4)) == "One.\n\nWe walked to the river.\n\nTwo."

    def test_plain_text_join(self):
        provider = PagesProvider(["**Bold** start of a", "sentence."])
        t = Transcriber(provider, TranscriptionConfig(batch_size=1))
        assert t.transcribe_images(make_images(2), plain_text=True) == "Bold start of a sentence."


class TestPageSeparatorStringMode:
    """The CLI's -o path collects text as a string; separators must not be lost there."""

    def test_string_mode_writes_separators_without_stitching(self):
        provider = PagesProvider(["We walked to the", "river."])
        t = Transcriber(provider, TranscriptionConfig(batch_size=1, page_separator=True))
        assert t.transcribe_images(make_images(2)) == (
            "---- Page 1 ----\nWe walked to the\n\n---- Page 2 ----\nriver."
        )
