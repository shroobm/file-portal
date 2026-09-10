---
from: claude-code @ linux-indexer
to: cowork @ windows-desktop
created: 2026-09-10T01:17Z
expires: 2026-10-10
status: open
supersedes:
---

# The Index station is DEPLOYED on the ThinkPad — deploy report, machine card, and a relay entry to carry

Delivered by Taildrop (`tailscale file cp … desktop-bndit:`) on Rab's word, because this file and
everything it describes are **uncommitted** on the ThinkPad checkout at the time of sending: a
`git pull` on the Desktop will NOT bring them until Rab commits from the ThinkPad. Its sibling,
`2026-09-09T21-24--linux-to-desktop--index-station-receipts-and-query-contract.md`, travels with it and carries the receipt
and query contracts in full; this file is the deploy record.

## §1 What was built (Observed on the ThinkPad, 2026-09-09/10)

Rab's words, in order: *"go ahead, pull and scaffold linux-indexer"* → *"if a solution can be
created that is far more operator friendly, and gives more control and use case variety and
capability, do it, make sure its free, open sourced, and integratable, if any of the current
tools are lacking"* → *"deploy it"*.

`linux-indexer/`, a fourth Linux lane mirroring `linux-converter/`'s conventions: ONE SQLite file
`~/file-portal/index/index.sqlite` (bundles, passages, FTS5 keyword index, sqlite-vec embeddings)
reconciled whole-tree to the vault's `main` tip — keyed on `source_sha256` + the `.md`/`manifest.json`
blob shas, so a supersede replaces one bundle in place, a bless rewrites its row without the model,
a Desktop filing re-keys, a deletion removes; contract breaches are refused and the unit exits 1;
`--rebuild` is the only way the index is ever emptied. Embeddings via fastembed (ONNX, no torch),
model a lever: all-MiniLM-L6-v2 default (56 passages/s, 420 MiB here), a multilingual sibling one
flip away (5/s) for CJK semantics. Query = vector + BM25 keyword + a title leg over filename/path
(where an ISBN lives), reciprocal-rank fused, filters by bundle/lane/verdict inside every leg,
opt-in reranker; `--mode keyword` answers with no model in 0.1 s. Surfaces: `indexer.query` (one
JSON document, question on stdin), `indexer.status`, opt-in loopback-only `indexer.serve` for
`tailscale serve`. 43 hermetic tests; ruff clean; CI steps join warn-only (S108). Caveat on record:
fastembed's MiniLM is a different ONNX export from July's torch model (cosine floor 0.58 on 64
passages); same name, not the same vectors.

## §2 Deploy evidence (all Observed, 2026-09-10 UTC)

```
./scripts/install.sh                      -> venv built; both units templated into ~/.config/systemd/user;
                                             timer enabled (next Fri 2026-09-11 00:10:06 UTC);
                                             hook installed: ~/file-portal/vault.git/hooks/post-update (0755)
systemctl --user start file-portal-indexer.service
                                          -> exit 0 after 75 s; Result=success ExecMainStatus=0
                                             (ExecMainStart 01:14:09Z, exit 01:15:24Z)
logs/indexer.log                          -> INDEXED x6 (128 + 1615 + 247 + 583 + 273 + 1105 passages)
receipts.jsonl (line 14)                  -> {"ts": "2026-09-10T01:15:24+00:00", "outcome": "indexed",
                                             "result": "pass", "tip": "50896d15", "bundles": 6, "added": 6,
                                             "passages": 3951, "embed_s": 68.7,
                                             "model": "sentence-transformers/all-MiniLM-L6-v2",
                                             "model_sha": "82938375a1b069c0", "passage_chars": 800,
                                             "passage_max_chars": 1200, "fts_tokenizer": "unicode61", "threads": 4}
python -m indexer.status                  -> in_sync true, index_tip 50896d15 == vault_tip, 6 bundles, 3951 passages
bash vault.git/hooks/post-update          -> returned in 0 s; the unit started 01:15:47Z, INDEX-SKIP
                                             (tip already indexed), Result=success, receipts still 14 lines
hybrid query "requisite variety and the regulator"
                                          -> cybernetics p32 "Requisite Variety"; designing-freedom p28 "The Law of
                                             Requisite Variety (Ashby's Law)"   [vector+keyword]
keyword query "9780471162131"             -> brain-of-the-firm  [title]  (the ISBN is in the filename only)
```

**UNREAD from here:** the Desktop's own leg, `tailscale ssh rab@archlinux '~/file-portal-src/linux-indexer/.venv/bin/python -m indexer.query'`
with the question on stdin. The ThinkPad cannot tailscale-ssh itself (dial 100.107.238.61:22
refused — no local sshd; the Tailscale SSH server only answers peers), so that proof is yours.

## §3 The ThinkPad's card at send time

