"""Tests for the transcribe command's date hint and header-date check.

The provider is replaced by a recording mock — no LLM calls.
"""

import argparse
from datetime import date
from pathlib import Path
from typing import List

import pytest
from PIL import Image

from supernote_utils.cli import transcribe as transcribe_cli
from supernote_utils.cli.main import date_hint_arg
from supernote_utils.cli.transcribe import resolve_expected_date, transcribe_file
from supernote_utils.providers.base import VisionProvider


class RecordingProvider(VisionProvider):
    """Mock provider that records prompts and returns a fixed transcription."""

    def __init__(self, response: str):
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


def make_args(inputs: List[Path], **overrides) -> argparse.Namespace:
    values = dict(
        input=[str(p) for p in inputs], output=None, directory=None, format="markdown",
        plain_text=False, model="mock", temperature=1.0, batch_size=5, page_separator=False,
        pdf=None, force_render=False, dpi=150, date_hint="auto",
    )
    values.update(overrides)
    return argparse.Namespace(**values)


@pytest.fixture
def dated_png(tmp_path: Path) -> Path:
    path = tmp_path / "Pages 20260920.png"
    Image.new("RGB", (20, 20), color=(255, 255, 255)).save(path)
    return path


def use_provider(monkeypatch, response: str) -> RecordingProvider:
    provider = RecordingProvider(response)
    monkeypatch.setattr(transcribe_cli, "_build_provider", lambda args: provider)
    return provider


class TestDateHintArg:
    @pytest.mark.parametrize("value", ["auto", "off"])
    def test_keywords(self, value):
        assert date_hint_arg(value) == value

    def test_iso_date(self):
        assert date_hint_arg("2026-01-02") == "2026-01-02"

    @pytest.mark.parametrize("value", ["yesterday", "2026-13-01", "20260102"])
    def test_invalid(self, value):
        with pytest.raises(argparse.ArgumentTypeError):
            date_hint_arg(value)


class TestResolveExpectedDate:
    def test_auto_reads_filename(self):
        assert resolve_expected_date("auto", Path("Pages 20260920.note")) == date(2026, 9, 20)

    def test_auto_without_filename_date(self):
        assert resolve_expected_date("auto", Path("journal.note")) is None

    def test_off(self):
        assert resolve_expected_date("off", Path("Pages 20260920.note")) is None

    def test_explicit_date_overrides_filename(self):
        assert resolve_expected_date("2026-01-02", Path("Pages 20260920.note")) == date(2026, 1, 2)


class TestPerFileMode:
    def test_hint_from_filename_reaches_prompt(self, monkeypatch, dated_png):
        provider = use_provider(monkeypatch, "**2026-09-20 SUN 06:32**\n\nText.")
        transcribe_file(make_args([dated_png]))
        assert "2026-09-20" in provider.prompts[0]

    def test_matching_header_gives_no_warning(self, monkeypatch, dated_png, capsys):
        use_provider(monkeypatch, "**2026-09-20 SUN 06:32**\n\nText.")
        transcribe_file(make_args([dated_png]))
        assert "Warning" not in capsys.readouterr().err

    def test_mismatched_header_warns_and_keeps_output(self, monkeypatch, dated_png, capsys):
        use_provider(monkeypatch, "**2024-09-22 SUN 06:32**\n\nText.")
        transcribe_file(make_args([dated_png]))
        err = capsys.readouterr().err
        assert "Warning" in err and "2024-09-22" in err and str(dated_png) in err
        out = dated_png.with_suffix(".md").read_text(encoding="utf-8")
        assert out.startswith("**2024-09-22 SUN 06:32**")  # warned about, never rewritten

    def test_off_disables_hint_and_check(self, monkeypatch, dated_png, capsys):
        provider = use_provider(monkeypatch, "**2024-09-22 SUN 06:32**\n\nText.")
        transcribe_file(make_args([dated_png], date_hint="off"))
        assert "Date context" not in provider.prompts[0]
        assert "Warning" not in capsys.readouterr().err


class TestCombinedMode:
    def test_mismatched_header_warns(self, monkeypatch, dated_png, tmp_path, capsys):
        use_provider(monkeypatch, "2024-09-22 SUN\n\nText.")
        transcribe_file(make_args([dated_png], output=str(tmp_path / "all.md")))
        err = capsys.readouterr().err
        assert "Warning" in err and "2024-09-22" in err
