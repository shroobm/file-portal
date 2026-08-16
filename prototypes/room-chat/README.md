# `room-chat` — the Room's assistant (quarantined prototype)

**S79, 2026-08-15.** Rab's spec: *a button loads the model, a window opens greeting you with a
model-loaded confirmation, a button unloads it, and a convert cannot happen while the chat is
loaded, and vice versa.*

Assessed first in **docs/33** (a Circle). Two semantic findings were signed by Rab before any of
this was written; the five mechanical ones are what this directory is.

Quarantine convention: stdlib only, nothing imports it, no pipeline coupling except the two
marker files in §3. Run it by hand, or via `.claude/launch.json`'s `room-chat` entry.

```bash
"C:\Users\Bndit\ml\marker-env\Scripts\python.exe" prototypes/room-chat/chat.py --port 7100
"C:\Users\Bndit\ml\marker-env\Scripts\python.exe" prototypes/room-chat/acceptance.py
```

## 1. What it is, and what it refuses to be

**A citation engine, not an oracle.** docs/33 §2.2: verify-before-instruct forbids instructing
from recall, and a model answering from baked context *is* recall — that rule exists because a
session once told Rab the ⚡ tile was a switch. So every answer either carries a citation that
**resolves to a document actually in the corpus**, or the answer is thrown away and replaced by
a refusal.

That check is mechanical (`_enforce_citation`), never a request in the prompt. Asking a model to
cite and trusting that it did is a proxy for compliance, and docs/32 is a document about what
proxies do.

`Observed 2026-08-15`, live, on the real manual:

| asked | verdict |
|---|---|
| "what does the watcher dot mean when it turns terracotta" | `cited` — correct, resolving to `docs/20 §2` |
| "what is the analyst's measured tokens per second" | `honest-refusal` — and the number *exists* (76 tok/s, measured this session); it simply is not in the manual |

**It may not speak for the pipeline.** docs/33 §2.1, signed: live values render through the
existing projection path verbatim; the model may point at a surface, never restate it. `/api/state`
reads the pipeline from disk and the page renders it; the model never sees those numbers and the
system prompt forbids it stating any.

## 2. The three lifecycle fixes borrowed from `bench.rs` — and corrected

`bench.rs` is the right foundation and carries four paid-for lessons (detached spawn, last-words
stderr, the S37 kill-on-close Job Object, main-thread window). A copy-paste would have shipped
three defects, each found by the Circle before a line was written:

| # | `bench.rs` | here, and why |
|---|---|---|
| 1 | readiness wait **6 s** (`30 × 200 ms`) | **90 s + 12 s/GB.** An 8B model takes ~20 s cold (measured 19.54 s; this build came up in **33.2 s**). 6 s would report a healthy server dead on every cold start. And *alive-but-silent* (LOADING) is told apart from *exited* (died, last words on disk) — bench.rs cannot distinguish them |
| 2 | ports **7077..7096** | **7110..7119** for the model, **7100** for the UI. Taking a bench port would make the next Repair Bench land somewhere its window does not expect |
| 3 | path derived from the repo layout | llama-server lives **outside** the repo, so a path is required. `--llama` / `FP_LLAMA_SERVER`; at graduation this becomes `llama_server_exe` in `config.toml`, where **empty key = feature hidden** (docs/20 §11) — the button simply will not exist on a machine that has not set it up, the ThinkPad included |

## 3. The mutex — built, because there wasn't one

docs/33 §2.3: **`.gpu-lock` is not a lock.** `watch_and_convert.py:77` writes it, `:86` deletes
it, and nothing reads it as a gate. A file named lock that locks nothing.

| file | written by | read by |
|---|---|---|
| `chat-hold.json` | **this prototype** (sole writer — the `analyst-mode.txt` pattern) | the watcher, once the signed gate lands |
| `.gpu-lock` | the converter | this prototype, read-only — the projection law working normally |

Load is two-phase: **write the hold, then read the lock**; if the lock is there, drop the hold and
refuse. Recording precedes action (docs/28's chokepoint), and the ordering makes the chat yield to
the pipeline — a convert is expensive and interruption-hostile, a chat session is neither. A lost
race means both sides yield, which is the safe direction.

Unload kills the server and removes the hold. **Release is an act, not a timer** — the same rule
as the analyst's residency fix this session, and the shape of Rab's permanence rule.

## 4. What it cannot do — read before trusting it

1. **The guard resolves the document, not the sentence.** A citation to `docs/20 §3` passes if
   `docs/20` is in the corpus, even when the claim really lives in §8. Same family as the glass
   detector's "referenced ≠ reaches a human." It stops fabricated *sources*, not misplaced
   *sections*.
2. **The corpus is one file.** `docs/20`, the operator manual, because it is written for exactly
   this reader and fits an 8k context beside a question and an answer. It cannot answer anything
   the manual does not contain — which is why it refuses often, and the refusals are the feature.
   Whether retrieval over the wider corpus is needed is docs/33 §3.3 and waits on Rab's ten real
   questions; choosing the context before seeing the workload would be picking a proxy and
   calling it the property.
3. **No model quality claim is made here.** Two questions is an anecdote, not a measurement.
4. **The Job Object is not inherited yet.** `bench.rs` adopts children so they die with the
   widget by any exit; this prototype is a plain `Popen`, so a hard kill of `chat.py` orphans
   `llama-server`. That is a graduation requirement, not an optional polish — S37 was paid for.

## 5. Graduation requirements (what moving into the widget needs)

- `llama_server_exe` config key, empty-hides-feature.
- The spawn adopted into the watcher's Job Object (§4.4).
- The **signed** watcher gate: `watch_and_convert.py` reads `chat-hold.json` before converting,
  defers with a log line, and picks the PDF up on the next 5 s poll. Its tripwire: drop a PDF
  while the hold is set, prove it defers **and** prove it converts the moment the hold clears.
- Every field the panel projects dispositioned or rendered **in the same commit** (docs/29 §5.4).
