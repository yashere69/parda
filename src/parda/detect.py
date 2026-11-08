"""Detect Indian personal identifiers in free text.

Every detector is a regex for the shape plus, where one exists, the official check digit.
Overlaps are resolved by keeping the longest span, so a GSTIN (which contains a PAN) is
reported once as a GSTIN, and a UPI ID like 9876543210@ybl as UPI, not PHONE.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass

from .checksums import aadhaar_valid, gstin_valid, luhn_valid
from .numbers import spoken_numbers, to_ascii_digits


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    kind: str
    value: str  # canonical form: digits only for numbers, upper case for codes


_B = r"(?<![\w@])"  # left boundary that also refuses the middle of an email or UPI id
_E = r"(?![\w@])"

PAN_HOLDER_TYPES = "ABCFGHJLPT"
_PAN = re.compile(rf"{_B}[A-Z]{{3}}[{PAN_HOLDER_TYPES}][A-Z][0-9]{{4}}[A-Z]{_E}", re.I)
_GSTIN = re.compile(rf"{_B}[0-9]{{2}}[A-Z]{{5}}[0-9]{{4}}[A-Z][1-9A-Z]Z[0-9A-Z]{_E}", re.I)
_IFSC = re.compile(rf"{_B}[A-Z]{{4}}0[A-Z0-9]{{6}}{_E}", re.I)
_EMAIL = re.compile(rf"{_B}[\w.+-]+@[\w-]+(\.[\w-]+)+{_E}")
_UPI = re.compile(rf"{_B}[\w.-]{{2,256}}@[a-zA-Z][a-zA-Z0-9]{{1,63}}(?![\w@.])")
_AADHAAR = re.compile(rf"{_B}[2-9][0-9]{{3}}[ -]?[0-9]{{4}}[ -]?[0-9]{{4}}{_E}")
_PHONE = re.compile(
    rf"{_B}(?:\+?91[ -]?|0)?"
    rf"(?:[6-9][0-9]{{4}}[ -]?[0-9]{{5}}|[6-9][0-9]{{2}}[ .-][0-9]{{3}}[ .-][0-9]{{4}}){_E}"
)
# A ten-digit number right after one of these is a reference, not a phone: "order id
# 8561304451". The nearest keyword before the number decides, so "order ke liye call karo
# 98765 43210" is still a phone. Account numbers are deliberately not in the list.
_REFERENCE = re.compile(
    r"\b(order|invoice|inv|awb|tracking|track|ref|reference|txn|transaction|utr|booking"
    r"|pnr|ticket|receipt|consignment|docket|shipment|sku)\b|ऑर्डर",
    re.I,
)
_CALLABLE = re.compile(r"\b(call|phone|mobile|mob|whatsapp|contact|cell|sms)\b|फोन|कॉल", re.I)
_CARD = re.compile(rf"{_B}(?:[0-9][ -]?){{12,18}}[0-9]{_E}")
_PIN = re.compile(rf"{_B}[1-9][0-9]{{2}} ?[0-9]{{3}}{_E}")
_PIN_CONTEXT = re.compile(r"\b(pin|pincode|pin code|postal|zip)\b|पिन", re.I)


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _phone_value(raw: str) -> str:
    d = _digits(raw)
    return d[-10:]


Detector = Callable[[str, str], list[Span]]


def _regex(kind: str, rx: re.Pattern[str], ok: Callable[[str], bool], canon: Callable[[str], str]):
    def run(original: str, ascii_text: str) -> list[Span]:
        out = []
        for m in rx.finditer(ascii_text):
            raw = m.group()
            if ok(raw):
                out.append(Span(m.start(), m.end(), kind, canon(raw)))
        return out

    return run


def _phone(original: str, ascii_text: str) -> list[Span]:
    out = []
    for m in _PHONE.finditer(ascii_text):
        window = ascii_text[max(0, m.start() - 30) : m.start()]
        ref = [x.end() for x in _REFERENCE.finditer(window)]
        call = [x.end() for x in _CALLABLE.finditer(window)]
        if ref and (not call or ref[-1] > call[-1]):
            continue
        out.append(Span(m.start(), m.end(), "PHONE", _phone_value(m.group())))
    return out


_AADHAAR_WORDS = re.compile(r"\b(aadhaar|aadhar|adhar|uid|uidai|kyc)\b|आधार", re.I)
_PHONE_PREFIX = re.compile(r"(\+|wa\.me/|tel:)$", re.I)


def _aadhaar(original: str, ascii_text: str) -> list[Span]:
    """Twelve digits with a valid Verhoeff check digit, unless they read as 91 plus a mobile
    number in a phone context: one in ten +91 numbers passes the Aadhaar check by chance."""
    out = []
    for m in _AADHAAR.finditer(ascii_text):
        d = _digits(m.group())
        if not aadhaar_valid(d):
            continue
        if d.startswith("91") and d[2] in "6789":
            before = ascii_text[max(0, m.start() - 30) : m.start()]
            said_aadhaar = [x.end() for x in _AADHAAR_WORDS.finditer(before)]
            said_phone = [x.end() for x in _CALLABLE.finditer(before)]
            if _PHONE_PREFIX.search(before) or (
                said_phone and (not said_aadhaar or said_phone[-1] > said_aadhaar[-1])
            ):
                continue
        out.append(Span(m.start(), m.end(), "AADHAAR", d))
    return out


def _pin(original: str, ascii_text: str) -> list[Span]:
    out = []
    for m in _PIN.finditer(ascii_text):
        window = ascii_text[max(0, m.start() - 30) : m.start()]
        if _PIN_CONTEXT.search(window):
            out.append(Span(m.start(), m.end(), "PIN", _digits(m.group())))
    return out


def _spoken(original: str, ascii_text: str) -> list[Span]:
    out = []
    for s in spoken_numbers(original):
        d = s.digits
        if len(d) == 12 and aadhaar_valid(d):
            out.append(Span(s.start, s.end, "AADHAAR", d))
        elif len(d) in (10, 12) and d[-10] in "6789" and (len(d) == 10 or d.startswith("91")):
            out.append(Span(s.start, s.end, "PHONE", d[-10:]))
        elif len(d) == 6 and _PIN_CONTEXT.search(ascii_text[max(0, s.start - 30) : s.start]):
            out.append(Span(s.start, s.end, "PIN", d))
    return out


DETECTORS: list[Detector] = [
    _regex("GSTIN", _GSTIN, lambda r: gstin_valid(r), str.upper),
    _regex("PAN", _PAN, lambda r: True, str.upper),
    _regex("IFSC", _IFSC, lambda r: True, str.upper),
    _regex("EMAIL", _EMAIL, lambda r: True, str.lower),
    _regex("UPI", _UPI, lambda r: True, str.lower),
    _aadhaar,
    _regex(
        "CARD", _CARD, lambda r: 13 <= len(_digits(r)) <= 19 and luhn_valid(_digits(r)), _digits
    ),
    _phone,
    _pin,
    _spoken,
]


def detect(
    text: str,
    extra: list[Span] | None = None,
    ignore: list[re.Pattern[str]] | None = None,
) -> list[Span]:
    """All non-overlapping spans, longest first wins.

    `extra` merges spans from another detector (Presidio, a name recogniser) into the same
    pass. `ignore` drops any span whose matched text fully matches one of the patterns:
    your own order-id format, say, which would otherwise look like a phone number.
    """
    ascii_text = to_ascii_digits(text)
    spans = [s for det in DETECTORS for s in det(text, ascii_text)] + list(extra or [])
    if ignore:
        spans = [
            s
            for s in spans
            if not any(rx.fullmatch(text[s.start : s.end].strip()) for rx in ignore)
        ]
    spans.sort(key=lambda s: (-(s.end - s.start), s.start))
    # Keep a span only if it doesn't overlap one already kept. `starts` stays sorted, so each
    # check is a bisect against the two neighbours instead of a scan of everything kept.
    starts: list[int] = []
    ends: list[int] = []
    taken: list[Span] = []
    for s in spans:
        i = bisect_left(starts, s.start)
        if i > 0 and ends[i - 1] > s.start:
            continue
        if i < len(starts) and starts[i] < s.end:
            continue
        starts.insert(i, s.start)
        ends.insert(i, s.end)
        taken.append(s)
    return sorted(taken, key=lambda s: s.start)
