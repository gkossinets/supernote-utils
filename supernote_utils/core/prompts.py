"""
Shared transcription prompts for handwriting OCR tasks.
"""

from datetime import date
from typing import Optional

from supernote_utils.core.dates import WEEKDAYS

DEFAULT_PROMPT = """You are performing OCR (Optical Character Recognition) on a personal handwritten note image. This is an original handwritten document, not published or copyrighted text. Your task is to analyze the handwriting and transcribe the visual content you see into digital text.

Your two most important goals are **semantic fidelity** (the transcription must mean the same thing as the handwritten content) and **output purity** (you must only output the transcription).

**Output Purity: Provide ONLY the transcribed text as standard Markdown. Absolutely no introductions, summaries, or commentary.**

**1. Guiding Principles for Transcription**

* **Logic is Law:** The final transcription of any sentence **must** make logical sense. Be skeptical of odd phrases. For example, a phrase like "moon year" is less probable in a personal journal than "mood repair." Prioritize the interpretation that fits the context of personal reflection over a simple visual match. This applies to words and phrases, not to dates, times, or numbers (see section 3).
* **The Conservative Principle for Proper Nouns (Very Important):**
    * Proper nouns are the most common source of error. **Do not guess or substitute a more common name.**
    * If a name is highly ambiguous, transcribe it phonetically as best as you can, even if it does not form a known word. It is better to have a close phonetic match than a completely different name.
* **Context Over Shape:** Use the surrounding context to resolve ambiguity. A word in a "scary legend" is more likely to be "witch" than "wheel," even if the handwriting is unclear. "Writing" is more probable than "Ugh" near "filmmaking".

**2. Formatting Rules (Strict)**

* **Paragraphs:** Join all lines in a visually contiguous block of text into a single flowing paragraph. Separate distinct text blocks with one blank line.
* **Headers:** Use Markdown bolding for headers (highlighted inverted text). **Do not** use '#' heading symbols.
* **Highlighting & Symbols:** Pay extremely close attention to special formatting.
    * Only enclose text in `==highlight tags==` if it is explicitly highlighted.
    * Accurately place all symbols like em-dashes (—), exclamation points (!), and stars (☆ or ★).

**3. Dates, Times, and Numbers (Strict)**

* Transcribe every date, time, and number digit by digit, exactly as written. Do not normalize, complete, or "correct" them.
* Never change a date, year, or weekday to make them agree with each other or with the surrounding text. If a written date and weekday seem inconsistent, transcribe both exactly as written.
* Handwritten digits are easy to confuse (6 with 0 or 4, 1 with 7). Read each digit of a year; do not fill it in with a familiar or likely-looking year.

**Final Review:** Before concluding, perform one last check of your output, specifically for misspelled proper nouns, for dates that are not exactly as written, and to ensure no introductory commentary has been added.
"""


def date_hint(expected_date: date) -> str:
    """
    Build the prompt paragraph that tells the model which date the note is expected to carry.

    Args:
        expected_date: The date the note's header is expected to show (usually from its filename)

    Returns:
        Prompt text naming the date and its weekday
    """
    return (
        f"**Date context:** This note comes from a file dated {expected_date.isoformat()} "
        f"(a {WEEKDAYS[expected_date.weekday()].capitalize()}). Entry headers usually carry this date, or the next "
        "day for entries written after midnight. Use it only to resolve digits in a date that you "
        "cannot read confidently. If the handwriting clearly shows a different date, transcribe "
        "what is written."
    )


def get_prompt(additional_instructions: str = "", expected_date: Optional[date] = None) -> str:
    """
    Get transcription prompt with an optional date hint and additional instructions.

    Args:
        additional_instructions: Additional instructions to append to the default prompt
        expected_date: If given, a paragraph naming this date is appended as a hint for date headers

    Returns:
        Complete transcription prompt
    """
    prompt = DEFAULT_PROMPT
    if expected_date:
        prompt = f"{prompt}\n{date_hint(expected_date)}\n"
    if additional_instructions:
        return f"{prompt}\n\nAdditional instructions: {additional_instructions}\n\n"
    return prompt
