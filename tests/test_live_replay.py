"""Scoring a recorded live run. The recording here is hand-written to cover each outcome;
it is not model output."""

import json

import pytest

from parda.bench import live_roundtrip
from parda.vault import Parda


def test_replay_scores_each_kind_of_reply(tmp_path):
    msg = "Mera number 98765 43210 hai aur UPI asha@okaxis"
    red = Parda().redact(msg).text  # tokens are numbered per message, so this is stable
    phone, upi = "[PHONE_1]", "[UPI_1]"
    assert phone in red and upi in red
    rows = [
        {"message": msg, "reply": f"Ji, {phone} aur {upi} note kar liya."},  # all back
        {"message": msg, "reply": f"Ji, {phone.lower()} note kiya."},  # one back, rewritten
        {"message": msg, "reply": "Ji, aapka number note kar liya."},  # dropped both
        {"message": msg, "reply": "Ji, [PHONE_7] pe call karenge."},  # unknown token
        {"message": msg, "error": "timed out"},
    ]
    rec = tmp_path / "run.jsonl"
    rec.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    got = live_roundtrip([], replay=rec)
    assert got == {
        "sent": 4,
        "all_restored": 1,
        "partly_restored": 1,
        "dropped": 2,
        "unknown_tokens": 1,
        "errors": 1,
    }


def test_live_run_needs_an_endpoint():
    with pytest.raises(ValueError, match="endpoint"):
        live_roundtrip([])
