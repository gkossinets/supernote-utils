"""Tests for prompt assembly: the date rule and the optional date hint."""

from datetime import date
from typing import List

from PIL import Image

from supernote_utils.config import TranscriptionConfig
from supernote_utils.core.prompts import DEFAULT_PROMPT, date_hint, get_prompt
from supernote_utils.core.transcriber import Transcriber
from supernote_utils.providers.base import VisionProvider


class RecordingProvider(VisionProvider):
    """Mock provider that records the prompts it receives."""

    def __init__(self, response: str = "text"):
        super().__init__(temperature=1.0)
        self.response = response
        self.prompts: List[str] = []

    def transcribe_image(self, image: Image.Image, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response

    def transcribe_images_batch(self, images: List[Image.Image], prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response

    def is_available(self) -> bool:
        return True

    def get_display_name(self) -> str:
        return "RecordingProvider"


def make_images(n: int) -> List[Image.Image]:
    return [Image.new("RGB", (10, 10)) for _ in range(n)]


class TestDateRule:
    def test_default_prompt_requires_digit_by_digit_dates(self):
        assert "digit by digit" in DEFAULT_PROMPT

    def test_default_prompt_forbids_reconciling_date_and_weekday(self):
        assert "Never change a date, year, or weekday" in DEFAULT_PROMPT

    def test_logic_rule_excludes_digits(self):
        logic_line = next(line for line in DEFAULT_PROMPT.splitlines() if "Logic is Law" in line)
        assert "not to dates" in logic_line


class TestDateHint:
    def test_hint_names_date_and_weekday(self):
        hint = date_hint(date(2026, 9, 20))
        assert "2026-09-20" in hint
        assert "Sunday" in hint

    def test_hint_defers_to_clear_handwriting(self):
        assert "transcribe what is written" in date_hint(date(2026, 9, 20))


class TestGetPrompt:
    def test_no_arguments_returns_default(self):
        assert get_prompt() == DEFAULT_PROMPT

    def test_expected_date_appends_hint(self):
        prompt = get_prompt(expected_date=date(2026, 9, 20))
        assert prompt.startswith(DEFAULT_PROMPT)
        assert date_hint(date(2026, 9, 20)) in prompt

    def test_hint_and_additional_instructions_both_present(self):
        prompt = get_prompt("Keep Cyrillic as is.", expected_date=date(2026, 9, 20))
        assert "Additional instructions: Keep Cyrillic as is." in prompt
        assert "2026-09-20" in prompt


class TestTranscriberUsesHint:
    def test_single_page_prompt_contains_hint(self):
        provider = RecordingProvider()
        config = TranscriptionConfig(batch_size=1, expected_date=date(2026, 9, 20))
        Transcriber(provider, config).transcribe_images(make_images(1))
        assert "2026-09-20" in provider.prompts[0]

    def test_batch_prompt_contains_hint(self):
        provider = RecordingProvider()
        config = TranscriptionConfig(batch_size=3, expected_date=date(2026, 9, 20))
        Transcriber(provider, config).transcribe_images(make_images(3))
        assert "2026-09-20" in provider.prompts[0]

    def test_no_hint_without_expected_date(self):
        provider = RecordingProvider()
        Transcriber(provider, TranscriptionConfig(batch_size=1)).transcribe_images(make_images(1))
        assert "Date context" not in provider.prompts[0]
