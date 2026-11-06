"""Find numbers that are written out the way people speak or type them in India.

    "mera number nau aath double seven ..."     romanised Hindi and English digit words
    "९८७६५ ४३२१०"                               Devanagari digits
    "98 76 54 32 10"                            spaced groups

Devanagari digits are one code point each, so they are translated in place and offsets
don't move. Spoken runs are found as token sequences and converted to a digit string;
the span returned covers the original words, so redaction replaces exactly what was said.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

WORD_DIGITS = {
    # English
    "zero": "0",
    "oh": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    # Romanised Hindi (common spellings)
    "shunya": "0",
    "sunya": "0",
    "ek": "1",
    "do": "2",
    "teen": "3",
    "tin": "3",
    "char": "4",
    "chaar": "4",
    "paanch": "5",
    "panch": "5",
    "chhe": "6",
    "chhah": "6",
    "chah": "6",
    "che": "6",
    "saat": "7",
    "sat": "7",
    "aath": "8",
    "ath": "8",
    "nau": "9",
    # Devanagari words
    "शून्य": "0",
    "एक": "1",
    "दो": "2",
    "तीन": "3",
    "चार": "4",
    "पांच": "5",
    "पाँच": "5",
    "छह": "6",
    "छः": "6",
    "सात": "7",
    "आठ": "8",
    "नौ": "9",
}
REPEATERS = {"double": 2, "triple": 3, "डबल": 2, "ट्रिपल": 3}

# Devanagari vowel signs are combining marks, not \w, so the script gets its own class.
_TOKEN = re.compile(r"[0-9०-९]+|[\u0900-\u0963\u0970-\u097F]+|[^\W\d_]+")
_GAP = re.compile(r"^[\s,.\-/]*$")


@dataclass
class SpokenNumber:
    start: int
    end: int
    digits: str


def to_ascii_digits(text: str) -> str:
    """Translate Devanagari digits to ASCII. Same length, same offsets."""
    return text.translate(DEVANAGARI_DIGITS)


def spoken_numbers(text: str, min_digits: int = 6) -> list[SpokenNumber]:
    """Runs of digit words and digit groups that add up to at least `min_digits` digits.

    A run must contain at least one word ("nau", "double", "सात"); runs of plain digits are
    left to the regex detectors. Short runs are ignored because "do", "che" and "sat" are
    also ordinary words.
    """
    found: list[SpokenNumber] = []
    start = end = -1
    digits = ""
    has_word = False
    repeat = 1
    prev_end = 0

    def flush() -> None:
        nonlocal start, digits, has_word, repeat
        if start >= 0 and has_word and len(digits) >= min_digits:
            found.append(SpokenNumber(start, end, digits))
        start, digits, has_word, repeat = -1, "", False, 1

    for m in _TOKEN.finditer(text):
        tok = m.group().lower()
        if start >= 0 and not _GAP.match(text[prev_end : m.start()]):
            flush()
        prev_end = m.end()
        if tok in REPEATERS:
            if start < 0:
                start = m.start()
            end, repeat, has_word = m.end(), REPEATERS[tok], True
            continue
        if tok in WORD_DIGITS:
            value, has_word = WORD_DIGITS[tok], True
        elif tok.isdigit():
            value = to_ascii_digits(tok)
        else:
            flush()
            continue
        if start < 0:
            start = m.start()
        # "double 7" repeats one digit; "double 77" is read as written
        digits += value * repeat if len(value) == 1 else value
        end, repeat = m.end(), 1
    flush()
    return found
