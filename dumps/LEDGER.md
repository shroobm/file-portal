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
| D0042 | 2026-09-13T00:28:39Z | Fable | evidence | orphaned analyst chunk journal d58db211c41b0e17 (2026-08-30; SURF-12 of the S140 second reading; its book reached DONE 2026-09-01) - ledgered before removal | 2432455 | `75f0304d86f02ec04d7f9bef441074f01ca19e193fd3fa23fc7ca70aaf09f1ce` |
| D0043 | 2026-09-13T11:31:07Z | pipeline | evidence | chunk journal - run 702f1b9661287055 | 701422 | `d9ee8a0b16c640a7d2f398bb769ba097855766af1449c4a39eab91adfc58d776` |
| D0044 | 2026-09-13T17:44:55Z | pipeline | evidence | chunk journal - run da03b7cd2f6403de | 745 | `f4d5dceb6f58d9d9082fde4e4ee0ce89220ddde80972e480979735bb78008afe` |
| D0045 | 2026-09-13T17:44:56Z | pipeline | evidence | chunk journal - run 3717d06965c3f8a7 | 262 | `b2bd6fb09e284c6354a27216816dcadc594ab0d457dc3a95ccdaaa242def29b6` |
| D0046 | 2026-09-13T17:47:18Z | pipeline | evidence | chunk journal - run da03b7cd2f6403de | 745 | `f4d5dceb6f58d9d9082fde4e4ee0ce89220ddde80972e480979735bb78008afe` |
| D0047 | 2026-09-13T17:47:19Z | pipeline | evidence | chunk journal - run 3717d06965c3f8a7 | 262 | `b2bd6fb09e284c6354a27216816dcadc594ab0d457dc3a95ccdaaa242def29b6` |
| D0048 | 2026-09-17T01:35:31Z | pipeline | evidence | chunk journal - run b5c2b2c5ec228c1e | 2128 | `bae42466776887d25d222cedfa8655c59e6f6eb11e5313c44a474b7609be1fee` |
| D0049 | 2026-09-17T01:37:01Z | pipeline | evidence | chunk journal - run c5226dc4e8e096ae | 106 | `1320fd4da654f2d91714e91cc28ff895f41762698ec379ba8a05dd8aee5f1278` |
| D0050 | 2026-09-17T01:58:05Z | pipeline | evidence | chunk journal - run 90d6a69a39aadf0d | 3742 | `7c82246e89f933553e34a739a534f6d88ffab3da72be0b3ead1ba8200e625e1b` |
