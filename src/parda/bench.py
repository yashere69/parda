"""Benchmarks: detection on a generated corpus, and token survival through a reply.

Everything here is generated in memory from a seed. Identifier values are random but
pass their check digits (that's what makes them detectable), so the corpus is never
written to disk.

Round-trip transforms imitate what models do to placeholders. They are simulations, chosen
from rewrites seen in practice; `live_roundtrip` runs the same check against a real
OpenAI-compatible endpoint when you have one.
"""

from __future__ import annotations

import json
import os
import random
import re
import string
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from .checksums import gstin_check_char, verhoeff_check_digit
from .vault import HINDI_LABELS, STYLES, Parda

DEV = str.maketrans("0123456789", "०१२३४५६७८९")
ENGLISH = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
HINGLISH = ["shunya", "ek", "do", "teen", "chaar", "paanch", "chhe", "saat", "aath", "nau"]


def _aadhaar(r: random.Random) -> str:
    body = str(r.randint(2, 9)) + "".join(r.choice(string.digits) for _ in range(10))
    return body + verhoeff_check_digit(body)


def _pan(r: random.Random) -> str:
    up = string.ascii_uppercase
    return (
        "".join(r.choice(up) for _ in range(3))
        + r.choice("PCF")
        + r.choice(up)
        + "".join(r.choice(string.digits) for _ in range(4))
        + r.choice(up)
    )


def _gstin(r: random.Random) -> str:
    first = f"{r.randint(1, 37):02d}" + _pan(r) + r.choice("123") + "Z"
    return first + gstin_check_char(first)


def _phone(r: random.Random) -> str:
    return r.choice("6789") + "".join(r.choice(string.digits) for _ in range(9))


def _upi(r: random.Random) -> str:
    return r.choice(["asha.k", "ravi1990", "meera.s", "kabir_r"]) + "@" + r.choice(
        ["okicici", "oksbi", "ybl", "paytm", "okaxis"]
    )


def _ifsc(r: random.Random) -> str:
    return r.choice(["HDFC", "SBIN", "ICIC", "UTIB"]) + "0" + "".join(
        r.choice(string.digits) for _ in range(6)
    )


def _phone_surface(r: random.Random, d: str) -> tuple[str, str]:
    form = r.choice(
        ["plain", "spaced", "plus91", "devanagari", "spoken", "spoken-en", "hyphen", "3-3-4"]
    )
    if form == "plain":
        return d, form
    if form == "hyphen":
        return f"{d[:5]}-{d[5:]}", form
    if form == "3-3-4":
        return f"{d[:3]} {d[3:6]} {d[6:]}", form
    if form == "spoken-en":
        return " ".join(ENGLISH[int(c)] for c in d), form
    if form == "spaced":
        return f"{d[:5]} {d[5:]}", form
    if form == "plus91":
        return f"+91 {d}", form
    if form == "devanagari":
        return f"{d[:5]} {d[5:]}".translate(DEV), form
    return " ".join(HINGLISH[int(c)] for c in d), form


def _aadhaar_surface(r: random.Random, d: str) -> tuple[str, str]:
    form = r.choice(["plain", "grouped", "devanagari"])
    grouped = f"{d[:4]} {d[4:8]} {d[8:]}"
    return {"plain": d, "grouped": grouped, "devanagari": grouped.translate(DEV)}[form], form


TEMPLATES = [
    ("PHONE", "Mera number {v} hai, call kar lena"),
    ("PHONE", "please call me on {v} after 6"),
    ("PHONE", "WhatsApp karo {v} pe"),
    ("PAN", "PAN {v} hai for the invoice"),
    ("PAN", "billing ke liye PAN: {v}"),
    ("GSTIN", "our GSTIN is {v}, please add it to the bill"),
    ("UPI", "refund {v} pe bhej do"),
    ("UPI", "UPI id {v}"),
    ("AADHAAR", "KYC ke liye Aadhaar {v} share kiya tha"),
    ("IFSC", "IFSC {v}, account details mail kar diye"),
    ("PIN", "delivery address ka pincode {v} hai"),
    ("PIN", "Rajpur Road, Dehradun {v}"),
]

