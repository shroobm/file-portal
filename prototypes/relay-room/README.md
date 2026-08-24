# `relay-room` — the operator's quickstart

**The interpreter is `C:\Users\Bndit\ml\marker-env\Scripts\python.exe`. A bare `python` on this
machine is the Windows Store stub and exits 49.** Every command below spells the interpreter out
for that reason.

---

## What this is

A **prototype** of the thing Rab asked for on 2026-08-24:

> "both you and codex open a gate relay agent … develop a really simple ui that each of you can
> write into a markdown file, the markdown file is treated as a chat, I can type into a separate
> bar, that goes into transmission towards the markdown file, an agent that catches it, gives it
> to the relay agent, the relay agent gives it to you guys, and then you guys just type in the
> markdown file replying to me. Quarantine this artifact. Also make it work Live. With loading
> and conditions that help distill the agents actions and the models actions."

One append-only markdown file — `state/room.md` — is the chat. Three lanes write into it. A browser
page renders it live and gives Rab a bar to type into. Between his bar and the models sits a
**mechanical agent layer** that is deliberately kept visually and structurally separate from the
**model layer**, because the interesting half of this build is not the chat: it is that a reader
can tell, at a glance, **which layer a claim came from** and **whether anyone actually measured it**.

The frozen interface is `CONTRACT.md`. The design record and the honest defect register are
`DESIGN.md`. This file is only how you start it and what to distrust.

---

## QUARANTINED, and disposable

This lives under `prototypes/`. That is a load-bearing fact, not a filing convenience:

- **Nothing in the live system imports, spawns, watches, ships, or runs it, and CI does not touch
  it.** It graduates only by an explicit separate decision — never by living here.
- **It writes nothing outside `prototypes/relay-room/`.** Every mutating filesystem call goes
  through `assert_inside()`, which raises rather than write one byte outside this directory.
- **It runs its OWN relay-gate instance.** `gate.py` honours the `FP_COORD` environment variable
  (`gate.py:36`), and this prototype points it at `state/coord/`. The real `coordination/` — where
  Rab has a live open escalation — is never opened. `FP_COORD` is **never inherited**: every gate
  subprocess is launched with an explicitly constructed environment, because gate.py's check is a
  truthiness test and an empty inherited value would silently fall through to the real directory.
- **Everything mutable lives in `state/`, which is gitignored.** Delete the whole directory and
  re-run `init`; nothing of value is lost. That is what disposable means here.

`selftest.py` snapshots the real `coordination/` tree and the live `state/` tree before it runs
anything and re-measures both at the end. "I did not touch the real relay" is a **measurement**
in this prototype, not a promise.

---

## The three lanes

| Lane | Who | Writes into `room.md` by | Status published by |
|---|---|---|---|
| **Rab** | the human | the browser bar → `POST /api/say` (token-gated) | nothing — see below |
| **Fable** | Claude | `room.py say --from Fable …` from its own session | `catcher.py --lane Fable` |
| **Codex** | OpenAI Codex | `room.py say --from Codex …` from its own session | `catcher.py --lane Codex` |

**The Rab card is deliberately thin.** It shows how many live clients are connected and when he
last spoke, and then it says the honest thing: *no probe exists for a human's attention.* A
message addressed to Rab reaches `landed` and stops there. Rendering "delivered" for a human
because a file was written is exactly the substitution of a mechanical signal for a judgment
reading that this whole design exists to prevent.

### What happens to one message

```
Rab types  ──POST /api/say──▶  appended to state/room.md   (append-only, under a lock)
                                        │
                          catcher.py --lane Fable notices it
                                        │
              writes state/handoff/Fable/RM-….json  +  invokes the quarantined gate.py
                                        │
                       the model reads its handoff dir and CLAIMS the message
                                        │
                       the model appends its reply to the SAME room.md
                                        │
                              Rab sees it live (SSE, or polling)
```

