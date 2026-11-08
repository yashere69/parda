"""Redirected output on Windows uses the locale code page (cp1252), which can't encode
Devanagari. PYTHONIOENCODING=cp1252 reproduces that on any platform."""

import os
import subprocess
import sys


def test_demo_survives_a_cp1252_stdout():
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    out = subprocess.run(
        [sys.executable, "-m", "parda.cli", "demo"], capture_output=True, env=env, check=False
    )
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    assert "फोन".encode() in out.stdout or "पर".encode() in out.stdout


def test_redact_reads_utf8_stdin_under_a_cp1252_locale():
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    text = "मेरा नंबर ९८७६५ ४३२१० है"
    out = subprocess.run(
        [sys.executable, "-m", "parda.cli", "redact"],
        input=text.encode(),
        capture_output=True,
        env=env,
        check=False,
    )
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    assert out.stdout.decode().strip() == "मेरा नंबर [PHONE_1] है"
