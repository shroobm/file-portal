# docs/65 — Downloads, installs and machine changes: the policy (S213, 2026-09-25)

*Rab, on the Desk, 2026-09-25:*
- *103ff076, 16:08:51Z: "I'm going to give you the go ahead. Just always itemize the bill of what you downloaded and what has changed. Always be aware of what you are going to do before you do it, by planning your steps and reasons prior."*
- *Scope "A" (under 17258df3, 16:44:36Z): anything the work needs.*
- *16:44:46Z: "But make a clear policy obviously."*

*This is that policy. It binds every agent session on this machine. It was born of one mistake: a bare `python3` that silently installed a Python runtime (SYM-186).*

**The rule in one line: plan it, source it, bill it, be able to undo it — or don't install it.**

## 1. What counts

- **Counts:**
  - anything downloaded: packages, models, weights, datasets, tools, a third-party repository;
  - anything installed or uninstalled;
  - anything removed outside the git repositories;
  - any setting or configuration changed: config files, the registry, PATH, environment variables, harness settings, scheduled tasks;
  - any lasting process started or stopped: servers, watchers, pumps.
- **Does not count:** edits inside the repositories that go into a commit. The commit is their record.

## 2. What the go-ahead allows

Anything the work needs may be downloaded and installed **without asking first**, when every condition in §3–§7 is met.

## 3. Before: the plan

- **Before the first download,** write the plan in the sitting's record. When it is more than one package, or a model, it also goes on the Desk. The plan names:
  - each item;
  - where it comes from;
  - why the work needs it;
  - where it will go;
  - how it will be undone.
- **A need found along the way** is added to the plan and said on the Desk *before* it is fetched, not after.

## 4. The source

- **Official sources only:**
  - PyPI;
  - the Hugging Face Hub (the publisher's own repository);
  - python.org;
  - a project's own GitHub releases;
  - a vendor's own site.
- **Exact versions** (`==`), never "latest".
- **A signature or checksum is checked** whenever the source publishes one, and the check is recorded.
- **Stop and ask Rab first** when:
  - the source is not official or not known;
  - the install needs administrator rights, a driver or a system service;
  - the license restricts use;
  - it costs money;
  - it would replace or upgrade something already installed in a pinned environment.

## 5. Where it goes, and the check after

- **Python packages** go into a named environment by its path: `uv pip install --python <that environment's python.exe>`. Never into the system, and never with a bare `pip` (SYM-186). Do a dry run first; it lists everything that will come in.
- **The converter's environment (`marker-env`):**
  - nothing already there may change without saying so;
  - after the install, the same sample conversion must come out byte-identical, or the difference is shown and explained;
  - `windows-converter/marker-env.freeze.txt` is updated in the same commit.
- **Models and datasets** go into the existing caches (the Hugging Face cache), with their size recorded.

## 6. After: the bill (the Footprint)

- **Every item gets a row at the act,** written with `footprint.py add` (in the private `agent-scripts/developing/handoff/`). The tool measures the hash, the size and the time itself. It refuses a row without a reason or an undo.
- **Every episode's close posts its Footprint** on the Desk with `footprint.py post`, **even when nothing changed**. The Desk's **Footprint** button collects them, and Rab reads them and replies or signs in the thread.
- **Anything that cannot be measured says UNREAD,** and why.

## 7. Undo

Every row names how it is undone. **If an undo cannot be named, it is not installed.** Ask first.

## 8. What the go-ahead does not reach

- **These stay Rab's:**
  - arming PORTAL;
  - any threshold, gate or verdict;
  - the vault;
  - credentials, accounts and payments;
  - anything that publishes or sends;
  - system and security settings.
- **The GPU law** still applies: one lab process on the card, and check `.gpu-lock`, `nvidia-smi` and his game or stream first.
- **Sub-agents download and install nothing.** They work without internet; only the session downloads, under this policy.
- **Never a bare `python`, `python3`, `py` or `pip`.** Use the interpreter by its path (AGENTS.md; SYM-186).

## 9. When something slips

- **Reverse it at once.**
- **Tell Rab on the Desk** the moment it is found.
- **Record it:** a CORRECTIONS row and a Footprint row.

15:17Z on 2026-09-25 is the specimen: the install was reversed within a minute and told within two.

## Where it lives

- **The policy:** this file (public).
- **The tool and its tests:** `footprint.py` and `footprint_selftest.py`, in the private `agent-scripts/developing/handoff/`.
- **The duty to post:** the Desk skill's sixth obligation.
- **Memory:** `download-bill-and-plan-first`.
- **The pointer for every coding agent:** AGENTS.md, under Standing hazards.
