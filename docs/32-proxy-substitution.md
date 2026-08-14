# docs/32 — Symptom, condition, disease

Rab, 2026-08-14: *"if you end up finding anything more, diagnose what's causing the glitches.
Investigate the repo if you start building either a symptom or a condition or a disease."*

We found more. This is the diagnosis, and the answer is that we have been treating a **symptom**,
have correctly named a **condition**, and have never named the **disease** — which is why four
consecutive sessions reproduced the thing they were actively holding in mind.

## 1. The three, separated

**The symptom** — SYM-027: a measured value is computed correctly, persisted correctly, and
reaches no human. This is a *sign*. docs/29 §5.1's detector treats it.

**The condition** — docs/29 §1: every law in this corpus with teeth governs what may be
**written**; none governs what must be **read**. That is a standing state of the codebase, and it
is what lets the symptom recur indefinitely. Correctly diagnosed, and the converse projection law
(§4) is the right treatment for it.

**The disease** — not yet named, until now:

> **PROXY SUBSTITUTION: establishing a property by checking something cheaper that correlates
> with it, and never re-checking that the correlation still holds.**

## 2. Why that, and not something else

Take every defect the two Circles found and ask what each one actually did. Not what it broke —
what its *author was doing at the moment it was written*.

| The proxy that was checked | The property it stood in for |
|---|---|
| `tail -1` on the ledger | which row is the **newest** |
| `head -1` on `MEMORY.md` | which number is the **clock** |
| `len(diff) > 500` | the diff **introduces a producer key** |
| `scoped_rows >= 0` | the tool **ran without crashing** |
| `--since HEAD` (empty diff) | the filter **works on a real range** |
| `grep -c $'\r'` | the file **has CRs** |
| a count written down (`93`, `77`, `19/19`) | the count **as it is now** |
| "the doc records a signature" | the thing is **wired** |
| "the renderer's text contains this identifier" | a **human sees this value** |
| "the acceptance suite is green" | the **behaviour is correct** |
| the ritual step **written** | the ritual step **runs** (bare `python` → exit 49) |

Eleven defects, one shape. In every case the proxy was *true when chosen* and drifted from the
property afterwards — which is precisely why nobody noticed: the check kept passing, and passing
was the evidence.

**And the observability class is itself an instance.** A producer writes a value and treats
*"I wrote it"* as proof of *"it was received."* Write-side laws are strong here because writing is
an **act** you can chokepoint. Reading is a **property**, and this project has only ever checked
proxies for it. The condition in §1 is not a separate problem — it is the disease's largest
colony.

## 3. Why it is *most* active while building a guard

This is the part that explains the recurrence, and it is not a story about carelessness.

**A guard is a proxy. That is what a guard is.** You cannot write a check without choosing an
observable to stand in for the property you care about. So the act of defending against the
symptom is the single moment at which the disease is most certain to act.

The record bears this out exactly:

- **S76** named the class, then shipped a fourth instance ninety minutes later.
- **S77** produced two more while writing the census that counted them.
- **S78** built the detector for the class, and the detector's `--since` filter was blind to an
  entire language dialect — Mode D inside the Mode D detector — while its README said "wired into
  nothing" beside a doc citing that README as proof it was signed.
- **S79** fixed "a harness that could not fail" by writing a check that could not fail
  (`scoped_rows >= 0`), shipped the suite **red** while three artifacts recorded it green, and —
  in the very edit that removed a stale number from `MEMORY.md` — re-planted the second anchor
  that `muster.sh` had been repaired for that same hour.

Four sessions, four recurrences, each committed by someone holding the concept in working memory.
That is not attention failing. That is a mechanism.

## 4. The repo already had the fingerprint, filed as incurable

**SYM-001**, recorded S60: *"Tests and harness all green, but the shipped behaviour is wrong —
the fake/stub shared the same assumption as the code under test. Two checks that share an
assumption are one check."* Status: **`Historical` — class is permanent, no mechanical guard
possible.**

That is proxy substitution, seen once, in one location, and written off. docs/29 is the same
disease seen at scale on the read side. **The two were never connected**, so SYM-001's remedy was
never generalised — and its remedy is the correct one:

> `docs/21` §1: **`Verified` requires a differently-shaped second method.**

Already written. Already signed. Applied only to the word *Verified* in closeout prose, and never
to a single guard.

## 5. The treatment — which Rab named before the diagnosis existed

You cannot remove proxies; a check is a proxy by definition. What you can do is make the
proxy→property link **explicit and continuously tested**. That is exactly what a tripwire is:

> *"trip wire is like stepping into it, and see if it explodes or it was disarmed by the fix…
> there is risk involved, but that risk is safe since this is a program, and not literal c4."*
> — Rab, 2026-08-14

A tripwire violates the **property** and checks that the **proxy** fires. It is the only test that
measures the correlation itself rather than assuming it. His instruction is the cure, arrived at
by instinct, before anything here was diagnosed.

It works, and this session is the evidence: every S79 fix was tripwired, and the tripwires caught
what review did not — the two-anchor fixture printed a green `✓ 71` off an index bullet while the
real clock sat blank, which no amount of reading the diff would have surfaced.

**The three rules that follow:**

1. **A guard states the property it stands for, in the guard.** Not in a commit message, not in a
   doc — in the code, where the next person changing the proxy will read it.
2. **A guard ships with a tripwire that violates the property.** A guard nobody has watched fire
   is not a guard; it is a proxy with a reputation.
3. **A number is re-measured, never quoted.** Every count in this session's records was wrong
   within two commits of being written: 93 → 77 → 76, 13/13 → 19/19 → 18/19 → 19/19.

## 6. What this predicts

If the diagnosis is right, the next instance will appear **in whatever we build next to enforce
rules 1–3** — because that will be a guard, and a guard is a proxy. The prediction is falsifiable
and should be checked at the next Circle rather than assumed.

It also predicts that the 76 standing glitches are **not** the main debt. They are one colony. The
debt is every place a proxy is currently standing in for a property with no tripwire on the link —
and nobody has counted those, because counting them requires asking, of every check in the repo,
*"what would have to be true for this to pass while the thing it guards is broken?"*

That question is the next Circle's commission.

## 7. Status

**Not signed.** This is a diagnosis, not a law. It proposes no mechanism, changes no code, and
asks for nothing except that the next Circle test §6's prediction. If Rab signs the three rules in
§5, they belong in `docs/21` beside SYM-001's remedy, which they generalise.
