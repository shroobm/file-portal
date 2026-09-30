# linux-indexer

The user-level index station. It reconciles ONE SQLite file, `~/file-portal/index/index.sqlite`
(passages, a BM25 keyword index via FTS5, embeddings via the sqlite-vec extension), to the tip of
the bare authoritative vault (`~/file-portal/vault.git`, branch `main`) and answers hybrid
queries over it: every bundle's body markdown is split into ~800-character passages, embedded
through fastembed (ONNX Runtime, no torch; the model is a lever -- the fast English MiniLM by
default, a multilingual sibling one flip away because the vault already holds a Chinese book), and stored with the manifest's provenance (lane,
verdict, survival, bless, supersede). Everything is free and open source (SQLite public domain,
sqlite-vec Apache-2.0/MIT, fastembed Apache-2.0, the default embedding models and the ms-marco reranker
Apache-2.0; the jina reranker candidate named in the levers file is CC-BY-NC-4.0 and NOT open source), and an operator can open
the index with `sqlite3`, back it up by copying one file, and filter it with a WHERE clause.

**Status: built 2026-09-09 and deployed 2026-09-10 on the ThinkPad (units, timer, hook; first run 6 bundles → 3,951 passages), OPEN-TASKS D7.** Measured in
docs/11 Phase 3 (2026-07-19) and built as a separate consumer because the exporter copies
bytes and never reads them (CLAUDE_README Open Decision #5); the index lives beside the vault,
never inside it, and gates nothing -- no export, verdict or vault write waits on it. See
[`../docs/11-gpu-pipeline-revamp.md`](../docs/11-gpu-pipeline-revamp.md) (Phase 3) and
[`../docs/18-levers-and-heartbeats.md`](../docs/18-levers-and-heartbeats.md) (the levers).

Event model: `vault.git/hooks/post-update` fires `file-portal-indexer.service` without waiting
after every push (the exporter's or a hand push); the daily `file-portal-indexer.timer`
(`Persistent=true`) catches up on anything the hook could not announce. Each run is a whole-tree
reconcile keyed on the manifest's `source_sha256` and the `.md`/`manifest.json` blob shas:
unchanged bundles cost nothing, a supersede replaces one bundle's passages in place, a bless
rewrites metadata without the model, a Desktop filing re-keys, a deletion removes. Bundles that
break the contract (not exactly one `.md`, unreadable manifest, a sha vaulted twice) are refused,
logged, and the run exits 1 so the unit shows red -- nothing is guessed or auto-repaired.

## Run in the foreground (for development/debugging)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m indexer.main            # reconcile once (first run downloads the model, ~90 MB)
python -m indexer.status          # JSON: index tip vs vault tip, counts, model
echo "how does a viable system model regulate itself" | python -m indexer.query
python -m indexer.query --mode keyword --query "requisite variety"       # no model load
python -m indexer.query --mode keyword --query "9780471162131"           # an ISBN in a filename
python -m indexer.query --lane scan --verdict flag --query "figure"       # filters
python -m indexer.serve           # opt-in loopback HTTP endpoint, see below
```

Default root is `~/file-portal` (override with `--root`). Creates `index/` and `logs/` on
first run; logs to `logs/indexer.log`. `python -m indexer.main --rebuild` is the only way the
index is ever emptied and re-embedded (the store refuses a model, passage-size or tokenizer
mismatch until you say so). Levers live in `config/indexer.toml` and are read once per run.
Model files land in `~/file-portal/index/models/` once and are never re-fetched.

## Install as a systemd --user oneshot + timer

```bash
./scripts/install.sh
systemctl --user start file-portal-indexer.service    # first reconcile, now
systemctl --user list-timers file-portal-indexer.timer
journalctl --user -u file-portal-indexer -f
```

Never run `install.sh` with `sudo` -- it refuses to run as root on purpose, same as the
allocator. It installs both units, enables the timer, and installs the post-update hook into
`vault.git/hooks/` only if no hook is there already. Linger is enabled by the Part 1 bootstrap.

## Receipts

One line per run that changed the index, appended to `~/file-portal/receipts.jsonl` with the
exporter's own `append_receipt` shape (mirror copy in `indexer/receipts.py`):

```
{"ts": "...", "outcome": "indexed", "result": "pass", "tip": "50896d15", "bundle": "<dir>",
 "note": "Inbox/<dir>", "bundles": 6, "added": 0, "replaced": 1, "updated": 0, "removed": 0,
 "refused": 0, "unchanged": 5, "passages": 3012, "embed_s": 4.1,
 "model": "sentence-transformers/all-MiniLM-L6-v2", "model_sha": "<16 hex>",
 "passage_chars": 800, "passage_max_chars": 1200, "fts_tokenizer": "unicode61", "threads": 4}
```

`bundle`/`note` are present when exactly one bundle changed (the steady state). `result` is
`fail` when a bundle was refused. `index-failed` (with `error`) means the run could not
reconcile at all. No receipt is written when the tip was already indexed. Never the exporter's
outcomes -- the widget's alarms key on those.

## Query contract

`python -m indexer.query` reads the question from stdin (or `--query`), prints exactly one
JSON document, exits 0. `{"available": false, "reason": ...}` when there is no index yet.
Options: `--mode hybrid|vector|keyword`, `--top-k N`, `--bundle <substring of the vault path>`,
`--lane clean|scan`, `--verdict pass|flag|fail|none`. Hits carry `bundle`, `note`, `source`,
`source_sha256`, `heading`, `page_hint` (1-based page of the nearest preceding figure, or null
-- a hint, never a promise), `passage`, `text`, `score` (reciprocal-rank fusion), `matched_by`
(`vector`, `keyword`, `title` -- a hit on the bundle's filename/path, where an ISBN or title lives
-- or a `+`-joined combination) and, when the `rerank` lever is on, `rerank_score`.
The document also carries `mode`, `filters`, `tip`, `reconciled_at`, `model`, `rerank` and the
effective `levers`. Over the tailnet, as one fixed literal with the question on stdin:

```bash
tailscale ssh rab@archlinux '~/file-portal-src/linux-indexer/.venv/bin/python -m indexer.query'
```

## HTTP endpoint (opt-in, loopback only)

`python -m indexer.serve` binds `127.0.0.1:<serve_port>` and nothing else (`--port N` overrides the
lever for one run); it ships no unit
and nothing starts it. Routes: `GET /health`, `GET /status`, `GET /query?q=...&k=&mode=&bundle=&lane=&verdict=`,
`POST /query` (JSON body, same keys), `GET /graph` (the Library graph, cached beside the index). The model
stays warm, so a query costs milliseconds.
To reach it from the tailnet without opening a port, front it with Tailscale's own identity-bound
proxy (docs/06 names exactly this pattern):

```bash
tailscale serve --bg --set-path /index http://127.0.0.1:8765
# a scripted client of any route but /health must show where it came from: with --no-token send
# X-FP-Local: 1 (any value); with a token, X-FP-Token proves it too (see "Request locks", below)
curl -H "X-FP-Local: 1" "https://archlinux.<tailnet>.ts.net/index/query?q=requisite+variety&mode=keyword"
# with a token, without putting it in the process list:
printf 'X-FP-Token: %s\n' "$(cat ~/file-portal/serve.token)" | curl -H @- "https://archlinux.<tailnet>.ts.net/index/status"
```

### Its own auth: `~/file-portal/serve.token` (S214 E16; fails closed since 2026-09-30)

docs/06 asks a `tailscale serve`-fronted endpoint to carry its own auth. Write one line into
`~/file-portal/serve.token` (for example `openssl rand -hex 16 > ~/file-portal/serve.token && chmod 600`
`~/file-portal/serve.token`) and every route but `/health` requires the header `X-FP-Token` equal to it;
a missing or wrong token is a 403 that names the file. The gate fails closed: with no token file (or a
blank one) every route but `/health` answers 503 until the operator writes one, or starts the server with
`--no-token`, the explicit opt-in to the tailnet identity alone. A token file that exists but cannot be
read (a permission error, a directory in its place, bytes that are not text) aborts startup rather than
serving open, and a token that is present always gates, `--no-token` or not. `/health` is the one ungated
route; it answers `{"ok": true}` (`dashboard.serve`'s also says `"gated": <bool>`). The file is the
operator's and lives outside this repository (which is public). `dashboard.serve` (linux-dashboard)
reads the same file.

Four locks sit under the token and need no configuration. The server refuses to start unless its bind
is a literal loopback or Tailscale address. A connection from any peer that is neither loopback nor
Tailscale (`100.64.0.0/10`, `fd7a:115c:a1e0::/48`) gets a bare 403 before a request line is read. A
request carrying a `Tailscale-Funnel-Request` header, whatever its value, gets the same bare 403 before
any route, token or body is read, `/health` included. That one is what keeps a public caller out of
HTTP-mode Funnel (Tailscale's public-internet exposure), which reaches this loopback socket from
`127.0.0.1` exactly as a tailnet caller does; Tailscale's own proxy sets the header on every request that
came in through it and strips any client-sent copy (`ipn/ipnlocal/serve.go`). It covers **HTTP-mode
Funnel only**: a TCP-mode funnel forwards raw TCP and carries no header, so nothing here can see it, and
`security/lockdown_check.py` D4/T1 in the private layer is what catches any Funnel. Front this with
`tailscale serve`, never `tailscale funnel`. The fourth lock is the request lock, next.

### Request locks: a foreign page in the operator's own browser (2026-09-30)

A page from another site, open in a browser on one of the operator's tailnet devices (it learned the
address from a screenshot), can never READ an answer, because no File Portal server answers CORS. It can still fire
"simple" requests: a GET from an `<img>`, a link, an iframe or a form, or a POST whose body is
`text/plain`, form-urlencoded or multipart. The feeds are reached over plain http (`tailscale serve
--http=8080`), where a browser sends `Origin` on every POST and on any cross-origin fetch, `Referer`
unless the page suppressed it, and **no `Sec-Fetch-*` header at all**. So, before any route, token or
body, every request is checked, and a refusal is a 403 whose JSON `reason` names the rule:

| `reason` | Refuses | Note |
|---|---|---|
| `host` | no `Host`, two, or one that is not loopback (an IPv4-mapped form included), `localhost` or this machine's own tailnet name | closes DNS rebinding |
| `origin` | an `Origin` that is not http(s) over one of this machine's own tailnet names; `null` (a sandboxed frame, a `data:` URL, a no-referrer POST), a loopback, `localhost` or IP-literal origin (an IPv4-mapped form included) and, while the Host pin is loose, every `Origin` are refused; any method | a browser POST always sends one, so a simple cross-site POST dies here; a POST with none is a tool and passes |
| `fetch-site` | a `Sec-Fetch-Site` other than `same-origin`, `same-site`, `none` | fires **only where a browser sends it** (https or loopback), so it is inert over plain http |
| `unproven-origin` | a GET (any route but `/health`) with no proof it came from our own page or tool | proof is `Sec-Fetch-Site` same-origin/same-site/none when sent, else a `Referer` naming one of this machine's own tailnet names (never while the pin is loose), else the header `X-FP-Local` (any value) or `X-FP-Token` |

The proof is a custom request header because a cross-site browser request cannot carry one without a CORS
preflight, and this server never answers a preflight (`OPTIONS` is the stdlib's 501). Clients that already
send `X-FP-Token` (Control's Library tab) need no change while a token is set. **With `--no-token` a
scripted client of a proven route (every GET but `/health`: curl, a cron job, a session tool) must send
`X-FP-Local: 1`**; the curl lines in this README do. `/health` needs no proof (it changes nothing and
reveals nothing).

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

What each route does (the side effect is what the proof rule guards): `/health` nothing. `/status` reads
the index and runs `git rev-parse` on the vault. `/query` (GET or POST) writes nothing, but a server
started before the first index existed builds its embedder per request, and a cold build fetches the model
files. `/graph` rewrites `graph.json` beside the index when the vault's tip moved; it is a GET because its
one client (Control) calls it that way, so it is guarded instead of moved.

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

Hermetic: a real bare git vault under `tmp_path`, a real SQLite store with sqlite-vec and FTS5,
a deterministic hash embedder in place of the model (the reconcile and retrieval logic is what
is under test; embedding quality was measured against the real vault, docs/11 and the 2026-09-09
model bench). Nothing downloads, nothing touches `~/file-portal`.

## Uninstalling

```bash
systemctl --user disable --now file-portal-indexer.timer
rm ~/.config/systemd/user/file-portal-indexer.service ~/.config/systemd/user/file-portal-indexer.timer
systemctl --user daemon-reload
rm ~/file-portal/vault.git/hooks/post-update     # only if it is this lane's hook
rm -r ~/file-portal/index                         # derived data + model files; rebuilds in minutes
```
