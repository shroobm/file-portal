# DUMP LEDGER — tracked, append-only, written only by `dumps/dump.sh`

**This file is the durable half.** The bytes it points at are gitignored and live only on this
machine; this row survives in git history even after a dump is deleted. So the answer to *"what was
in that dump?"* is never lost, even when the dump is.

**Do not hand-edit.** `dump.sh` assigns the id, stamps UTC, and computes the sha256 — none of them
are typed, because a hand-typed id or digest is a future SYM-039. A row added by hand is a row
nobody can verify.

**Reading a dump is `Historical`, never `Observed`.** It is bytes at a timestamp. It carries no
verdict and proves nothing about now.

| id | utc | lane | category | subject | bytes | sha256 |
|---|---|---|---|---|---|---|
| D0001 | 2026-08-26T05:27:39Z | Fable | evidence | SYM-056 chunk journal snapshot - Ashby, taken before analyst.py rmtree'd it | 3916 | `a9876cfa388f1ef2fe3dbc9b0747d454318d35cdb4932cc58c2e4328334fc9a9` |
| D0002 | 2026-08-27T07:50:55Z | Fable | qa | CHANGELOG backfill S105-S110: 6 drafts + 6 adversarial audits, ALL SIX NEEDS-FIX, deliberately NOT landed | 121147 | `6de8aafbc7627481f8baf27219148ec4a316aa5b0fd85a6d880cea187cc5047b` |
| D0003 | 2026-08-28T02:08:57Z | Fable | qa | FALSIFIED CLASSIFICATION EVIDENCE - 147-row census; st:GOV was invented, NOT DATA | 67491 | `b1efc07dbcab762a75a9dd2e778840f63e9ea65f7eaf40c804ebee5c43bfc123` |
| D0004 | 2026-08-30T16:31:37Z | Fable | evidence | okular fleet full sweep+audit reports (falsified census warning n/a; 404/404 citations audited) | 441225 | `60c3154106a9d7dc9e1158941ea466ee5576ab1a0771a75db0404457c7ba1622` |
| D0005 | 2026-08-30T16:48:17Z | Fable | evidence | okular fleet evidence v2 - sweeps, audits, corrected downgrade metadata (supersedes D0004) | 441639 | `981f295932140acd033668b454760999ad1f5e071f771d9eb793140d8da57099` |