Eight stages are tracked per message: `typed · transmitted · landed · caught · handed ·
delivered · model-working · replied`. **Stages 1–2 are the browser's own optimism and are rendered
dashed and labelled `client-asserted`** — they exist nowhere on disk. **Stages 3 and 8 are derived
from `room.md` itself** — the log is its own witness. **Stages 4–5 belong to the agent; 6–7 belong
to the model, and an agent is refused by both the writer and the reader if it tries to write
them.** Delivery is a judgment, not a piece of machinery.

---

## Launch (PowerShell, in this order)

```powershell
$PY   = "C:\Users\Bndit\ml\marker-env\Scripts\python.exe"
$ROOM = "C:\Users\Bndit\Projects\file-portal\prototypes\relay-room"

# 1 - create state/, state/coord/, config.json and room.md's preamble. Idempotent.
#     This also runs `gate.py init` for both lanes with FP_COORD forced at state\coord:
#     relay.md is opened in "a" mode with no mkdir, so `post` raises FileNotFoundError if the
#     directory does not exist yet. ALWAYS INIT FIRST.
& $PY "$ROOM\room.py" init

# 2 - the server (terminal 1). It prints the TOKEN-BEARING URL. Open exactly that URL.
& $PY "$ROOM\room.py" serve --port 7133

# 3 - the agents, one terminal each. Filesystem-only: no token, no server URL, on purpose,
#     so the agent layer stays observable even when the server is dead.
& $PY "$ROOM\catcher.py" --lane Fable
& $PY "$ROOM\catcher.py" --lane Codex
```

Step 2 prints:

```
relay-room · http://127.0.0.1:7133/?token=4b7e0c9a1d2f3e5a6b8c0d1e2f3a4b5c
  state    C:\Users\Bndit\Projects\file-portal\prototypes\relay-room\state
  coord    C:\Users\Bndit\Projects\file-portal\prototypes\relay-room\state\coord   (FP_COORD)
  QUARANTINE: the real coordination/ is NOT touched by this process
  open the URL ABOVE, including ?token= — mutating routes fail closed without it
  agents:  python catcher.py --lane Fable   |   python catcher.py --lane Codex
```

**Open the URL including `?token=`.** Mutating routes fail closed without it and answer 403 with a
remedy sentence. (The repo's other standalone launchers print a token-less URL, so an operator who
starts them by hand gets a page that 403s every POST until they hand-append the token. That gap is
not reproduced here.)

### What a model runs from its own session (no token — it is a local process)

```powershell
& $PY "$ROOM\room.py" say   --from Fable --to Rab --re RM-a1b2c3d4e5f6 --body -    # body on stdin
& $PY "$ROOM\room.py" say   --from Fable --to Codex --body msg.md
& $PY "$ROOM\room.py" state --lane Fable --state composing --ticket RM-a1b2c3d4e5f6 --note "drafting"
& $PY "$ROOM\room.py" claim --lane Fable --id RM-a1b2c3d4e5f6      # the ONLY way stage 6 is reached
& $PY "$ROOM\room.py" status                                        # the board, without a browser
```

### The tests

```powershell
& $PY "$ROOM\selftest.py"                                          # the eight laws, both ways
& $PY -m unittest discover -s "$ROOM" -p "test_room.py" -v         # the 39 named tripwires
& $PY "$ROOM\room.py" selftest                                     # end-to-end on a throwaway tree
```

`selftest.py` copies the sources into a fresh temp tree and runs them from there, so it can never
write into the live `state/`. It prints three verdicts and they are not interchangeable:

| verdict | means |
|---|---|
| `PASS` | the guard was measured and it held |
| `FAIL` | the guard was measured and it did not hold |
| `UNREAD` | **the check could not be run at all** — a module has not landed, a server would not start |

**`UNREAD` is counted as a failure and exits non-zero.** A law with no reading behind it is an
unproven law, not a satisfied one. Add `--verbose` for detail on passing checks, `--keep` to keep
the temp tree, `--list` for the roster.

Every guarded assertion in `selftest.py` is paired with an **unguarded control** that must fail it.
A control that does not fail is reported as a `TAUTOLOGY` and is a hard failure — a tripwire that
passes both ways measures nothing.

