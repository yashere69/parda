import random
import time

from parda import Parda
from parda.cli import main
from parda.detect import Span, detect


def _brute_force(spans):
    spans = sorted(spans, key=lambda s: (-(s.end - s.start), s.start))
    taken = []
    for s in spans:
        if all(s.end <= t.start or s.start >= t.end for t in taken):
            taken.append(s)
    return sorted(taken, key=lambda s: s.start)


def test_overlap_resolution_matches_the_obvious_algorithm():
    r = random.Random(0)
    for _ in range(200):
        extra = []
        for _ in range(r.randint(0, 30)):
            a = r.randint(0, 200)
            extra.append(Span(a, a + r.randint(1, 25), "X", str(a)))
        assert detect("x" * 230, extra) == _brute_force(extra)


def test_large_input_is_linear_enough():
    text = "call 9876543210 " * 50_000  # 800 KB, 50k identifiers
    start = time.perf_counter()
    red = Parda().redact(text)
    assert time.perf_counter() - start < 10  # took ~56 s with the quadratic overlap check
    assert len(red.spans) == 50_000 and "9876543210" not in red.text


def test_ignore_keeps_your_own_formats():
    p = Parda(ignore=[r"7\d{9}"])
    assert p.redact("order 7834512690, call 9876543210").text == "order 7834512690, call [PHONE_1]"
    assert p.leaks("order 7834512690") == []


def test_message_list_shares_one_vault():
    p = Parda()
    msgs = [
        {"role": "user", "content": "call 9876543210"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "I said ९८७६५ ४३२१०"},
        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "x"}}]},
    ]
    out = p.redact_messages(msgs)
    assert out[0]["content"] == "call [PHONE_1]" and out[2]["content"] == "I said [PHONE_1]"
    assert out[3] == msgs[3] and msgs[0]["content"] == "call 9876543210"  # input untouched


def test_cli_ignore(capsys):
    assert main(["redact", "--text", "order 7834512690", "--ignore", r"7\d{9}"]) == 0
    assert capsys.readouterr().out == "order 7834512690\n"
    assert main(["redact", "--text", "x", "--ignore", "("]) == 2
