"""WHAT THIS FILE DOES: pytest tests for the token gate of indexer.serve (read_token and the
request handler). It starts a real HTTP server on a loopback port per test, with a hand-built
state (no store, no model), and checks which requests are admitted. Writes serve.token only
inside pytest's tmp_path.

The endpoint's own auth (docs/06: "a tailscale serve-fronted endpoint with its own auth"; S214
E16): `<root>/serve.token`, one line the operator writes outside the repo. When it exists every
route but /health wants `X-FP-Token`; when it does not, the tailnet identity alone admits only on
the operator's explicit --no-token (fail closed since 2026-09-30: no token and no flag is a 503,
see test_serve_lock.py). Positive and negative controls on a loopback port; no store, no model."""

import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from indexer import serve
from indexer.config import Settings


# -- helpers: a throwaway server and a GET client --
def _server(tmp_path, token_line, no_token=False):
    """Start the serve handler on a free loopback port in a daemon thread. Writes `token_line`
    to the token file when not None. Returns (server, base_url); the caller shuts it down."""
    if token_line is not None:
        (tmp_path / serve.TOKEN_FILE).write_text(token_line, encoding="utf-8")
    # Build the state object by hand, skipping its constructor (which would load a model).
    state = serve._State.__new__(serve._State)
    state.root = tmp_path
    state.settings = Settings.load(tmp_path / "missing.toml")  # every lever at its default
    state.lock = threading.Lock()
    state.embedder = None
    state.reranker = None
    state.token = serve.read_token(tmp_path)
    state.no_token = no_token
    # Ask the OS for a free port, release it, then bind the server to it.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), serve._handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{port}"


def _get(url, token=None):
    """GET `url` with the local-proof header (and X-FP-Token when given). Returns
    (status_code, parsed JSON body), for error statuses too."""
    # X-FP-Local: a File Portal tool's proof that a GET is not a foreign page's <img> or link
    # (Handler._proven; test_serve_lock.py holds the requests that must be refused without it)
    headers = {"X-FP-Local": "1"}
    if token:
        headers["X-FP-Token"] = token
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


# -- tests --
def test_read_token_absent_blank_present(tmp_path):
    """read_token gives "" for a missing or blank file and the stripped line otherwise."""
    assert serve.read_token(tmp_path) == ""
    (tmp_path / serve.TOKEN_FILE).write_text("  \n", encoding="utf-8")
    assert serve.read_token(tmp_path) == ""
    (tmp_path / serve.TOKEN_FILE).write_text("s3cret-token\n", encoding="utf-8")
    assert serve.read_token(tmp_path) == "s3cret-token"


def test_gate_with_a_token(tmp_path):
    """With a token file: /health is open; other routes are 403 without the right token."""
    server, base = _server(tmp_path, "s3cret-token\n")
    try:
        code, doc = _get(base + "/health")
        assert (code, doc) == (200, {"ok": True}), (
            "health is never gated (a liveness probe carries no data)"
        )
        code, doc = _get(base + "/status")
        assert code == 403 and "X-FP-Token" in doc["error"]
        code, doc = _get(base + "/status", token="wrong")
        assert code == 403
        code, doc = _get(base + "/status", token="s3cret-token")
        assert code == 200 and "available" in doc, (
            "the calm status document (no index on this root) reaches the caller"
        )
        code, doc = _get(base + "/query?q=anything", token="wrong")
        assert code == 403, "a query without the token never reaches the model"
    finally:
        server.shutdown()


def test_no_token_file_and_no_token_flag_means_identity_only(tmp_path):
    """With no token file but the explicit no_token flag, requests are admitted without a token."""
    server, base = _server(tmp_path, None, no_token=True)
    try:
        assert _get(base + "/health") == (200, {"ok": True})
        code, doc = _get(base + "/status")
        assert code == 200 and "available" in doc
    finally:
        server.shutdown()
