"""Read-only view of the bare authoritative vault, `git --git-dir` only (fixity.py's idiom).

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

VAULT_BRANCH = "main"  # HEAD of the bare repo is pinned to refs/heads/main (Decision #4)
MANIFEST_NAME = "manifest.json"
# Generated reports that may sit beside the body but are never the body (repair-bench).
GENERATED_MD = frozenset({"REPAIRS.md"})


class VaultError(Exception):
    pass


@dataclass(frozen=True)
class Bundle:
    note: str  # repo-relative bundle dir, e.g. Inbox/<slug>--<sha8>
    manifest_blob: str
    md_names: tuple[str, ...]  # .md entries directly in the dir, generated reports excluded
    md_blob: str | None  # set only when exactly one .md is present

    @property
    def md_name(self) -> str | None:
        return self.md_names[0] if len(self.md_names) == 1 else None


class Vault:
    def __init__(self, bare: Path):
        self.bare = bare

    def exists(self) -> bool:
        return (self.bare / "HEAD").is_file()

    def _git(self, *args: str, text: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "--git-dir", str(self.bare), *args], capture_output=True, text=text
        )

    def tip(self) -> str | None:
        proc = self._git("rev-parse", VAULT_BRANCH)
        return proc.stdout.strip() if proc.returncode == 0 else None

    def blob(self, sha: str) -> bytes:
        proc = self._git("cat-file", "blob", sha, text=False)
        if proc.returncode != 0:
            raise VaultError(f"git cat-file blob {sha}: {proc.stderr.decode(errors='replace')}")
        return proc.stdout

    def bundles(self, commit: str) -> list[Bundle]:
        proc = self._git("ls-tree", "-r", "-z", commit, text=False)
        if proc.returncode != 0:
            raise VaultError(f"git ls-tree {commit}: {proc.stderr.decode(errors='replace')}")
        manifests: dict[str, str] = {}
        bodies: dict[str, dict[str, str]] = {}
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
