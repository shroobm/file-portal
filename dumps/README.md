# `dumps/` — heavy things that must survive, and the ledger that finds them

**Rab, 2026-08-26:** *"All questions are compacted into a dump file with a ledger. This will just
sit inside my computer and literally pick up weight, but i'll do it for yall. We should actually
have many clean dump files for things, especially for coordination between yall."*

He is buying disk so that evidence stops evaporating. This file says what that buys and what the
rules are, so the weight stays useful instead of becoming a swamp.

---

## The split, and why it is exactly this split

| what | where | tracked? |
|---|---|---|
| the **record** that a dump exists — id, date, author, subject, sha256, path | `LEDGER.md` | **YES** |
| the **bytes** | `qa/` `coordination/` `evidence/` `transcripts/` | **never** |

`.gitignore` enforces it: `dumps/*` with three negations for `README.md`, `LEDGER.md`, `dump.sh`.

**Why the ledger is tracked and the bytes are not — this is the whole design:**

- **Tracked bytes break the close.** `close.sh` prints `DIFF … 0 uncommitted`. A live dump folder
  would leave the tree permanently dirty, so every close would either commit work-in-progress or
  report red. Ignoring the bytes keeps the close honest.
- **Tracked bytes bloat forever.** Rab said this sits on *his* machine. It should not also sit in
  everyone's clone, permanently, in git history where it can never be removed.
- **But an untracked-only dump is unrecoverable.** Delete it and there is no evidence it ever
  existed. That is why the LEDGER is tracked: **git history preserves the RECORD of every dump even
  after the bytes are gone.** You can always prove what was dumped, when, by whom, and what its
  digest was — you just may not still have it.

This is `coordination/private/`'s pattern, one level up: *the bus carries the pointer and the
digest; the bytes never leave the machine.*

---

## Laws — each one paid for

1. **APPEND, NEVER ERASE.** `BUS-STANDARD.md:22`: *"the worst two writers can do to each other on
   an append-only log is misorder — never destroy."* A consumed Q&A entry is marked `ANSWERED`.
   **It is never deleted.** An absence is not a receipt; a state change is.
2. **SINGLE WRITER PER FILE.** Two agents never write one file. `qa/<topic>.questions.md` has one
   author; `qa/<topic>.answers.md` has the other. This kills the lost-update race outright rather
   than hoping two writers interleave politely.
3. **ATOMIC WRITES.** Write `.part-<name>`, then rename. The renamer is the only moment a reader can
   see the file change, so no reader ever gets a torn read. This codebase already does it in three
   places (`transfer.rs:109-111`, the watcher's dotfile skip, the analyst journal).
4. **EVERY ENTRY CARRIES ITS IDENTITY.** id, UTC timestamp, author lane, subject. Without it, round
   N's answer can be read as round N+1's — the failure the relay's message-ids exist to prevent.
5. **CRLF IS A HAZARD HERE, NOT A DETAIL.** SYM-029 is open. Two vendors write this folder: Claude
   tends to LF, Codex on PowerShell tends to CRLF. Anchored greps fail *silently* across the
   mismatch. Normalise on write; `grep -U` when it matters.
6. **AN EMPTY BOX IS NOT A READING.** Between a delete and a write, a box is empty — which looks
   identical to "nothing pending." Never infer "no questions" from emptiness; read the ledger.
7. **THE LEDGER IS WRITTEN BY `dump.sh`, NOT BY HAND.** A hand-typed id or digest is a future
   SYM-039. The script assigns the id, computes the sha256, and appends the row in one act.

---

## The folders

| folder | holds |
|---|---|
| `qa/` | the Q&A boxes between the two models. Single-writer per file, append-only, `ANSWERED` not deleted. |
| `coordination/` | compacted cross-model dumps — anything too heavy for `relay.md`, which stays a log and not a warehouse. |
| `evidence/` | **probe output that would otherwise vanish.** The founding case: `analyst.py:393` runs `shutil.rmtree(work_dir)` when a book completes, so the chunk journal that produced SYM-056 was deleted minutes after it was read. That evidence had nowhere to live. Now it does. |
| `transcripts/` | session output pasted in by Rab, other-model boots, anything currently living only in a chat window. |

---

## Use

```bash
bash dumps/dump.sh <category> "<subject>" <file>     # file into a dump + ledger row
some_probe | bash dumps/dump.sh evidence "<subject>" -    # or straight from stdin
```

It prints a **pointer + sha256** line built for pasting into `relay.md` — which is how the other
lane learns a dump exists without the bytes ever crossing the bus.

```bash
tail -20 dumps/LEDGER.md          # what exists
grep -i "<term>" dumps/LEDGER.md  # find it
```

---

## What this does NOT solve

- **It does not bound growth.** Rab accepted the weight explicitly. Nothing here prunes, and nothing
  should prune without his word — a dump deleted by a script is evidence destroyed by a script.
- **It does not make a dump true.** A dump is bytes at a timestamp with a digest. It carries no
  verdict, and reading one is `Historical`, never `Observed`.
- **It does not replace the relay.** Coordination *decisions* stay on the append-only bus with
  digests and restatements. This holds the weight the bus should not carry.

---

## S141 — the ledger extended, not forked (2026-09-12, provenance/extend-dump-ledger-not-invent-manifest)

The audit layer's receipts (`file-portal-private/agent-scripts/journal/`) needed a manifest — who wrote each file, from
what bytes, with what digest. The study that asked for one (`measurement/STUDY-2026-09-12-astra-mandate.md`) first
proposed a new family; its second reading found THIS ledger already doing it since D0001. So `dump.sh` grew instead:

- **`--ref`** records a file IN PLACE — no copy; the md row points at it (the receipts are tracked in the private repo
  already, copying them here would put private bytes in the public tree — POLICY §1).
- **`LEDGER.jsonl`, the twin** — one JSON object per md row, written by the same `dump.sh` act: the seven columns plus
  `path`, `producer {path, blob}` (`git hash-object` of the script that wrote the file — the bytes that RAN),
  `sources [{path, bytes, sha256}]`, `coverage`, and `row_sha256` over the row's canonical JSON (sorted keys, no
  whitespace, UTF-8 — RFC 8785's shape) without itself. **The md row's SEVEN columns never change shape**: a reader of
  D0001 reads D0099 the same way; the twin is where the columns grow.
- **`--ledger <dir>`** writes another ledger pair: the private receipts are rowed into
  `agent-scripts/journal/LEDGER.md` + `.jsonl` at every close, by the chain, with `--producer` = the writer.
- **`ledger_check.py [<dir>]`** verifies a ledger: each twin row's `row_sha256` recomputes; md and twin agree on
  id/bytes/sha; a `--ref` file's bytes reproduce; a copy whose bytes were deleted reads `bytes gone — the ledger
  survives, by design`; a pre-S141 md row without a twin is said, not red. Exit 0 · 1 a disagreement · 2 no LEDGER.md.
  Tripwire: `ledger_check_selftest.py` (11 cases).
- **Trust boundary, stated:** the files and the ledger live on one disk under one user; the commit of the ledger is the
  tamper-evidence line. A sha proves the bytes did not drift after hashing; it does not prove the source told the truth.
  This is in-toto/SLSA-SHAPED (producer, materials, digests), not conformant, unsigned.
- One coreutils trap, paid on the first `--ref` run: `sha256sum` prefixes its digest with a backslash when the path
  carries one (a Windows path); the script strips it.
