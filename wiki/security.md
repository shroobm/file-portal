---
title: Security Posture
section: Governance
last-verified: 2026-08-23
verified-against: "1790554"
sources: [docs/06-security-model.md, docs/37-next-stage-plan.md, docs/38-file-portal-full-system-scope.md, windows-widget/src-tauri/tauri.conf.json, windows-widget/src-tauri/capabilities/default.json, windows-widget/src-tauri/src/assay.rs, windows-widget/src-tauri/src/line.rs, windows-widget/src-tauri/src/watcher.rs, windows-converter/analyst.py, windows-converter/room_chat.py, windows-converter/watch_and_convert.py, windows-converter/convert_and_ship.py, prototypes/repair-bench/bench.py, linux-converter/systemd/file-portal-converter.service, linux-converter/systemd/file-portal-vault-fixity.service, linux-receiver/systemd/file-portal-allocator.service, .gitignore, wiki/profiles/README.md, wiki/roadmap.md, OPEN-TASKS.md]
---

# Security Posture

**If you read nothing else: THE REPO IS PUBLIC on GitHub** (`curl -s https://api.github.com/repos/shroobm/file-portal` → `"private": false, "visibility": "public"`, run 2026-08-23; remote per `git remote -v`). Everything tracked here is world-readable: no personal data in tracked files, no secrets ever, and profile personal content lives only in the gitignored private layer (wiki/profiles/README.md:11-15, .gitignore:57). The trust perimeter is the Tailscale tailnet — no public listening ports anywhere (docs/06-security-model.md:15-16). The core is genuinely sound: a strict widget CSP, an 8-permission capability grant, path-validated IPC, and a tracked-file secret sweep that comes back clean. The honest gaps: two loopback HTTP servers mutate files with zero request authentication — against the repo's own written rule (docs/38:756-758) — the lane that parses untrusted PDFs has no dependency manifest, `Cargo.lock` is gitignored, all three systemd units carry zero hardening directives, and there is no SECURITY.md. None of the gaps is internet-reachable; remediation is owned by roadmap catalysts C4 (the bench auth token, wiki/roadmap.md:33) and C5 (the standards slate, :34).

## 1. Trust model: the tailnet is the perimeter

- **No public listening ports.** "no port is opened on any router or public interface. All traffic rides the Tailscale WireGuard tunnel" (docs/06-security-model.md:15-16).
- **Identity is the tailnet node**, not keys or passwords: Tailscale SSH authenticates by node identity, gated by the Tailscale account login + optional 2FA (docs/06:17-19). The residual risk docs/06 itself names: a compromised Tailscale account inherits the tailnet (docs/06:31-33).
- **Privilege ceiling on the Linux side:** the ACL restricts SSH `users` to a non-root account — a fully compromised Windows app "can only do what your unprivileged Linux user can do" (docs/06:21-23). The allocator writes only inside `~/file-portal/...` and accepts a *category*, never a destination path (docs/06:24-27).

## 2. What is sound

- **Widget CSP** — `default-src 'none'; script-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; connect-src ipc: http://ipc.localhost` (windows-widget/src-tauri/tauri.conf.json:24). No remote script, style, or connect surface.
- **Minimal capability grant** — 8 permission strings (of the whole Tauri v2 permission catalog), all `core:*` window/webview basics, scoped `"windows": ["main"]` (windows-widget/src-tauri/capabilities/default.json).
- **IPC input validation** — `source` names from the frontend are rejected on any path separator: `source.contains(['/', '\\', ':'])` at assay.rs:220, and the same guard repeated at :285 and :345 (windows-widget/src-tauri/src/assay.rs). The engineering-file opener is a closed allowlist: "the match below IS the allowlist" — named targets only, never an arbitrary path (windows-widget/src-tauri/src/line.rs:333-342).
- **No committed secrets** — probe: `git grep -IE` over all tracked files for 5 secret shapes (`AIza[0-9A-Za-z_-]{35}`, `ghp_[A-Za-z0-9]{36}`, `sk-[A-Za-z0-9]{32,}`, `tskey-…`, `BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY`) → **0 tracked files match**. Probe controlled first per contract: a planted positive file hit 3/3 patterns, a negative file hit 0. Scope: tracked files at 1790554 only — untracked and history not swept.
- **GEMINI_API_KEY never touches argv** — read from env (windows-converter/analyst.py:116), sent as an `x-goog-api-key` request header (analyst.py:132); the code's own comment records the fix: the key "is never on any argv (the curl form put it there…)" (analyst.py:112). ⚠ **Stale-fix trap:** docs/37-next-stage-plan.md:89 still lists F-13 "Gemini key in curl argv (CWE-214)" as **CONFIRMED** — the record lags the code. Trust analyst.py, not the F-13 row.

## 3. The gaps

Each one cited; none is disputed by any register.

