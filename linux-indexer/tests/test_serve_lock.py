"""WHAT THIS FILE DOES: pytest tests for the security locks of indexer/serve.py (the index HTTP
server): peer address, bind check, token gate, Funnel header, Host/Origin/Referer/fetch-site rules and
the proof of origin on GETs. Run by pytest (CI and the session); it has no entry point of its own. It
drives the real request handler through a fake connection or a real loopback socket, writes only under
pytest's tmp_path, and never starts the tailscale CLI.

indexer.serve -- the locks under the token gate (Rab, 2026-09-30: "absolute locked inside my
tailscale vpn, and no one can access it"). Each test violates one rule and must see its guard fire,
after a positive control: the peer lock (loopback and tailnet in, everything else a bare 403 before
any request line is read), the bind check at startup (a wide bind never starts), and the token
gate's fail-closed default (no token is a 503, an unreadable token aborts startup). The handler is
driven through a fake connection (every byte written is captured) and, where a real socket matters,
through a real server on 127.0.0.1 with an OS-assigned port. No store, no model: the state is built
over an empty root. The last section holds the request locks (the Host pin, Origin, Sec-Fetch-Site,
and the proof of origin a GET must carry): every request there models what a browser sends over
PLAIN HTTP, which includes no Sec-Fetch-* header, and the routes' work is stubbed so a refusal is
seen as the route NOT running. No test here may run the tailscale CLI (the autouse fixture below
fails one that tries)."""

import atexit
import contextlib
import io
import ipaddress
import json
import re
import shutil
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from indexer import serve
from indexer.config import Settings

# -- shared constants: HTTP methods, peers, wide binds, the made-up tailnet name --
METHODS = ("GET", "POST", "HEAD", "OPTIONS", "PUT")
ALLOWED_PEERS = ("127.0.0.1", "::1", "100.64.0.7", "fd7a:115c:a1e0::1")
REFUSED_PEERS = ("192.168.2.207", "8.8.8.8", "::ffff:192.168.2.207", "2001:db8::7f00:1")
WIDE_BINDS = ["", "0.0.0.0", "::", "192.168.2.102", "desktop-bndit", "localhost", "8.8.8.8"]
LOCAL = "X-FP-Local: 1"  # what a File Portal tool sends on a GET to prove where it came from

# A made-up MagicDNS name and its first label: what the Host pin reads from `tailscale status
# --json` at start. The real name is never in this repo.
TAILNET = "thinkbox.tail-test.ts.net"
LABEL = "thinkbox"
NAMES = frozenset({TAILNET, LABEL})
_REAL_TAILNET_NAMES = serve.tailnet_names
_REAL_TAILSCALE_STATUS = serve._tailscale_status


# -- fixtures that apply to every test: no tailscale CLI, temp-dir cleanup --
@pytest.fixture(autouse=True)
def _no_tailscale_cli(monkeypatch):
    """No test in this file may run the tailscale CLI. main() reads the Host pin's names once; that
    read is replaced by a fake (its calls counted, returned as the fixture's value), and the CLI
    wrapper itself fails the test if anything reaches it."""
    calls = []

    def fake_names():
        """Stand-in for serve.tailnet_names: count the call, return the made-up names."""
        calls.append(1)
        return NAMES

    def never(timeout):
        """Stand-in for the CLI wrapper: reaching it at all fails the running test."""
        pytest.fail("a test reached the tailscale CLI wrapper")

    monkeypatch.setattr(serve, "tailnet_names", fake_names)
    monkeypatch.setattr(serve, "_tailscale_status", never)
    return calls


@pytest.fixture(scope="session", autouse=True)
def _drop_the_pytest_temp_base(tmp_path_factory):
    """Every test here writes under pytest's temp base (tmp_path), and pytest keeps the last three
    bases after a run. This run's base is removed at interpreter exit, so the suite leaves no temp
    directory behind (a base still held open is skipped, never an error)."""
    atexit.register(shutil.rmtree, str(tmp_path_factory.getbasetemp()), True)


# -- peer lock and bind check: (address, expected) table and the tests over it --
PEERS = [
    ("127.0.0.1", True),
    ("::1", True),
    ("100.64.0.7", True),
    ("100.64.0.1", True),
    ("fd7a:115c:a1e0::1", True),
    ("::ffff:100.64.0.7", True),
    ("::ffff:127.0.0.1", True),
    ("100.127.255.255", True),
    ("127.255.255.255", True),
    ("192.168.2.207", False),
    ("8.8.8.8", False),
    ("::ffff:192.168.2.207", False),
    ("2001:db8::7f00:1", False),
    ("100.63.255.255", False),
    ("100.128.0.1", False),
    ("fe80::1%eth0", False),
    ("", False),
    ("not-an-ip", False),
    (None, False),
]


@pytest.mark.parametrize(("addr", "expected"), PEERS)
def test_peer_ok_table(addr, expected):
    """peer_ok gives the table's answer for each address."""
    assert serve.peer_ok(addr) is expected


@pytest.mark.parametrize("addr", ["100.64.0.1", "127.0.0.1", "::1"])
def test_bind_ok_accepts_a_literal_loopback_or_tailnet_ip(addr):
    """Positive control: bind_ok admits literal loopback and tailnet IPs."""
    assert serve.bind_ok(addr) is True


@pytest.mark.parametrize("addr", [*WIDE_BINDS, "::ffff:0.0.0.0"])
def test_bind_ok_refuses_wildcards_lan_public_and_names(addr):
    """bind_ok refuses wildcard, LAN, public and hostname binds."""
    assert serve.bind_ok(addr) is False


def test_the_shipped_bind_passes_its_own_check():
    """The BIND constant that ships is 127.0.0.1 and passes bind_ok."""
    assert serve.bind_ok(serve.BIND) and serve.BIND == "127.0.0.1"


# -- test helpers: fake connection, request builders, state builder, handler driver --
class _Recorded(io.BytesIO):
    """A request stream that notes, as the server closes it, what was left unread."""

    unread = None

    def close(self):
        """Record any bytes still unread in `unread`, then close as usual."""
        if not self.closed:
            self.unread = self.read()
        super().close()


class _FakeConn:
    """The accepted socket, stood in for: a canned request to read, every byte written captured."""

    def __init__(self, request):
        """Hold the canned request bytes as the readable stream; start with nothing sent."""
        self.sent = bytearray()
        self.stream = _Recorded(request)

    def makefile(self, mode, bufsize=-1):
        """Hand the handler the same canned stream for both reading and writing."""
        return self.stream

    def sendall(self, data):
        """Capture bytes the server sends."""
        self.sent += bytes(data)


def _req(method, path="/health"):
    """A minimal raw request (bytes) for `method` and `path` with Host: x."""
    return f"{method} {path} HTTP/1.1\r\nHost: x\r\n\r\n".encode()


REQUESTS = [_req(m) for m in METHODS] + [b"x\r\n"]


def _request(method, path, host=LABEL, headers=(), body=b""):
    """A raw request as a browser or a tool would send it; host=None sends no Host header at all."""
    lines = [f"{method} {path} HTTP/1.1"]
    if host is not None:
        lines.append(f"Host: {host}")
    lines += headers
    if body:
        lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode() + body


def _settings(root):
    """Settings with every lever at its default (loaded from a config file that does not exist)."""
    return Settings.load(root / "missing.toml")  # every lever at its default


def _state(root, token="", no_token=False, names=None):
    """A complete state without the model load: what _State builds over an empty root."""
    state = serve._State.__new__(serve._State)
    state.root = root
    state.settings = _settings(root)
    state.lock = threading.Lock()
    state.embedder = None
    state.reranker = None
    state.token = token
    state.no_token = no_token
    state.names = names
    return state


def _recording(cls, ran):
    """Replace every do_<METHOD> on a handler class with a stub that records it ran."""
    for method in METHODS:
        setattr(cls, f"do_{method}", lambda self, m=method: ran.append(m))
    return cls


def _drive(cls, client_address, raw):
    """Run one connection through the real Handler; return every byte the server wrote."""
    conn = _FakeConn(raw)
    cls(conn, client_address, None)
    return bytes(conn.sent)


# -- peer lock through the real handler: bare 403, allowed peers, forwarded headers, bad addresses --
@pytest.mark.parametrize("peer", REFUSED_PEERS)
@pytest.mark.parametrize("raw", REQUESTS)
def test_a_refused_peer_gets_the_bare_403_and_no_method_runs(tmp_path, peer, raw):
    """A refused peer gets exactly the bare 403 and no do_* method runs, for every request."""
    ran = []
    cls = _recording(serve._handler(_state(tmp_path, no_token=True)), ran)
    assert _drive(cls, (peer, 5555), raw) == serve._FORBIDDEN
    assert ran == [], "a refused peer must never reach a do_* method"


@pytest.mark.parametrize("peer", ALLOWED_PEERS)
@pytest.mark.parametrize("method", METHODS)
def test_an_allowed_peer_reaches_every_method(tmp_path, peer, method):
    """Positive control: an allowed peer reaches each method and the guard adds no bytes."""
    ran = []
    cls = _recording(serve._handler(_state(tmp_path, no_token=True)), ran)
    sent = _drive(cls, (peer, 5555), _req(method))
    assert ran == [method]
    assert sent == b"", "the stub wrote nothing, so the guard added no bytes of its own"


def test_the_403_is_exactly_the_bare_refusal():
    """The _FORBIDDEN constant is the literal bare HTTP/1.0 403 with no body."""
    expected = b"HTTP/1.0 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    assert serve._FORBIDDEN == expected


