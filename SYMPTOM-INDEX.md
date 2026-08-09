# SYMPTOM INDEX

**Retrieve by what the system is doing, not by which session produced it.** You are here because
something looks wrong and you don't know why. Grep the Symptom column.

Read this file at every session open (it is part of MUSTER). **A defect rediscovered is a MUSTER
failure, not bad luck.** Per `docs/21-session-closeout-contract.md` §5: keyed on symptom, terse,
append-only in spirit, session number always present but never the retrieval key. Fixed rows stay
— the recurrence is what you're guarding against.

**Seeding note (2026-08-09, receiver lane):** rows below were transcribed from the `CLAUDE_README.md`
Change Ledger, `docs/19`'s laws, and `coordination/messages/`. They are therefore **Historical** —
recorded by the cited session, faithful to its own account, not re-observed by the seeding session
— *except* rows explicitly tagged `Observed` with a date. Guards named in the "Guard lives at"
column were confirmed present in the working tree at seeding time (`Observed 2026-08-09`).

| ID | Symptom — what you notice | Root cause | Session | Status | Guard lives at |
|---|---|---|---|---|---|
| SYM-001 | Tests and harness all green, but the shipped behaviour is wrong | The fake/stub shared the same assumption as the code under test. Two checks that share an assumption are one check | S60 | `Historical` — class is permanent, no mechanical guard possible | `docs/21` §1 (`Verified` requires a differently-shaped second method) |
| SYM-002 | Page numbers above the first slice point at pages that don't exist (assets numbered ~2553 on a 1,356-pp book). Nothing is lost — navigation simply lies | Marker already numbers slice assets by ABSOLUTE page; the added offset double-counted | S60 (fix `6d0a560`) | `fixed` | `windows-converter/convert_and_ship.py` (absolute-page asset renumbering) |
| SYM-003 | Audit verdict `fail` with degeneration on table-heavy books; excerpts are repeated table rows, no seam nearby | "Table-loop disease" — the model loops on tabular structure. Seen on Beer, Valentine, Damodaran, Cybernetics | S60, S61, earlier | **OPEN** — `Observed` repeatedly; the Repair Bench is the response, not a fix | `prototypes/repair-bench/` (human-in-the-loop repair) |
| SYM-004 | An `ssh`/`scp` from a windowless or background process hangs forever; zombie ssh/scp pairs accumulate in Task Manager | System32 OpenSSH keeps its OWN `known_hosts` (git ships a separate ssh) → invisible host-key prompt with nowhere to answer. Nine zombie pairs before diagnosis | S56 | `fixed` — hang class extinct | Standing options `-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10` (`docs/19` law 6) |
| SYM-005 | `publickey` denied, and **no passphrase prompt** appears | Public key silently truncated in transit by clipboard paste (73 of 106 bytes); the line-start check still accepted it | S47 | `fixed` | Law: key material travels by file (`scp`), never clipboard (`docs/19` law 5). Diagnose by byte length + `ssh-keygen -lf` match |
| SYM-006 | The GPU stays held / VRAM unreleased after a kill; a process you killed appears gone but work continues | `proc.kill()` on a single pid leaves the venv console-script launcher's real python alive | S48, S52 | `fixed` | `_kill_tree` helper / `taskkill /pid N /t /f` (`docs/19` law 7) |
| SYM-007 | A write "succeeded" but the system behaves as though it never happened; verifying from the same place shows it present | MSIX-packaged desktop-app session's AppData/registry writes are silently virtualized | S29, S45, S48 (three separate disasters) | `fixed` by rule, not by code | `docs/19` law 3: never verify a write from the surface that made it; adoption is Rab's hand; system config only from elevated unpackaged shells or over SSH |
| SYM-008 | A venv launcher dies immediately with exit `0x67` | The base CPython under uv-managed `%APPDATA%\uv\python\…` is missing again | S48 | `Historical` | Reinstall the uv-managed base; see `docs/19` §1 |
| SYM-009 | A human's repair work vanishes after a re-run | `_enforce_hold` rmtree'd a held bundle that carried repairs, to park the incoming one | S65 | `fixed` | `windows-converter/convert_and_ship.py` — repairs-bearing occupant keeps its slot; incoming parks beside, timestamped |
| SYM-010 | A test harness appears to drive the real running app; live guards refuse test payloads | Hardcoded port (7078) reached the LIVE bench via `SO_REUSEADDR` | S65 | `fixed` | `prototypes/repair-bench/acceptance.py` — OS-assigned ports |
| SYM-011 | The converter never fires on a file the allocator just moved in | inotify reports the allocator's cross-watch hop as an **unpaired `IN_MOVED_TO`** → arrives as a plain watchdog `created` event, never `moved`/`closed` | recorded 2026-07-10 (`c718ed2`) | `fixed` | `linux-converter/converter/main.py:11-16` — load-bearing comment + `on_created` with size-stability wait |
| SYM-012 | OCR output still contains the source's bad prior OCR text | pymupdf4llm `force_ocr=True` means `FORCE_KEEP_OLD` — the opposite of what the name implies | recorded 2026-07-10 | `fixed` | `linux-converter/converter/engines.py` — Scan lane uses `OCRMode.FORCE_DROP_OLD` |
| SYM-013 | `ENOENT` naming `.part-<underscored_stem>/assets/…` on a file whose name contains spaces | Assembly dir was keyed on the stem, which the engine's sanitizer rewrote | L13 (2026-07-12) | `fixed` | `linux-converter` — assembly dir keyed on source SHA-256 (`.part-<sha256[:16]>`), sanitizer-proof by construction |
| SYM-014 | A bundle's interior filenames exceed Windows MAX_PATH on the desktop side | Unclamped published bundle names | L15 (2026-07-12) | `fixed` | `bundle.clamp_name` — 200 utf-8 bytes, codepoint-safe |
| SYM-015 | `receipts.jsonl` records the same `supersede-held` for one bundle on every boot | A retained fail-verdict bundle sits in `library/staging/`; the converter's startup sweep re-processes it each time. Guard is fail-closed and correct — the cost is repetition, not risk | `Observed 2026-08-09` (3rd firing: 08-03, 08-06, 08-09) — bundle `claude-code-up-and-running`, sha `5998f114ae93f65c` | **OPEN** — awaiting Rab's decision on the bundle's fate (`docs/19` open items) | `linux-converter/converter/exporter.py` supersede branch (working as designed) |
| SYM-016 | A Change Ledger row cites a SHA that isn't in the history | The closing commit was `--amend`ed after the row was written, orphaning the SHA | recorded 2026-07-10 | `fixed` by rule | `CLAUDE_README.md` §4: ledger row is a separate follow-up commit, NEVER amend. Detect with `git merge-base --is-ancestor <SHA> HEAD` |
| SYM-017 | `ps -W` in git-bash reports a PID that doesn't match reality | The PID column lies under git-bash | S65 | `Historical` | Cross-check with Task Manager / `tasklist` |

## Adding a row

From your closeout's §15. Write the Symptom column **for someone who has the symptom and not the
cause** — what they'd see on screen or in a log, in their words, not the mechanism's name. If you
cannot describe it without naming the cause, you don't yet understand the failure well enough to
index it.
