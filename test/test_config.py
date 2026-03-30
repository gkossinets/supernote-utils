"""Tests for TranscriptionConfig and VisionProvider validation."""

import pytest

from supernote_utils.config import TranscriptionConfig
from supernote_utils.providers.base import VisionProvider


class TestTranscriptionConfig:
    def test_defaults(self):
        cfg = TranscriptionConfig()
        assert cfg.temperature == 1.0
        assert cfg.page_separator is False
        assert cfg.additional_prompt == ""
        assert cfg.batch_size == 3

    def test_valid_temperature_boundaries(self):
        TranscriptionConfig(temperature=0.0)
        TranscriptionConfig(temperature=2.0)

    def test_temperature_below_zero_raises(self):
        with pytest.raises(ValueError, match="Temperature"):
            TranscriptionConfig(temperature=-0.1)

    def test_temperature_above_two_raises(self):
        with pytest.raises(ValueError, match="Temperature"):
            TranscriptionConfig(temperature=2.1)

    def test_batch_size_zero_raises(self):
        with pytest.raises(ValueError, match="Batch size"):
            TranscriptionConfig(batch_size=0)

    def test_batch_size_negative_raises(self):
        with pytest.raises(ValueError, match="Batch size"):
            TranscriptionConfig(batch_size=-1)

    def test_batch_size_one_is_valid(self):
        cfg = TranscriptionConfig(batch_size=1)
        assert cfg.batch_size == 1


class TestVisionProviderTemperatureValidation:
    """VisionProvider rejects invalid temperatures at construction."""

    def _make_provider(self, temperature: float) -> VisionProvider:
        """Build a minimal concrete subclass to test base class validation."""
        class _DummyProvider(VisionProvider):
            def transcribe_image(self, image, prompt): return ""
            def is_available(self): return True
            def get_display_name(self): return "Dummy"

        return _DummyProvider(temperature=temperature)

    def test_valid_temperature(self):
        self._make_provider(0.5)

    def test_temperature_zero_is_valid(self):
        self._make_provider(0.0)

    def test_temperature_two_is_valid(self):
        self._make_provider(2.0)

    def test_temperature_below_zero_raises(self):
        with pytest.raises(ValueError, match="Temperature"):
            self._make_provider(-0.1)

    def test_temperature_above_two_raises(self):
        with pytest.raises(ValueError, match="Temperature"):
            self._make_provider(2.1)
