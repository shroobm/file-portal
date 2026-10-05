# The Repair Bench — prototype (Stage G, docs/19 §7)

**"The human IS the vision model."** (Rab, docs/18.) The Survival Audit can say *where* a
conversion went wrong — degeneration zones with line numbers, omission runs with pages — but
not what the page really held. A human can, in one glance. This bench puts the source-PDF page
and the markdown at the flagged zone side by side and makes the repair one gesture.

## What it does

- **Navigate by evidence**: the damage map + zone chips come straight from the held bundle's
  `manifest["fidelity"]` block; clicking a zone opens the page the line ratio predicts
  (`line / md_lines × pages`) — a seed for the human to refine with ◂ ▸, not a claim.
- **Repair = one gesture**: drag a rectangle on the page (server crops the 220-dpi raster), or
  Ctrl+V a screenshot. Either way the image lands in the bundle's `assets/` as
  `_repair_pN_k.png` (collision-safe), embedded at the zone as `![[assets/…]]` — the vault's
  own reference style — with a provenance record appended to `manifest["repairs"]`
  (`ts / zone_line / page / asset / mode / note / by`).
- **Re-score is a PREVIEW**: it re-runs `fidelity_audit.degeneration()` on the current text and
  reports repairs-vs-zones — it writes **no** fidelity block and changes **no** verdict.
  Whether a repair image earns audit credit is an **unsigned policy question** (a text-layer restoration is credited as text since 2026-10-05, docs/28 §4a); Rab signs it
  (docs/19 §10) before any such credit exists in the real pipeline.
- **Inspect source evidence (OK-15 quarantine prototype)**: **◉ evidence** measures five
  independent PDF signals page by page — MuPDF warnings, logical page labels, a PyMuPDF/Xpdf
  reading-order comparison, a disposable all-OCG-off raster counterfactual, and embedded
  `/Thumb` metadata. Affected page buttons jump back to the source page. `partial` and
  `UNREAD` show their exact probe reasons; an absent `/Thumb` is measured absence, not failure.
  Every page-level `UNREAD` reason remains available in a bounded scroll surface. Pixels and
  extracted text are hashed/count-only in the report and are not retained.
- **Sandbox mode** (`--sandbox`) copies the bundle under `.sandbox/` and repairs the copy —
  how the acceptance harness runs, and how a first trial should.

## Run

```bash
# from prototypes/repair-bench, with the marker-env python (pymupdf lives there):
C:\Users\Bndit\ml\marker-env\Scripts\python.exe bench.py b6fbdd75f6242f53 --sandbox --token local-only-secret
# then open http://127.0.0.1:7077/?token=local-only-secret
```