---

## What this cannot see

Read this section before you trust anything on the board. It is the honest register, and it is the
part of the README most likely to save someone.

**About identity and authority**

1. **`from:` is a claim, not an identity.** Any local process — with the token, or with plain
   filesystem access and no token at all — can append as `Rab`. The loopback token fences the
   *network* (a drive-by page in a local browser firing cross-origin requests at the port). It is
   **not** an authentication boundary against local processes: argv is readable by same-user
   processes, and the CLI writes the log with no token, deliberately.
2. **The digest proves a body was not edited after it was written. It does not prove who wrote
   it.** There are no signatures here.
3. **The catcher never confirms, escalates, or resolves.** Those four gate subcommands are
   permanently forbidden to the agent layer. ACK discipline and escalation remain model and human
   work; a restatement generated by a loop would be a forged act of reading, and no agent reaches
   the principal.

**About what is measurable at all**

4. **There is no probe for a human's attention.** Whether Rab has read a message is UNREAD,
   permanently, by construction. Nothing here will ever tell you otherwise.
5. **A model's declared state is unverifiable from outside.** `working` and `composing` are the
   model's own word. The board renders them as *declared* and lets the relay-gate sidecar override
   them when the sidecar says the lane is blocked — but a model that declares `working` while doing
   nothing cannot be caught by this prototype.
6. **Staleness is measured against the local wall clock.** A clock jump, a laptop resuming from
   sleep, or an NTP correction renders lanes STALE. That is the correct failure direction — an
   unmeasurable lane must never render green — but a STALE lane here is *"nobody has heard from
   it"*, which is not the same reading as *"it is dead"*.
7. **`model_stale_after_s` is 300 s for a measured reason, not a chosen one.** gate.py stamps its
   sidecar `updated_utc` at **minute precision, truncated**, so a threshold under about 120 s would
   render a perfectly healthy lane STALE on clock granularity alone. Do not "fix" it downward; you
   will manufacture false alarms.

**About the two digest systems**

8. **A `room.md` digest and a `relay.md` digest of "the same message" are expected to differ.**
   They cover different bytes: gate.py digests an entry *including its header line*, and this
   prototype digests the **body only**, because the digest lives *in* the header and cannot cover
   itself. They are not comparable quantities and a mismatch between them is not a defect.

**About what the tests do and do not establish**

9. **Nothing here renders the page.** The UI checks are source greps: they prove `room.html`
   contains no `innerHTML` and reaches no external host. They do **not** prove the page lays out
   correctly, that the two status rows are actually distinguishable to a human eye, or that the
   dark theme is legible. No browser is opened by any test in this prototype.
10. **The concurrency proof is evidence, not a theorem.** It is two real threads making fifty real
    appends on one machine. It says nothing about two separate *processes* contending on NTFS under
    load, and nothing about a network filesystem.
11. **`selftest.py` proves the eight laws. `test_room.py` proves the 39 named tripwires. Neither
    proves the build is correct** — they prove specific named failure modes do not occur. The
    UNREAD count tells you how much was not measured at all; read it before you read the PASS count.
12. **A module that has not landed makes every law it carries UNREAD, not satisfied.** If the
    selftest reports 19 UNREAD, nineteen laws have no reading behind them. That is not a partial
    pass.

**About the prototype's standing**

13. **Two open items are Rab's call and are recorded in `DESIGN.md` under "Open for Rab", not
    silently resolved:** the directory sits at `prototypes/relay-room/` (one level) where the
    convention is `prototypes/<category>/<name>/`, and the index row in `prototypes/README.md`
    still has to be landed by hand — no builder may write outside this directory, so no builder
    could add it.
14. **This is a prototype.** It is not on the pipeline, not in CI, not watched, not shipped, and
    not backed up. Treat `state/` as scratch.

---

*`prototypes/relay-room/README.md` · authored 2026-08-24 · ⟨claimed: Fable⟩ — an authorship
claim only, never Rab's authority.*
