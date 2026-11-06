import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from parda.bench import corpus, detection, false_restores, live_roundtrip, roundtrip
from parda.cli import main


def test_corpus_is_deterministic():
    assert [s.text for s in corpus(50, 1)] == [s.text for s in corpus(50, 1)]


def test_benchmark_shape_and_invariants():
    samples = corpus(200, 3)
    det = detection(samples)
    assert det["per_kind"]["PAN"]["fn"] == 0
    rt = roundtrip(samples)
    for rewrite, score in rt["parda restore"].items():
        assert score >= rt["exact match"][rewrite]
    assert false_restores(samples) == 0


def test_live_roundtrip_against_a_fake_endpoint(monkeypatch):
    class Echo(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            content = "ठीक है: " + body["messages"][-1]["content"].lower()
            data = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = HTTPServer(("127.0.0.1", 0), Echo)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("PARDA_API_KEY", "test")
    res = live_roundtrip(corpus(40, 2), f"http://127.0.0.1:{srv.server_port}", "echo", limit=5)
    srv.shutdown()
    assert res["sent"] == 5 and res["all_restored"] == 5


def test_cli(capsys):
    assert main(["redact", "--text", "PAN ABCPE1234F"]) == 0
    assert capsys.readouterr().out == "PAN [PAN_1]\n"
    assert main(["demo"]) == 0
    assert "leaks in outbound text: 0" in capsys.readouterr().out