def test_a_tailnet_peer_gets_a_normal_answer_from_the_real_handler(tmp_path):
    """A tailnet peer's GET /health gets a 200 {"ok": true} from the unstubbed handler."""
    cls = serve._handler(_state(tmp_path, no_token=True))
    sent = _drive(cls, ("100.64.0.7", 5555), _req("GET"))
    head, _, body = sent.partition(b"\r\n\r\n")
    assert head.startswith(b"HTTP/1.0 200")
    assert json.loads(body) == {"ok": True}


def test_a_malformed_line_from_an_allowed_peer_is_the_servers_own_400(tmp_path):
    """A malformed request line from an allowed peer gets the stdlib's error, not the 403."""
    ran = []
    cls = _recording(serve._handler(_state(tmp_path, no_token=True)), ran)
    sent = _drive(cls, ("127.0.0.1", 5555), b"x\r\n")
    assert ran == [] and sent and sent != serve._FORBIDDEN


def test_a_forwarded_header_cannot_buy_a_refused_peer_entry(tmp_path):
    """X-Forwarded-For / Forwarded claiming loopback do not let a refused peer in."""
    raw = b"\r\n".join(
        [
            b"GET /health HTTP/1.1",
            b"Host: x",
            b"X-Forwarded-For: 127.0.0.1",
            b"Forwarded: for=127.0.0.1",
            b"",
            b"",
        ]
    )
    cls = serve._handler(_state(tmp_path, no_token=True))
    assert _drive(cls, ("192.168.2.207", 5555), raw) == serve._FORBIDDEN


class _Hostile:
    """An object whose string form raises: a client address that cannot even be printed."""

    def __str__(self):
        """Always raises, to prove callers cope with an unprintable address."""
        raise RuntimeError("an address that cannot even be printed")


@pytest.mark.parametrize("client_address", [("", 1), "", (), (_Hostile(), 1)])
def test_an_unreadable_peer_address_fails_closed(tmp_path, client_address):
    """An empty, malformed or unprintable client address gets the bare 403."""
    cls = serve._handler(_state(tmp_path, no_token=True))
    assert _drive(cls, client_address, _req("GET")) == serve._FORBIDDEN


def test_refusals_are_noted_first_five_then_every_thousandth(monkeypatch, capsys):
    """1000 refusals write six stderr lines: the first five and the 1000th, each naming the peer."""
    monkeypatch.setattr(serve, "_REFUSALS", 0)
    for _ in range(1000):
        serve._count_refusal("192.168.2.207")
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 6 and lines[-1].endswith("#1000")
    assert all("192.168.2.207" in line for line in lines)


def test_the_refusal_note_never_raises(monkeypatch):
    """_count_refusal swallows an address that cannot be printed."""
    monkeypatch.setattr(serve, "_REFUSALS", 0)
    serve._count_refusal(_Hostile())


# -- token gate and real-socket tests: a server on 127.0.0.1, the 503 / 403 / 200 behaviour --
@contextlib.contextmanager
def _running(state):
    """A real server on 127.0.0.1 (an OS-assigned port); yields the port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), serve._handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def _call(port, path, data=None, token=None):
    """GET when data is None, else POST the bytes; returns (status, parsed JSON body). It sends a
    File Portal tool's own proof of origin (Handler._proven), so what is under test here is the
    gate, not the proof; the refusals of a GET without it are in the last section below."""
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data)
    req.add_header("X-FP-Local", "1")
    if token is not None:
        req.add_header("X-FP-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_a_refused_peer_over_a_real_socket_and_the_server_survives(tmp_path, monkeypatch):
    """Over a real socket a refused peer reads the bare 403, and the next request still works."""
    with _running(_state(tmp_path, no_token=True)) as port:
        assert _call(port, "/health")[0] == 200, "positive control: loopback is let in"
        with monkeypatch.context() as m:
            m.setattr(serve, "peer_ok", lambda addr: False)
            with socket.create_connection(("127.0.0.1", port), timeout=10) as s:
                got = b""
                while chunk := s.recv(4096):
                    got += chunk
        assert got == serve._FORBIDDEN
        assert _call(port, "/health")[0] == 200, "the accept loop outlives a refusal"


def test_no_token_and_no_flag_answers_503_on_every_route_but_health(tmp_path):
    """With no token and no --no-token, every route except /health is a 503 naming the flag."""
    with _running(_state(tmp_path)) as port:
        assert _call(port, "/health") == (200, {"ok": True})
        for path in ("/status", "/query?q=anything", "/graph", "/nope", "/"):
            code, doc = _call(port, path, token="anything")
            assert code == 503 and "--no-token" in doc["error"], path
        for path in ("/query", "/nope"):
            code, doc = _call(port, path, data=b'{"q": "x"}', token="anything")
            assert code == 503 and "--no-token" in doc["error"], path


def test_a_blank_token_file_is_no_token(tmp_path):
    """A token file holding only whitespace counts as no token: /status is a 503."""
    (tmp_path / serve.TOKEN_FILE).write_text("  \n", encoding="utf-8")
    with _running(_state(tmp_path, token=serve.read_token(tmp_path))) as port:
        assert _call(port, "/status")[0] == 503


def test_the_no_token_flag_is_the_only_way_to_identity_only(tmp_path):
    """With no_token set and no token file, requests pass the gate to the route's own answer."""
    with _running(_state(tmp_path, no_token=True)) as port:
        code, doc = _call(port, "/status")
        assert code == 200 and "available" in doc, "past the gate, the route's own answer"
        assert _call(port, "/nope")[0] == 404
        assert _call(port, "/query", data=b"{}")[0] == 400, "a POST gets past the gate too"
        assert _call(port, "/nope", data=b"{}")[0] == 404


def test_a_token_still_gates_when_the_no_token_flag_is_also_given(tmp_path):
    """A token file wins over --no-token: a missing or wrong token is a 403, the right one a 200."""
    (tmp_path / serve.TOKEN_FILE).write_text("s3cret\n", encoding="utf-8")
    state = _state(tmp_path, token=serve.read_token(tmp_path), no_token=True)
    with _running(state) as port:
        assert _call(port, "/status")[0] == 403
        assert _call(port, "/status", token="wrong")[0] == 403
        assert _call(port, "/nope", data=b"{}")[0] == 403
        assert _call(port, "/status", token="s3cret")[0] == 200


def test_a_state_with_no_gate_attributes_is_closed(tmp_path):
    """A state object lacking token and no_token attributes fails closed with a 503."""
    state = serve._State.__new__(serve._State)
    state.root = tmp_path
    state.settings = _settings(tmp_path)
    sent = _drive(serve._handler(state), ("127.0.0.1", 5555), _req("GET", "/status"))
    assert sent.startswith(b"HTTP/1.0 503")


def test_the_real_state_carries_the_gate_it_was_given(tmp_path):
    """The real _State stores the token and no_token it is given (or reads the token file)."""
    settings = _settings(tmp_path)
    closed = serve._State(tmp_path, settings)
    assert (closed.token, closed.no_token) == ("", False)
    assert closed.embedder is None and closed.reranker is None
    open_ = serve._State(tmp_path, settings, no_token=True)
    assert (open_.token, open_.no_token) == ("", True)
    (tmp_path / serve.TOKEN_FILE).write_text("s3cret\n", encoding="utf-8")
    assert serve._State(tmp_path, settings).token == "s3cret"


def test_read_token_treats_only_a_missing_file_as_no_token(tmp_path):
    """Only a missing token file is "no token"; a directory in its place raises OSError."""
    assert serve.read_token(tmp_path) == "", "positive control: absent is no token"
    (tmp_path / serve.TOKEN_FILE).mkdir()
    with pytest.raises(OSError):  # the old code swallowed this and admitted everyone
        serve.read_token(tmp_path)
    with pytest.raises(OSError):
        serve._State(tmp_path, _settings(tmp_path))


# -- startup tests: main() with a faked command line and faked server classes --
def _argv(monkeypatch, root, *extra):
    """Set sys.argv to run indexer.serve with --root, --config under `root`, plus `extra` flags."""
    argv = [
        "indexer.serve",
        "--root",
        str(root),
        "--config",
        str(root / "indexer.toml"),
        *extra,
    ]
    monkeypatch.setattr(sys, "argv", argv)


def _refuse_everything(monkeypatch):
    """Make creating a server or a _State fail the test, to prove startup stopped earlier."""

    def boom(*args, **kwargs):
        """Raise AssertionError: a socket or state was created too early."""
        raise AssertionError("a socket or state was created before the refusal")

    monkeypatch.setattr(serve, "ThreadingHTTPServer", boom)
    monkeypatch.setattr(serve, "_State", boom)


def _capture_server(monkeypatch):
    """Replace the HTTP server class with a fake that records (address, handler) and returns at once.
    Returns the list those records go into."""
    made = []

    class FakeServer:
        """A server that opens no socket."""

        def __init__(self, addr, handler):
            """Record the address and handler class main() built."""
            made.append((addr, handler))

        def serve_forever(self):
            """Stop immediately (as Ctrl-C would) so main() returns."""
            raise KeyboardInterrupt

    monkeypatch.setattr(serve, "ThreadingHTTPServer", FakeServer)
    return made


@pytest.mark.parametrize("bind", WIDE_BINDS)
def test_a_wide_bind_never_starts(tmp_path, monkeypatch, bind):
    """main() exits with "refusing to start" for every wide BIND, before any socket or state."""
    _argv(monkeypatch, tmp_path)
    _refuse_everything(monkeypatch)
    monkeypatch.setattr(serve, "BIND", bind)
    with pytest.raises(SystemExit) as exc:
        serve.main()
    # a str code is printed to stderr and the process exits 1
    assert isinstance(exc.value.code, str) and "refusing to start" in exc.value.code


