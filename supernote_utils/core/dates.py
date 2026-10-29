"""Date handling for dated notes: the date in a filename, and the date header in a transcription.

Journal-style notes usually open with a handwritten date header ("2026-09-20 SUN 06:32"). Vision
models misread the year digits of such headers, and may then shift the day or weekday to make the
misread date self-consistent. When the filename carries the date, it can be passed to the model as a
hint and used afterwards to check what the model wrote.
"""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Plausible years only, so that arbitrary 8-digit IDs in filenames are not read as dates.
MIN_YEAR, MAX_YEAR = 1990, 2100

FILENAME_DATE = re.compile(r"(?<!\d)(\d{4})-?(\d{2})-?(\d{2})(?!\d)")
HEADER_DATE = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)(?:\s+([A-Za-z]+))?")

HEADER_SEARCH_LINES = 5


@dataclass(frozen=True)
class HeaderDate:
    """A date found at the top of a transcription.

    Attributes:
        text: The matched text, including the weekday if one follows the date.
        date: The date, or None if the digits do not form a valid calendar date.
        weekday: The weekday token as written (e.g. "SUN", "Thur"), or None if absent.
    """

    text: str
    date: Optional[date]
    weekday: Optional[str]


def _make_date(year: str, month: str, day: str) -> Optional[date]:
    """Build a date from digit strings, or return None if it is not a valid date."""
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def date_from_filename(path: Path) -> Optional[date]:
    """Return the date encoded in a filename (YYYYMMDD or YYYY-MM-DD), if any.

    Only the file's stem is searched, not its directories.

    Args:
        path: Input file path, e.g. "Pages 20260920.note".

    Returns:
        The date, or None if the stem holds no valid date in a plausible year.
    """
    for match in FILENAME_DATE.finditer(path.stem):
        found = _make_date(*match.groups())
        if found and MIN_YEAR <= found.year <= MAX_YEAR:
            return found
    return None


def parse_weekday(token: str) -> Optional[int]:
    """Return the weekday number (Monday=0) for a written weekday, or None.

    Accepts full names and abbreviations of three or more letters ("SUN", "Tues", "Thur").

    Args:
        token: A word that may name a weekday.

    Returns:
        The weekday number, or None if the token is not a weekday.
    """
    word = token.lower()
    if len(word) < 3:
        return None
    for number, name in enumerate(WEEKDAYS):
        if name.startswith(word):
            return number
    return None


def find_header_date(text: str, max_lines: int = HEADER_SEARCH_LINES) -> Optional[HeaderDate]:
    """Find the first YYYY-MM-DD date in the first non-empty lines of a transcription.

    Args:
        text: Transcribed text.
        max_lines: How many non-empty lines to search.

    Returns:
        The first date found, with its weekday if one follows it, or None if there is none.
    """
    lines = [line for line in text.splitlines() if line.strip()][:max_lines]
    for line in lines:
        match = HEADER_DATE.search(line)
        if not match:
            continue
        year, month, day, word = match.groups()
        if word and parse_weekday(word) is not None:
            return HeaderDate(match.group(0), _make_date(year, month, day), word)
        return HeaderDate(f"{year}-{month}-{day}", _make_date(year, month, day), None)
    return None


def check_header_date(text: str, expected: date) -> List[str]:
    """Compare a transcription's date header with the expected date.

    Reports problems for a person to review; never changes the text. A late-night entry may
    legitimately be headed with the next day, so a mismatch is a prompt to look, not proof of error.

    Args:
        text: Transcribed text.
        expected: The date the note is expected to carry (usually from its filename).

    Returns:
        Warning messages; empty if the header matches.
    """
    expected_desc = f"{expected.isoformat()} ({WEEKDAYS[expected.weekday()].capitalize()})"
    found = find_header_date(text)
    if found is None:
        return [f"no date found in the first {HEADER_SEARCH_LINES} lines (expected {expected_desc})"]
    if found.date is None:
        return [f'header date "{found.text}" is not a valid date (expected {expected_desc})']

    warnings = []
    if found.date != expected:
        warnings.append(
            f'header date "{found.text}" differs from the expected date {expected_desc}'
        )
    if found.weekday is not None and parse_weekday(found.weekday) != found.date.weekday():
        actual = WEEKDAYS[found.date.weekday()].capitalize()
        warnings.append(
            f'header weekday "{found.weekday}" does not match {found.date.isoformat()}, a {actual}'
        )
    return warnings