- **Two loopback servers mutate files with zero Origin/token/CSRF check.** The repo's own rule, verbatim: "Loopback is a network boundary, not authentication; another local process may still be hostile. Any future route that mutates files requires the same path/authority scrutiny as a native command." (docs/38-file-portal-full-system-scope.md:756-758). Against that rule:
  - **prototypes/repair-bench/bench.py** — `do_POST` (:1411) parses the body with `json.loads` regardless of Content-Type and with no origin check (:1414-1415). `/api/md` (:1424) overwrites the served bundle's markdown body; `/api/open` (:1438) opens `payload["path"]` — an **arbitrary filesystem path taken from the request body**. Binds 127.0.0.1 (:1500).
  - **windows-converter/room_chat.py** — `do_POST` (:467) same shape (:468-469). `/api/load` spawns a llama-server subprocess (:317-319) and writes `chat-hold.json` (:88), which defers pipeline converts — so an unauthenticated local POST can hold the GPU lane. It sets a CSP on its *own* pages (:445-449) but validates nothing about who is POSTing. Binds 127.0.0.1 (:535).
- **windows-converter has NO dependency manifest** though it parses untrusted PDFs: `git ls-files windows-converter | grep -E 'pyproject|requirements'` → 0 of its 18 tracked files. The interpreter is an out-of-repo venv; the environment is unreconstructable from the repo. (Every Linux Python lane has a pyproject.toml.)
- **Cargo.lock gitignored, package-lock.json tracked** — `.gitignore:5` ignores `windows-widget/src-tauri/Cargo.lock`; `git ls-files windows-widget/package-lock.json` returns it tracked. The Rust build is unpinned while the JS build is pinned — backwards for the lane that ships the binary.
- **All three systemd `.service` units carry zero hardening directives** — probe: grep for 12 directives (`ProtectSystem|ProtectHome|NoNewPrivileges|PrivateTmp|ReadWritePaths|CapabilityBoundingSet|RestrictAddressFamilies|SystemCallFilter|ProtectKernel*|LockPersonality|MemoryDenyWriteExecute`) → 0 matches in file-portal-converter.service (23 lines), file-portal-vault-fixity.service (10), file-portal-allocator.service (22). The converter unit hosts the vault exporter (linux-converter/converter/main.py:304-311) — the vault's only writer; the fixity unit is report-only.
- **No SECURITY.md** — `ls SECURITY.md` fails; `git ls-files | grep -i security.md` is empty. docs/06 is a design doc, not a disclosure policy — and the repo is public.
- **No per-file SHA-256 transport inventory before vault commit** — docs/38's own words: the streaming tar/SSH hop has "no arrival inventory or package digest … currently enforced" (docs/38:314); "this remains an explicit gap" (docs/38:783; risk row :892).

## 4. Severity honesty

The loopback-CSRF gap requires **the server running AND a hostile local page or process**. Both servers bind 127.0.0.1 only (bench.py:1500, room_chat.py:535) and nothing is router-forwarded (docs/06:15-16) — this is not internet-reachable. The realistic vector is a hostile web page in the operator's browser firing a cross-site "simple request" at the known local port (the handlers parse any body as JSON, bench.py:1414-1415), or any other process on the machine. The bench is a prototype the operator starts deliberately; room_chat runs while the Room assistant is up. Real gap, local blast radius.

## 5. The untrusted-input boundary

PDFs are the system's attacker-controllable input, and they are parsed **in-process, unsandboxed, with the operator's full user rights**:

- `import fitz`/pymupdf in 8 tracked .py files (probe: `git grep -lE '^import fitz|import pymupdf' -- '*.py'` → 8 — convert_and_ship.py, fidelity_audit.py, figure_coverage.py among them; unfiltered the probe also hits 5 docs/prose files) plus deferred imports in bench.py (:417, :869); Marker runs as a spawned subprocess of the same user.
- What limits exist are **wall-clock only**: kill at `max(3600, pages * 20)` s (windows-converter/convert_and_ship.py:690), frozen-stall kill at 900 s (:95, :722), outer 6 h cap (windows-converter/watch_and_convert.py:166).
- What does not: no memory cap, no privilege drop, no filesystem jail. The widget's Job Object is lifetime control — its only limit flag is `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` (windows-widget/src-tauri/src/watcher.rs:27, :40) — not a sandbox. A pymupdf parser exploit executes as the operator (unverified that one exists; the exposure shape is what is being recorded).

## 6. Where this is owned

Roadmap **catalyst C5** owns the remediation slate: SECURITY.md + disclosure, Cargo.lock tracked + dependency audit in CI, license inventory, systemd hardening (wiki/roadmap.md:34; gap rows :61-63). Note the register blind spot: OPEN-TASKS.md has **zero** rows matching `security|CVE|CSRF` (probe: `grep -ciE 'security|CVE|CSRF' OPEN-TASKS.md` → 0) — until C5 lands, this page and roadmap C5 are the only surfaces that gather these gaps in one place (docs/38 names the loopback rule and the transport gap individually, but no register row tracks them).

## Open items

- **wiki/roadmap.md:34 — catalyst C5**: the whole standards-and-policy slate above.
- **docs/37:89 — F-13 record correction**: still reads CONFIRMED for a fixed defect (analyst.py:112-132); a record repair, docs/45-Family-1 shape.
- **docs/38:756-758 vs bench.py:1424/:1438 and room_chat.py:467**: the loopback mutating routes vs the repo's own rule — needs a signed decision (token, Origin check, or a signed acceptance).
- **docs/38:783, :892 — transport arrival inventory/digest handshake**: named an explicit gap by the scope doc itself.
- **OPEN-TASKS.md**: no security section exists to point at (0 keyword hits) — itself an open item for the register.