@pytest.mark.parametrize("extra", [(), ("--no-token",)])
def test_a_token_file_that_cannot_be_read_aborts_startup(tmp_path, monkeypatch, extra):
    """An unreadable token file (a directory) aborts startup, with or without --no-token."""
    (tmp_path / serve.TOKEN_FILE).mkdir()
    _argv(monkeypatch, tmp_path, *extra)
    _refuse_everything(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        serve.main()
    assert isinstance(exc.value.code, str) and serve.TOKEN_FILE in exc.value.code
    assert "cannot be read" in exc.value.code


def test_a_token_file_that_is_not_text_aborts_startup(tmp_path, monkeypatch):
    """A token file of undecodable bytes raises in read_token and aborts main() startup."""
    (tmp_path / serve.TOKEN_FILE).write_bytes(b"\xff\xfe\x00\x80")
    with pytest.raises(UnicodeDecodeError):
        serve.read_token(tmp_path)
    _argv(monkeypatch, tmp_path)
    _refuse_everything(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        serve.main()
    assert isinstance(exc.value.code, str) and "cannot be read" in exc.value.code


def test_main_starts_closed_by_default_and_says_so(tmp_path, monkeypatch, capsys):
    """With no token and no flag, main() prints CLOSED and its handler answers 503."""
    made = _capture_server(monkeypatch)
    _argv(monkeypatch, tmp_path)
    serve.main()
    assert "CLOSED" in capsys.readouterr().err
    addr, handler = made[0]
    assert addr[0] == "127.0.0.1"
    sent = _drive(handler, ("127.0.0.1", 5555), _request("GET", "/status"))
    assert sent.startswith(b"HTTP/1.0 503")


def test_main_with_the_no_token_flag_says_so_and_admits(tmp_path, monkeypatch, capsys):
    """With --no-token, main() says so on stderr and its handler admits (a 404 for an unknown route)."""
    made = _capture_server(monkeypatch)
    _argv(monkeypatch, tmp_path, "--no-token")
    serve.main()
    assert "--no-token" in capsys.readouterr().err
    sent = _drive(made[0][1], ("127.0.0.1", 5555), _request("GET", "/nope", headers=[LOCAL]))
    assert sent.startswith(b"HTTP/1.0 404")


def test_main_with_a_token_file_is_gated(tmp_path, monkeypatch, capsys):
    """With a token file, main() reports "token gated" and a request without the token gets a 403."""
    (tmp_path / serve.TOKEN_FILE).write_text("s3cret\n", encoding="utf-8")
    made = _capture_server(monkeypatch)
    _argv(monkeypatch, tmp_path)
    serve.main()
    assert "token gated" in capsys.readouterr().err
    sent = _drive(made[0][1], ("127.0.0.1", 5555), _request("GET", "/nope"))
    assert sent.startswith(b"HTTP/1.0 403") and b"X-FP-Token" in sent


# The Funnel lock. Behind `tailscale serve` every caller, tailnet or public, reaches this socket
# from 127.0.0.1, so the peer lock cannot tell them apart; Tailscale's proxy marks a request that
# came in through Funnel (the public internet) with Tailscale-Funnel-Request and strips client-sent
# Tailscale-* headers (ipn/ipnlocal/serve.go). The header's presence, whatever its value, is
# refused.
# -- Funnel lock tests: any Tailscale-Funnel-Request header gets the bare 403 --
FUNNEL = "Tailscale-Funnel-Request"
FUNNEL_VALUES = [
    "?1",
    "?0",
    pytest.param("", id="empty"),
    "true",
    pytest.param("x" * 300, id="long"),
]


def _raw(method, path, headers=(), body=b""):
    """A raw request (bytes) with Host: x, the given extra header lines and optional body."""
    lines = [f"{method} {path} HTTP/1.1", "Host: x", *headers]
    if body:
        lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode() + body


@pytest.mark.parametrize("value", FUNNEL_VALUES)
@pytest.mark.parametrize("method", METHODS)
def test_a_funnel_request_gets_the_bare_403_and_no_method_runs(tmp_path, method, value):
    """Any value of the Funnel header, on any method, gets the bare 403 and no do_* runs."""
    ran = []
    cls = _recording(serve._handler(_state(tmp_path, no_token=True)), ran)
    raw = _raw(method, "/health", [f"{FUNNEL}: {value}"])
    assert _drive(cls, ("127.0.0.1", 5555), raw) == serve._FORBIDDEN
    assert ran == [], "a Funnel request must never reach a do_* method"


@pytest.mark.parametrize("name", [FUNNEL.lower(), FUNNEL.upper(), "Tailscale-funnel-REQUEST"])
def test_the_funnel_header_is_matched_whatever_its_case(tmp_path, name):
    """The Funnel header is found whatever its letter case."""
    cls = serve._handler(_state(tmp_path, no_token=True))
    raw = _raw("GET", "/health", [f"{name}: ?1"])
    assert _drive(cls, ("100.64.0.7", 5555), raw) == serve._FORBIDDEN


@pytest.mark.parametrize("gate", [{"no_token": True}, {}, {"token": "s3cret"}])
@pytest.mark.parametrize("path", ["/health", "/status", "/query?q=x", "/graph", "/nope"])
def test_a_funnel_request_is_refused_before_the_route_and_the_token_gate(tmp_path, gate, path):
    """A Funnel GET is refused bare on every route and gate setting, even with the right token."""
    cls = serve._handler(_state(tmp_path, **gate))
    raw = _raw("GET", path, [f"{FUNNEL}: ?1", "X-FP-Token: s3cret"])
    assert _drive(cls, ("127.0.0.1", 5555), raw) == serve._FORBIDDEN, "even with the right token"


@pytest.mark.parametrize("gate", [{"no_token": True}, {}, {"token": "s3cret"}])
def test_a_funnel_post_is_refused_before_the_gate_too(tmp_path, gate):
    """A Funnel POST to /query is refused bare on every gate setting."""
    cls = serve._handler(_state(tmp_path, **gate))
    raw = _raw("POST", "/query", [f"{FUNNEL}: ?1", "X-FP-Token: s3cret"], b"{}")
    assert _drive(cls, ("127.0.0.1", 5555), raw) == serve._FORBIDDEN


def test_the_same_requests_without_the_funnel_header_are_answered_normally(tmp_path):
    """Positive control: without the header (or with a look-alike name) requests get normal answers."""
    cls = serve._handler(_state(tmp_path, token="s3cret"))
    serve_identity = ["Tailscale-User-Login: rab@example.com", "X-FP-Token: s3cret"]
    for headers, path, status in (
        ([], "/health", b"200"),
        (["X-FP-Token: s3cret"], "/nope", b"404"),
        (serve_identity, "/nope", b"404"),
        (["Tailscale-Funnel-Requests: ?1", "X-FP-Token: s3cret"], "/nope", b"404"),
    ):
        sent = _drive(cls, ("127.0.0.1", 5555), _raw("GET", path, headers))
        assert sent.startswith(b"HTTP/1.0 " + status), (headers, path)


def test_a_funnel_request_body_is_never_read(tmp_path):
    """A plain POST has its body read; a Funnel POST is refused with its body left unread."""
    cls = serve._handler(_state(tmp_path, no_token=True))
    plain = _FakeConn(_raw("POST", "/query", [], b"{}"))
    cls(plain, ("127.0.0.1", 5555), None)
    assert plain.stream.unread == b"", "positive control: a plain POST has its body read"
    conn = _FakeConn(_raw("POST", "/query", [f"{FUNNEL}: ?1"], b"{}"))
    cls(conn, ("127.0.0.1", 5555), None)
    assert bytes(conn.sent) == serve._FORBIDDEN
    assert conn.stream.unread == b"{}", "the refusal left the request's body unread"


def test_a_funnel_refusal_is_noted_on_stderr(tmp_path, monkeypatch, capsys):
    """A Funnel refusal writes one stderr line mentioning Funnel and numbered #1."""
    monkeypatch.setattr(serve, "_REFUSALS", 0)
    cls = serve._handler(_state(tmp_path, no_token=True))
    _drive(cls, ("127.0.0.1", 5555), _raw("GET", "/health", [f"{FUNNEL}: ?1"]))
    err = capsys.readouterr().err
    assert "Funnel" in err and err.rstrip().endswith("#1")


def test_a_funnel_request_over_a_real_socket_and_the_server_survives(tmp_path):
    """Over a real socket a Funnel request reads the bare 403 and /health still answers after."""
    with _running(_state(tmp_path, token="s3cret")) as port:
        with socket.create_connection(("127.0.0.1", port), timeout=10) as s:
            s.sendall(_raw("GET", "/health", [f"{FUNNEL}: ?1"]))
            got = b""
            while chunk := s.recv(4096):
                got += chunk
        assert got == serve._FORBIDDEN
        assert _call(port, "/health") == (200, {"ok": True})


# -- request locks: Host pin, Origin, Sec-Fetch-Site and proof of origin (stubs, fixtures, tests) --
# The request locks. A foreign web page open in his browser on one of his tailnet devices fires
# requests at this address (it learned the address from a screenshot), and the peer lock admits it,
# because the device is a tailnet peer. Over PLAIN HTTP a browser sends no Sec-Fetch-* header, so
# the requests below model what such a page can really send: an Origin on a POST or a cross-origin
# fetch, maybe a Referer, and on an <img>, link, iframe or form GET nothing at all. Each test
# violates one rule after a positive control.
FOREIGN = "evil.example"
BROWSER = [
    "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Accept: image/avif,image/webp,*/*;q=0.8",
    "Accept-Language: en-US,en;q=0.5",
    "Connection: keep-alive",
]


class _FakeStore:
    """An index that exists, so /graph gets as far as the (stubbed) graph build."""

    def __init__(self, path):
        """Ignore the path; there is no real index."""
        pass

    def exists(self):
        """Report that an index exists."""
        return True

    def open_readonly(self):
        """Do nothing (no database is opened)."""
        pass

    def close(self):
        """Do nothing (nothing was opened)."""
        pass


@pytest.fixture
def ran(monkeypatch):
    """Stand-ins for the routes' work that record being called: what a refusal must never do."""
    calls = []

    def status_run(root):
        """Stub for status.run: record the call, return an empty status document."""
        calls.append("status")
        return {"available": False}

    def query_run(*args, **kw):
        """Stub for query.run: record the call, return an empty hit list."""
        calls.append("query")
        return {"available": True, "hits": []}

    def graph_cached(index, store, **levers):
        """Stub for graph.cached: record the call, return an empty graph."""
        calls.append("graph")
        return {"nodes": [], "edges": []}

    monkeypatch.setattr(serve.status, "run", status_run)
    monkeypatch.setattr(serve.query, "run", query_run)
    monkeypatch.setattr(serve.graph, "cached", graph_cached)
    monkeypatch.setattr(serve, "Store", _FakeStore)
    return calls


def _pinned(tmp_path, **kw):
    """The real Handler over a state whose Host pin is this machine's names (NAMES)."""
    return serve._handler(_state(tmp_path, names=NAMES, **kw))


def _answer(sent):
    """(status code, JSON body or None, lower-cased headers) of what the server wrote."""
    head, _, body = sent.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    headers = {k.lower(): v for k, _, v in (ln.partition(": ") for ln in lines[1:])}
    is_json = headers.get("content-type", "").startswith("application/json")
    return int(lines[0].split()[1]), (json.loads(body) if is_json else None), headers


def _ask(cls, method="GET", path="/status", **kw):
    """One request through the real handler from a loopback peer (which is what `tailscale serve`
    makes every tailnet caller look like)."""
    return _answer(_drive(cls, ("127.0.0.1", 5555), _request(method, path, **kw)))


OUR_HOSTS = [
    "127.0.0.1",
    "127.0.0.1:8765",
    "127.9.8.7",
    "localhost",
    "localhost:8765",
    "LOCALHOST",
    "[::1]:8765",
    LABEL,
    f"{LABEL}:8080",
    TAILNET,
    f"{TAILNET}:8080",
    TAILNET.upper(),
    f"{TAILNET}.",
    f"{TAILNET}.:8080",
]
OTHER_HOSTS = [
    FOREIGN,
    f"{FOREIGN}:8765",
    "127.0.0.1.evil.example",
    "localhost.evil.example",
    "other.tail-test.ts.net",
    f"x.{TAILNET}",
    f"{LABEL}.other-tail.ts.net",
    f"{LABEL}.{FOREIGN}",
    "100.64.0.7",
    "192.168.2.207",
    "8.8.8.8",
    "0.0.0.0",
    "router",
    "x",
    "127.0.0.1@evil.example",
    "evil.example@127.0.0.1",
    "127.0.0.1:80:90",
    "127.0.0.1/",
    "[::ffff:8.8.8.8]",
    "ts.net",
    ".ts.net",
    "",
]


@pytest.mark.parametrize("host", OUR_HOSTS)
def test_the_host_pin_admits_loopback_localhost_and_this_machines_names(tmp_path, ran, host):
    """Each Host in OUR_HOSTS passes the Host pin and the status route runs."""
    code, _, _ = _ask(_pinned(tmp_path, no_token=True), host=host, headers=[LOCAL])
    assert code == 200 and ran == ["status"]


@pytest.mark.parametrize("host", OTHER_HOSTS)
def test_the_host_pin_refuses_every_other_name(tmp_path, ran, host):
    """Each Host in OTHER_HOSTS is a 403 with reason "host" and no route runs."""
    code, doc, _ = _ask(_pinned(tmp_path, no_token=True), host=host, headers=[LOCAL])
    assert code == 403 and doc["reason"] == "host" and ran == []


def test_a_request_with_no_host_or_two_hosts_is_refused(tmp_path, ran):
    """No Host header, or two Host headers, is refused with reason "host"."""
    cls = _pinned(tmp_path, no_token=True)
    for kw in (
        {"host": None, "headers": [LOCAL]},
        {"headers": [LOCAL, f"Host: {LABEL}"]},
        {"headers": [LOCAL, f"Host: {FOREIGN}"]},
    ):
        code, doc, _ = _ask(cls, **kw)
        assert code == 403 and doc["reason"] == "host", kw
    assert ran == []


# The last round's item 1: the Host check is the ONLY one that admits loopback, 'localhost' and the
# IPv4-mapped forms of loopback (`tailscale serve` may rewrite Host to 127.0.0.1:<port>). Origin and
# Referer name a PAGE, and a page served from loopback is some other app on this machine.
MAPPED_LOOPBACK_HOSTS = [
    "[::ffff:127.0.0.1]",
    "[::ffff:127.0.0.1]:8765",
    "[::ffff:7f00:1]",
    "[::FFFF:127.9.8.7]:8765",
]
MAPPED_OTHER_HOSTS = [
    "[::ffff:100.64.0.7]",
    "[::ffff:192.168.2.207]",
    "[::ffff:0.0.0.0]",
    "[::ffff:8.8.8.8]:8765",
]


# -- IPv4-mapped loopback Host forms, tested under both interpreter behaviours --
@pytest.fixture(params=["this Python", "mapped form ignored"])
def ipaddress_of(request, monkeypatch):
    """The ipaddress module as this Python has it, and with its IPv6 is_loopback simulated as only
    '::1', so an IPv4-mapped loopback ('::ffff:127.0.0.1') is NOT is_loopback: what an interpreter
    that does not unmap a mapped form would say (3.12.13's unmaps it, so its own answer is not what
    the Host check may lean on; the CI runs another Python). Both must give the same answers."""
    if request.param == "mapped form ignored":
        monkeypatch.setattr(ipaddress.IPv6Address, "is_loopback", property(lambda a: int(a) == 1))
    return request.param


def _cls_for(tmp_path, pin):
    """The real Handler over the pinned names (NAMES) or over the loose pin (names None)."""
    names = NAMES if pin == "pinned" else None
    return serve._handler(_state(tmp_path, names=names, no_token=True))


@pytest.mark.parametrize("pin", ["pinned", "loose"])
@pytest.mark.parametrize("host", MAPPED_LOOPBACK_HOSTS)
def test_the_host_check_admits_ipv4_mapped_loopback_forms(tmp_path, ran, ipaddress_of, pin, host):
    """IPv4-mapped loopback Hosts pass under the pinned and the loose pin."""
    assert _ask(_cls_for(tmp_path, pin), host=host, headers=[LOCAL])[0] == 200
    assert ran == ["status"]


@pytest.mark.parametrize("pin", ["pinned", "loose"])
@pytest.mark.parametrize("host", MAPPED_OTHER_HOSTS)
def test_the_host_check_refuses_ipv4_mapped_forms_of_anything_else(
    tmp_path, ran, ipaddress_of, pin, host
):
    """IPv4-mapped forms of non-loopback addresses are refused as "host"; a mapped loopback is the control."""
    assert _ask(_cls_for(tmp_path, pin), host="[::ffff:127.0.0.1]", headers=[LOCAL])[0] == 200
    code, doc, _ = _ask(_cls_for(tmp_path, pin), host=host, headers=[LOCAL])
    assert code == 403 and doc["reason"] == "host" and ran == ["status"]


# -- the loose Host pin (used when the tailscale read failed) --
LOOSE_OK = ["x", "archlinux", TAILNET, "anything.ts.net", "a.b.ts.net", "localhost", "[::1]:8765"]
LOOSE_NO = [FOREIGN, "a.b.example", "ts.net", ".ts.net", "x.ts.net.example", "100.64.0.7", ""]


@pytest.mark.parametrize("host", LOOSE_OK)
def test_the_loose_pin_admits_single_label_and_ts_net_names(tmp_path, ran, host):
    """With no pinned names, single-label and *.ts.net Hosts still pass."""
    cls = serve._handler(_state(tmp_path, no_token=True))  # names None: the tailscale read failed
    assert _ask(cls, host=host, headers=[LOCAL])[0] == 200


@pytest.mark.parametrize("host", LOOSE_NO)
def test_the_loose_pin_still_refuses_everything_else(tmp_path, ran, host):
    """With no pinned names, other Hosts are refused as "host" and no route runs."""
    cls = serve._handler(_state(tmp_path, no_token=True))
    code, doc, _ = _ask(cls, host=host, headers=[LOCAL])
    assert code == 403 and doc["reason"] == "host" and ran == []


@pytest.mark.parametrize(
    ("raw", "host"),
    [
        ("[::1]:8765", "::1"),
        ("Name.TS.net.:8080", "name.ts.net"),
        ("127.0.0.1", "127.0.0.1"),
        ("a@b", ""),
        ("a b", ""),
        ("a:1:2", ""),
        ("a/b", ""),
        (".", "."),
        ("", ""),
        (None, ""),
    ],
)
def test_host_of_reads_host_and_port_and_nothing_else(raw, host):
    """_host_of returns the lower-cased host of host[:port], and "" for anything else."""
    assert serve._host_of(raw) == host


# -- Origin rule: only the pinned tailnet names are ours --
OUR_ORIGINS = [
    f"http://{TAILNET}:8080",
    f"http://{TAILNET}",
    f"https://{TAILNET}",
    f"http://{LABEL}:8080",
    f"HTTP://{TAILNET.upper()}:8080",
]
# Loopback, 'localhost' and IPv4-mapped forms pass the Host check but are NOT ours as an Origin or a
# Referer: only the pinned tailnet names are (the last round's item 1).
LOOPBACK_ORIGINS = [
    "http://127.0.0.1:8765",
    "http://127.9.8.7",
    "http://localhost:8765",
    "HTTP://LOCALHOST",
    "http://[::1]:8765",
    "http://[::1]",
    "http://[::ffff:127.0.0.1]:8765",
    "http://[::ffff:7f00:1]",
    "https://[::FFFF:127.0.0.1]",
    "http://[::ffff:100.64.0.7]:8080",
    "http://[::ffff:8.8.8.8]",
]
FOREIGN_ORIGINS = [
    f"http://{FOREIGN}",
    f"https://{FOREIGN}:8443",
    "null",
    "NULL",
    "file://",
    "chrome-extension://abcdef",
    f"http://{TAILNET}.{FOREIGN}",
    f"http://{TAILNET}@{FOREIGN}",
    f"http://{FOREIGN}/{TAILNET}",
    TAILNET,
    "http://100.64.0.7:8080",
    "",
]


@pytest.mark.parametrize("origin", OUR_ORIGINS)
def test_a_present_origin_that_is_ours_is_admitted(tmp_path, ran, origin):
    """An Origin naming a pinned tailnet name passes and the route runs."""
    code, _, _ = _ask(_pinned(tmp_path, no_token=True), headers=[LOCAL, f"Origin: {origin}"])
    assert code == 200 and ran == ["status"]


@pytest.mark.parametrize("origin", FOREIGN_ORIGINS)
def test_a_foreign_or_null_origin_is_refused_even_with_the_proof_header(tmp_path, ran, origin):
    """A foreign, "null" or empty Origin is a 403 "origin" even when X-FP-Local is sent."""
    # a cross-origin fetch() GET carries its page's Origin; a page cannot add X-FP-Local without a
    # preflight that never succeeds, but the Origin is refused on its own either way
    cls = _pinned(tmp_path, no_token=True)
    code, doc, _ = _ask(cls, headers=[LOCAL, f"Origin: {origin}"])
    assert code == 403 and doc["reason"] == "origin" and ran == []


@pytest.mark.parametrize("origin", LOOPBACK_ORIGINS)
def test_a_loopback_or_mapped_origin_is_not_ours_though_its_host_passes(
    tmp_path, ran, ipaddress_of, origin
):
    """A loopback or mapped Origin is refused as "origin" though the same Host passes."""
    # a page served from loopback is some other app on this machine, and its simple requests carry
    # an Origin naming loopback; the Host check admits loopback (tailscale serve may rewrite Host
    # to 127.0.0.1:<port>), the Origin check must not
    cls = _pinned(tmp_path, no_token=True)
    positive = [LOCAL, f"Origin: http://{TAILNET}:8080"]
    assert _ask(cls, host="127.0.0.1:8765", headers=positive)[0] == 200, "control: Host and Origin"
    code, doc, _ = _ask(cls, host="127.0.0.1:8765", headers=[LOCAL, f"Origin: {origin}"])
    assert code == 403 and doc["reason"] == "origin" and ran == ["status"]


def test_two_origin_headers_are_refused(tmp_path, ran):
    """Two Origin headers are refused as "origin" even if both are ours."""
    cls = _pinned(tmp_path, no_token=True)
    headers = [LOCAL, f"Origin: http://{TAILNET}", f"Origin: http://{TAILNET}"]
    code, doc, _ = _ask(cls, headers=headers)
    assert code == 403 and doc["reason"] == "origin" and ran == []


# -- Sec-Fetch-Site rule --
@pytest.mark.parametrize("value", ["same-origin", "none", "SAME-ORIGIN", " none "])
def test_sec_fetch_site_own_values_pass_and_are_a_proof_on_their_own(tmp_path, ran, value):
    """same-origin and none pass, and count as proof of origin without any custom header."""
    # Sent only to https URLs and loopback; over plain http a browser sends none of these headers
    code, _, _ = _ask(_pinned(tmp_path, no_token=True), headers=[f"Sec-Fetch-Site: {value}"])
    assert code == 200 and ran == ["status"]


@pytest.mark.parametrize("value", ["cross-site", "CROSS-SITE", "same-site", "", "nonsense"])
def test_sec_fetch_site_anything_else_is_refused_even_with_the_proof_header(tmp_path, ran, value):
    """cross-site, same-site, empty or unknown Sec-Fetch-Site is a 403 "fetch-site"."""
    cls = _pinned(tmp_path, no_token=True)
    code, doc, _ = _ask(cls, headers=[LOCAL, f"Sec-Fetch-Site: {value}"])
    assert code == 403 and doc["reason"] == "fetch-site" and ran == []


def test_a_cross_site_link_click_is_refused_too(tmp_path, ran):
    """A cross-site navigation (a link click) to /graph is refused as "fetch-site"."""
    cls = _pinned(tmp_path, no_token=True)
    nav = ["Sec-Fetch-Site: cross-site", "Sec-Fetch-Mode: navigate", "Sec-Fetch-Dest: document"]
    code, doc, _ = _ask(cls, path="/graph", headers=nav)
    assert code == 403 and doc["reason"] == "fetch-site" and ran == []


def test_the_proof_rule_refuses_a_cross_site_fetch_site_on_its_own(tmp_path, ran):
    """With the parse-time lock disabled, the GET proof rule alone refuses a cross-site fetch."""
    # defence in depth: with the parse-time lock switched off, the GET rule alone still refuses a
    # cross-site Sec-Fetch-Site, even beside the custom header (the browser's word outranks it)
    cls = _pinned(tmp_path, no_token=True)
    cls._request_refusal = lambda self: None
    code, doc, _ = _ask(cls, path="/graph", headers=[LOCAL, "Sec-Fetch-Site: cross-site"])
    assert code == 403 and doc["reason"] == "unproven-origin" and ran == []


# -- proof of origin on GETs: Referer, custom headers, and /health needing none --
GETS = ["/status", "/query?q=x", "/graph", "/nope", "/"]


@pytest.mark.parametrize("path", GETS)
def test_a_plain_http_get_with_no_origin_and_no_referer_is_refused(tmp_path, ran, path):
    """A browser-shaped GET with no Origin, Referer or proof header is a 403 "unproven-origin"."""
    # what a foreign page's <img>, link, iframe, navigation or form GET sends: a Host and nothing
    # that says where it came from. The route never runs, an unknown route included.
    code, doc, _ = _ask(_pinned(tmp_path, no_token=True), path=path, headers=BROWSER)
    assert code == 403 and doc["reason"] == serve.UNPROVEN_REASON == "unproven-origin"
    assert ran == [] and "X-FP-Local" in doc["error"]


FOREIGN_REFERERS = [
    f"http://{FOREIGN}/page",
    f"https://{FOREIGN}/",
    f"http://{FOREIGN}/http://127.0.0.1/",
    f"http://{FOREIGN}/?next=http://{TAILNET}/",
    f"http://{FOREIGN}#http://localhost/",
    f"http://{FOREIGN}\\@127.0.0.1/",
    f"http://127.0.0.1.{FOREIGN}/",
    f"http://127.0.0.1@{FOREIGN}/",
    f"http://{TAILNET}.{FOREIGN}/",
    "ftp://127.0.0.1/",
    "null",
    "127.0.0.1",
    "",
]
OUR_REFERERS = [
    f"http://{TAILNET}:8080/library",
    f"https://{TAILNET}/",
    f"http://{LABEL}/x?y=z",
]
LOOPBACK_REFERERS = [
    "http://127.0.0.1:8765/",
    "http://127.9.8.7/x",
    "http://localhost:3000/app",
    "HTTP://LOCALHOST/",
    "http://[::1]:8765/",
    "http://[::ffff:127.0.0.1]:8765/x?y=z",
    "http://[::ffff:7f00:1]/",
    "https://[::FFFF:127.0.0.1]/",
    "http://[::ffff:100.64.0.7]:8080/",
]


@pytest.mark.parametrize("referer", FOREIGN_REFERERS)
@pytest.mark.parametrize("path", ["/graph", "/query?q=x"])
def test_a_plain_http_get_with_a_foreign_referer_is_refused(tmp_path, ran, path, referer):
    """A GET whose Referer does not name a pinned tailnet name is refused as unproven."""
    # a foreign page can suppress its Referer, never forge one that names our host
    cls = _pinned(tmp_path, no_token=True)
    code, doc, _ = _ask(cls, path=path, headers=[*BROWSER, f"Referer: {referer}"])
    assert code == 403 and doc["reason"] == "unproven-origin" and ran == []


@pytest.mark.parametrize("referer", OUR_REFERERS)
def test_a_get_with_a_referer_that_names_our_host_is_a_proof(tmp_path, ran, referer):
    """A Referer naming a pinned tailnet name is accepted as proof and the route runs."""
    cls = _pinned(tmp_path, no_token=True)
    assert _ask(cls, headers=[*BROWSER, f"Referer: {referer}"])[0] == 200 and ran == ["status"]


@pytest.mark.parametrize("referer", LOOPBACK_REFERERS)
def test_a_loopback_or_mapped_referer_is_no_proof(tmp_path, ran, ipaddress_of, referer):
    """A loopback or mapped Referer is no proof; the X-FP-Local header added beside it is."""
    # the same rule as the Origin: a page served from loopback is some other app on this machine
    cls = _pinned(tmp_path, no_token=True)
    positive = [*BROWSER, f"Referer: http://{TAILNET}:8080/x"]
    assert _ask(cls, headers=positive)[0] == 200, "control: a Referer naming a pinned name proves"
    code, doc, _ = _ask(cls, headers=[*BROWSER, f"Referer: {referer}"])
    assert code == 403 and doc["reason"] == "unproven-origin" and ran == ["status"]
    assert _ask(cls, headers=[*BROWSER, f"Referer: {referer}", LOCAL])[0] == 200, "the header does"


@pytest.mark.parametrize("header", ["X-FP-Local: 1", "X-FP-Local:", "X-FP-Local: any value"])
def test_a_get_with_the_custom_header_is_a_proof_whatever_its_value(tmp_path, ran, header):
    """X-FP-Local proves origin whatever its value, even empty."""
    cls = _pinned(tmp_path, no_token=True)
    assert _ask(cls, headers=[*BROWSER, header])[0] == 200 and ran == ["status"]


def test_the_token_header_is_a_proof_too_and_the_gate_still_comes_first(tmp_path, ran):
    """X-FP-Token counts as proof, and a wrong or missing token is the gate's 403, not the proof's."""
    # X-FP-Token is as un-forgeable by a cross-site browser request as X-FP-Local (both force a
    # preflight), and every gated client already sends it; with a token set the gate judges it
    cls = _pinned(tmp_path, token="s3cret")
    assert _ask(cls, headers=["X-FP-Token: s3cret"])[0] == 200 and ran == ["status"]
    code, doc, _ = _ask(cls, headers=["X-FP-Token: wrong"])
    assert code == 403 and "reason" not in doc and "X-FP-Token" in doc["error"]
    code, doc, _ = _ask(cls, headers=BROWSER)
    assert code == 403 and "reason" not in doc, "no token: the gate answers, not the proof rule"
    assert ran == ["status"]


def test_health_needs_no_proof_but_still_answers_to_no_foreign_host_or_origin(tmp_path):
    """/health needs no token or proof, but a foreign Host or Origin is still refused."""
    cls = _pinned(tmp_path, token="s3cret")
    assert _ask(cls, path="/health", headers=BROWSER)[:2] == (200, {"ok": True})
    referer = f"Referer: http://{FOREIGN}/"
    assert _ask(cls, path="/health", headers=[referer])[0] == 200, "a read that changes nothing"
    assert _ask(cls, path="/health", host=FOREIGN)[1]["reason"] == "host"
    origin = f"Origin: http://{FOREIGN}"
    assert _ask(cls, path="/health", headers=[origin])[1]["reason"] == "origin"


# -- POST rules: simple cross-site POSTs, tool POSTs, and no CORS headers on any answer --
SIMPLE_POSTS = [
    ("text/plain", b'{"q": "x", "mode": "keyword"}'),
    ("application/x-www-form-urlencoded", b"q=x&mode=keyword"),
    (
        "multipart/form-data; boundary=----b",
        b'------b\r\nContent-Disposition: form-data; name="q"\r\n\r\nx\r\n------b--\r\n',
    ),
]


@pytest.mark.parametrize("gate", [{"no_token": True}, {"token": "s3cret"}])
@pytest.mark.parametrize(("ctype", "body"), SIMPLE_POSTS)
@pytest.mark.parametrize(
    "origin",
    [
        f"http://{FOREIGN}",
        "null",
        f"https://{FOREIGN}:8443",
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://[::ffff:127.0.0.1]:8765",
    ],
)
def test_a_simple_cross_site_post_is_refused_with_its_body_unread(
    tmp_path, ran, gate, ctype, body, origin
):
    """A "simple" cross-site POST to /query is a 403 "origin"; the route never runs, body unread."""
    # a browser always sends Origin on a POST; "null" is a sandboxed frame, a data: URL, or a page
    # under Referrer-Policy: no-referrer; a page served from loopback is some other app on this
    # machine. POST /query runs a query, so this is the route's guard: it never runs, the body
    # stays unread, and a token the page cannot have makes no difference.
    headers = [f"Origin: {origin}", f"Content-Type: {ctype}"]
    conn = _FakeConn(_request("POST", "/query", headers=headers, body=body))
    _pinned(tmp_path, **gate)(conn, ("127.0.0.1", 5555), None)
    code, doc, _ = _answer(bytes(conn.sent))
    assert code == 403 and doc["reason"] == "origin" and ran == []
    assert conn.stream.unread == body


@pytest.mark.parametrize(
    "headers", [[], [f"Origin: http://{TAILNET}:8080"], [f"Origin: http://{LABEL}"]]
)
def test_a_post_with_no_origin_or_one_of_ours_runs_the_query(tmp_path, ran, headers):
    """A POST with no Origin (a tool) or one of ours runs the query and gets a 200."""
    # no Origin on a POST means a tool, not a browser (a POST needs no X-FP-Local); our own Origin
    # is our own page
    body = b'{"q": "x", "mode": "keyword"}'
    cls = _pinned(tmp_path, no_token=True)
    code, _, _ = _ask(cls, "POST", "/query", headers=headers, body=body)
    assert code == 200 and ran == ["query"]


def test_no_answer_carries_a_cors_header_so_a_preflight_can_never_succeed(tmp_path, ran):
    """No response, refusal or success, has an Access-Control-* header; OPTIONS is a 501."""
    cls = _pinned(tmp_path, token="s3cret")
    preflight = [
        f"Origin: http://{FOREIGN}",
        "Access-Control-Request-Method: POST",
        "Access-Control-Request-Headers: x-fp-token,content-type",
    ]
    asked = [
        _ask(cls, "OPTIONS", "/query", headers=preflight),
        _ask(cls, "OPTIONS", "/query", headers=[LOCAL]),
        _ask(cls, headers=[f"Origin: http://{FOREIGN}", LOCAL, "X-FP-Token: s3cret"]),
        _ask(cls, headers=[LOCAL, "X-FP-Token: s3cret"]),
        _ask(cls, path="/health"),
    ]
    assert [a[0] for a in asked] == [403, 501, 403, 200, 200]
    for _, _, headers in asked:
        assert not [h for h in headers if h.startswith("access-control-")]


def test_a_funnel_request_is_refused_bare_before_the_request_locks(tmp_path):
    """A Funnel request gets the bare 403 (not the JSON one) whatever its Host."""
    cls = _pinned(tmp_path, no_token=True)
    for host in (FOREIGN, TAILNET):
        raw = _request("GET", "/graph", host=host, headers=[f"{FUNNEL}: ?1", LOCAL])
        assert _drive(cls, ("127.0.0.1", 5555), raw) == serve._FORBIDDEN


# -- real client shapes: what `tailscale serve` and File Portal's own tools actually send --
# what `tailscale serve` adds when it relays a tailnet request to a loopback port
SERVE_HEADERS = [
    "X-Forwarded-For: 100.64.0.7",
    "X-Forwarded-Proto: http",
    f"X-Forwarded-Host: {TAILNET}:8080",
    "Tailscale-User-Login: rab@example.com",
    "Tailscale-User-Name: Rab",
    "Tailscale-Headers-Info: https://tailscale.com/s/serve-headers",
]
CLIENTS = {
    # Control's Library tab (control/server.py _graph_fetch): urllib through `tailscale serve`,
    # which passes the ORIGINAL Host; it sends X-FP-Local always and X-FP-Token from the one copy
    # of the feed's token that lives outside both repos
    "control graph fetch, original Host": (
        f"{TAILNET}:8080",
        [
            *SERVE_HEADERS,
            LOCAL,
            "X-FP-Token: s3cret",
            "User-Agent: Python-urllib/3.12",
            "Accept-Encoding: identity",
            "Connection: close",
        ],
    ),
    # the same call when `tailscale serve` passes the TARGET's Host instead
    "control graph fetch, target Host": (
        "127.0.0.1:8765",
        [*SERVE_HEADERS, LOCAL, "X-FP-Token: s3cret", "User-Agent: Python-urllib/3.12"],
    ),
    # a session tool that sends only the token (sittings/S215/s215_close_sections.py)
    "a tool with the token only": (
        f"{TAILNET}:8080",
        [*SERVE_HEADERS, "X-FP-Token: s3cret", "User-Agent: Python-urllib/3.12"],
    ),
    "curl on the ThinkPad": (
        "127.0.0.1:8765",
        ["User-Agent: curl/8.10.1", "Accept: */*", "X-FP-Token: s3cret"],
    ),
}


@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize("path", ["/graph", "/status", "/query?q=Frege&mode=keyword&k=2"])
def test_every_real_client_shape_still_passes_on_every_get_route(tmp_path, ran, client, path):
    """Each known client shape reaches /graph, /status and /query with a 200 and the route runs."""
    host, headers = CLIENTS[client]
    code, _, _ = _ask(_pinned(tmp_path, token="s3cret"), path=path, host=host, headers=headers)
    assert code == 200 and ran == [path.split("?")[0].lstrip("/")], (client, path)


@pytest.mark.parametrize("client", CLIENTS)
def test_every_real_client_shape_still_passes_a_post_query(tmp_path, ran, client):
    """Each known client shape can POST /query and get a 200."""
    # curl -d sends form-urlencoded by default; a python client sends application/json
    host, headers = CLIENTS[client]
    body = b'{"q": "Frege", "mode": "keyword"}'
    ctype = "Content-Type: application/x-www-form-urlencoded"
    cls = _pinned(tmp_path, token="s3cret")
    code, _, _ = _ask(cls, "POST", "/query", host=host, headers=[*headers, ctype], body=body)
    assert code == 200 and ran == ["query"], client


def test_control_passes_on_its_proof_header_alone_when_the_feed_has_no_token(tmp_path, ran):
    """Control's graph fetch passes with X-FP-Local alone when the feed has no token."""
    # control/server.py sends X-FP-Token only when it has a token file; X-FP-Local always
    headers = [*SERVE_HEADERS, LOCAL, "User-Agent: Python-urllib/3.12", "Connection: close"]
    cls = _pinned(tmp_path, no_token=True)
    code, _, _ = _ask(cls, path="/graph", host=f"{TAILNET}:8080", headers=headers)
    assert code == 200 and ran == ["graph"]


def test_the_switchboard_probe_shape_passes_on_both_hosts(tmp_path):
    """The Switchboard's PowerShell /health probe passes on the tailnet Host and the loopback Host."""
    # widgets/switchboard/Switchboard.ps1 probes <peer>/index/health: Invoke-WebRequest, no token
    agent = "User-Agent: Mozilla/5.0 (Windows NT 10.0; en-US) WindowsPowerShell/5.1.19041.4648"
    cls = _pinned(tmp_path, token="s3cret")
    for host in (f"{TAILNET}:8080", "127.0.0.1:8765"):
        answer = _ask(cls, path="/health", host=host, headers=[agent, "Connection: Keep-Alive"])
        assert answer[:2] == (200, {"ok": True}), host


def test_every_answer_carries_nosniff_and_forbids_framing(tmp_path, ran):
    """Every answer, success or refusal, has nosniff and frame-ancestors 'none' headers."""
    cls = _pinned(tmp_path, no_token=True)
    gated = _pinned(tmp_path, token="s3cret")
    closed = _pinned(tmp_path)
    asked = [
        _ask(cls, headers=[LOCAL]),
        _ask(cls, path="/nope", headers=[LOCAL]),
        _ask(cls, "POST", "/query", body=b"[1]"),
        _ask(cls, path="/health"),
        _ask(cls, headers=BROWSER),
        _ask(cls, host=FOREIGN),
        _ask(gated, headers=[LOCAL]),
        _ask(closed, headers=[LOCAL]),
    ]
    assert [a[0] for a in asked] == [200, 404, 400, 200, 403, 403, 403, 503]
    for _, _, headers in asked:
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["content-security-policy"] == "frame-ancestors 'none'"


def test_a_request_refusal_is_noted_on_stderr_with_its_reason(tmp_path, monkeypatch, capsys):
    """A refused request logs its reason on stderr and never echoes the caller's own Host text."""
    monkeypatch.setattr(serve, "_REFUSALS", 0)
    _ask(_pinned(tmp_path, no_token=True), host=FOREIGN)
    err = capsys.readouterr().err
    assert "request refused: host" in err and err.rstrip().endswith("#1")
    assert FOREIGN not in err, "what the caller typed is never echoed into the log"


def test_the_request_locks_over_a_real_socket(tmp_path, ran):
    """The Host, Origin, Referer and proof rules hold over a real loopback connection."""
    with _running(_state(tmp_path, names=NAMES, no_token=True)) as port:

        def call(path, data=None, **headers):
            """GET (or POST with `data`) with the given headers; return (status, parsed JSON)."""
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data)
            for name, value in headers.items():
                req.add_header(name, value)
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, json.load(r)
            except urllib.error.HTTPError as e:
                return e.code, json.load(e)

        proof = {"X-FP-Local": "1"}
        assert call("/status", **proof)[0] == 200, "positive control: a tool, a loopback Host"
        assert call("/status")[1]["reason"] == "unproven-origin"
        assert call("/status", Host=FOREIGN, **proof)[1]["reason"] == "host"
        assert call("/status", Origin=f"http://{FOREIGN}", **proof)[1]["reason"] == "origin"
        assert call("/status", Origin="null", **proof)[1]["reason"] == "origin"
        assert call("/status", Referer=f"http://{FOREIGN}/")[1]["reason"] == "unproven-origin"
        assert call("/status", Referer=f"http://{TAILNET}/x", Host=TAILNET)[0] == 200
        body = b'{"q": "x", "mode": "keyword"}'
        assert call("/query", body, Origin="null")[1]["reason"] == "origin"
        assert call("/query", body, Origin=f"http://{TAILNET}")[0] == 200
        assert call("/query", body)[0] == 200, "no Origin: a tool"
        assert call("/health")[0] == 200
        assert ran == ["status", "status", "query", "query"]


# The last round's item 2: in the LOOSE mode (the tailscale read failed at start) the loose names
# apply to Host ONLY. Origin and Referer then prove nothing: every Origin is refused, a Referer is
# no proof, and only X-FP-Local, X-FP-Token (or a browser's own Sec-Fetch-Site) proves a GET.
LOOSE_ORIGINS = [
    f"http://{TAILNET}:8080",
    f"http://{LABEL}",
    "http://anything.ts.net",
    "http://x",
    "http://127.0.0.1:8765",
    "http://localhost",
    "http://[::ffff:127.0.0.1]:8765",
    "null",
    f"http://{FOREIGN}",
]
LOOSE_REFERERS = [
    f"http://{TAILNET}:8080/x",
    f"http://{LABEL}/",
    "http://anything.ts.net/",
    "http://x/",
    "http://localhost/",
    "http://127.0.0.1:8765/",
]


def _loose(tmp_path, **kw):
    """The real Handler over the LOOSE pin (names None: the tailscale read failed at start)."""
    return serve._handler(_state(tmp_path, names=None, **kw))


@pytest.mark.parametrize("origin", LOOSE_ORIGINS)
def test_the_loose_pin_refuses_every_origin_even_with_the_proof_header(tmp_path, ran, origin):
    """Under the loose pin every Origin is a 403 "origin"; the pinned control passes."""
    pinned = [LOCAL, f"Origin: http://{TAILNET}:8080"]
    assert _ask(_pinned(tmp_path, no_token=True), headers=pinned)[0] == 200, "control: pinned"
    cls = _loose(tmp_path, no_token=True)
    code, doc, _ = _ask(cls, headers=[LOCAL, f"Origin: {origin}"])
    assert code == 403 and doc["reason"] == "origin" and ran == ["status"]


@pytest.mark.parametrize("referer", LOOSE_REFERERS)
def test_the_loose_pin_takes_no_referer_as_proof(tmp_path, ran, referer):
    """Under the loose pin no Referer proves origin; the pinned control does."""
    pinned = [*BROWSER, f"Referer: http://{TAILNET}:8080/x"]
    assert _ask(_pinned(tmp_path, no_token=True), headers=pinned)[0] == 200, "control: pinned"
    cls = _loose(tmp_path, no_token=True)
    code, doc, _ = _ask(cls, headers=[*BROWSER, f"Referer: {referer}"])
    assert code == 403 and doc["reason"] == "unproven-origin" and ran == ["status"]


def test_the_loose_pin_still_proves_by_the_custom_headers_and_sec_fetch_site(tmp_path, ran):
    """Under the loose pin X-FP-Local, X-FP-Token and Sec-Fetch-Site same-origin still prove a GET."""
    cls = _loose(tmp_path, no_token=True)
    for header in (LOCAL, "X-FP-Token: anything", "Sec-Fetch-Site: same-origin"):
        assert _ask(cls, headers=[*BROWSER, header])[0] == 200, header
    assert _ask(_loose(tmp_path, token="s3cret"), headers=["X-FP-Token: s3cret"])[0] == 200
    assert ran == ["status"] * 4


def test_the_loose_pin_refuses_a_posts_own_looking_origin_and_admits_a_tool(tmp_path, ran):
    """Under the loose pin a POST with any Origin is refused (body unread); an Origin-less POST runs."""
    cls = _loose(tmp_path, no_token=True)
    body = b'{"q": "x", "mode": "keyword"}'
    headers = [f"Origin: http://{TAILNET}", "Content-Type: text/plain"]
    conn = _FakeConn(_request("POST", "/query", headers=headers, body=body))
    cls(conn, ("127.0.0.1", 5555), None)
    code, doc, _ = _answer(bytes(conn.sent))
    assert code == 403 and doc["reason"] == "origin" and ran == []
    assert conn.stream.unread == body
    code, _, _ = _ask(cls, "POST", "/query", body=body)
    assert code == 200 and ran == ["query"], "no Origin on a POST is a tool, and still passes"


# -- unit tests of own_name / origin_ok / referer_ok against a pin that holds IP literals --
# A pin that held an IP literal cannot happen (the names come from a DNS name), but the rule is
# "refused outright", so it is tested against a pin that does.
IP_PIN = frozenset(
    {
        TAILNET,
        "127.0.0.1",
        "::1",
        "::ffff:127.0.0.1",
        "::ffff:7f00:1",
        "100.64.0.7",
        "::ffff:100.64.0.7",
    }
)


@pytest.mark.parametrize(
    ("name", "names", "expected"),
    [
        (TAILNET, NAMES, True),
        (LABEL, NAMES, True),
        (TAILNET, frozenset({LABEL}), False),
        ("localhost", NAMES, False),
        ("127.0.0.1", NAMES, False),
        ("::1", NAMES, False),
        ("::ffff:127.0.0.1", NAMES, False),
        ("", NAMES, False),
        (TAILNET, None, False),
        (TAILNET, frozenset(), False),
        ("", frozenset({""}), False),
        (TAILNET, IP_PIN, True),
        ("127.0.0.1", IP_PIN, False),
        ("::1", IP_PIN, False),
        ("::ffff:127.0.0.1", IP_PIN, False),
        ("::ffff:7f00:1", IP_PIN, False),
        ("100.64.0.7", IP_PIN, False),
        ("::ffff:100.64.0.7", IP_PIN, False),
    ],
)
def test_own_name_is_a_pinned_tailnet_name_and_nothing_else(name, names, expected):
    """own_name is True only for a non-IP name that is in the pin."""
    assert serve.own_name(name, names) is expected


@pytest.mark.parametrize(
    "authority",
    [
        "127.0.0.1:8765",
        "[::1]:8765",
        "[::ffff:127.0.0.1]:8765",
        "[::ffff:7f00:1]",
        "[::ffff:100.64.0.7]:8080",
        "100.64.0.7:8080",
    ],
)
def test_origin_and_referer_refuse_an_ip_literal_even_if_the_pin_held_it(authority):
    """origin_ok and referer_ok refuse any IP-literal authority, though the tailnet name is the control."""
    assert serve.origin_ok(f"http://{TAILNET}:8080", IP_PIN) is True, "positive control"
    assert serve.referer_ok(f"http://{TAILNET}/x", IP_PIN) is True, "positive control"
    assert serve.origin_ok(f"http://{authority}", IP_PIN) is False
    assert serve.referer_ok(f"http://{authority}/x?y=z", IP_PIN) is False


# -- tailnet_names and the CLI wrapper, tested with fake reads and a fake subprocess --
def _status_doc(name):
    """A minimal `tailscale status --json` document whose Self.DNSName is `name`."""
    return {"Self": {"DNSName": name}}


class _Reads:
    """A fake `tailscale status --json`: each call takes the next outcome, raising an exception."""

    def __init__(self, *outcomes):
        """Queue the outcomes (documents, or exceptions to raise), one per call."""
        self.outcomes = list(outcomes)
        self.timeouts = []

    def __call__(self, timeout):
        """Record the timeout it was given, then return or raise the next queued outcome."""
        self.timeouts.append(timeout)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_tailnet_names_is_the_full_name_and_its_first_label():
    """One good read gives the full MagicDNS name and its first label, with no sleep."""
    reads, sleeps = _Reads(_status_doc("Thinkbox.Tail-Test.ts.net.")), []
    assert _REAL_TAILNET_NAMES(read=reads, sleep=sleeps.append) == NAMES
    assert reads.timeouts == [5] and sleeps == []


def test_tailnet_names_retries_three_times_five_seconds_apart():
    """Two failed reads then a good one: three attempts, each with a 5 s timeout, 5 s pauses."""
    timeout = subprocess.TimeoutExpired(["tailscale"], 5)
    reads, sleeps = _Reads(OSError("no such file"), timeout, _status_doc(TAILNET)), []
    assert _REAL_TAILNET_NAMES(read=reads, sleep=sleeps.append) == NAMES
    assert reads.timeouts == [5, 5, 5] and sleeps == [5.0, 5.0]


def test_tailnet_names_gives_up_after_three_attempts_with_an_empty_set():
    """Three failed or blank reads give an empty set after exactly two pauses."""
    bad = subprocess.CalledProcessError(1, ["tailscale"])
    reads, sleeps = _Reads(bad, _status_doc(""), {"Self": None}), []
    assert _REAL_TAILNET_NAMES(read=reads, sleep=sleeps.append) == frozenset()
    assert len(reads.timeouts) == 3 and sleeps == [5.0, 5.0]


@pytest.mark.parametrize("doc", [[], {}, {"Self": {}}, _status_doc(None), _status_doc(" . ")])
def test_tailnet_names_reads_a_blank_or_odd_document_as_a_failed_read(doc):
    """A blank or oddly shaped status document counts as a failed read (empty set)."""
    sleeps = []
    assert _REAL_TAILNET_NAMES(read=_Reads(doc, doc, doc), sleep=sleeps.append) == frozenset()


def test_the_cli_wrapper_runs_a_fixed_argv_with_a_timeout_and_no_shell(monkeypatch):
    """The CLI wrapper runs a fixed argv list (no shell) with a timeout, and falls back to /usr/bin."""
    seen = []

    def fake_run(argv, **kw):
        """Stub for subprocess.run: record argv and keywords, return canned JSON output."""
        seen.append((argv, kw))
        return subprocess.CompletedProcess(argv, 0, stdout=b'{"Self": {"DNSName": "a.b.ts.net."}}')

    monkeypatch.setattr(serve.subprocess, "run", fake_run)
    monkeypatch.setattr(serve.shutil, "which", lambda name: "/opt/ts/tailscale")
    assert _REAL_TAILSCALE_STATUS(5) == {"Self": {"DNSName": "a.b.ts.net."}}
    argv, kw = seen[0]
    assert argv == ["/opt/ts/tailscale", "status", "--json"]
    assert kw == {"capture_output": True, "timeout": 5, "check": True}
    monkeypatch.setattr(serve.shutil, "which", lambda name: None)
    _REAL_TAILSCALE_STATUS(5)
    assert seen[-1][0][0] == "/usr/bin/tailscale"


def test_main_reads_the_names_once_and_pins_the_host(
    tmp_path, monkeypatch, capsys, _no_tailscale_cli
):
    """main() reads the tailnet names once, prints the pin, and the handler pins Host and Origin."""
    made = _capture_server(monkeypatch)
    _argv(monkeypatch, tmp_path, "--no-token")
    serve.main()
    err = capsys.readouterr().err
    assert "Host pinned" in err and TAILNET in err and LABEL in err and "LOOSE" not in err
    cls = made[0][1]
    for host, code in ((TAILNET, 404), (f"{LABEL}:8080", 404), ("127.0.0.1", 404), (FOREIGN, 403)):
        sent = _drive(cls, ("127.0.0.1", 5555), _request("GET", "/nope", host, [LOCAL]))
        assert _answer(sent)[0] == code, host
    assert _no_tailscale_cli == [1], "the names are read once, at start, never per request"
    # the Origin is ours only by a pinned name: the pinned one passes the locks (404, no such
    # route), a loopback one does not
    for origin, code in ((f"http://{TAILNET}:8080", 404), ("http://127.0.0.1:8765", 403)):
        headers = [LOCAL, f"Origin: {origin}"]
        sent = _drive(cls, ("127.0.0.1", 5555), _request("GET", "/nope", TAILNET, headers))
        assert _answer(sent)[0] == code, origin


def test_main_runs_the_loose_pin_and_says_so_in_one_line(tmp_path, monkeypatch, capsys):
    """When no names are read, main() prints one LOOSE line and the handler uses the loose rules."""
    monkeypatch.setattr(serve, "tailnet_names", lambda: frozenset())
    made = _capture_server(monkeypatch)
    _argv(monkeypatch, tmp_path, "--no-token")
    serve.main()
    lines = [ln for ln in capsys.readouterr().err.splitlines() if "LOOSE" in ln]
    assert len(lines) == 1 and "tailscale read failed" in lines[0]
    assert "Host only" in lines[0] and "Origin" in lines[0] and "X-FP-Local" in lines[0]
    for host, code in (("x", 404), (TAILNET, 404), ("anything.ts.net", 404), (FOREIGN, 403)):
        sent = _drive(made[0][1], ("127.0.0.1", 5555), _request("GET", "/nope", host, [LOCAL]))
        assert _answer(sent)[0] == code, host
    # the loose names are for Host only: Origin and Referer fail closed in the handler main built
    headers = [LOCAL, f"Origin: http://{TAILNET}:8080"]
    sent = _drive(made[0][1], ("127.0.0.1", 5555), _request("GET", "/nope", TAILNET, headers))
    assert _answer(sent)[:2] == (403, {"error": serve.REFUSED_ERROR, "reason": "origin"})
    headers = [*BROWSER, f"Referer: http://{TAILNET}:8080/x"]
    sent = _drive(made[0][1], ("127.0.0.1", 5555), _request("GET", "/nope", TAILNET, headers))
    assert _answer(sent)[1]["reason"] == serve.UNPROVEN_REASON


# -- documentation check: curl lines in this package must carry the proof header --
# The last round's item 3: in --no-token mode a scripted client of a proven route (every GET but
# /health) must send X-FP-Local: 1, so a curl line in this package's README or scripts that hits one
# must carry the header (or X-FP-Token). A curl at /health needs neither.
PACKAGE = Path(__file__).resolve().parent.parent


def _unproven_curls(text):
    """The numbers of every command line that runs curl at something but /health without sending
    X-FP-Local or X-FP-Token (a backslash continuation joins its next line first). A comment line,
    and prose that does not start a command, are skipped."""
    bad = []
    # join backslash continuations, skip comments and non-commands, flag curl lines without the header
    for number, line in enumerate(re.sub(r"\\\r?\n", " ", text).splitlines(), 1):
        if line.lstrip().startswith("#") or not re.match(r"\s*(?:.*\|\s*)?curl\s", line):
            continue
        if "/health" not in line and not re.search(r"X-FP-(?:Local|Token)", line):
            bad.append(number)
    return bad


def test_the_curl_checker_flags_a_proven_route_without_the_header():
    """_unproven_curls flags exactly the curl lines that lack the header and are not /health."""
    text = "\n".join(
        [
            "curl https://h.ts.net/index/query?q=x",
            'curl -H "X-FP-Local: 1" https://h.ts.net/index/query?q=x',
            "curl -s https://h.ts.net/index/health",
            "  printf 'X-FP-Token: %s\\n' \"$T\" | curl -H @- https://h.ts.net/index/status",
            "# curl https://h.ts.net/index/status",
            "a prose line that says curl, a cron job",
            "curl 'https://h.ts.net/index/graph'",
            "curl \\",
            '  -H "X-FP-Local: 1" https://h.ts.net/index/graph',
        ]
    )
    assert _unproven_curls(text) == [1, 7]


def test_no_curl_line_in_this_package_hits_a_proven_route_without_the_header():
    """Reads README.md, scripts/ and systemd/ of this package; none may hold an unproven curl line."""
    files = [PACKAGE / "README.md", *sorted((PACKAGE / "scripts").glob("*"))]
    files += sorted((PACKAGE / "systemd").glob("*"))
    assert len(files) > 1 and all(f.is_file() for f in files)
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert _unproven_curls(text) == [], path.name