The positional argument is a bundle directory or a bare sha16 resolved against
`ml\library\held\`. The source PDF is auto-found in `drop\done\` (override with `--pdf`).
Drop `--sandbox` to repair the real held bundle — Valentine is the designated first patient.

`acceptance.py` proves the loop end to end on a sandbox copy of the real Valentine (real
zones, real rasters, real stamps; the real bundle hash-verified untouched).

The token is required for every mutation and for the expensive evidence GET. The widget
generates and supplies its own token. The reading-order probe records the installed
`pdftotext` implementation and version; this Windows host currently supplies Xpdf 4.06, not
Poppler. Missing, failed, timed-out, non-UTF-8, or wrong-page-count oracle output is `UNREAD`.
A failed collection is cached in process as an explicit `UNREAD` report so repeated clicks do
not repay a 900-second failure; **↻ retry collection** is the deliberate retry. A concurrent
request returns `IN-PROGRESS` immediately and never starts a duplicate child.

## Who can reach it

The bench listens on `127.0.0.1` and, with `--also-bind <addr>`, on one more address that must be
a literal loopback or Tailscale IP (127.0.0.0/8, ::1, 100.64.0.0/10, fd7a:115c:a1e0::/48).
`0.0.0.0`, an empty string, `::`, a LAN or public address, or a name is refused at the start
(exit 2, "is not a literal loopback or Tailscale address"), before any bundle or socket exists.
`--host <name>` (repeatable) adds a name the bench answers to. A running bench refuses, in this order:

| Request | Answer |
|---|---|
| a connection from outside loopback and the tailnet | bare `403`, no body, connection closed before any request byte is read; the console names the address |
| a `Host` that is not 127.0.0.1, localhost, ::1, the address the request arrived on, or a `--host` name; or more than one `Host` header | `421` `{"error": "this bench answers only to its own names ..."}` |
| any `Forwarded`, `Via`, `X-Real-IP`, `X-Forwarded-*`, CDN or `Tailscale-*` header (a proxy, `tailscale serve` or Funnel) | `403` `{"error": "this bench answers direct requests only ..."}` |
| any request with an `Origin` that is not the bench's own: another site, `null`, another port, https, or a second `Origin` header. On the tailnet listener a loopback name (127.0.0.1, localhost, ::1, ::ffff:127.0.0.1) is not the bench's own either, in an `Origin` or a `Referer`: only the listener's own address and the tailnet names are (the loopback listener keeps its loopback names) | `403` `{"error": ..., "reason": "origin"}`; a POST's body is drained first and nothing is written |
| a request whose `Sec-Fetch-Site` is not same-origin, same-site or none (in practice `cross-site`), except a GET navigation of the page itself (`/`) into a window or a frame. Only where the browser sends that header: https or loopback, never plain http to the tailnet | `403` `{"reason": "fetch-site"}` |
| the evidence GET with no proof it came from the bench's own page or a local tool: Fetch Metadata of the same site, a `Referer` from the bench, or an `X-FP-Token` / `X-FP-Local` header | `403` `{"reason": "unproven-origin"}` |
| a POST, or the evidence GET, without the token | `403`, the remedy in the body ("mutating routes are disabled" when started without `--token`) |
| a `Content-Length` that is not a whole number of bytes | `400` |

**What each request check can see, and where it fires.** A browser sends Fetch Metadata
(`Sec-Fetch-Site`, `-Mode`, `-Dest`) only to a potentially trustworthy URL: https, or 127.0.0.0/8, ::1, localhost.
Over plain http to the tailnet address or a `*.ts.net` name it sends none of it. So the
`Sec-Fetch-Site` rule fires only where browsers send it (loopback; https, which the bench never speaks) and is
inert on the tailnet, where the `Origin` and proof rules carry the lock: a browser sends `Origin` on every POST
(a same-origin one too) and on a cross-origin fetch, and none on a navigation, `<img>`, `<script>`, `<link>`,
`<iframe>` or form GET. A present `Origin` must be the bench's own (http, one of its names, its own port); an
`Origin`-less POST is a non-browser client (PowerShell, a script) and goes on to the token gate. The token is
read from the `X-FP-Token` **header only** (a header forces a CORS preflight, which no File Portal server
answers; a `?token=` or a form field is never read). No answer carries `Access-Control-Allow-Origin`, so a
foreign page can fire a simple request but never read what it gets back. A blind GET can only reach a route
that reads (its answer is unreadable to the page and it changes nothing), or the one GET with a side effect,
`/api/evidence` (it spawns the OK-15 collector and caches its report): that one needs proof, and it stays a GET
because OK-15 is signed as a read route.

The `Tailscale-*` refusal covers an HTTP-mode Funnel only: a TCP-mode funnel carries no header and reaches the
bench from 127.0.0.1 like any local client. `security/lockdown_check.py` (checks D4 and T1) is what catches any Funnel.

The bench sends no `Content-Security-Policy` and no `frame-ancestors` (every other File Portal server sends one), and
every answer says `Referrer-Policy: no-referrer`, because the page's URL carries `?token=`.

Every route (Observed in the source, 2026-09-30; the bench lane's run of `test_bench_page.py`, 196 tests OK, asks each
one over a real tiny PDF, and was not re-run when this file was written): GET `/`, `/api/state`, `/api/md`, `/api/page`,
`/fp-tokens.css`, `/vendor/*.js`, `/api/asset`, `/api/ledger`, `/api/rescore`, `/api/toc`, `/api/find`, `/api/rects`,
`/api/locate`, `/api/trimbox`, `/api/textlayer`, `/api/table`, `/api/library` only read (an in-memory cache fills,
no answer changes); GET `/api/evidence` spawns a child and caches its report; the eleven POST routes (`MUTATING_POSTS`)
write, swap the served bundle, or spend the GPU; every other method answers `501`. `test_bench_page.py` holds each
rule (the peer and bind tables, every proxy marker, a wide `--also-bind` refused before any server is built, the
plain-http browser's requests, every real client's shape, and a mutant per guard).

## Quarantine (prototypes/ convention)

Disposable, zero pipeline coupling: nothing in the pipeline imports this; this imports only
`fidelity_audit` read-only for the preview. Graduation criteria (docs/19 §7): Rab uses it on
Valentine successfully — then it earns a widget surface and the audit-credit policy discussion.
OK-15 evidence is likewise held only in Bench process memory. It does not alter the source PDF,
Marker input, bundle/manifest, audit verdict, pipeline, vault, or frozen Visual Witness path.
Persisting these signals into conversion bundle evidence is a separate, unsigned graduation.
