"""Opt-in HTTP JSON endpoint on the LOOPBACK interface only, for anything that would rather
speak HTTP than ssh: the dashboard, a phone window (docs/14 Phase A), curl, or the widget --
fronted by `tailscale serve`, which is the pattern docs/06 names for a new surface ("a
tailscale serve-fronted endpoint with its own auth ... rather than exposing anything new").
Binds 127.0.0.1 and nothing else, ever; opens no other port; no unit ships for it and nothing
starts it -- it is a segment the operator turns on:

    python -m indexer.serve                      # foreground, port from the serve_port lever
    tailscale serve --bg --set-path /index http://127.0.0.1:8765   # tailnet-only, identity-bound

Routes (all GET unless noted, all read-only, all return one JSON document):
    /health                      {"ok": true}
    /status                      the status.run() document
    /query?q=...&k=&mode=&bundle=&lane=&verdict=     the query.run() document
    /query  (POST, JSON body with the same keys)

The embedder and reranker load once and stay warm, so a query costs milliseconds instead of
the CLI's cold model load. Stdlib only.
"""

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from indexer import query, status
from indexer.config import DEFAULT_ROOT, Paths, Settings, lever_menu, lever_range
from indexer.embed import FastEmbedder, Reranker
from indexer.store import Store

BIND = "127.0.0.1"  # loopback only, by construction (docs/06); reach it through tailscale serve
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

        def do_GET(self) -> None:  # noqa: N802 -- http.server's contract
            url = urlparse(self.path)
            if url.path == "/health":
                self._send(200, {"ok": True})
            elif url.path == "/status":
                self._send(200, status.run(state.root))
            elif url.path == "/query":
                self._query({k: v[0] for k, v in parse_qs(url.query).items()})
            else:
                self._send(404, {"error": "unknown route"})

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/query":
                self._send(404, {"error": "unknown route"})
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
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

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
