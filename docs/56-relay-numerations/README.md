# docs/56 — The relay numerations (the NR-set)

⟨claimed: Fable · S120 · 2026-09-09⟩ · instrument `coordination/relay_numerations.py` · born of Rab's order, 2026-09-09T19:19Z: *"find real another set of numerations that is strictly between your communication and processes utilizing coordination relay"*

## §0 What this is

docs/51 numbers the pipeline. This numbers the **bus**: the two lanes' communication and the processes that use `coordination/relay.md` (the append-only log), `coordination/ack-fable.json` and `coordination/ack-codex.json` (the single-writer sidecars), `gate.py`, the 24/7 watcher and the close. Every row is measured **only from those files** — never from prose, never from a closeout's claim — and every row names its numerator, denominator and conditions (docs/34). A row the files cannot support prints `UNREAD` with the reason, never `0` (SYM-031).

```bash
python coordination/relay_numerations.py            # the table (either lane's interpreter; stdlib; read-only)
python coordination/relay_numerations.py --json     # machine-readable, for a register or a diff
```

The instrument is a meter, not a gate: it always exits 0. Gates read it.

## §1 The rows

| NR | name | numerator / denominator / conditions | what a move means |
|---|---|---|---|
| 01 | relay entries | dated `## 20…` headers (the card's count) = canonical `## <UTC> · ⟨from⟩ → ⟨to⟩ · ⟨msg⟩` + legacy; per lane | volume, not virtue |
| 02 | gated appends, per lane | headers whose id has a `sent` record in the lane's own sidecar / the lane's canonical headers | below 100 % = entries the peer's `inbox` and `watch` could not see (B4) |
| 03 | no-ack notices, per lane | `sent` rows with `requires_ack` false / all `sent` rows | notices are invisible to `inbox` by design; a rising share means more traffic the handler never confirms |
| 04 | ack latency, per direction | `confirmed_utc − utc` for every ack-required message the lane sent that the peer confirmed; minute-granular; median · p90 · max (with the id) · n | **the latency Rab asked about.** The median is the tool; the tail is sessions that were not open |
| 05 | ack debt, per direction | ack-required messages sent with no confirmation in the peer's sidecar; count and the oldest's age in hours | `inbox` from the sender's side; a debt older than a session is a decision, not a delay |
| 06 | envelope conformance, per lane | entries carrying all of `**RECAP` / `**FOR RAB` / `**SUGGESTED PROMPT` / the lane's canonical entries; also the last 10 | the form Rab signed (CR-CDX-0002, 2026-08-24) — after S120 the gate refuses a body without it, so this can only rise from the cutoff |
| 07 | entry length, per lane | whitespace words per body; median · p90 · last-10 median | **the succinctness meter.** No threshold: a cap is a lever and Rab's |
| 08 | restatement length, per lane | words per confirmation restatement; median · min · n | law 3 refuses under ten characters; the rest is the lane's habit |
| 09 | beat age, per lane | `now − beat.utc`; stale past 45 min (the board's own rule) | cadence is UNREAD: the sidecar keeps only the latest beat |
| 10 | escalations, per lane | rows in `escalations[]`, open ones, disagreements | an open one is FULL STOP for both lanes |
| 11 | state, per lane | the sidecar's own `state · current_ticket · occupant · sent · confirmed` | rendered, not judged |
| 12 | peer bytes unstaged in the shared checkout | `git status` paths naming the peer + relay.md's uncommitted `+## ` headers per writer | what a close must state and never absorb (MSG-CDX-0048); `gate.py stage` is the remedy (B7) |
| 13 | watcher signals logged | signal lines in `coordination/private/relay-watch.log` | UNREAD until the tracked watcher writes the log (B8) |
| 14 | handler turnaround | `confirmed_utc − signal utc` per handled signal | needs 13 |
| 15 | line-ending purity of relay.md | bare-LF lines / all lines | every bare-LF line is a future +N/−N diff under `core.autocrlf=true` (S116 F8); the gate appends the body's bytes verbatim (B6) |

## §2 The baseline — 2026-09-09T19:26Z, before any fix (S120 §5)

| NR | Fable | Codex |
|---|---|---|
| 01 | 78 canonical | 48 canonical (145 dated headers = 126 canonical + 19 legacy) |
| 02 | 71/78 = 91.0 % (ungated MSG-FAB-0030, 0044–0049) | 47/48 = 97.9 % (MSG-CDX-0027) |
| 03 | 23/70 = 32.9 % | 11/47 = 23.4 % |
| 04 | sent by Fable: median 7 min · p90 477 · max 8,377 (MSG-FAB-0068) · n 47 | sent by Codex: median 6 min · p90 74 · max 8,456 (MSG-CDX-0044) · n 23 |
| 05 | owed by Codex: 0 | owed by Fable: 13, oldest MSG-CDX-0029 at 232.6 h |
| 06 | 30/78 = 38.5 %, last 10: 3/10 | 15/48 = 31.2 %, last 10: 1/10 |
| 07 | median 536 · p90 949 · last 10: 456 | median 293 · p90 530 · last 10: 200 |
| 08 | median 123 · min 31 · n 24 | median 34 · min 16 · n 47 |
| 09 | 28 min | 27 min |
| 10 | 1 total · 0 open | 0 |
| 12 | 2 files + relay.md: Codex 1 header uncommitted | |
| 13 / 14 | UNREAD | |
| 15 | CRLF 5,252 · bare-LF 1,117 · 17.5 % | |

**Reading.** When both lanes are awake an ACK takes 6–7 minutes either way; the p90 and the max are made of sessions that were not open, so "solving latency" is a question of what wakes a lane (the watcher, the handler), not of the tool. Succinctness is Fable's problem before Codex's: 536 words against 293, restatements of 123 against 34.

## §2b After — 2026-09-09T21:52Z, the fixes merged (S120 §5b)

| NR | Fable | Codex | moved by |
|---|---|---|---|
| 04 | median 7 · p90 477 · max 8,377 · n 48 | median 6 · p90 74 · max 8,456 · n 23 | one new sample: MSG-FAB-0079 posted 19:37Z, confirmed 19:43Z = **6 min** |
| 06 | 31/79 = 39.2 %, last 10: 4/10 | 16/49 = 32.7 %, last 10: 2/10 | `post` now refuses a body without the envelope (`d5ee349`), so this rises from the cutoff `2026-09-09T20:00Z` onward and never falls |
| 07 | median 521 · p90 949 · last 10: 464 | median 279 · p90 530 · last 10: 200 | MSG-FAB-0079 ~430 words, MSG-FAB-0080 335 (the meter printed it at post time), MSG-CDX-0049 169 |
| 09 | 34 min · gate `f34009c8` | 17 min · gate `5b8c1475` | the board's rev-flag: Codex's 21:36 beat ran the merged gate.py |
| 12 | `ack-codex.json` + relay.md: Codex 1 | | `gate.py stage --as Fable` staged only Fable's bytes (`45cf119`); the peer's stay for its own commit |
| 13 | 3 signals (BEAT 1, INBOX 1, NEW-ENTRY 1) · 1 arm · 2 alive beats · last alive 21:50:24Z | | the tracked watcher's log (`d802ea1`); the INBOX line is the B11 phantom, fixed `354bc32` |
| 14 | UNREAD — no ack-owed signal has been confirmed since the log began | | needs the next ack-required Codex entry |
| 15 | CRLF 5,252 · bare-LF 1,153 · 18.0 % | | 0079/0049 appended before B6 (`f208f20`); every append from here lands in the log's dominant EOL, so this falls only as the log grows |

What changed structurally between the two tables: `post` refuses a missing envelope slot and prints the word count; `watch`/`inbox` see ungated appends; `status` renders the derived settle and `beat` settles under the Guard B clause; `stage --as <lane>` gives each writer its own index entry (line-ending-blind, B12); appends land in the log's own EOL; the watcher is tracked, UTC-stamped, logged and selftested (25 cases); `coordination/selftest.sh` is green for the right reasons (20 cases); `close.sh` attributes the peer's dirty bytes instead of going red on them (muster suite 79).

## §3 What it cannot see

- **Cadence.** Only the latest beat survives in a sidecar; NR-09 is an age, not a rhythm.
- **Prose appends without a header.** An entry that is not a `## ` header is not an entry to any of this.
- **Minutes.** Stamps are minute-granular; a within-minute exchange reads 0.
- **Who read what.** A confirmation proves a restatement was written; nothing here proves the entry was understood. Law 4 (the re-digest) proves the bytes, not the meaning.
- **The watcher and the handler** until B8 lands the log (NR-13/14).

## §4 Provenance

Single-lane (Fable), measured on the live files at the stated minute; Codex was asked to re-run it (MSG-FAB-0079) and any deviation it reports is the record's, not this file's. Re-measure, never quote: the numbers above are `Historical` the moment the next entry lands.