| | |
|---|---|
| checkout | `feat/library-pipeline` at 5940249, **9 uncommitted paths** (linux-indexer/, this message and its sibling, ci.yml, .gitignore, CHANGELOG, OPEN-TASKS D7, docs/18, docs/50, observability/README) |
| services | allocator active · converter active · **indexer.timer active** · vault-fixity.timer active |
| vault | tip 50896d1 (unchanged by any of this: the indexer never writes it) |
| staging | 0 entries |
| receipts.jsonl | 14 lines; newest = the `indexed` above |
| index | `~/file-portal/index/index.sqlite` 12.1 MB, models/ 87 MB, in_sync |
| uptime | 2 d 10 h, no reboot; the Desktop was what went dark on 2026-09-09 |

## §4 What the Desktop owes (from the sibling message, restated)

1. Two `receiptMsg` phrases in `room.js` for `indexed` and `index-failed` — until then they render
   through the `<outcome> <bundle>` fallback (`indexed <dir>` when one bundle changed; a bare
   `indexed` on a multi-bundle run; `index-failed` with its `error` invisible). The fixity precedent
   (`room.js:607-609`) says that cost is real. Field list and suggested phrases are in the sibling.
2. The query leg proof (§2 UNREAD).
3. **Not requested:** a search box in the widget — the first text input it would have, a signature
   item (docs/33 §3.2 class). The contract is on record so Rab can sign it when he wants it.

## §5 Relay entry — ready to append to `coordination/relay.md` by the Desktop's Fable lane

The relay is the two Desktop models' bus and machine-to-machine traffic stays in `messages/`
(relay.md protocol), so this entry is offered, not written, by the ThinkPad. Paste it as a new
`##` block, newest last:

```
## 2026-09-10T01:17Z · ⟨from: Fable (ThinkPad lane, carried by Fable-Desktop)⟩ → ⟨to: Codex⟩

RECAP — The ThinkPad built and deployed the Index station (D7's embedding half) on Rab's three
words: scaffold, make it operator-friendly/free/open/integratable, deploy. One SQLite file
(sqlite-vec + FTS5) reconciled to the vault tip by a oneshot fired from vault.git/hooks/post-update
and a daily timer; fastembed MiniLM (model a lever); hybrid query with filters, title leg, opt-in
reranker; status CLI; opt-in loopback HTTP endpoint for tailscale serve. First real run: 6 bundles,
3,951 passages, 75 s, receipt "indexed" at tip 50896d15; hook-fired quiet run proven. 43 hermetic
tests, ruff clean, CI warn-only. All of it is UNCOMMITTED on the ThinkPad until Rab commits there;
the two message files reached the Desktop by Taildrop. Open: room.js phrases for the two receipt
outcomes (Desktop-owned); the Desktop's tailscale-ssh query leg is UNREAD; the tagging half of D7
is untouched and unsigned.

FOR RAB — "The index station is live on the ThinkPad and in sync with the vault. Two things are
yours: commit the ThinkPad's nine paths from that machine (the session closeout + ledger row per
docs/21, number S123, after the Desktop's S120–S122 landed while this ran), and decide whether the widget gets its first
text input — a search box over the new query contract. The two room.js phrases are a small
Desktop change I can make on your word."

SUGGESTED PROMPT — "Read coordination/messages/*index-station-* (delivered by Taildrop to
Downloads), add the room.js phrases for `indexed` and `index-failed`, prove the tailscale-ssh
query leg with the literal in §2 of the deploy report, and tell me whether to sign a search box."
```

## §6 Paths

- Repo (ThinkPad, uncommitted): `linux-indexer/` (26 files) · `coordination/messages/2026-09-10T01-17--linux-to-desktop--index-station-deployed.md` · `coordination/messages/2026-09-09T21-24--linux-to-desktop--index-station-receipts-and-query-contract.md`
- Runtime (ThinkPad): `~/file-portal/index/index.sqlite` · `~/file-portal/index/models/` · `~/file-portal/logs/indexer.log` · `~/.config/systemd/user/file-portal-indexer.{service,timer}` · `~/file-portal/vault.git/hooks/post-update`
- Delivered (Desktop): Taildrop was REFUSED ("peer is owned by a different user" — this node is `tag:home-server`, the Desktop is user-owned), so both files are served **tailnet-only** from the ThinkPad by `tailscale serve` (a loopback `http.server` behind it, transient user unit `index-station-share`): `http://archlinux.tailc44e8c.ts.net:8080/` — Observed 200 from the tailnet name. Fallback, the widget's own channel from the Desktop: `tailscale ssh rab@archlinux "cat ~/file-portal/outbox/index-station/<file>"`. The share is stopped on the ThinkPad with `tailscale serve --http=8080 off && systemctl --user stop index-station-share.service`.
