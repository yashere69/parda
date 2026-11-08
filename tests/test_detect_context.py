"""Detector behaviour that depends on the words around a number."""

import json
from pathlib import Path

import pytest

from parda.detect import detect

ROOT = Path(__file__).resolve().parent.parent


def kinds(text):
    return [(s.kind, s.value) for s in detect(text)]


@pytest.mark.parametrize(
    "text, expected",
    [
        # regressions from the benchmark: 3-3-4 grouping was never detected...
        ("mera number 987 654 3210", [("PHONE", "9876543210")]),
        ("+91 987-654-3210 pe whatsapp", [("PHONE", "9876543210")]),
        # ...and ten-digit order ids were redacted as phone numbers
        ("order id 8561304451 check karo", []),
        ("AWB 7894561230 track karo", []),
        ("invoice 9876543210 aur mera mobile 9123456789", [("PHONE", "9123456789")]),
        # the nearest keyword decides
        ("order ke liye call karo 98765 43210", [("PHONE", "9876543210")]),
        # account numbers stay redacted: better a wrong label than a leak
        ("account no 9876543210", [("PHONE", "9876543210")]),
        # regression from the held-out set: wa.me/91... read as an Aadhaar number
        ("chat here wa.me/916546507669", [("PHONE", "6546507669")]),
        ("Aadhaar 9165 4650 7669", [("AADHAAR", "916546507669")]),
    ],
)
def test_context(text, expected):
    assert kinds(text) == expected


def test_heldout_set_does_not_regress():
    """examples/heldout.jsonl was written after tuning, in other words. Known misses
    (landlines, 2-2-2-2-2 grouping) are listed in the README; anything else is a bug."""
    rows = [
        json.loads(x) for x in (ROOT / "examples/heldout.jsonl").read_text("utf-8").splitlines()
    ]
    fp, fn = [], []
    for row in rows:
        got, truth = set(kinds(row["text"])), {tuple(t) for t in row["truth"]}
        fp += [(x, row["text"]) for x in got - truth]
        fn += [(x, row["text"]) for x in truth - got]
    assert fp == []
    assert all("landline" in t or t.count("-") == 4 for _, t in fn), fn
    assert len(fn) == 6
