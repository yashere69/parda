import pytest

from parda.checksums import (
    aadhaar_valid,
    gstin_check_char,
    gstin_valid,
    luhn_valid,
    verhoeff_check_digit,
    verhoeff_valid,
)


def test_verhoeff_reference_vector():
    # the textbook example: check digit of 236 is 3
    assert verhoeff_check_digit("236") == "3"
    assert verhoeff_valid("2363") and not verhoeff_valid("2364")


@pytest.mark.parametrize("body", ["23456789012", "98765432101", "50000000000"])
def test_generated_check_digit_validates(body):
    assert verhoeff_valid(body + verhoeff_check_digit(body))


def test_verhoeff_catches_adjacent_transposition():
    n = "23456789012" + verhoeff_check_digit("23456789012")
    swapped = n[:3] + n[4] + n[3] + n[5:]
    assert not verhoeff_valid(swapped)


def test_aadhaar_rules():
    body = "23456789012"
    good = body + verhoeff_check_digit(body)
    assert aadhaar_valid(good)
    assert not aadhaar_valid("1" + good[1:])  # cannot start with 0 or 1
    assert not aadhaar_valid(good[:-1])


def test_gstin_published_sample():
    # 27AAPFU0939F1ZV is the sample GSTIN used in GST portal documentation
    assert gstin_check_char("27AAPFU0939F1Z") == "V"
    assert gstin_valid("27AAPFU0939F1ZV")
    assert gstin_valid("27aapfu0939f1zv")
    assert not gstin_valid("27AAPFU0939F1ZW")
    assert not gstin_valid("40AAPFU0939F1ZV")  # no state 40


def test_luhn():
    assert luhn_valid("4111111111111111")
    assert not luhn_valid("4111111111111112")