NEGATIVES = [
    "order #KC{n4} kab aayega?",
    "invoice no. {n12} ka payment ho gaya",
    "price ₹1,{n3} hai na?",
    "tracking id {n10x}",
    "size 38 aur 40 dono bhejo",
    "do kurtas chahiye, ek blue ek green",
    "meeting 12/03/2026 ko 10:30 baje",
    "coupon code SAVE{n3}NOW",
    "order id {n10} check karo",
    "ref no {n12g}",
]


@dataclass
class Sample:
    text: str
    truth: list[tuple[str, str]]  # (kind, canonical value)
    form: str


def corpus(n: int = 600, seed: int = 7) -> list[Sample]:
    r = random.Random(seed)
    out: list[Sample] = []
    for _ in range(n):
        if r.random() < 0.25:
            t = r.choice(NEGATIVES)
            twelve = _aadhaar(r)
            bad12 = twelve[:-1] + str((int(twelve[-1]) + 1) % 10)  # fails Verhoeff
            text = t.format(
                n4=r.randint(1000, 9999),
                n12=bad12,
                n3=r.randint(100, 999),
                n10x="AWB" + "".join(r.choice(string.digits) for _ in range(9)),
                n10=r.choice("6789") + "".join(r.choice(string.digits) for _ in range(9)),
                n12g=" ".join(
                    "".join(r.choice(string.digits) for _ in range(4)) for _ in range(3)
                ),
            )
            out.append(Sample(text, [], "negative"))
            continue
        kind, t = r.choice(TEMPLATES)
        form = "plain"
        if kind == "PHONE":
            value = _phone(r)
            surface, form = _phone_surface(r, value)
        elif kind == "AADHAAR":
            value = _aadhaar(r)
            surface, form = _aadhaar_surface(r, value)
        elif kind == "PAN":
            value = _pan(r)
            surface = value.lower() if r.random() < 0.2 else value
            form = "lowercase" if surface != value else "plain"
        elif kind == "GSTIN":
            value = surface = _gstin(r)
        elif kind == "UPI":
            value = surface = _upi(r)
        elif kind == "IFSC":
            value = surface = _ifsc(r)
        else:
            value = surface = f"{r.randint(110, 855)}{r.randint(0, 999):03d}"
        out.append(Sample(t.format(v=surface), [(kind, value)], form))
    return out


def detection(samples: list[Sample]) -> dict:
    from .detect import detect

    per: dict[str, dict[str, int]] = {}
    forms: dict[str, list[int]] = {}
    for s in samples:
        got = {(sp.kind, sp.value) for sp in detect(s.text)}
        truth = set(s.truth)
        for k, _ in truth | got:
            per.setdefault(k, {"tp": 0, "fp": 0, "fn": 0})
        for item in got & truth:
            per[item[0]]["tp"] += 1
        for item in got - truth:
            per[item[0]]["fp"] += 1
        for item in truth - got:
            per[item[0]]["fn"] += 1
        if s.truth:
            forms.setdefault(s.form, [0, 0])
            forms[s.form][0] += int(truth <= got)
            forms[s.form][1] += 1
    return {"per_kind": per, "by_form": forms}


# --- round trip ----------------------------------------------------------------------------

_TOK = re.compile(r"(\[|<<)?([A-Z]+)_(\d+)(\]|>>)?")


def _map_tokens(text: str, fn: Callable[[re.Match[str]], str]) -> str:
    return _TOK.sub(fn, text)


def _hindi(m: re.Match[str], digits: bool = False) -> str:
    n = m.group(3).translate(DEV) if digits else m.group(3)
    label = HINDI_LABELS.get(m.group(2), [m.group(2)])[0]
    return (m.group(1) or "") + label + "_" + n + (m.group(4) or "")


