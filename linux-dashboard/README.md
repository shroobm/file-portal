# linux-dashboard

A standalone GTK4 viewer for `~/file-portal/sorted/` — a thumbnail gallery for `photos`, a
browsable list for `documents`/`code`/`archive`/`misc`. Read-only: it never touches `inbox/` or
the allocator's sorting logic. See [`../docs/09-linux-dashboard.md`](../docs/09-linux-dashboard.md)
for the design rationale.

## Install on Arch Linux

```bash
cd linux-dashboard
./scripts/install.sh
```

This installs `gtk4`/`libadwaita`/`python-gobject` via `pacman` (one-time `sudo`, same category as
`tailscale up` itself), creates a venv for the rest of the Python deps, and registers an app-menu
launcher named "File Portal Dashboard".

## Run in the foreground (for development/debugging)

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m dashboard.main
```

`--system-site-packages` is required so `import gi` resolves to the pacman-installed GTK bindings
— pip can't install those reliably on its own.

## Toggling show/hide with a hotkey

The app is single-instance: running `python -m dashboard.main` again while it's already open hides
it if visible, or shows + focuses it if hidden. Bind a keyboard shortcut to that same command in
XFCE's *Settings > Keyboard > Application Shortcuts* to get a global toggle hotkey.

"Always on top" and "show on all workspaces" are left to xfwm4's own window properties (right-click
the titlebar) rather than duplicated in-app.

## Settings

Window size, refresh interval, category filters, and the photo date range live in
`~/.config/file-portal/dashboard.toml`, editable from the gear menu in the app's header bar or by
hand (re-read on next launch / next settings change, no restart required for in-app edits).

## Serving sorted/ to the tailnet (opt-in, loopback only) — S214 E16

`python -m dashboard.serve` is the sorted browse without the GTK window: it binds `127.0.0.1:<serve_port>`
(8766 by default, `serve_port` in dashboard.toml, `--port N` overrides) and nothing else, opens no other
port, and no unit ships for it. Reach it through `tailscale serve` — the pattern docs/06 names for a new
surface:

```bash
python -m dashboard.serve                                    # foreground
tailscale serve --bg --set-path /sorted http://127.0.0.1:8766   # tailnet-only, identity-bound
```

Routes (GET, read-only): `/health`; `/sorted?category=&from=&to=` — the same `scan()` model the window
renders, as JSON, paths relative to `sorted/`; `/thumb?path=&px=` — a small JPEG of one photo under
`sorted/photos` (GdkPixbuf, else Pillow, else an honest 501). Its own auth is `~/file-portal/serve.token`,
shared with the indexer's endpoint, and it fails closed (2026-09-30): when the file exists every route
but `/health` wants `X-FP-Token` equal to it (a missing or wrong token is a 403); with no file, or a blank
one, every route but `/health` answers 503 until the operator writes one or starts the server with
`--no-token`, the explicit opt-in to the tailnet identity alone; a token file that exists but cannot be
read aborts startup. `/health` is the one ungated route and answers `{"ok": true, "gated": <bool>}`.
Four locks under the token need no configuration: the server refuses to start unless its bind is a
literal loopback or Tailscale address; a peer that is neither loopback nor Tailscale gets a bare 403
before a request line is read; any request carrying a `Tailscale-Funnel-Request` header, whatever its
value, gets the same bare 403 before any route, token or body is read, `/health` included; and a request
that looks like a web page on another site is refused with a JSON 403 (below). Behind `tailscale serve`
every caller, tailnet or public, reaches this socket from `127.0.0.1`, and Tailscale's proxy sets the
Funnel header on every request that came in through **HTTP-mode** Funnel (`ipn/ipnlocal/serve.go`), so it
is the only thing that tells a public caller from a tailnet one there. A TCP-mode funnel forwards raw TCP
and carries no header, so nothing here can see it; `security/lockdown_check.py` D4/T1 in the private layer
is what catches any Funnel. Front this with `tailscale serve`, never `tailscale funnel`. Nothing here
opens, moves or writes a file. Tests: `pytest tests/` (hermetic; no GTK; none runs the tailscale CLI).

### Request locks: a foreign page in the operator's own browser (2026-09-30)

A page from another site, open in a browser on one of the operator's tailnet devices (it learned the
address from a screenshot), can never READ an answer, because no File Portal server answers CORS. It can
still fire "simple" requests: a GET from an `<img>`, a link, an iframe or a form, or a POST with a
`text/plain`, form or multipart body. The feeds are reached over plain http (`tailscale serve
--http=8080`), where a browser sends `Origin` on every POST and on any cross-origin fetch, `Referer`
unless the page suppressed it, and **no `Sec-Fetch-*` header at all**. So, before any route, token or
body, every request is checked, and a refusal is a 403 whose JSON `reason` names the rule:

| `reason` | Refuses | Note |
|---|---|---|
| `host` | no `Host`, two, or one that is not loopback (an IPv4-mapped form included), `localhost` or this machine's own tailnet name | closes DNS rebinding |
| `origin` | an `Origin` that is not http(s) over one of this machine's own tailnet names; `null` (a sandboxed frame, a `data:` URL), a loopback, `localhost` or IP-literal origin (an IPv4-mapped form included) and, while the Host pin is loose, every `Origin` are refused; any method | this server has no POST route, but the lock does not depend on that |
| `fetch-site` | a `Sec-Fetch-Site` other than `same-origin`, `same-site`, `none` | fires **only where a browser sends it** (https or loopback), so it is inert over plain http |
| `unproven-origin` | a GET (any route but `/health`) with no proof it came from our own page or tool | proof is `Sec-Fetch-Site` same-origin/same-site/none when sent, else a `Referer` naming one of this machine's own tailnet names (never while the pin is loose), else the header `X-FP-Local` (any value) or `X-FP-Token` |

The proof is a custom request header because a cross-site browser request cannot carry one without a CORS
preflight, and this server never answers a preflight (`OPTIONS` is the stdlib's 501). A client that sends
`X-FP-Token` (every gated call) needs no change while a token is set. **With `--no-token` a scripted client
of a proven route (every GET but `/health`: curl, a cron job, a session tool) must send `X-FP-Local: 1`**;
a curl line in this package that hits one must carry it (`tests/test_serve_lock.py` fails otherwise).
`/sorted` and `/thumb` change nothing, but both are proof-gated: a foreign page's `<img>` can read an
image's existence and size (`onload`, `naturalWidth`) even though it can read no bytes.

The Host pin reads this machine's own tailnet names once at start from `tailscale status --json`
(`Self.DNSName` and its first label; 3 tries, 5 s apart, 5 s each). Only the `Host` check admits loopback
(an IPv4-mapped form included) and `localhost` besides, because `tailscale serve` may hand the backend the
original `Host` or `127.0.0.1:<port>`; both pass. `Origin` and `Referer` are stricter: only the pinned
tailnet names are ours there, never loopback, `localhost` or an IP literal, because a page served from
loopback is some other app on this machine. If the read fails (the loose pin) the `Host` check also admits
any single-label name and any `*.ts.net` name, **for `Host` only**: every `Origin` is then refused, a
`Referer` proves nothing, and only `X-FP-Local`, `X-FP-Token` (or a browser's own `Sec-Fetch-Site`) prove a
GET; one line on stderr says so. There is no
proxy-header lock here (unlike servers reached directly): `tailscale serve` adds `X-Forwarded-*` and
`Tailscale-User-*` to everything it relays. Every answer carries `X-Content-Type-Options: nosniff` and
`Content-Security-Policy: frame-ancestors 'none'`.

## Uninstalling

```bash
rm ~/.local/share/applications/file-portal-dashboard.desktop
rm -rf ~/file-portal-src/linux-dashboard/.venv
```
