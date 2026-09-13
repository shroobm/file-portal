# The journal — the autonomy experiment (from 2026-09-13 17:24Z, Rab's word e34253e4)

*This is the half Rab reads. One entry per improvement, dated (UTC), written so it can be felt within a minute of looking: what you will notice · where to look · before → after with its denominator · what it cost · what would undo it. The session records (`sessions/S<N>-*.md`) and the private receipts are the audit half and keep running underneath. Appends only; nothing here is rewritten.*

*Rab's words that opened it: "I want to see and feel the improvements. I want you to journal as well." (1f355f41) · "Record everything you must and more if you may." (e34253e4)*

---

## 2026-09-13 17:3xZ — the journal opens (S146 E1)

**What you will notice:** this file, and one Desk line per entry pointing at it. **Where to look:** here; the Desk (orange board). **Cost:** minutes. **Undo:** none needed.

## 2026-09-13 — the card tells you what the lever means (S145 E1, landed 15:28Z)

**What you will notice:** at every session open the card now prints a line of its own: `SHIPS ON VERDICT audit-mode=report — every verdict SHIPS (fail included) and the exporter's first ingest has no guard` — and it goes quiet the day the lever reads `enforce`. **Where to look:** §2 of any record from S145 on (line ~24 of the S146 card), or run `bash .claude/skills/muster/open.sh`. **Before → after:** the card had printed `levers audit=report` at three opens (S142, S143, S144) and the reader read past it every time; a failing book (Ashby) reached your vault under it. Now the consequence is on the card in words, with a tripwire that fires on `report` and stays quiet on `enforce` (selftest 103/103). **Cost:** one episode, no pipeline code. **Undo:** delete the four-line block after the `levers` row in `open.sh`; the standing order in the muster skill would stay.

## 2026-09-13 — twenty pages you would look at first (S145 E5–E7, landed 16:16Z)

**What you will notice:** a held scan no longer arrives as "FAIL, 465 pages". For Valentine there is an evidence CARD (one row per page: the four instruments' readings, their flags, an attention rule), twenty OVERLAYS (Marker's blocks boxed by type, the words the second witness disagrees on boxed), a contact sheet, and surya's own confidence per flagged page. **Where to look (private):** `measurement/evidence/valentine-evidence-card.md`, `measurement/evidence/valentine-overlays/contact-sheet.png`. **Before → after:** 465 pages → 40 worth an eye first, the 32 typed exhibits on top; on the dot-matrix checklists the engine is UNSURE (median confidence 0.66, 87 of 104 lines under 0.8) while on the flowcharts, the index and the tables it is confident (0.96–0.997) and the losses are layout decisions — two different repairs, told apart before the bench. **Cost:** three episodes, CPU only. **Undo:** nothing to undo; they are evidence files.

## 2026-09-13 — the converter's death was not the converter (S145 E3, E4, E8, landed 17:25Z)

**What you will notice:** no slice or budget constant will be changed on this book's account, and the next time a Marker slice dies at the card's ceiling the record will be able to say WHOSE memory the rest was (that is S146 E3). **Where to look:** `sessions/S145-desktop-2026-09-13.md` §8 findings 5, 9 and 11, and the Episode 8 section. **Before → after:** the morning's run of Valentine's first 200 pages died at its 4,000 s budget with the card at 9,515 of 10,240 MiB and 100 % busy; the same slice inside the same converter at 16:45Z took 1,698.6 s at 5.6 GB (the direct sidecar run: 1,701 s) — and the whole book converted in 4,078.5 s (8.8 s/page) and anchored with its blocks, nothing shipped. Three probes re-ran the mechanism; three times it reproduced itself. **Cost:** ~2.5 hours of card time, measurement only. **Undo:** none.

## 2026-09-13 — the registers grew honestly (S145 E8, landed 17:04Z)

**What you will notice:** the close card's DEBT line went `open SYM 43 -> 49`: five rows whose status word had been written unbackticked now count, plus one new row — SYM-132, the converter's blind memory signature. Two rows are mine: ERR-104 (I trusted a tracker's "no stream or game process" that had no row for the pass itself) and its correction C-025; IB-018 files the tracker's miss. **Where to look:** `SYMPTOM-INDEX.md` (SYM-132), `ERROR-BIN.md` (ERR-2026-09-13-104). **Cost:** minutes. **Undo:** rows are never erased; a wrong row gets a correction row.

## 2026-09-13 17:26Z — S146 opens on your experiment

**What you will notice:** the echo on the Desk (three readings, the broad one taken), and this plan: E1 this journal + my vision written beside yours; E2 the lever's provenance event and the flip to `enforce` through it (the first write to that file in the library's history that names its writer — you will see it as an event row); E3 the converter's per-process memory signature; E4–E6 the three guards with numbers behind them (a ship never nests onto a held name; the analyst's chunks bounded; the exporter's first ingest reads the verdict); E7 the vault note on the numbers; E8 the re-conversions one at a time as dry-runs; E9 the live watcher onto current code. **Where to look:** `sessions/S146-desktop-2026-09-13.md` §9. The lever still reads `report` at this entry.
