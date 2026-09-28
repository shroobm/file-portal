"""Opt-in HTTP JSON endpoint for the `sorted/` tree, on the LOOPBACK interface only -- the sorted
browse the GTK dashboard shows on the ThinkPad's own screen, made readable from the tailnet
through `tailscale serve` (docs/06: "a tailscale serve-fronted endpoint with its own auth ...
rather than exposing anything new"). The same shape as linux-indexer/indexer/serve.py: binds
127.0.0.1 and nothing else, opens no other port, no unit ships for it -- the operator turns it
on (S214 E16, Rab's word 2026-09-27):

    python -m dashboard.serve                     # foreground, port from dashboard.toml's serve_port
    tailscale serve --bg --set-path /sorted http://127.0.0.1:8766   # tailnet-only, identity-bound

Its own auth: the file `<root>/serve.token` (one line, made by the operator, never in the repo --
the repo is public). When the file exists every route but /health requires the header
`X-FP-Token` equal to it; when it does not exist the tailnet identity alone admits, as the Desk,
PORTAL and Control do today. A missing or wrong token is a 403 that says so.

Routes (all GET, all read-only, one JSON document each, except /thumb which is an image):
    /health                                   {"ok": true}
    /sorted?category=&from=&to=               the dashboard's own scan() model: {"categories": {name: [entry]}}
                                              entry = {name, path (relative to sorted/), category, mtime, year_month}
                                              category= limits to one; from=/to= (yyyy-mm) bound the photos
    /thumb?path=<relative path>&px=           a small JPEG of one photo (GdkPixbuf if present, else Pillow, else 501)

Nothing here opens, moves or writes a file. Stdlib only for the JSON routes.
"""

from __future__ import annotations

import argparse
import hmac
import io
import json
import re
import sys
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dashboard.config import ALL_CATEGORIES, CONFIG_PATH, DEFAULT_ROOT, Paths, Settings
from dashboard.scanner import scan

BIND = "127.0.0.1"  # loopback only, by construction (docs/06); reach it through tailscale serve
TOKEN_FILE = "serve.token"  # <root>/serve.token, the operator's, outside the repo
DEFAULT_PORT = 8766  # lever-waiver: a port, not a threshold (the indexer's serve takes 8765); overridden by --port
_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
THUMB_PX_DEFAULT = 320  # lever-waiver: Rab; the thumbnail's edge when ?px= is absent — moves on the phone's own read
THUMB_PX_MAX = 1024  # lever-waiver: Rab; the ceiling on ?px= (a cap on the work one request may ask), not a quality threshold


