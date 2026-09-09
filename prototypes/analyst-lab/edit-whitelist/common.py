"""Shared loaders for the edit-whitelist prototype (quarantined: prototypes/README.md).

Reads the held DDIA bundle READ-ONLY and rebuilds the analyst's 492 chunks exactly as
analyst.process does (fence -> _chunks). Nothing here is imported by the pipeline.
"""
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
WC = REPO / "windows-converter"
sys.path.insert(0, str(WC))
os.environ.setdefault("FP_PIPELINE", str(pathlib.Path(os.environ.get("TEMP", ".")) / "edit-whitelist-quarantine"))

import analyst  # noqa: E402
import fidelity_audit as fa  # noqa: E402
import text_norm as tn  # noqa: E402

LIB = pathlib.Path(r"C:\Users\Bndit\ml\library")
HELD = LIB / "held" / "fc1f068c3a8eeb63"
PDF = (LIB / "drop" / "done" /
       "Designing Data-Intensive Applications_ The Big Ideas Behind -- Martin Kleppmann, "
       "Chris Riccomini -- 2, 2026 -- O'Reilly Media, Incorporated -- isbn13 9781098119065 --.pdf")


def load_bundle(held: pathlib.Path = HELD) -> dict:
    manifest = json.loads((held / "manifest.json").read_text(encoding="utf-8"))
    sidecar_path = held / manifest["marker_body"]["file"]
    sidecar_text = sidecar_path.read_text(encoding="utf-8")
    md_path = next(p for p in held.glob("*.md"))
    shipped_md = md_path.read_text(encoding="utf-8")
    parts = shipped_md.split("---\n", 2)
    shipped_body = parts[2] if len(parts) == 3 else shipped_md
    fenced_in, embeds = analyst.fence(sidecar_text)
    chunks_in = analyst._chunks(fenced_in)
    return {
        "manifest": manifest,
        "sidecar_path": sidecar_path,
        "sidecar_text": sidecar_text,
        "md_path": md_path,
        "shipped_md": shipped_md,
        "frontmatter": parts[1] if len(parts) == 3 else "",
        "shipped_body": shipped_body,
        "fenced_in": fenced_in,
        "embeds": embeds,
        "chunks_in": chunks_in,
        "chunk_scores": {r["i"]: r for r in manifest["analyst"]["chunk_scores"]},
    }


def ladder(text: str) -> str:
    """The shipped j32a-v2 ladder, exactly as audit_analyst applies it."""
    return tn.punct_free(tn.unescape(tn.prepare_output(text)))
