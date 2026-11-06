"""Replace identifiers with tokens, and put them back in the model's reply.

A `Parda` instance is a session: the same value always gets the same token
("[PHONE_1]" stays "[PHONE_1]" across turns), and the mapping lives only in memory.

Restoring is the hard half. Models rewrite what they're given: lowercase it, drop the
brackets, bold it, translate the label into Hindi. `restore` accepts those variants for
tokens it issued and reports any token-like string it didn't issue rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .detect import Span, detect

STYLES = {
    "bracket": "[{kind}_{n}]",
    "angle": "<<{kind}_{n}>>",
    "bare": "{kind}_{n}",
}

# Labels as a model might write them after translating a reply into Hindi.
HINDI_LABELS = {
    "PHONE": ["फोन", "फ़ोन", "नंबर"],
    "PAN": ["पैन"],
    "AADHAAR": ["आधार"],
    "UPI": ["यूपीआई"],
    "EMAIL": ["ईमेल"],
    "GSTIN": ["जीएसटीआईएन", "जीएसटी"],
    "IFSC": ["आईएफएससी"],
    "PIN": ["पिन"],
    "CARD": ["कार्ड"],
}


@dataclass
class Redacted:
    text: str
    spans: list[Span]
    tokens: dict[str, str]  # token -> kind, for this call only (values stay in the vault)


@dataclass
class RestoreResult:
    text: str
    restored: int
    unknown: list[str] = field(default_factory=list)  # token-like strings we never issued


class Parda:
    def __init__(self, style: str = "bracket"):
        if style not in STYLES:
            raise ValueError(f"style must be one of {sorted(STYLES)}")
        self.style = style
        self._by_value: dict[tuple[str, str], str] = {}
        self._by_key: dict[tuple[str, int], str] = {}  # (kind, n) -> original value
        self._counts: dict[str, int] = {}

    def _token(self, kind: str, value: str) -> str:
        key = (kind, value)
        if key not in self._by_value:
            n = self._counts.get(kind, 0) + 1
            self._counts[kind] = n
            self._by_value[key] = STYLES[self.style].format(kind=kind, n=n)
            self._by_key[(kind, n)] = value
        return self._by_value[key]

    def redact(self, text: str, extra: list[Span] | None = None) -> Redacted:
        spans = detect(text, extra)
        out, last, tokens = [], 0, {}
        for s in spans:
            tok = self._token(s.kind, s.value)
            tokens[tok] = s.kind
            out.append(text[last : s.start])
            out.append(tok)
            last = s.end
        out.append(text[last:])
        return Redacted("".join(out), spans, tokens)

    def _pattern(self) -> re.Pattern[str]:
        kinds = sorted(set(self._counts) | set(HINDI_LABELS), key=len, reverse=True)
        labels = [re.escape(k) for k in kinds]
        labels += [re.escape(h) for k in kinds for h in HINDI_LABELS.get(k, [])]
        label = "|".join(labels)
        return re.compile(
            rf"(?:\[\s*|<<\s*|\*\*)?(?<![\w])({label})[\s_\-]?(\d+)(?![\d])(?:\s*\]|\s*>>|\*\*)?",
            re.I,
        )

    def value_of(self, token: str) -> str | None:
        m = re.fullmatch(r"\W*([A-Z]+)_(\d+)\W*", token)
        return self._by_key.get((m.group(1), int(m.group(2)))) if m else None

    def restore(self, text: str) -> RestoreResult:
        restored = 0
        unknown: list[str] = []
        hindi_to_kind = {h: k for k, hs in HINDI_LABELS.items() for h in hs}

        def sub(m: re.Match[str]) -> str:
            nonlocal restored
            label, n = m.group(1), int(m.group(2))
            kind = hindi_to_kind.get(label, label.upper())
            value = self._by_key.get((kind, n))
            if value is None:
                if kind in self._counts:  # looks like ours, but we never issued this index
                    unknown.append(m.group())
                return m.group()
            restored += 1
            return value

        return RestoreResult(self._pattern().sub(sub, text), restored, unknown)

    def leaks(self, outbound: str) -> list[Span]:
        """Identifiers still present in text you're about to send. Should be empty."""
        return detect(outbound)
