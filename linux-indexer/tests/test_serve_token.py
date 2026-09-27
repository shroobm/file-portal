"""The endpoint's own auth (docs/06: "a tailscale serve-fronted endpoint with its own auth"; S214
E16): `<root>/serve.token`, one line the operator writes outside the repo. When it exists every
route but /health wants `X-FP-Token`; when it does not, the tailnet identity alone admits, as
before. Positive and negative controls on a loopback port; no store, no model."""

import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from indexer import serve
from indexer.config import Settings


def _server(tmp_path, token_line):
    if token_line is not None:
        (tmp_path / serve.TOKEN_FILE).write_text(token_line, encoding="utf-8")
    state = serve._State.__new__(serve._State)
    state.root = tmp_path
    state.settings = Settings.load(tmp_path / "missing.toml")  # every lever at its default
    state.lock = threading.Lock()
    state.embedder = None
    state.reranker = None
    state.token = serve.read_token(tmp_path)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), serve._handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{port}"


def _get(url, token=None):
    req = urllib.request.Request(url, headers={"X-FP-Token": token} if token else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_read_token_absent_blank_present(tmp_path):
    assert serve.read_token(tmp_path) == ""
    (tmp_path / serve.TOKEN_FILE).write_text("  \n", encoding="utf-8")
    assert serve.read_token(tmp_path) == ""
    (tmp_path / serve.TOKEN_FILE).write_text("s3cret-token\n", encoding="utf-8")
    assert serve.read_token(tmp_path) == "s3cret-token"


def test_gate_with_a_token(tmp_path):
    server, base = _server(tmp_path, "s3cret-token\n")
    try:
        code, doc = _get(base + "/health")
        assert (code, doc) == (200, {"ok": True, "gated": True}), (
            "health is never gated (a liveness probe carries no data)"
        )
        code, doc = _get(base + "/status")
        assert code == 403 and "X-FP-Token" in doc["error"]
        code, doc = _get(base + "/status", token="wrong")
        assert code == 403
        code, doc = _get(base + "/status", token="s3cret-token")
        assert code == 200 and "in_sync" in doc
        code, doc = _get(base + "/query?q=anything", token="wrong")
        assert code == 403, "a query without the token never reaches the model"
    finally:
        server.shutdown()


def test_no_token_file_means_identity_only(tmp_path):
    server, base = _server(tmp_path, None)
    try:
        assert _get(base + "/health") == (200, {"ok": True, "gated": False})
        code, doc = _get(base + "/status")
        assert code == 200 and "in_sync" in doc
    finally:
        server.shutdown()
