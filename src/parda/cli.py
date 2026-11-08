"""parda command line: redact stdin, or run the demo."""

from __future__ import annotations

import argparse
import io
import re
import sys

from . import __version__
from .vault import STYLES, Parda

DEMO = (
    "Bhaiya order abhi tak nahi aaya. Mera number ९८७६५ ४३२१० hai, PAN ABCPE1234F, "
    "refund asha.k@okicici pe kar dena. Pincode 248001."
)


def _utf8_output() -> None:
    """Write UTF-8 even when output is redirected on Windows, where it would otherwise use
    the locale's code page and fail on Devanagari or Hinglish text."""
    for stream in (sys.stdout, sys.stderr):
        enc = (stream.encoding or "").lower().replace("-", "")
        if enc != "utf8" and isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    _utf8_output()
    ap = argparse.ArgumentParser(prog="parda")
    ap.add_argument("--version", action="version", version=f"parda {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("redact", help="redact text from stdin (or --text)")
    r.add_argument("--text")
    r.add_argument("--style", choices=sorted(STYLES), default="bracket")
    r.add_argument("--show-spans", action="store_true", help="list what was found (to stderr)")
    r.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="REGEX",
        help="never redact values that fully match this (e.g. your order-id format)",
    )
    sub.add_parser("demo", help="redact, fake a model reply, restore")
    args = ap.parse_args(argv)

    if args.cmd == "redact":
        if args.text is not None:
            text = args.text
        else:  # bytes, so a Windows code page can't mangle Devanagari on the way in
            text = sys.stdin.buffer.read().decode("utf-8-sig")
        try:
            p = Parda(style=args.style, ignore=args.ignore)
        except re.error as e:
            print(f"error: --ignore: {e}", file=sys.stderr)
            return 2
        red = p.redact(text)
        sys.stdout.write(red.text if text.endswith("\n") or not red.text else red.text + "\n")
        if args.show_spans:
            for s in red.spans:
                print(f"  {s.kind:<8} chars {s.start}-{s.end}", file=sys.stderr)
        return 0

    p = Parda()
    red = p.redact(DEMO)
    print("customer   ", DEMO)
    print("to the LLM ", red.text)
    reply = "ठीक है, refund [upi_1] पर भेज दिया है। हम फोन_1 पर कॉल करेंगे।"
    print("LLM reply  ", reply)
    res = p.restore(reply)
    print("restored   ", res.text)
    print(f"leaks in outbound text: {len(p.leaks(red.text))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
