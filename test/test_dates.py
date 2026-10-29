"""Tests for date handling: filename dates, header detection, and the header check."""

from datetime import date
from pathlib import Path

import pytest

from supernote_utils.core.dates import (
    HeaderDate,
    check_header_date,
    date_from_filename,
    find_header_date,
    parse_weekday,
)


class TestDateFromFilename:
    def test_compact_date_in_stem(self):
        assert date_from_filename(Path("Pages 20260920.note")) == date(2026, 9, 20)

    def test_suffix_letter_after_date(self):
        assert date_from_filename(Path("Pages 20260913a.note")) == date(2026, 9, 13)

    def test_suffix_words_after_date(self):
        assert date_from_filename(Path("Pages 20260824 plans.note")) == date(2026, 8, 24)

    def test_dashed_date(self):
        assert date_from_filename(Path("scan 2026-09-20.pdf")) == date(2026, 9, 20)

    def test_directory_part_is_ignored(self):
        assert date_from_filename(Path("/notes/20250101/page.note")) is None

    def test_no_date(self):
        assert date_from_filename(Path("journal.note")) is None

    def test_impossible_date(self):
        assert date_from_filename(Path("Pages 20261332.note")) is None

    def test_longer_digit_run_is_not_a_date(self):
        assert date_from_filename(Path("IMG_202609201.png")) is None

    def test_implausible_year(self):
        assert date_from_filename(Path("id 12340101.png")) is None


class TestParseWeekday:
    @pytest.mark.parametrize("token,expected", [
        ("SUN", 6), ("Sun", 6), ("sunday", 6),
        ("MON", 0), ("TUE", 1), ("Tues", 1), ("WED", 2),
        ("THU", 3), ("Thur", 3), ("Thurs", 3), ("FRI", 4), ("SAT", 5),
    ])
    def test_recognized(self, token, expected):
        assert parse_weekday(token) == expected

    @pytest.mark.parametrize("token", ["at", "sa", "sunny", "month", "friend", "wedding", ""])
    def test_not_a_weekday(self, token):
        assert parse_weekday(token) is None


class TestFindHeaderDate:
    def test_bold_header_with_weekday(self):
        found = find_header_date("**2026-09-20 SUN 06:32**\n\nSome text.")
        assert found == HeaderDate(text="2026-09-20 SUN", date=date(2026, 9, 20), weekday="SUN")

    def test_header_without_weekday(self):
        found = find_header_date("2026-09-13 02:09\n\nText.")
        assert found.date == date(2026, 9, 13)
        assert found.weekday is None

    def test_word_after_date_is_not_taken_as_weekday(self):
        found = find_header_date("2026-09-20 at the cafe")
        assert found.weekday is None
        assert found.text == "2026-09-20"

    def test_leading_blank_line(self):
        found = find_header_date("\n**2025-11-04 TUE 7:27**\nText.")
        assert found.date == date(2025, 11, 4)

    def test_no_date(self):
        assert find_header_date("Just some text\nwithout dates.") is None

    def test_date_beyond_search_window_is_ignored(self):
        text = "\n".join(["line"] * 5 + ["2026-09-20 SUN"])
        assert find_header_date(text) is None

    def test_invalid_date_is_reported_with_none(self):
        found = find_header_date("2026-02-30 MON")
        assert found.text == "2026-02-30 MON"
        assert found.date is None


class TestCheckHeaderDate:
    expected = date(2026, 9, 20)  # a Sunday

    def test_matching_header_has_no_warnings(self):
        assert check_header_date("**2026-09-20 SUN 06:32**", self.expected) == []

    def test_matching_header_without_weekday_has_no_warnings(self):
        assert check_header_date("2026-09-20 06:32", self.expected) == []

    def test_wrong_year(self):
        warnings = check_header_date("2024-09-20 SUN", self.expected)
        assert len(warnings) == 2  # wrong date, and SUN does not fit 2024-09-20 (a Friday)
        assert "2024-09-20" in warnings[0] and "2026-09-20" in warnings[0]

    def test_wrong_year_with_reconciled_day(self):
        # The observed failure: year misread, then the day shifted to fit the weekday.
        warnings = check_header_date("**2024-09-22 SUN 06:32**", self.expected)
        assert len(warnings) == 1
        assert "2024-09-22" in warnings[0]

    def test_weekday_inconsistent_with_date(self):
        warnings = check_header_date("2026-09-20 TUE", self.expected)
        assert len(warnings) == 1
        assert "TUE" in warnings[0] and "Sunday" in warnings[0]

    def test_no_date_found(self):
        warnings = check_header_date("No header here.", self.expected)
        assert len(warnings) == 1
        assert "no date" in warnings[0]

    def test_invalid_date(self):
        warnings = check_header_date("2026-02-30 MON", self.expected)
        assert len(warnings) == 1
        assert "not a valid date" in warnings[0]
