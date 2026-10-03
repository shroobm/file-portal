"""WHAT THIS FILE DOES: a small read-only HTTP server (standard library only) that publishes the
dashboard's sorted/ tree as JSON (/sorted), small JPEG thumbnails (/thumb) and a liveness check
(/health). Entry point: main() (run as `python -m dashboard.serve`), which checks the bind address,
reads <root>/serve.token, reads this machine's tailnet names once, then serves on 127.0.0.1 until
interrupted. _handler(state) builds the request handler that applies every lock described below.
It reads the sorted/ tree, serve.token and dashboard.toml, runs the `tailscale` CLI once at start,
and writes only to stderr. Called by the operator (or a service) and by tests/test_serve*.py.

Opt-in HTTP JSON endpoint for the `sorted/` tree, on the LOOPBACK interface only -- the sorted
browse the GTK dashboard shows on the ThinkPad's own screen, made readable from the tailnet
through `tailscale serve` (docs/06: "a tailscale serve-fronted endpoint with its own auth ...
rather than exposing anything new"). The same shape as linux-indexer/indexer/serve.py: binds
127.0.0.1 and nothing else, opens no other port, no unit ships for it -- the operator turns it
on (S214 E16, Rab's word 2026-09-27):

    python -m dashboard.serve                     # foreground, port from dashboard.toml's serve_port
    tailscale serve --bg --set-path /sorted http://127.0.0.1:8766   # tailnet-only, identity-bound

Its own auth: the file `<root>/serve.token` (one line, made by the operator, never in the repo --
the repo is public). When the file exists every route but /health requires the header
`X-FP-Token` equal to it (a missing or wrong token is a 403 that says so). The gate FAILS CLOSED
(Rab, 2026-09-30: "absolute locked inside my tailscale vpn"): a token file that exists but cannot
be read aborts startup; with no token at all every route but /health answers 503 until the
operator writes the file -- or starts the server with --no-token, the explicit opt-in to the
tailnet identity alone. Four more locks sit under it: main() refuses to start unless BIND is a
literal loopback or Tailscale address (bind_ok); a connection from a peer that is neither
loopback nor tailnet gets a bare 403 before any request line is read (peer_ok); a request
carrying a Tailscale-Funnel-Request header (Tailscale's mark of a request that came in from the
public internet through Funnel) gets the same bare 403 before any route, token or body is read;
and a request that looks like a web page on another site is refused before any route, token or
body with a 403 whose JSON names the rule (Handler._request_refusal: host, origin, fetch-site;
Handler._proven: unproven-origin). Behind `tailscale serve` every peer is 127.0.0.1, so peer_ok is
a TRIPWIRE for a wrong bind, never the thing that tells one tailnet caller from another (the token
gate does that) or a tailnet caller from a public one (the Funnel header does that, see below).

What each lock can and cannot see (Observed in source; no request was sent to a live port):
  * The Funnel refusal covers HTTP-mode Funnel only. A TCP-mode funnel forwards raw TCP to the
    backend and Tailscale adds no header to it, so nothing in this file can see it; the private
    layer's security/lockdown_check.py (D4/T1) is what catches any Funnel.
  * The Sec-Fetch-Site rule fires only where browsers send that header: https URLs and loopback
    (the "potentially trustworthy" origins). The feeds are reached over plain http
    (`tailscale serve --http=8080`), where a browser sends no Sec-Fetch-* header at all, so there
    the rule is inert and the Host, Origin and proof-of-origin rules carry the weight.
  * Over plain http a browser still sends Origin on every POST and on any cross-origin fetch, and
    Referer unless the page suppressed it; it sends neither Origin nor a guaranteed Referer on a
    GET navigation, <img>, <script>, <link>, <iframe> or form GET. No File Portal server answers
    CORS, so a foreign page can never READ an answer; it can only cause effects with "simple"
    requests. Hence: a present Origin must be ours ("null" is not); and a GET must PROVE it came
    from our own page or tool -- Sec-Fetch-Site same-origin/same-site/none when sent, else a
    Referer naming one of this machine's pinned tailnet names, else a custom header (X-FP-Local,
    or the X-FP-Token a gated client already sends) that a cross-site browser request cannot
    carry without a preflight, which this server never answers. No proof is a 403 with reason
    "unproven-origin". With --no-token a scripted client of any GET but /health (curl, a cron
    job, a session tool) therefore sends `X-FP-Local: 1`.
  * The Host pin admits loopback literals (IPv4-mapped forms included), "localhost" and this
    machine's own tailnet names (read once at start from `tailscale status --json`: Self.DNSName
    and its first label). `tailscale serve` may hand the backend the original Host or the target's
    (127.0.0.1:<port>); both pass the Host check. ORIGIN and REFERER are stricter: only the pinned
    tailnet names are ours there, never a loopback literal, "localhost", an IPv4-mapped form or any
    IP literal (a page served by some other app on this machine is not one of ours). If the
    tailscale read fails (the LOOSE mode) the loose names (loopback, localhost, any single-label or
    *.ts.net name) apply to Host ONLY: every Origin is then refused, a Referer proves nothing, and
    only X-FP-Local or X-FP-Token prove a GET; one line on stderr says so.
  * There is no proxy-header lock here, unlike the servers that are reached directly: `tailscale
    serve` itself adds X-Forwarded-* and Tailscale-User-* to every request it relays.

Routes (all GET, all read-only, one JSON document each, except /thumb which is an image; every
other method is the stdlib's 501). Nothing here writes, spawns or contacts anything, so no route
has a side effect to move into a POST; /sorted and /thumb still need the token (when set) AND the
proof of origin above, because a foreign page's <img> can learn from /thumb whether a path exists
and how big the photo is (naturalWidth/onload), even though it can read no bytes:
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
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dashboard.config import ALL_CATEGORIES, CONFIG_PATH, DEFAULT_ROOT, Paths, Settings
from dashboard.scanner import scan

# -- constants: bind address, token file, defaults, error text --
BIND = "127.0.0.1"  # loopback only, by construction (docs/06); reach it through tailscale serve
TOKEN_FILE = "serve.token"  # <root>/serve.token, the operator's, outside the repo
DEFAULT_PORT = 8766  # lever-waiver: a port, not a threshold (the indexer's serve takes 8765); overridden by --port
_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
THUMB_PX_DEFAULT = 320  # lever-waiver: Rab; the thumbnail's edge when ?px= is absent — moves on the phone's own read
THUMB_PX_MAX = 1024  # lever-waiver: Rab; the ceiling on ?px= (a cap on the work one request may ask), not a quality threshold
NO_TOKEN_ERROR = (
    "no serve.token on this machine: every route but /health answers 503 until the operator "
    "writes <root>/serve.token (or starts this server with --no-token)"
)

# -- lock 1: the peer lock (who may connect) and the bind check --
# File Portal answers only this machine and the tailnet (Rab, 2026-09-30: "absolute locked inside
# my tailscale vpn"). The same block sits in every File Portal server; keep the names.
_PEER_CIDRS = ("127.0.0.0/8", "::1/128", "100.64.0.0/10", "fd7a:115c:a1e0::/48")
_PEER_NETS = tuple(ipaddress.ip_network(n) for n in _PEER_CIDRS)
_FORBIDDEN = b"HTTP/1.0 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
# Set by Tailscale's own proxy on every request that came in through Funnel (the public internet);
# see Handler.parse_request. The name is Tailscale's, not ours: never rename it.
FUNNEL_HEADER = "Tailscale-Funnel-Request"
_REFUSALS = 0
_REFUSALS_LOCK = threading.Lock()


def peer_ok(addr: object) -> bool:
    """True only for loopback or a Tailscale address; fails closed on anything unparseable."""
    try:
        # drop an IPv6 zone suffix ("%eth0") before parsing
        ip = ipaddress.ip_address(str(addr).split("%", 1)[0])
    except ValueError:
        return False
    # an IPv4-mapped IPv6 address is judged as the IPv4 address it wraps
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return any(ip.version == n.version and ip in n for n in _PEER_NETS)


def bind_ok(addr: object) -> bool:
    """A server may listen only on a literal loopback or Tailscale IP: no wildcard, no name."""
    try:
        ip = ipaddress.ip_address(str(addr))
    except ValueError:
        return False
    return not ip.is_unspecified and peer_ok(ip)


def _count_refusal(addr: object, why: str = "not loopback or tailnet") -> None:
    """Note a refused peer on stderr: the first 5, then every 1000th; never the request body."""
    global _REFUSALS
    try:
        with _REFUSALS_LOCK:
            _REFUSALS += 1
            n = _REFUSALS
        if n <= 5 or n % 1000 == 0:
            sys.stderr.write(f"refused peer {str(addr)[:64]!r} ({why}) #{n}\n")
    except Exception:  # noqa: BLE001 -- a log line must never take a connection down
        pass


# -- lock 3: the request locks (Host pin, Origin, Sec-Fetch-Site, proof of origin) and their constants --
# Lock 3: what a WEB PAGE (not a person, not a tool) can send. The peer lock admits his own devices,
# and a foreign page open in his browser on one of them fires requests from that device (behind
# `tailscale serve` it is 127.0.0.1 besides). The module docstring says what each rule can and
# cannot see. The same block sits in both ThinkPad feeds; keep the names.
_HOSTPORT = re.compile(r"^(?:\[([0-9a-f:.]+)\]|([a-z0-9._-]+))(?::[0-9]{1,5})?$")
# Sec-Fetch-Site values that are File Portal's own: a page of ours (same-origin) or the person
# (none: typed, bookmarked, a script). "same-site" is a page on ANOTHER port of the same host and
# "cross-site" a page on another site; neither is ours. Browsers send the header only to https URLs
# and loopback, so over plain http this set is never consulted.
_OWN_FETCH_SITES = ("same-origin", "none")
# A custom request header cannot ride a cross-site browser request without a CORS preflight, and no
# File Portal server answers one. A GET carrying either header therefore came from a tool or from a
# page of ours; X-FP-Token is here because the gated clients already send it on every call.
PROOF_HEADERS = ("X-FP-Local", "X-FP-Token")
REFUSED_ERROR = "refused: this feed answers File Portal's own tools and tailnet requests only"
UNPROVEN_ERROR = (
    "refused: a GET here must show it came from a File Portal page or tool -- send the header "
    "X-FP-Local (any value), or X-FP-Token"
)
UNPROVEN_REASON = "unproven-origin"
FRAME_POLICY = "frame-ancestors 'none'"  # nothing may frame an answer of these feeds
LOOSE_SUFFIX = ".ts.net"  # the loose pin's one name family: Tailscale's MagicDNS domain
# The one-time read of this machine's own tailnet names (tailnet_names). The bounds are a startup
# retry and a CLI timeout, not quality thresholds.
TAILNET_READ_TRIES = 3  # lever-waiver: a startup retry bound; tailscaled may still be coming up
TAILNET_READ_PAUSE_S = 5.0  # lever-waiver: a startup retry bound; three attempts span about 10 s
TAILNET_READ_TIMEOUT_S = 5  # lever-waiver: a CLI timeout bound; a hung attempt is cut here


def _host_of(value: object) -> str:
    """The host of a Host header, or of an Origin's or Referer's authority: '[::1]:8766' -> '::1',
    'Name.TS.net.:8080' -> 'name.ts.net' (lower-case, brackets off, ONE trailing dot dropped); ''
    when it is not host[:port] (userinfo, a path, a space, a second colon outside brackets)."""
    m = _HOSTPORT.match(str(value or "").strip().lower())
    if not m:
        return ""
    name = m.group(1) or m.group(2)
    if m.group(2) and name.endswith(".") and len(name) > 1:
        name = name[:-1]
    return name


def _ip(value: object):
    """An ipaddress object for a literal IP, else None (a name, '', None)."""
    try:
        return ipaddress.ip_address(str(value))
    except ValueError:
        return None


def _tailscale_status(timeout: float) -> dict:
    """`tailscale status --json` as a dict. The ONE place this file runs the tailscale CLI; a
    missing CLI, a timeout or a non-zero exit raises, and tailnet_names() decides what that
    means."""
    exe = shutil.which("tailscale") or "/usr/bin/tailscale"
    argv = [exe, "status", "--json"]
    done = subprocess.run(argv, capture_output=True, timeout=timeout, check=True)
    return json.loads(done.stdout.decode("utf-8", "replace"))


def tailnet_names(read=None, sleep=time.sleep) -> frozenset[str]:
    """This machine's own tailnet names: the full MagicDNS name and its first label, from `tailscale
    status --json` (Self.DNSName). Read ONCE, at serve start, never at import or per request.
    TAILNET_READ_TRIES attempts, TAILNET_READ_PAUSE_S apart; an empty set when every attempt fails
    (or the name is blank), and main() then runs the loose pin and says so."""
    read = read or _tailscale_status
    for attempt in range(TAILNET_READ_TRIES):
        if attempt:
            sleep(TAILNET_READ_PAUSE_S)
        try:
            doc = read(TAILNET_READ_TIMEOUT_S)
            full = _host_of((doc.get("Self") or {}).get("DNSName") or "")
        except Exception:  # noqa: BLE001 -- a name we cannot read is a name we do not pin
            continue
        names = {n for n in (full, full.split(".")[0]) if n.strip(".")}
        if names:
            return frozenset(names)
    return frozenset()


def host_ok(name: str, names: frozenset[str] | None) -> bool:
    """True when `name` (already through _host_of) is ours AS A HOST: a loopback literal (an
    IPv4-mapped form of one included), 'localhost', or one of this machine's own tailnet names
    (`names`). `tailscale serve` may rewrite Host to 127.0.0.1:<port>, so the Host check alone
    admits these. `names` None is the LOOSE pin, used only when the tailscale read failed: any
    single-label name or *.ts.net name passes too, for Host ONLY (own_name, below, is what Origin
    and Referer use). Another device's tailnet name or address, a LAN or public address and
    evil.example are not ours, which is what closes DNS rebinding."""
    if not name:
        return False
    ip = _ip(name)
    if ip is not None:
        if ip.version == 6 and ip.ipv4_mapped is not None:
            # '::ffff:127.0.0.1' is loopback: decided here, not left to what this Python's IPv6
            # is_loopback says about a mapped form (3.12.13's unmaps it itself; not every one does)
            ip = ip.ipv4_mapped
        return ip.is_loopback
    if name == "localhost":
        return True
    if names is None:
        return "." not in name or (name.endswith(LOOSE_SUFFIX) and not name.startswith("."))
    return name in names


def own_name(name: str, names: frozenset[str] | None) -> bool:
    """True only when `name` (already through _host_of) is one of this machine's own PINNED tailnet
    names: the one test Origin and Referer use, stricter than host_ok. A page that came from a
    loopback literal, 'localhost' or some other app on this machine is not one of ours, so none of
    those pass; an IP literal of any kind (an IPv4-mapped form included) is refused outright; and
    with no pin (`names` None or empty: the LOOSE mode) nothing passes, so the Origin rule refuses
    every Origin and a Referer proves nothing: X-FP-Local or X-FP-Token are the only proof."""
    return bool(name) and bool(names) and _ip(name) is None and name in names


def origin_ok(value: object, names: frozenset[str] | None) -> bool:
    """An Origin header: http(s) over one of this machine's own pinned tailnet names (own_name).
    'null' (a sandboxed frame, a data: URL, a POST under Referrer-Policy: no-referrer) is never
    ours, on any method, and neither is a loopback, 'localhost' or IP-literal origin."""
    scheme, sep, rest = str(value or "").strip().lower().partition("://")
    return bool(sep) and scheme in ("http", "https") and own_name(_host_of(rest), names)


def referer_ok(value: object, names: frozenset[str] | None) -> bool:
    """A Referer whose host is one of this machine's own pinned tailnet names (own_name). Only
    scheme://authority is read, never the path or query."""
    scheme, sep, rest = str(value or "").strip().lower().partition("://")
    if not sep or scheme not in ("http", "https"):
        return False
    return own_name(_host_of(re.split(r"[/?#\\]", rest, maxsplit=1)[0]), names)


# -- the token gate: reading the operator's token file --
def read_token(root: Path) -> str:
    """The operator's token, one line; "" only when the file is absent or blank (no token).

    Only FileNotFoundError means "no token file". Any other OSError (a permission error, a
    directory where the file should be, an I/O fault) propagates: a token file that exists but
    cannot be read must never turn into an open door (it used to, and admitted everyone)."""
    try:
        return (root / TOKEN_FILE).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def _token_or_exit(root: Path) -> str:
    """read_token, but a token file that exists and cannot be read ends startup with a message."""
    try:
        return read_token(root)
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(
            f"refusing to start: {root / TOKEN_FILE} exists but cannot be read "
            f"({e.__class__.__name__}: {e}) -- an unreadable token must not become an open door"
        )


# -- the two data routes' work: the /sorted listing and the /thumb image --
def sorted_document(
    paths: Paths,
    settings: Settings,
    category: str | None,
    date_from: str | None,
    date_to: str | None,
) -> dict:
    """The scan() model as JSON-ready dicts; paths relative to sorted/ so nothing about the
    machine's layout leaves it beyond what the dashboard itself shows."""
    # eff = the settings for this one request: the caller's date bounds and category override the defaults
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
    # turn each scanned Entry into a plain dict, with the path relative to sorted/
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
    # path checks first: refuse absolute paths and ".." before touching the disk
    if not rel or rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
        return None, 400, "path must be relative to sorted/ and inside it"
    target = (paths.sorted / rel).resolve()
    photos = (paths.sorted / "photos").resolve()
    if photos not in target.parents:
        return None, 400, "thumbnails are for sorted/photos only"
    if not target.is_file():
        return None, 404, "no such photo"
    px = max(32, min(THUMB_PX_MAX, px))
    # first choice: GdkPixbuf (what the dashboard itself uses); any failure falls through to Pillow
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
    # second choice: Pillow; no library at all is an honest 501, an unreadable image a 415
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


# -- the server's shared state and the request handler --
class _State:
    """What the handler needs: paths, settings, the token, the --no-token choice and the Host pin names."""

    def __init__(self, root: Path, settings: Settings, *, no_token=False, token=None, names=None):
        """Store the state; reads <root>/serve.token (via read_token) when `token` is not given."""
        self.paths = Paths.from_root(root)
        self.settings = settings
        self.token = read_token(root) if token is None else token
        self.no_token = no_token  # --no-token: the operator chose the tailnet identity alone
        # This machine's own tailnet names (tailnet_names); None is the LOOSE Host pin, which main()
        # uses only when the tailscale read failed.
        self.names = names


def _handler(state: _State):
    """Return a request-handler class bound to `state`; the class applies the peer, Funnel and request
    locks, then the token gate and the routes. No I/O until the class is used by a server."""

    class Handler(BaseHTTPRequestHandler):
        """One HTTP connection: GET only (other methods get the stdlib's 501)."""

        # -- the locks, in the order a connection meets them --
        def handle(self) -> None:
            """Serve one connection, but first refuse a peer that is not loopback or tailnet with a
            bare 403 (writes to the socket; counts the refusal on stderr)."""
            # The peer lock: a connection from anywhere but loopback or the tailnet gets a bare 403
            # and is closed before any request line is read, for every method (HEAD/OPTIONS/PUT and
            # malformed lines included). A TRIPWIRE only: behind `tailscale serve` every peer is
            # 127.0.0.1, so this cannot tell one tailnet caller from another (the token gate does);
            # it catches a wrong bind that lets a LAN or public peer reach the socket directly.
            try:
                peer = self.client_address[0]
                ok = peer_ok(peer)
            except Exception:  # noqa: BLE001 -- fail closed on anything odd
                peer, ok = "?", False
            if not ok:
                self.close_connection = True
                try:
                    self.wfile.write(_FORBIDDEN)
                except OSError:
                    pass
                _count_refusal(peer)
                return
            super().handle()

        def parse_request(self) -> bool:
            """Parse the request line and headers, then apply the Funnel lock and the request locks.
            Returns True to go on to a do_* method; False after the refusal has been written."""
            # The Funnel lock. `tailscale funnel` puts a port on the PUBLIC internet, and behind
            # `tailscale serve` a public caller reaches this socket from 127.0.0.1 exactly as a
            # tailnet caller does, so the peer lock above cannot tell the two apart. Tailscale's
            # proxy (ipn/ipnlocal/serve.go) sets `Tailscale-Funnel-Request: ?1` on every request
            # that came in through Funnel and strips any Tailscale-* header a client sent itself
            # (a tailnet request through Serve carries Tailscale-User-Login and the like instead),
            # so the header's PRESENCE, whatever its value, is the one mark a public request
            # carries. Refused with the bare 403 once the headers are parsed and before any route,
            # token or body is read, for every method and every path (/health included). It
            # covers HTTP-mode Funnel ONLY: a TCP-mode funnel forwards raw TCP and carries no
            # header, so nothing here can see it (security/lockdown_check.py D4/T1 catches any
            # Funnel).
            if not super().parse_request():
                return False
            if FUNNEL_HEADER in self.headers:
                self.close_connection = True
                try:
                    self.wfile.write(_FORBIDDEN)
                except OSError:
                    pass
                _count_refusal(self.client_address[0], "Tailscale Funnel: the public internet")
                return False
            # The request locks: a page on another site, not one of ours. Refused with a 403 whose
            # JSON names the rule, before any route, token or body is read.
            try:
                why = self._request_refusal()
            except Exception:  # noqa: BLE001 -- headers we cannot read are headers we do not trust
                why = "headers"
            if why is None:
                return True
            self.close_connection = True
            self._send(403, {"error": REFUSED_ERROR, "reason": why})
            _count_refusal(self.client_address[0], f"request refused: {why}")
            return False

        def _request_refusal(self) -> str | None:
            """Why this request looks like a web page on another site rather than one of ours:
            'host', 'origin' or 'fetch-site'; None when it passes. The headers are parsed by now."""
            h = self.headers
            names = getattr(state, "names", None)  # None: the loose pin, for Host only
            hosts = h.get_all("Host") or []
            if len(hosts) != 1 or not host_ok(_host_of(hosts[0]), names):
                return "host"  # none, two, or one that is not ours: DNS rebinding, a stray name
            origins = h.get_all("Origin") or []
            if len(origins) > 1 or (origins and not origin_ok(origins[0], names)):
                # a foreign page's request, 'null' (sandboxed, no-referrer), a loopback or IP
                # literal origin, or ANY Origin while the pin is loose (own_name: none is ours)
                return "origin"
            # Fires only where browsers send it: https and loopback. Over plain http to a tailnet
            # name or address (the `tailscale serve --http=8080` mode) no Sec-Fetch-* header exists.
            fetch = h.get("Sec-Fetch-Site")
            if fetch is not None and fetch.strip().lower() not in _OWN_FETCH_SITES:
                return "fetch-site"
            return None

        def _proven(self) -> bool:
            """A GET must show it came from a page or tool of ours, not from a foreign page's <img>,
            link, iframe or form (which send no Origin, and may send no Referer): Sec-Fetch-Site
            same-origin/same-site/none when the browser sent it (parse_request has already refused
            the other values), else a Referer naming one of this machine's pinned tailnet names
            (never while the pin is loose), else a custom header (PROOF_HEADERS) that a cross-site
            browser request cannot carry without a preflight. No proof: a 403 with reason
            'unproven-origin', and the route never runs."""
            h = self.headers
            fetch = h.get("Sec-Fetch-Site")
            if fetch is not None:
                proven = fetch.strip().lower() in _OWN_FETCH_SITES
            else:
                names = getattr(state, "names", None)
                proven = referer_ok(h.get("Referer"), names) or any(p in h for p in PROOF_HEADERS)
            if not proven:
                self._send(403, {"error": UNPROVEN_ERROR, "reason": UNPROVEN_REASON})
            return proven

        # -- writing answers --
        def _head(self, code: int, ctype: str, length: int) -> None:
            """Write the status line and the standard headers (type, length, nosniff, no-framing)."""
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(length))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", FRAME_POLICY)
            self.end_headers()

        def _send(self, code: int, doc: dict) -> None:
            """Answer with `doc` as UTF-8 JSON and status `code`."""
            body = json.dumps(doc, ensure_ascii=False).encode("utf-8")
            self._head(code, "application/json; charset=utf-8", len(body))
            self.wfile.write(body)

        def _send_bytes(self, code: int, data: bytes, ctype: str) -> None:
            """Answer with raw `data` of content type `ctype` and status `code`."""
            self._head(code, ctype, len(data))
            self.wfile.write(data)

        # -- the token gate and the routes --
        def _admitted(self) -> bool:
            """The token gate. True when the request may go on: --no-token with no token file, or an
            X-FP-Token header equal to the token. Otherwise sends a 503 or 403 and returns False."""
            token = getattr(state, "token", "") or ""
            if not token:
                # Fail closed: with no token only the operator's explicit --no-token admits (the
                # tailnet identity alone); otherwise nothing but /health is served.
                if getattr(state, "no_token", False):
                    return True
                self._send(503, {"error": NO_TOKEN_ERROR})
                return False
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
            """Route a GET: /health (open), then the token gate and proof of origin, then /sorted or
            /thumb; anything else is a 404. Query errors are 400s. Reads the sorted/ tree only."""
            url = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path == "/health":
                self._send(200, {"ok": True, "gated": bool(getattr(state, "token", ""))})
                return
            if not self._admitted():
                return
            if not self._proven():
                return
            if url.path == "/sorted":
                category = params.get("category") or None
                if category is not None and category not in ALL_CATEGORIES:
                    self._send(400, {"error": f"category must be one of {ALL_CATEGORIES}"})
                    return
                date_from, date_to = params.get("from"), params.get("to")
                # from= and to= must each be empty or yyyy-mm
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
            """Write one access-log line (client address and the formatted message) to stderr."""
            sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    return Handler


# -- startup --
def main() -> None:
    """Command-line entry: parse --root/--config/--port/--no-token, run the startup checks (bind, token
    file, Host pin), then serve until Ctrl-C. Reads serve.token, dashboard.toml and the tailscale CLI;
    exits with a message if the bind is wide or the token file is unreadable."""
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
    parser.add_argument(
        "--no-token",
        action="store_true",
        help="allow no serve.token (the tailnet identity alone); default: no token means 503",
    )
    args = parser.parse_args()
    if not bind_ok(BIND):  # before any socket, state or file: a wide bind never starts
        sys.exit(f"refusing to start: BIND {BIND!r} is not a literal loopback or Tailscale address")
    token = _token_or_exit(args.root)
    names = tailnet_names()  # the Host pin: read ONCE, here, never at import or per request
    # say on stderr which Host pin is in force (pinned names, or the loose fallback)
    if names:
        pin = f"Host pinned to loopback, localhost and {', '.join(sorted(names))}"
    else:
        pin = (
            "Host pin is LOOSE (the tailscale read failed): loopback, localhost, "
            "any single-label name, any *.ts.net name, for Host only; every Origin is refused "
            "and a Referer proves nothing (send X-FP-Local or X-FP-Token)"
        )
    print(pin, file=sys.stderr)
    settings = Settings.load(args.config)
    port = args.port if args.port is not None else getattr(settings, "serve_port", DEFAULT_PORT)
    state = _State(args.root, settings, no_token=args.no_token, token=token, names=names or None)
    server = ThreadingHTTPServer((BIND, port), _handler(state))
    # describe the gate in the startup line: token gated, identity only, or closed
    if state.token:
        gate = "token gated"
    elif args.no_token:
        gate = "identity only -- --no-token, no serve.token"
    else:
        gate = "CLOSED -- no serve.token: every route but /health answers 503"
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
