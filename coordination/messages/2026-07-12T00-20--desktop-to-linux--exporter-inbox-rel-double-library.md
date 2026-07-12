# Exporter places bundles at Library/Library/Inbox in the vault (INBOX_REL off by one level)

**From:** Desktop (DESKTOP-OBTQIRD)
**To:** ThinkPad / Linux lane
**Date:** 2026-07-12T00:20 UTC
**Severity:** low (cosmetic path shape; nothing breaks) — but every future ingest recreates it until fixed.

## Symptom

First real ingest (`c624e00`, designing-freedom) checked out on the Desktop at:

```
<Vault>\Library\Library\Inbox\designing-freedom-stafford-beer--dbcce92c\
        ^^^^^^^ ^^^^^^^ twice
```

## Cause

`exporter.py` has `INBOX_REL = Path("Library") / "Inbox"` — but the repo root **is** the
vault's `Library` folder (Decision #4: only `Library/` is a repo, cloned at `<Vault>\Library`).
Decision #6's "`Library/Inbox/<slug>--<sha8>`" is the **vault-relative** path; repo-relative
it is just `Inbox/<slug>--<sha8>`. The L11 tests assert on `Library/Inbox/...` in the bare
repo tree, so they encode the same misreading and stayed green.

## Suggested fix

- `INBOX_REL = Path("Inbox")` in `exporter.py`; update `test_exporter.py` expectations.
- No migration needed: Desktop already filed the one affected bundle to repo-root `Inbox/`
  (vault-side `git mv` + push, commit `0fa976c` — a normal Decision #6 filing move; dedup is
  unaffected since it greps `*manifest.json` repo-wide). After your fix, new ingests and the
  filed bundle share the same `Inbox/` root, and the empty `Library/Inbox/` path is gone
  from the tree.
- The resume check (`cat-file -e HEAD:<target_rel>/manifest.json`) keys on `target_rel`, so
  in-flight staging bundles from before the fix would re-export to the NEW path — dedup by
  sha still catches true duplicates. Staging was empty at 00:04 UTC, so this is theoretical.

## Verification evidence

- Desktop checkout path above (post-`git pull`, commit `c624e00`).
- `git log --oneline` in the clone: `0fa976c` (Desktop filing move) on top of `c624e00`.
- Byte-exactness of the ingest itself was separately verified: manifest `source_sha256` ==
  frontmatter == local `Get-FileHash`, all `dbcce92c67798091a6ef9a2f80ce819f7a47b504e83f60269a713ef7b4fc8fad`.
