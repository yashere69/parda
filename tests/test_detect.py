import pytest

from parda.checksums import gstin_check_char, verhoeff_check_digit
from parda.detect import Span, detect

AADHAAR = "23456789012" + verhoeff_check_digit("23456789012")
GSTIN = "27AAPFU0939F1ZV"


def kinds(text):
    return [(s.kind, s.value) for s in detect(text)]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("call 9876543210", [("PHONE", "9876543210")]),
        ("call +91 98765 43210", [("PHONE", "9876543210")]),
        ("call 098765-43210", [("PHONE", "9876543210")]),
        ("call ९८७६५ ४३२१०", [("PHONE", "9876543210")]),
        ("PAN abcpe1234f", [("PAN", "ABCPE1234F")]),
        (f"GSTIN {GSTIN}", [("GSTIN", GSTIN)]),
        ("IFSC HDFC0001234", [("IFSC", "HDFC0001234")]),
        ("pay asha.k@okicici", [("UPI", "asha.k@okicici")]),
        ("pay 9876543210@ybl", [("UPI", "9876543210@ybl")]),
        ("mail asha@example.com", [("EMAIL", "asha@example.com")]),
        (f"aadhaar {AADHAAR[:4]} {AADHAAR[4:8]} {AADHAAR[8:]}", [("AADHAAR", AADHAAR)]),
        ("card 4111 1111 1111 1111", [("CARD", "4111111111111111")]),
        ("pincode 248001", [("PIN", "248001")]),
    ],
)
def test_detects(text, expected):
    assert kinds(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "order #KC1042 kab aayega",
        "price ₹1,499 hai",
        "size 38 aur 40",
        "Dehradun 248001",  # a PIN needs a nearby cue word
        "meeting 12/03/2026 10:30",
        "27AAPFU0939F1ZW",  # bad GSTIN check character
    ],
)
def test_ignores(text):
    assert kinds(text) == []


def test_twelve_digits_failing_verhoeff_are_not_aadhaar():
    bad = AADHAAR[:-1] + str((int(AADHAAR[-1]) + 1) % 10)
    assert ("AADHAAR", bad) not in kinds(f"invoice {bad}")


def test_gstin_wins_over_the_pan_inside_it():
    assert kinds(f"bill to {GSTIN}") == [("GSTIN", GSTIN)]


def test_extra_spans_merge_and_longest_wins():
    text = "Asha Sharma, 9876543210"
    extra = [Span(0, 11, "NAME", "Asha Sharma")]
    assert kinds_with(text, extra) == [("NAME", "Asha Sharma"), ("PHONE", "9876543210")]


def kinds_with(text, extra):
    return [(s.kind, s.value) for s in detect(text, extra)]


def test_check_char_helper_is_consistent():
    first = "07ABCPE1234F1Z"
    assert kinds(f"GSTIN {first}{gstin_check_char(first)}")[0][0] == "GSTIN"
