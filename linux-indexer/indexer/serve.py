"""Opt-in HTTP JSON endpoint on the LOOPBACK interface only, for anything that would rather
speak HTTP than ssh: the dashboard, a phone window (docs/14 Phase A), curl, or the widget --
fronted by `tailscale serve`, which is the pattern docs/06 names for a new surface ("a
tailscale serve-fronted endpoint with its own auth ... rather than exposing anything new").
Binds 127.0.0.1 and nothing else, ever; opens no other port; no unit ships for it and nothing
starts it -- it is a segment the operator turns on:

    python -m indexer.serve                      # foreground, port from the serve_port lever
    tailscale serve --bg --set-path /index http://127.0.0.1:8765   # tailnet-only, identity-bound

Its own auth (S214 E16, docs/06's "with its own auth"): the file `<root>/serve.token` (one line, the
operator's, never in the repo -- the repo is public). When it exists every route but /health wants
the header `X-FP-Token` equal to it (a missing or wrong token is a 403 that says so); when it does
not, the tailnet identity alone admits, as the Desk, PORTAL and Control do today.

Routes (all GET unless noted, all read-only, all return one JSON document):
    /health                      {"ok": true}
    /status                      the status.run() document
    /query?q=...&k=&mode=&bundle=&lane=&verdict=     the query.run() document
    /query  (POST, JSON body with the same keys)

The embedder and reranker load once and stay warm, so a query costs milliseconds instead of
the CLI's cold model load. Stdlib only.
"""

import argparse
import hmac
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from indexer import graph, query, status
from indexer.config import DEFAULT_ROOT, Paths, Settings, lever_menu, lever_range
from indexer.embed import FastEmbedder, Reranker
from indexer.store import Store

BIND = "127.0.0.1"  # loopback only, by construction (docs/06); reach it through tailscale serve
TOKEN_FILE = (
    "serve.token"  # <root>/serve.token: the operator's own auth, outside the repo (S214 E16)
)


def read_token(root: Path) -> str:
    """The operator's token, one line, or "" when the file is absent or blank (identity-only)."""
    try:
        return (root / TOKEN_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


# Request bounds. A question is a sentence, not a document: anything past these is a mistake
# or an abuse and gets a 4xx, never a model call.
MAX_BODY_BYTES = 65536  # lever-waiver: Rab; a safety bound, moves only if a real client needs more
MAX_QUERY_CHARS = 2000  # lever-waiver: Rab; a safety bound, moves only if a real client needs more


class _State:
    def __init__(self, root: Path, settings: Settings):
        self.root = root
        self.settings = settings
        # One query at a time through the shared ONNX session: onnxruntime documents Run() as
        # thread-safe, but a query costs milliseconds and a serialised endpoint has one fewer
        # thing to be wrong about (docs/47: never assume what a probe has not shown).
        self.lock = threading.Lock()
        self.token = read_token(root)
        paths = Paths.from_root(root)
        self.embedder = None
        self.reranker = None
        store = Store(paths.index)
        if store.exists():
            store.open_readonly()
            try:
                model = store.meta().get("model")
            finally:
                store.close()
            if model:
                self.embedder = FastEmbedder(model, settings.threads, paths.models)
                self.embedder.embed_query("warm")  # load now, not on the first request
        if settings.rerank != "off":
            self.reranker = Reranker(settings.rerank, settings.threads, paths.models)


def _handler(state: _State):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, doc: dict) -> None:
            body = json.dumps(doc, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _admitted(self) -> bool:
            token = getattr(state, "token", "") or ""
            if not token:
                return True  # identity-only: the tailnet admits, as the other surfaces do today
            presented = self.headers.get("X-FP-Token") or ""
            if hmac.compare_digest(presented.encode("utf-8"), token.encode("utf-8")):
                return True
            self._send(
                403,
                {
                    "error": "X-FP-Token missing or wrong -- the token is <root>/serve.token on this machine"
                },
            )
            return False

        def _query(self, params: dict) -> None:
            text = (params.get("q") or "").strip()
            if not text:
                self._send(400, {"error": "q (query text) required"})
                return
            if len(text) > MAX_QUERY_CHARS:
                self._send(400, {"error": f"q longer than {MAX_QUERY_CHARS} characters"})
                return
            k = params.get("k")
            low, high = lever_range("top_k")
            try:
                k = int(k) if k not in (None, "") else None
            except ValueError:
                self._send(400, {"error": "k must be an integer"})
                return
            if k is not None and not low <= k <= high:
                self._send(400, {"error": f"k must be within {low}..{high}"})
                return
            mode = params.get("mode") or None
            if mode is not None and mode not in lever_menu("query_mode"):
                self._send(400, {"error": f"mode must be one of {lever_menu('query_mode')}"})
                return
            with state.lock:
                doc = query.run(
                    state.root,
                    state.settings,
                    text,
                    top_k=k,
                    mode=mode,
                    bundle=params.get("bundle") or None,
                    lane=params.get("lane") or None,
                    verdict=params.get("verdict") or None,
                    embedder=state.embedder,
                    reranker=state.reranker,
                )
            self._send(200, doc)

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path == "/health":
                self._send(200, {"ok": True})  # the documented contract; the gate never touches it
            elif not self._admitted():
                return
            elif url.path == "/status":
                self._send(200, status.run(state.root))
            elif url.path == "/query":
                self._query({k: v[0] for k, v in parse_qs(url.query).items()})
            elif url.path == "/graph":
                # S214 E24: the Library graph — cached beside the index under its tip, rebuilt when the tip moves
                self._graph()
            else:
                self._send(404, {"error": "unknown route"})

        def _graph(self) -> None:
            paths = Paths.from_root(
                state.root
            )  # the module's own way (S214 E24: the first cut called the constructor and 502'd)
            store = Store(paths.index)
            if not store.exists():
                self._send(200, {"available": False, "reason": "no index yet"})
                return
            with state.lock:
                store.open_readonly()
                try:
                    doc = graph.cached(paths.index, store)
                finally:
                    store.close()
            doc["available"] = True
            self._send(200, doc)

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/query":
                self._send(404, {"error": "unknown route"})
                return
            if not self._admitted():
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self._send(400, {"error": "Content-Length must be an integer"})
                return
            if length > MAX_BODY_BYTES:
                self._send(413, {"error": f"body larger than {MAX_BODY_BYTES} bytes"})
                return
            try:
                params = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                self._send(400, {"error": "body must be JSON"})
                return
            if not isinstance(params, dict):
                self._send(400, {"error": "body must be a JSON object"})
                return
            self._query({k: ("" if v is None else str(v)) for k, v in params.items()})

        def log_message(self, fmt, *args):  # one line per request on stderr, no client noise
            sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="File Portal index HTTP endpoint (loopback)")
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent.parent / "config" / "indexer.toml",
    )
    parser.add_argument("--port", type=int, default=None, help="default: the serve_port lever")
    args = parser.parse_args()
    settings = Settings.load(args.config)
    port = args.port if args.port is not None else settings.serve_port
    state = _State(args.root, settings)
    server = ThreadingHTTPServer((BIND, port), _handler(state))
    print(f"serving on http://{BIND}:{port} (loopback only)", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