def read_token(root: Path) -> str:
    """The operator's token, one line, or "" when the file is absent or blank (identity-only)."""
    try:
        return (root / TOKEN_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def sorted_document(
    paths: Paths,
    settings: Settings,
    category: str | None,
    date_from: str | None,
    date_to: str | None,
) -> dict:
    """The scan() model as JSON-ready dicts; paths relative to sorted/ so nothing about the
    machine's layout leaves it beyond what the dashboard itself shows."""
    eff = settings
    if date_from is not None or date_to is not None:
        eff = replace(
            settings,
            photo_date_from=date_from if date_from is not None else settings.photo_date_from,
            photo_date_to=date_to if date_to is not None else settings.photo_date_to,
        )
    if category is not None:
        eff = replace(eff, enabled_categories=[category])
    model = scan(paths, eff)
    categories = {}
    for name, entries in model.items():
        categories[name] = [
            {
                "name": e.path.name,
                "path": e.path.relative_to(paths.sorted).as_posix(),
                "category": e.category,
                "mtime": round(e.mtime, 3),
                "year_month": e.year_month,
            }
            for e in entries
        ]
    return {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "categories": categories,
        "counts": {name: len(rows) for name, rows in categories.items()},
        "photo_date_from": eff.photo_date_from,
        "photo_date_to": eff.photo_date_to,
    }


def thumbnail(paths: Paths, rel: str, px: int) -> tuple[bytes | None, int, str]:
    """(jpeg bytes, 200, "") for a photo under sorted/photos; else (None, code, reason).
    Resolved paths must stay under sorted/photos -- a traversal is a 400, not a read."""
    if not rel or rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
        return None, 400, "path must be relative to sorted/ and inside it"
    target = (paths.sorted / rel).resolve()
    photos = (paths.sorted / "photos").resolve()
    if photos not in target.parents:
        return None, 400, "thumbnails are for sorted/photos only"
    if not target.is_file():
        return None, 404, "no such photo"
    px = max(32, min(THUMB_PX_MAX, px))
    try:  # the ThinkPad's own way (the dashboard already uses GdkPixbuf)
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf

        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(target), px, px, True)
        ok, data = pix.save_to_bufferv("jpeg", ["quality"], ["82"])
        if ok:
            return bytes(data), 200, ""
    except Exception as e:  # noqa: BLE001 -- fall through to Pillow, then to an honest 501
        sys.stderr.write(
            f"thumb: GdkPixbuf path unavailable ({e.__class__.__name__}); trying Pillow\n"
        )
    try:
        from PIL import Image

        with Image.open(target) as im:
            im.thumbnail((px, px))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=82)
            return buf.getvalue(), 200, ""
    except ImportError:
        return None, 501, "no image library here (GdkPixbuf or Pillow) -- the listing still works"
    except Exception as e:  # noqa: BLE001
        return None, 415, f"not an image this library can read: {e.__class__.__name__}"


class _State:
    def __init__(self, root: Path, settings: Settings):
        self.paths = Paths.from_root(root)
        self.settings = settings
        self.token = read_token(root)


def _handler(state: _State):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, doc: dict) -> None:
            body = json.dumps(doc, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_bytes(self, code: int, data: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

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

        def do_GET(self) -> None:
            url = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path == "/health":
                self._send(200, {"ok": True, "gated": bool(getattr(state, "token", ""))})
                return
            if not self._admitted():
                return
            if url.path == "/sorted":
                category = params.get("category") or None
                if category is not None and category not in ALL_CATEGORIES:
                    self._send(400, {"error": f"category must be one of {ALL_CATEGORIES}"})
                    return
                date_from, date_to = params.get("from"), params.get("to")
                for label, value in (("from", date_from), ("to", date_to)):
                    if value is not None and value != "" and not _YEAR_MONTH_RE.match(value):
                        self._send(400, {"error": f"{label} must be yyyy-mm"})
                        return
                self._send(
                    200, sorted_document(state.paths, state.settings, category, date_from, date_to)
                )
            elif url.path == "/thumb":
                try:
                    px = int(params.get("px") or THUMB_PX_DEFAULT)
                except ValueError:
                    self._send(400, {"error": "px must be an integer"})
                    return
                data, code, reason = thumbnail(state.paths, params.get("path") or "", px)
                if data is None:
                    self._send(code, {"error": reason})
                else:
                    self._send_bytes(200, data, "image/jpeg")
            else:
                self._send(404, {"error": "unknown route"})

        def log_message(self, fmt, *args):  # one line per request on stderr, no client noise
            sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="File Portal sorted/ HTTP endpoint (loopback)")
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory"
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="dashboard.toml")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"default: serve_port in dashboard.toml, else {DEFAULT_PORT}",
    )
    args = parser.parse_args()
    settings = Settings.load(args.config)
    port = args.port if args.port is not None else getattr(settings, "serve_port", DEFAULT_PORT)
    state = _State(args.root, settings)
    server = ThreadingHTTPServer((BIND, port), _handler(state))
    gate = "token gated" if state.token else "identity only -- no serve.token"
    print(
        f"serving on http://{BIND}:{port} (loopback only; {gate})",
        file=sys.stderr,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
