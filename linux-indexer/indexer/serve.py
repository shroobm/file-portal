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
the header `X-FP-Token` equal to it (a missing or wrong token is a 403 that says so). The gate FAILS
CLOSED (Rab, 2026-09-30: "absolute locked inside my tailscale vpn"): a token file that exists but
cannot be read aborts startup; with no token at all every route but /health answers 503 until the
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
    requests. Hence: a present Origin must be ours ("null" is not), on every method; an Origin-less
    POST is a tool (a browser always sends Origin on a POST) and may pass; and a GET must PROVE it
    came from our own page or tool -- Sec-Fetch-Site same-origin/same-site/none when sent, else a
    Referer naming one of this machine's pinned tailnet names, else a custom header (X-FP-Local,
    or the X-FP-Token a gated client already sends) that a cross-site browser request cannot carry
    without a preflight, which this server never answers. No proof is a 403 with reason
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

Routes (GET unless noted, each returns one JSON document; every other method is the stdlib's 501):
    /health                      {"ok": true}; no side effect, needs no proof
    /status                      the status.run() document; reads the index, runs `git rev-parse`
    /query?q=...&k=&mode=&bundle=&lane=&verdict=     the query.run() document; no write, but a
                                 server started before the first index existed builds its embedder
                                 per request, and a cold build fetches the model files
    /query  (POST, JSON body with the same keys)     the same work; no write
    /graph                       the Library graph (S214 E24): graph.json beside the index, which
                                 this route REWRITES when the vault's tip moved -- the one write
Every route but /health wants the token (when set) and, on a GET, the proof of origin above. The
graph's cache write cannot move into a POST without changing its one client, Control's Library
tab (a GET with X-FP-Token), so it is guarded instead: no GET reaches it without proof.

The embedder and reranker load once and stay warm, so a query costs milliseconds instead of
the CLI's cold model load. Stdlib only.
"""

import argparse
import hmac
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import threading
import time
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
NO_TOKEN_ERROR = (
    "no serve.token on this machine: every route but /health answers 503 until the operator "
    "writes <root>/serve.token (or starts this server with --no-token)"
)

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
        ip = ipaddress.ip_address(str(addr).split("%", 1)[0])
    except ValueError:
        return False
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
    """The host of a Host header, or of an Origin's or Referer's authority: '[::1]:8765' -> '::1',
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


# Request bounds. A question is a sentence, not a document: anything past these is a mistake
# or an abuse and gets a 4xx, never a model call.
MAX_BODY_BYTES = 65536  # lever-waiver: Rab; a safety bound, moves only if a real client needs more
MAX_QUERY_CHARS = 2000  # lever-waiver: Rab; a safety bound, moves only if a real client needs more


class _State:
    def __init__(self, root: Path, settings: Settings, *, no_token=False, token=None, names=None):
        self.root = root
        self.settings = settings
        # One query at a time through the shared ONNX session: onnxruntime documents Run() as
        # thread-safe, but a query costs milliseconds and a serialised endpoint has one fewer
        # thing to be wrong about (docs/47: never assume what a probe has not shown).
        self.lock = threading.Lock()
        self.token = read_token(root) if token is None else token
        self.no_token = no_token  # --no-token: the operator chose the tailnet identity alone
        # This machine's own tailnet names (tailnet_names); None is the LOOSE Host pin, which main()
        # uses only when the tailscale read failed.
        self.names = names
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
        def handle(self) -> None:
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

        def _send(self, code: int, doc: dict) -> None:
            body = json.dumps(doc, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", FRAME_POLICY)
            self.end_headers()
            self.wfile.write(body)

        def _admitted(self) -> bool:
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
            elif not self._proven():
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
            # By here parse_request has refused a POST carrying a foreign or "null" Origin (every
            # browser POST carries one, so a simple cross-site POST never gets this far; one with
            # none is a tool) and before its body was read. The gate next: an unknown route is not
            # answered to a stranger.
            if not self._admitted():
                return
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
    port = args.port if args.port is not None else settings.serve_port
    state = _State(args.root, settings, no_token=args.no_token, token=token, names=names or None)
    server = ThreadingHTTPServer((BIND, port), _handler(state))
    if state.token:
        gate = "token gated"
    elif args.no_token:
        gate = "identity only -- --no-token, no serve.token"
    else:
        gate = "CLOSED -- no serve.token: every route but /health answers 503"
    print(f"serving on http://{BIND}:{port} (loopback only; {gate})", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