TRANSFORMS: dict[str, Callable[[str], str]] = {
    "verbatim": lambda t: t,
    "lowercase": lambda t: _map_tokens(t, lambda m: m.group().lower()),
    "brackets dropped": lambda t: _map_tokens(t, lambda m: f"{m.group(2)}_{m.group(3)}"),
    "space for underscore": lambda t: _map_tokens(t, lambda m: m.group().replace("_", " ")),
    "markdown bold": lambda t: _map_tokens(t, lambda m: f"**{m.group()}**"),
    "label in Hindi": lambda t: _map_tokens(t, _hindi),
    "label and digit in Hindi": lambda t: _map_tokens(t, lambda m: _hindi(m, digits=True)),
    "label renamed": lambda t: _map_tokens(
        t, lambda m: m.group().replace(m.group(2), {"PHONE": "MOBILE"}.get(m.group(2), "ID"))
    ),
}


def reply_for(redacted: str) -> str:
    """A plausible agent reply that repeats every token back."""
    tokens = [m.group() for m in _TOK.finditer(redacted)]
    return "Ji, maine note kar liya: " + ", ".join(tokens) + ". Kuch aur?"


def _exact_restore(p: Parda, red_tokens: dict[str, str], reply: str) -> str:
    """What most wrappers do: str.replace on the exact token they issued."""
    for tok, value in ((t, p.value_of(t)) for t in red_tokens):
        reply = reply.replace(tok, value or tok)
    return reply


def roundtrip(samples: list[Sample]) -> dict[str, dict[str, float]]:
    """Share of replies where every original value comes back, per restore method."""
    table: dict[str, dict[str, float]] = {"exact match": {}, "parda restore": {}}
    positives = [s for s in samples if s.truth]
    for name, transform in TRANSFORMS.items():
        ok = {"exact match": 0, "parda restore": 0}
        total = 0
        for s in positives:
            p = Parda()
            red = p.redact(s.text)
            if not red.spans:
                continue  # detection miss; measured separately
            total += 1
            reply = transform(reply_for(red.text))
            values = {sp.value for sp in red.spans}
            ok["exact match"] += all(v in _exact_restore(p, red.tokens, reply) for v in values)
            ok["parda restore"] += all(v in p.restore(reply).text for v in values)
        for method in table:
            table[method][name] = round(100 * ok[method] / total, 1) if total else 0.0
    return table


def false_restores(samples: list[Sample]) -> int:
    """Replies that mention a token index we never issued must not get a value."""
    bad = 0
    for s in samples:
        if not s.truth:
            continue
        p = Parda()
        red = p.redact(s.text)
        if not red.spans:
            continue
        kind = red.spans[0].kind
        bad += p.restore(f"Aapka [{kind}_9] bhi chahiye").restored > 0
    return bad


def live_roundtrip(samples: list[Sample], endpoint: str, model: str, limit: int = 30) -> dict:
    """Send redacted messages to a real model and check its reply restores cleanly.

    Uses the OpenAI-compatible /chat/completions API; the key comes from PARDA_API_KEY.
    """
    key = os.environ.get("PARDA_API_KEY", "")
    results = {"sent": 0, "all_restored": 0, "dropped": 0, "unknown_tokens": 0}
    for s in [s for s in samples if s.truth][:limit]:
        p = Parda()
        red = p.redact(s.text)
        if not red.spans:
            continue
        body = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a support agent. Reply in Hindi, briefly, and confirm "
                    "the customer's details back to them exactly as given.",
                },
                {"role": "user", "content": red.text},
            ],
        }
        req = urllib.request.Request(
            endpoint.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            reply = json.load(r)["choices"][0]["message"]["content"]
        res = p.restore(reply)
        results["sent"] += 1
        values = {sp.value for sp in red.spans}
        if all(v in res.text for v in values):
            results["all_restored"] += 1
        elif res.restored == 0:
            results["dropped"] += 1
        results["unknown_tokens"] += len(res.unknown)
    return results
