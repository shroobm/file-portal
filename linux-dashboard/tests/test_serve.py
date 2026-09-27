"""dashboard.serve -- the sorted/ feed (S214 E16): a temp sorted/ tree, a loopback port, the token file present and
absent. Asserted: the listing's shape and counts, the category and photo-date filters, the gate's positive and negative
controls, /health never gated, a traversal refused before any read, a thumbnail of a non-photo refused, a thumbnail of a
photo either a JPEG (an image library present) or an honest 501 (none) -- never a 200 with nothing in it."""

import json
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from dashboard import serve
from dashboard.config import Paths, Settings


def _tree(root):
    """sorted/photos/2026/09/a.jpg (a real tiny JPEG header is not needed for the listing; the thumbnail test
    accepts 415/501 for bytes no library can read), sorted/photos/2025/12/b.jpg, sorted/documents/x.pdf,
    sorted/code/y.py; misc/ and archive/ absent."""
    (root / "sorted" / "photos" / "2026" / "09").mkdir(parents=True)
    (root / "sorted" / "photos" / "2025" / "12").mkdir(parents=True)
    (root / "sorted" / "documents").mkdir(parents=True)
    (root / "sorted" / "code").mkdir(parents=True)
    (root / "sorted" / "photos" / "2026" / "09" / "a.jpg").write_bytes(b"not really a jpeg")
    (root / "sorted" / "photos" / "2025" / "12" / "b.jpg").write_bytes(b"not really a jpeg either")
    (root / "sorted" / "documents" / "x.pdf").write_bytes(b"%PDF-1.4")
    (root / "sorted" / "code" / "y.py").write_text("print(1)\n", encoding="utf-8")
    old = time.time() - 86400
    os.utime(root / "sorted" / "code" / "y.py", (old, old))


def _server(root, token_line=None):
    if token_line is not None:
        (root / serve.TOKEN_FILE).write_text(token_line, encoding="utf-8")
    state = serve._State(root, Settings())
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), serve._handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{port}"


def _get(url, token=None, raw=False):
    req = urllib.request.Request(url, headers={"X-FP-Token": token} if token else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, (r.read() if raw else json.load(r)), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, json.load(e), e.headers.get("Content-Type", "")


def test_sorted_document_shape_and_filters(tmp_path):
    _tree(tmp_path)
    paths = Paths.from_root(tmp_path)
    doc = serve.sorted_document(paths, Settings(), None, None, None)
    assert doc["counts"] == {"photos": 2, "documents": 1, "code": 1, "archive": 0, "misc": 0}
    photo = doc["categories"]["photos"][0]
    assert set(photo) == {"name", "path", "category", "mtime", "year_month"}
    assert photo["path"].startswith("photos/") and photo["year_month"] in ("2026-09", "2025-12")
    assert doc["categories"]["documents"][0]["path"] == "documents/x.pdf"
    only = serve.sorted_document(paths, Settings(), "code", None, None)
    assert list(only["categories"]) == ["code"] and only["counts"] == {"code": 1}
    bounded = serve.sorted_document(paths, Settings(), "photos", "2026-01", None)
    assert [e["year_month"] for e in bounded["categories"]["photos"]] == ["2026-09"]


def test_routes_identity_only_when_no_token_file(tmp_path):
    _tree(tmp_path)
    server, base = _server(tmp_path)
    try:
        assert _get(base + "/health")[:2] == (200, {"ok": True, "gated": False})
        code, doc, _ = _get(base + "/sorted")
        assert code == 200 and doc["counts"]["photos"] == 2
        code, doc, _ = _get(base + "/sorted?category=code")
        assert code == 200 and doc["counts"] == {"code": 1}
        code, doc, _ = _get(base + "/sorted?category=nope")
        assert code == 400
        code, doc, _ = _get(base + "/sorted?from=2026")
        assert code == 400 and "yyyy-mm" in doc["error"]
        code, doc, _ = _get(base + "/nope")
        assert code == 404
    finally:
        server.shutdown()


def test_gate_with_a_token(tmp_path):
    _tree(tmp_path)
    server, base = _server(tmp_path, "s3cret\n")
    try:
        assert _get(base + "/health")[:2] == (200, {"ok": True, "gated": True}), (
            "health is never gated"
        )
        code, doc, _ = _get(base + "/sorted")
        assert code == 403 and "X-FP-Token" in doc["error"]
        assert _get(base + "/sorted", token="wrong")[0] == 403
        code, doc, _ = _get(base + "/sorted", token="s3cret")
        assert code == 200 and doc["counts"]["documents"] == 1
        assert _get(base + "/thumb?path=photos/2026/09/a.jpg")[0] == 403, (
            "the thumbnail route is gated too"
        )
    finally:
        server.shutdown()


def test_thumbnail_refusals_and_honesty(tmp_path):
    _tree(tmp_path)
    server, base = _server(tmp_path)
    try:
        code, doc, _ = _get(base + "/thumb?path=../serve.token")
        assert code == 400, "a traversal is refused before any read"
        code, doc, _ = _get(base + "/thumb?path=documents/x.pdf")
        assert code == 400 and "photos" in doc["error"], "thumbnails are for sorted/photos only"
        code, doc, _ = _get(base + "/thumb?path=photos/2026/09/missing.jpg")
        assert code == 404
        code, body, _ctype = _get(base + "/thumb?path=photos/2026/09/a.jpg", raw=True)
        # the bytes are not a real image: a library present answers 415 (cannot read), none present 501 -- never 200
        assert code in (415, 501), (code, body[:80])
        code, doc, _ = _get(base + "/thumb?path=photos/2026/09/a.jpg&px=abc")
        assert code == 400
    finally:
        server.shutdown()
