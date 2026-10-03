"""WHAT THIS FILE DOES: lets the indexer read the vault (a bare git repository) without writing to
it. Vault.tip() names the newest commit, Vault.bundles(commit) lists every bundle (a folder with a
manifest.json and one .md body) at that commit, and Vault.blob(sha) returns a file's bytes. It runs
the `git` program as a subprocess and nothing else. Called by reconcile.py.

Read-only view of the bare authoritative vault, `git --git-dir` only (fixity.py's idiom).

Bundles are discovered by locating every manifest.json blob anywhere in the tree -- the bundle
dir is its parent. `Inbox/` is not a contract: the Desktop may file a note elsewhere
(exporter.py "a bundle the Desktop has filed out of Inbox/ still counts"). The body is the
single `.md` directly in the bundle dir -- "exactly one .md", the guard the exporter enforces
on supersede; REPAIRS.md is a generated report, never the body. Paths are read NUL-separated
from `ls-tree -z` because the tree holds spaces, parentheses and CJK, which default git quoting
octal-escapes. Blobs are read by sha, so no path ever passes through a shell or a `main:<path>`
spec.

Everything is listed against ONE commit (the tip resolved once per run), so a push landing
mid-run cannot make a manifest and its body come from different snapshots. Nothing here has
a write verb.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

# -- constants: branch name, manifest file name, generated reports to ignore --
VAULT_BRANCH = "main"  # HEAD of the bare repo is pinned to refs/heads/main (Decision #4)
MANIFEST_NAME = "manifest.json"
# Generated reports that may sit beside the body but are never the body (repair-bench).
GENERATED_MD = frozenset({"REPAIRS.md"})


# -- error and data types --
class VaultError(Exception):
    """Raised when a git command against the vault fails."""

    pass


@dataclass(frozen=True)
class Bundle:
    """One vaulted bundle: its folder, its manifest blob sha and its .md body blob sha."""

    note: str  # repo-relative bundle dir, e.g. Inbox/<slug>--<sha8>
    manifest_blob: str
    md_names: tuple[str, ...]  # .md entries directly in the dir, generated reports excluded
    md_blob: str | None  # set only when exactly one .md is present

    @property
    def md_name(self) -> str | None:
        """The body's file name when exactly one .md is present, else None."""
        return self.md_names[0] if len(self.md_names) == 1 else None


# -- the read-only vault reader --
class Vault:
    """Read-only access to the bare vault repository at the path given."""

    def __init__(self, bare: Path):
        """Remember the path of the bare repository; does no I/O."""
        self.bare = bare

    def exists(self) -> bool:
        """True when the bare repository has a HEAD file."""
        return (self.bare / "HEAD").is_file()

    def _git(self, *args: str, text: bool = True) -> subprocess.CompletedProcess:
        """Run `git --git-dir <bare> <args>` and return the finished process (output captured, text or
        bytes per `text`). Side effect: starts a git subprocess."""
        return subprocess.run(
            ["git", "--git-dir", str(self.bare), *args], capture_output=True, text=text
        )

    def tip(self) -> str | None:
        """The commit sha at the tip of the main branch, or None if it cannot be resolved."""
        proc = self._git("rev-parse", VAULT_BRANCH)
        return proc.stdout.strip() if proc.returncode == 0 else None

    def blob(self, sha: str) -> bytes:
        """The raw bytes of the git blob `sha`; raises VaultError if git cannot read it."""
        proc = self._git("cat-file", "blob", sha, text=False)
        if proc.returncode != 0:
            raise VaultError(f"git cat-file blob {sha}: {proc.stderr.decode(errors='replace')}")
        return proc.stdout

    def bundles(self, commit: str) -> list[Bundle]:
        """List every bundle at `commit`, sorted by folder; raises VaultError if git fails.
        A bundle is any folder holding a manifest.json; its .md files are collected beside it."""
        proc = self._git("ls-tree", "-r", "-z", commit, text=False)
        if proc.returncode != 0:
            raise VaultError(f"git ls-tree {commit}: {proc.stderr.decode(errors='replace')}")
        manifests: dict[str, str] = {}
        bodies: dict[str, dict[str, str]] = {}
        # walk the NUL-separated tree listing: "<mode> <type> <sha>\t<path>" per entry; keep only
        # blobs, noting each folder's manifest sha and its .md file shas
        for entry in proc.stdout.split(b"\0"):
            if not entry:
                continue
            meta, _, raw_path = entry.partition(b"\t")
            fields = meta.split(b" ")
            if len(fields) != 3 or fields[1] != b"blob":
                continue
            path = raw_path.decode("utf-8")
            parent, _, name = path.rpartition("/")
            if not parent:
                continue  # the repo root holds .gitattributes, never a bundle
            if name == MANIFEST_NAME:
                manifests[parent] = fields[2].decode()
            elif name.endswith(".md") and name not in GENERATED_MD:
                bodies.setdefault(parent, {})[name] = fields[2].decode()
        # one Bundle per folder that has a manifest; md_blob is set only when there is exactly one .md
        found = []
        for parent in sorted(manifests):
            names = tuple(sorted(bodies.get(parent, {})))
            found.append(
                Bundle(
                    note=parent,
                    manifest_blob=manifests[parent],
                    md_names=names,
                    md_blob=bodies[parent][names[0]] if len(names) == 1 else None,
                )
            )
        return found
