"""Tripwires for J24 — the block-record sidecar (signed Rab 2026-09-01).

Run with the marker-env interpreter (convert_and_ship imports pymupdf at module level;
marker_blocks itself needs nothing but stdlib until main() runs):
  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe marker_blocks_selftest.py

No GPU, no real marker package, no real PDF, no `.gpu-lock` interaction — every marker
invocation here is either a pure-function call on synthetic block records, a monkeypatched
`_run_marker` stub (convert_and_ship's own established pattern), or a fully faked `marker`
package installed into sys.modules so `marker_blocks.main()` can run its real control flow
end to end. FP_PIPELINE is pointed at a temp dir BEFORE import so every fp_paths root lands
in quarantine (SYM-010: never the live dirs), exactly as convert_and_ship_selftest.py does.

Each tripwire names what breaks if it fires:
  B1  absolute page correction     — a block reports its position WITHIN a slice (page 0)
                                      instead of its corrected ABSOLUTE book page (800); the
                                      decoy is watched failing and then restored (see below)
  B2  merge is plain concatenation — merging per-slice records renumbers or drops the already-
                                      absolute page instead of a pure concatenation, and the
                                      merge is honest when fewer slices contributed than exist
  B3  resume contributes blocks    — a resumed (cached) slice's blocks reach the merged book
                                      file with ZERO calls to the GPU-shaped `_run_marker`;
                                      negative control: breaking identity-match must force the
                                      call back on, or the "zero GPU calls" claim is untested
  B4  markdown byte-identity       — marker_blocks.main()'s own control flow: the block pass
                                      succeeding, failing, or being skipped must never change
                                      one byte of the markdown save_output already wrote, and
                                      must always return 0 (never fail the book)
  B5  degrade-to-today (wiring)    — convert_and_ship._convert_chunked / _attach_blocks_safe:
                                      a pre-J24 cached slice, a chunk-render fault, or zero
                                      blocks anywhere all degrade to something byte-for-byte a
                                      pre-J24 bundle, never raising and never lying about
                                      completeness
  B6  split-slice blocks merge     — a stall-recovery split's two halves fold into ONE file at
                                      the parent slice's path, honest about a half that
                                      produced none
  B7  argv fidelity / kill switch  — FP_BLOCKS=off reproduces the pre-J24 marker_single.exe
                                      argv byte-for-byte; the blocks-enabled argv's marker-
                                      facing tail is identical either way
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).parent
QUARANTINE = Path(tempfile.mkdtemp(prefix="fp-j24-selftest-"))
os.environ["FP_PIPELINE"] = str(QUARANTINE)
# The simple fake convert_and_ship_selftest.py itself uses — enough for every test EXCEPT
# B4, which needs the full marker package surface and installs its own (and restores nothing
# after, by design: B4 runs last, see the section marker below).
sys.modules.setdefault("marker", types.SimpleNamespace(__version__="test"))
sys.path.insert(0, str(HERE))

import marker_blocks  # noqa: E402  stdlib-only until main() runs — safe to import directly
import convert_and_ship as cas  # noqa: E402  (env must be set first)

FAILURES: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def blk(page_id: str, html: str, raw_page, images: dict | None = None) -> dict:
    """One synthetic FlatBlockOutput-shaped dict, the input normalize_chunk_payload consumes."""
    return {"id": page_id, "block_type": "Text", "html": html, "page": raw_page,
            "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]], "bbox": [0, 0, 1, 1],
            "section_hierarchy": {}, "images": images or {}}


def block_record(blocks: list[dict], *, source: str, slices_total: int = 1) -> dict:
    """normalize_chunk_payload's output, then stamped with the slice-completeness fields main()
    and _convert_chunked add afterward — mirrors production usage exactly (see marker_blocks.py
    main() and convert_and_ship.py's _one/_attach_blocks_safe path)."""
    rec = marker_blocks.normalize_chunk_payload({"blocks": blocks, "page_info": {}}, source=source)
    rec["slices_total"] = slices_total
    rec["slices_with_blocks"] = 1
    rec["complete"] = rec["page_unresolved"] == 0
    return rec


class EmitRecorder:
    def __init__(self):
        self.events = []

    def __call__(self, stage, event, **fields):
        self.events.append((f"{stage}/{event}", fields))

    def named(self, key):
        return [f for k, f in self.events if k == key]


REAL_RUN_MARKER = cas._run_marker
REAL_DONE_MISMATCH = cas._done_identity_mismatch


# ============================================================================================
# B1 — absolute page correction, WITH THE PLANTED DECOY (constraint 2's exact failure mode)
# ============================================================================================
print("B1 absolute page correction (decoy: slice-relative page 0 for the book's true page 800)")

# A book sliced at SLICE_PAGES=200 puts absolute pages 800-999 in the 5th slice
# (--page_range 800-999). marker/builders/document.py stores page_id=p (the ABSOLUTE value
# from the parsed --page_range), so the block id marker ACTUALLY emits for the first block on
# that slice's first page is "/page/800/...". A block-id-index bug that reads the LAST segment
# instead of the id's own page segment [2] — the *exact same shape of defect* the module
# docstring documents in marker's real `json_to_chunks` (page 12 == 2 (2 == 0), = "0", not
# "800") — is precisely "a slice reporting its own page 0 for the book's page 800": the block
# counter that happens to be 0 for the first block on a page.
FIRST_BLOCK_ID = "/page/800/Text/0"     # book's TRUE absolute page: 800
SECOND_BLOCK_ID = "/page/999/Text/3"    # book's TRUE absolute page: 999
DECOY_FIRST = 0    # what int(id.split("/")[-1]) gives for FIRST_BLOCK_ID — the planted decoy
DECOY_SECOND = 3   # same wrong read for SECOND_BLOCK_ID
assert int(FIRST_BLOCK_ID.split("/")[-1]) == DECOY_FIRST, "decoy value must be independently true"
assert int(SECOND_BLOCK_ID.split("/")[-1]) == DECOY_SECOND, "decoy value must be independently true"

raw_payload_800 = {
    "blocks": [blk(FIRST_BLOCK_ID, "<p>slice start</p>", raw_page=47),
               blk(SECOND_BLOCK_ID, "<p>slice end</p>", raw_page=5)],
    "page_info": {"800": {}, "999": {}},
}


def _b1_check(record: dict) -> bool:
    p0, p1 = record["blocks"][0]["page"], record["blocks"][1]["page"]
    return (p0 == 800 and p0 != DECOY_FIRST
            and p1 == 999 and p1 != DECOY_SECOND
            and record["page_min"] == 800 and record["page_max"] == 999)


record_correct = marker_blocks.normalize_chunk_payload(raw_payload_800, source="slice5.blocks.json")
check(_b1_check(record_correct),
      f"true absolute pages 800/999 kept, decoy 0/3 rejected (got {record_correct['blocks'][0]['page']}"
      f"/{record_correct['blocks'][1]['page']}, page_min={record_correct['page_min']}, "
      f"page_max={record_correct['page_max']})")
check(record_correct["page_field_raw_disagreements"] == 2,
      "both blocks' raw shipped `page` field disagreed with the correction (expected: always, "
      "on marker-pdf 1.10.2)")

# ---- WATCH IT FAIL: swap in the wrong-shape implementation, confirm the SAME check goes RED ----
print("  [watched-failing] swapping in the last-segment bug (marker's own real defect shape)")


def _wrong_last_segment(block_id):
    parts = str(block_id).split("/")
    if len(parts) < 3 or parts[1] != "page":
        return None
    try:
        return int(parts[-1])
    except (TypeError, ValueError):
        return None


real_absolute_page_from_block_id = marker_blocks.absolute_page_from_block_id
marker_blocks.absolute_page_from_block_id = _wrong_last_segment
record_broken = marker_blocks.normalize_chunk_payload(raw_payload_800, source="slice5.blocks.json")
broken_result = _b1_check(record_broken)
print(f"    broken implementation: block[0].page={record_broken['blocks'][0]['page']} "
      f"block[1].page={record_broken['blocks'][1]['page']} page_min={record_broken['page_min']} "
      f"page_max={record_broken['page_max']}  -> _b1_check = {broken_result}")
print(f"    RED: {'the property fired as broken, exactly as expected' if not broken_result else 'DID NOT FIRE — the decoy is a tautology, this selftest is worthless'}")
marker_blocks.absolute_page_from_block_id = real_absolute_page_from_block_id  # restore
check(not broken_result,
      "watched failing: the last-segment bug DOES make the check go red (not a tautology)")
record_restored = marker_blocks.normalize_chunk_payload(raw_payload_800, source="slice5.blocks.json")
check(_b1_check(record_restored), "restored implementation is green again")


# ============================================================================================
# B2 — merge is plain concatenation across slices; honest about partial coverage
# ============================================================================================
print("B2 merge_block_files: plain concatenation, no offset table, honest completeness")
merge_dir = QUARANTINE / "b2"
merge_dir.mkdir(parents=True, exist_ok=True)
slice0_rec = block_record([blk("/page/5/Text/0", "<p>early</p>", raw_page=99)],
                          source="slice0.blocks.json")
slice4_rec = block_record([blk(FIRST_BLOCK_ID, "<p>late</p>", raw_page=47),
                           blk(SECOND_BLOCK_ID, "<p>later</p>", raw_page=5)],
                          source="slice4.blocks.json")
f0 = merge_dir / "s0.json"
f4 = merge_dir / "s4.json"
f0.write_text(json.dumps(slice0_rec), encoding="utf-8")
f4.write_text(json.dumps(slice4_rec), encoding="utf-8")

# Only 2 of a hypothetical 5-slice book's files are given — merge must ADMIT it is partial.
dest_partial = merge_dir / "merged-partial.json"
summary_partial = marker_blocks.merge_block_files([f0, f4], dest_partial, slices_total=5)
merged_partial = json.loads(dest_partial.read_text(encoding="utf-8"))
pages_seen = {b["page"] for b in merged_partial["blocks"]}
check(pages_seen == {5, 800, 999},
      f"absolute pages from BOTH slices present with NO renumbering (got {sorted(pages_seen)})")
check(summary_partial["slices_with_blocks"] == 2 and summary_partial["slices_total"] == 5,
      "denominator is the BOOK's slice count (5), not the number of files handed in (2)")
check(summary_partial["complete"] is False,
      "2 of 5 slices -> complete=False, said out loud (SYM-053's disease, one level up)")

# All slices given -> complete=True.
dest_full = merge_dir / "merged-full.json"
summary_full = marker_blocks.merge_block_files([f0, f4], dest_full, slices_total=2)
check(summary_full["complete"] is True, "2 of 2 slices given -> complete=True")

# An unreadable / wrong-schema file is named, not silently dropped.
bad = merge_dir / "corrupt.json"
bad.write_text("{not json", encoding="utf-8")
wrong_schema = merge_dir / "wrong-schema.json"
wrong_schema.write_text(json.dumps({"schema": 999, "blocks": []}), encoding="utf-8")
dest_bad = merge_dir / "merged-with-bad.json"
summary_bad = marker_blocks.merge_block_files([f0, bad, wrong_schema], dest_bad, slices_total=3)
check(summary_bad["slices_with_blocks"] == 1 and summary_bad["complete"] is False,
      "unreadable + wrong-schema files contribute nothing, and their absence is visible")
check(summary_bad.get("unreadable") and len(summary_bad["unreadable"]) == 2,
      "both faulty files are NAMED (corrupt.json, wrong-schema.json), not swallowed silently")


# ============================================================================================
# B3 — resume contributes blocks with ZERO GPU calls, plus a negative control
# ============================================================================================
print("B3 resume contributes blocks WITHOUT a GPU run (+ negative control)")

cas.CHUNK_BATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
cas.CHUNK_BATCH_FILE.write_text("8\n", encoding="utf-8")


class BlocksMarkerStub:
    """Like convert_and_ship_selftest.py's MarkerStub, but can also materialize a
    `<engine_stem>.blocks.json` inside out_dir for chosen page ranges — exactly what
    marker_blocks.main() writes on a successful chunk render. Unlisted ranges get NO blocks
    file (mirrors marker_single.exe / FP_BLOCKS=off / a chunk-render fault)."""

    def __init__(self, blocks_per_range: dict | None = None, wall: float = 50.0):
        self.blocks_per_range = blocks_per_range or {}
        self.wall = wall
        self.calls: list[str] = []

    def __call__(self, engine_src, engine_stem, out_root, extra, pages, source_name,
                 page_range=None, progress_prefix="", progress_context=None):
        self.calls.append(page_range)
        out_dir = Path(out_root) / engine_stem
        out_dir.mkdir(parents=True, exist_ok=True)
        rec = self.blocks_per_range.get(page_range)
        if rec is not None:
            (out_dir / f"{engine_stem}{marker_blocks.BLOCKS_SUFFIX}").write_text(
                json.dumps(rec), encoding="utf-8")
        return out_dir, f"[md {page_range}]", self.wall, 4321


extra_b3 = ["--recognition_batch_size", "8"]
sha_b3 = "b3" * 32
resumed_record = block_record([blk("/page/5/Text/0", "<p>resumed</p>", raw_page=999)],
                              source="resumed.blocks.json")
fresh_record = block_record([blk("/page/250/Text/0", "<p>fresh</p>", raw_page=1)],
                            source="fresh.blocks.json")

seed_dir = cas.CHUNK_WORK / sha_b3[:16] / "slice-00000-00199"
seed_dir.mkdir(parents=True, exist_ok=True)
(seed_dir / "slice.md").write_text("[cached resumed slice]", encoding="utf-8")
(seed_dir / "slice.blocks.json").write_text(json.dumps(resumed_record), encoding="utf-8")
(seed_dir / ".done").write_text(json.dumps({
    "source_sha256": sha_b3, "page_range": "0-199", "wall_s": 100.0, "batch": 8,
    "engine_args": list(extra_b3), "marker_version": "test",
    "blocks": True, "blocks_engine": "marker_blocks"}) + "\n", encoding="utf-8")

work_b3 = QUARANTINE / "b3-work"
work_b3.mkdir(parents=True, exist_ok=True)
stub_b3 = BlocksMarkerStub(blocks_per_range={"200-399": fresh_record})
cas._run_marker = stub_b3
cas.emit = EmitRecorder()
md_b3, assets_b3, wall_b3, peak_b3, chunking_b3, stats_b3 = cas._convert_chunked(
    "book.pdf", QUARANTINE / "book.pdf", "book", work_b3, work_b3 / "marker-out",
    extra_b3, 400, sha_b3)

check("0-199" not in stub_b3.calls,
      f"resumed slice: ZERO GPU (_run_marker) calls for its page range (calls={stub_b3.calls})")
check(stub_b3.calls == ["200-399"], "only the uncached slice reached the GPU-shaped stub")
check("blocks" in stats_b3 and stats_b3["blocks"]["slices_with_blocks"] == 2,
      "both slices contributed blocks -- one via GPU, one via the resume cache")
merged_b3 = json.loads(stats_b3["blocks_path"].read_text(encoding="utf-8"))
pages_b3 = {b["page"] for b in merged_b3["blocks"]}
check(5 in pages_b3,
      "the RESUMED slice's block (absolute page 5) reached the merged file with ZERO GPU calls")
check(250 in pages_b3, "the freshly-converted slice's block (absolute page 250) also merged")
check(stats_b3["blocks"]["complete"] is True, "both slices contributed -> complete=True")
check(md_b3 == "[cached resumed slice]\n\n[md 200-399]",
      "markdown itself: resumed text + fresh text, unaffected by blocks riding along")

# ---- negative control: break identity-matching, confirm the "resumed" slice DOES take a
# GPU call now -- proving the B3 claim above is a real, falsifiable property ----
print("  [negative control] forcing _done_identity_mismatch to ALWAYS mismatch")
cas._done_identity_mismatch = lambda *a, **k: ["forced-mismatch-for-negative-control"]
stub_neg = BlocksMarkerStub(blocks_per_range={"0-199": resumed_record, "200-399": fresh_record})
cas._run_marker = stub_neg
cas.emit = EmitRecorder()
cas._convert_chunked("book-neg.pdf", QUARANTINE / "book-neg.pdf", "bookneg",
                     QUARANTINE / "neg-work", QUARANTINE / "neg-work" / "marker-out",
                     extra_b3, 400, sha_b3)
print(f"    forced-stale identity -> GPU called for '0-199': {'0-199' in stub_neg.calls} "
      f"(expected True)")
cas._done_identity_mismatch = REAL_DONE_MISMATCH
check("0-199" in stub_neg.calls,
      "negative control: breaking identity-match DOES force a GPU call -- the resume guard "
      "can fail, so B3's pass above is meaningful, not a tautology")


# ============================================================================================
# B5 — degrade-to-today at the convert_and_ship.py wiring level
# ============================================================================================
print("B5 degrade-to-today: pre-J24 cached slice, and zero blocks anywhere")

# B5a: one slice cached BEFORE J24 existed (slice.md but NO slice.blocks.json) + one fresh
# slice WITH blocks -> partial, honestly reported, book still ships.
sha_b5a = "b5" * 32
seed_b5a = cas.CHUNK_WORK / sha_b5a[:16] / "slice-00000-00199"
seed_b5a.mkdir(parents=True, exist_ok=True)
(seed_b5a / "slice.md").write_text("[pre-J24 cached slice]", encoding="utf-8")
# deliberately NO slice.blocks.json -- this IS the pre-J24 cache shape
(seed_b5a / ".done").write_text(json.dumps({
    "source_sha256": sha_b5a, "page_range": "0-199", "wall_s": 90.0, "batch": 8,
    "engine_args": list(extra_b3), "marker_version": "test"}) + "\n", encoding="utf-8")
work_b5a = QUARANTINE / "b5a-work"
work_b5a.mkdir(parents=True, exist_ok=True)
stub_b5a = BlocksMarkerStub(blocks_per_range={"200-399": fresh_record})
cas._run_marker = stub_b5a
cas.emit = EmitRecorder()
md_b5a, _, _, _, _, stats_b5a = cas._convert_chunked(
    "book2.pdf", QUARANTINE / "book2.pdf", "book2", work_b5a, work_b5a / "marker-out",
    extra_b3, 400, sha_b5a)
check(stats_b5a["blocks"]["slices_with_blocks"] == 1,
      "only the fresh slice contributed blocks (the pre-J24 cached slice contributed none)")
check(stats_b5a["blocks"]["complete"] is False,
      "partial record admits it out loud instead of presenting a subset as the whole book")
check(stats_b5a["blocks"]["slices_total"] == 2,
      "denominator is the book's slice count, not the numerator of slices that happened to have blocks")
check(md_b5a == "[pre-J24 cached slice]\n\n[md 200-399]",
      "the book ships its full markdown regardless -- blocks degrading never costs the book")

# B5b: NEITHER slice has blocks (both pre-J24, or FP_BLOCKS=off for the whole run) -> stats
# carries NO "blocks" key at all: the bundle is byte-for-byte pre-J24 shaped.
sha_b5b = "b6" * 32
work_b5b = QUARANTINE / "b5b-work"
work_b5b.mkdir(parents=True, exist_ok=True)
stub_b5b = BlocksMarkerStub(blocks_per_range={})
cas._run_marker = stub_b5b
cas.emit = EmitRecorder()
md_b5b, _, _, _, _, stats_b5b = cas._convert_chunked(
    "book3.pdf", QUARANTINE / "book3.pdf", "book3", work_b5b, work_b5b / "marker-out",
    extra_b3, 400, sha_b5b)
check("blocks" not in stats_b5b,
      "zero blocks anywhere -> no 'blocks' key in stats at all (pre-J24 shape, not an empty one)")
check("blocks_path" not in stats_b5b, "and no blocks_path either")
check(md_b5b == "[md 0-199]\n\n[md 200-399]",
      "markdown is completely unaffected when blocks are entirely absent")

# _attach_blocks_safe: never raises, stamps the manifest honestly, degrades on any fault.
print("B5c _attach_blocks_safe: manifest stamping + fault tolerance")
tmp_ok = QUARANTINE / "attach-ok"
tmp_ok.mkdir(parents=True, exist_ok=True)
src_ok = QUARANTINE / "src-ok.json"
src_ok.write_text(json.dumps({"blocks": "payload"}), encoding="utf-8")
manifest_ok: dict = {}
rec_ok = EmitRecorder()
cas.emit = rec_ok
cas._attach_blocks_safe(tmp_ok, manifest_ok, {
    "blocks": {"blocks_total": 3, "pages_with_blocks": 2, "page_min": 1, "page_max": 2,
              "page_unresolved": 0, "slices_with_blocks": 1, "slices_total": 1,
              "complete": True}, "blocks_path": src_ok}, "book.pdf")
check((tmp_ok / cas.BLOCKS_BUNDLE_FILE).is_file(), "blocks.json copied into the bundle dir")
check(manifest_ok.get("blocks", {}).get("blocks_total") == 3, "manifest carries the summary")
check(manifest_ok["blocks"]["bytes"] == (tmp_ok / cas.BLOCKS_BUNDLE_FILE).stat().st_size,
      "bytes re-measured at the file's FINAL resting place, not assumed")
check(not rec_ok.named("convert/blocks_partial"), "a complete record fires no partial warning")

manifest_fault: dict = {}
tmp_fault = QUARANTINE / "attach-fault"
tmp_fault.mkdir(parents=True, exist_ok=True)
cas.emit = EmitRecorder()
try:
    cas._attach_blocks_safe(tmp_fault, manifest_fault,
                            {"blocks": {"blocks_total": 1}, "blocks_path": QUARANTINE / "missing.json"},
                            "book.pdf")
    raised = False
except Exception:
    raised = True
check(not raised, "_attach_blocks_safe never raises even when the source file has vanished")
check("blocks" not in manifest_fault, "manifest untouched on fault -- ships exactly pre-J24 shaped")

manifest_partial: dict = {}
tmp_partial = QUARANTINE / "attach-partial"
tmp_partial.mkdir(parents=True, exist_ok=True)
src_partial = QUARANTINE / "src-partial.json"
src_partial.write_text("{}", encoding="utf-8")
rec_partial = EmitRecorder()
cas.emit = rec_partial
cas._attach_blocks_safe(tmp_partial, manifest_partial, {
    "blocks": {"blocks_total": 1, "pages_with_blocks": 1, "page_min": 1, "page_max": 1,
              "page_unresolved": 5, "slices_with_blocks": 1, "slices_total": 3,
              "complete": False}, "blocks_path": src_partial}, "book.pdf")
check(bool(rec_partial.named("convert/blocks_partial")),
      "an incomplete record fires the honesty event out loud")


# ============================================================================================
# B6 — split-slice blocks fold into ONE file at the parent's path
# ============================================================================================
print("B6 split-slice blocks merge (stall-recovery path)")
out_root_b6 = QUARANTINE / "b6" / "marker-out"
left_path = cas._slice_blocks_path(out_root_b6, 0, 99, split_depth=1)
right_path = cas._slice_blocks_path(out_root_b6, 100, 199, split_depth=1)
left_path.parent.mkdir(parents=True, exist_ok=True)
left_rec = block_record([blk("/page/10/Text/0", "<p>left</p>", raw_page=1)], source="left")
left_path.write_text(json.dumps(left_rec), encoding="utf-8")
# right half deliberately MISSING first -- simulates that half's chunk render faulting
cas._merge_split_blocks(out_root_b6, 0, 99, 199, split_depth=0)
parent_path = cas._slice_blocks_path(out_root_b6, 0, 199, split_depth=0)
check(parent_path.is_file(), "parent slice's blocks file created even though only ONE half had blocks")
parent_rec = json.loads(parent_path.read_text(encoding="utf-8"))
check(parent_rec["slices_total"] == 2 and parent_rec["slices_with_blocks"] == 1,
      "half-blind split is honest: slices_total=2, slices_with_blocks=1")
check(parent_rec["complete"] is False, "a half missing its blocks makes the parent incomplete, out loud")
pages_parent = {b["page"] for b in parent_rec["blocks"]}
check(10 in pages_parent, "the surviving half's block (absolute page 10) merged into the parent")

right_rec = block_record([blk("/page/150/Text/0", "<p>right</p>", raw_page=1)], source="right")
right_path.write_text(json.dumps(right_rec), encoding="utf-8")
cas._merge_split_blocks(out_root_b6, 0, 99, 199, split_depth=0)
parent_rec2 = json.loads(parent_path.read_text(encoding="utf-8"))
check(parent_rec2["slices_with_blocks"] == 2 and parent_rec2["complete"] is True,
      "both halves present -> complete=True")
pages_parent2 = {b["page"] for b in parent_rec2["blocks"]}
check(10 in pages_parent2 and 150 in pages_parent2,
      "both halves' ABSOLUTE pages present (10, 150) -- no renumbering across the split")

# neither half has blocks -> no phantom parent file
dest_empty = cas._slice_blocks_path(out_root_b6, 500, 599, split_depth=0)
dest_empty.unlink(missing_ok=True)
cas._merge_split_blocks(out_root_b6, 500, 549, 599, split_depth=0)
check(not dest_empty.exists(), "neither half had blocks -> no phantom parent file, and no raise")


# ============================================================================================
# B7 — argv fidelity + the FP_BLOCKS=off kill switch
# ============================================================================================
print("B7 argv fidelity: FP_BLOCKS=off reproduces the pre-J24 argv byte-for-byte")
check(cas.MARKER_BLOCKS.is_file(), "the sidecar file exists on disk (required for the flag to matter)")
check(cas.MARKER_PYTHON.is_file(), "the marker-env interpreter exists at the derived path")
os.environ.pop(cas.BLOCKS_ENV, None)
common = ["--recognition_batch_size", "8"]
argv_on = cas._marker_argv(Path("some.pdf"), Path("outdir"), common, None)
os.environ[cas.BLOCKS_ENV] = "off"
argv_off = cas._marker_argv(Path("some.pdf"), Path("outdir"), common, None)
os.environ.pop(cas.BLOCKS_ENV, None)
expected_off = [str(cas.MARKER), "some.pdf", "--output_dir", "outdir",
               "--output_format", "markdown", "--recognition_batch_size", "8"]
check(argv_off == expected_off,
      f"FP_BLOCKS=off: argv is BYTE-FOR-BYTE the pre-J24 marker_single.exe invocation "
      f"(got {argv_off})")
check(argv_on[-6:] == argv_off[-6:],
      "the marker-facing argv tail (constraint 4's actual input) is IDENTICAL on vs off")
check(argv_on[0] == str(cas.MARKER_PYTHON) and argv_on[2] == str(cas.MARKER_BLOCKS),
      "blocks-enabled argv runs the sidecar under the SAME interpreter marker_single.exe wraps")

cas._run_marker = REAL_RUN_MARKER
cas._done_identity_mismatch = REAL_DONE_MISMATCH


# ============================================================================================
# B4 — marker_blocks.main() end to end: markdown byte-identity + degrade, via a fully faked
# `marker` package (installed LAST: it overwrites sys.modules["marker"] and its submodules,
# which the cas-based sections above depend on in their simpler form)
# ============================================================================================
print("B4 markdown byte-identity across block-pass success / failure / skip (main())")


class FakeDocument:
    def __init__(self, n):
        self.pages = list(range(n))


class FakeRendered:
    def __init__(self, text):
        self.markdown = text


class FakeChunkOutput:
    def __init__(self, payload):
        self._payload = payload

    def model_dump_json(self, exclude=None):
        return json.dumps(self._payload)


class FakeConverter:
    def __init__(self, config, artifact_dict, processor_list, renderer, llm_service, control):
        self.renderer = renderer
        self.control = control
        self.page_count = 0

    def filepath_to_str(self, fpath):
        return contextlib.nullcontext(fpath)

    def build_document(self, temp_path):
        return FakeDocument(self.control["pages"])

    def resolve_dependencies(self, target):
        control = self.control

        def _call(document):
            if target is control["ChunkRenderer"]:
                if control.get("chunk_raises") is not None:
                    raise control["chunk_raises"]
                return FakeChunkOutput(control["chunk_payload"])
            # Any other target is the TOP-LEVEL render (marker_blocks.py always renders
            # `converter.renderer`, whatever ConfigParser selected — MarkdownRenderer in
            # scenarios A/B, any other renderer in scenario C). It always yields the SAME
            # text: that identity is exactly the property under test.
            return FakeRendered(control["markdown_text"])

        return _call


class FakeConfigParser:
    def __init__(self, kwargs, control):
        self.control = control

    def get_converter_cls(self):
        control = self.control
        return lambda **kw: FakeConverter(control=control, **kw)

    def generate_config_dict(self):
        return {}

    def get_processors(self):
        return []

    def get_renderer(self):
        return self.control["renderer_cls"]

    def get_llm_service(self):
        return None

    def get_output_folder(self, fpath):
        return str(self.control["out_dir"])

    def get_base_filename(self, fpath):
        return self.control["fname_base"]


class FakeCtx:
    def __init__(self, params):
        self.params = params


def install_fake_marker(control: dict) -> dict:
    def mk(name):
        m = types.ModuleType(name)
        sys.modules[name] = m
        return m

    marker_mod = mk("marker")
    config_mod = mk("marker.config")
    config_parser_mod = mk("marker.config.parser")
    logger_mod = mk("marker.logger")
    models_mod = mk("marker.models")
    output_mod = mk("marker.output")
    scripts_mod = mk("marker.scripts")
    convert_single_mod = mk("marker.scripts.convert_single")
    renderers_mod = mk("marker.renderers")
    chunk_mod = mk("marker.renderers.chunk")
    markdown_mod = mk("marker.renderers.markdown")
    settings_mod = mk("marker.settings")

    marker_mod.__version__ = "fake-test"
    marker_mod.config, marker_mod.logger, marker_mod.models = config_mod, logger_mod, models_mod
    marker_mod.output, marker_mod.scripts, marker_mod.renderers = output_mod, scripts_mod, renderers_mod
    marker_mod.settings = settings_mod
    config_mod.parser = config_parser_mod
    scripts_mod.convert_single = convert_single_mod
    renderers_mod.chunk, renderers_mod.markdown = chunk_mod, markdown_mod

    config_parser_mod.ConfigParser = lambda kwargs: FakeConfigParser(kwargs, control)
    logger_mod.configure_logging = lambda: None
    models_mod.create_model_dict = lambda: {}

    def _save_output(rendered, out_folder, fname_base):
        control.setdefault("save_output_calls", []).append(rendered.markdown)
        p = Path(out_folder)
        p.mkdir(parents=True, exist_ok=True)
        (p / (fname_base + ".md")).write_text(rendered.markdown, encoding="utf-8")

    output_mod.save_output = _save_output

    class _CLI:
        @staticmethod
        def make_context(prog_name, argv):
            return FakeCtx({"fpath": argv[0]})

    convert_single_mod.convert_single_cli = _CLI

    class MarkdownRenderer:
        pass

    class ChunkRenderer:
        pass

    markdown_mod.MarkdownRenderer = MarkdownRenderer
    chunk_mod.ChunkRenderer = ChunkRenderer
    control["MarkdownRenderer"] = MarkdownRenderer
    control["ChunkRenderer"] = ChunkRenderer
    control.setdefault("renderer_cls", MarkdownRenderer)

    class _Settings:
        OUTPUT_IMAGE_FORMAT = "JPEG"

    settings_mod.settings = _Settings()
    return control


control = {"pages": 2, "out_dir": QUARANTINE / "b4" / "run-a", "fname_base": "book",
          "markdown_text": "# Chapter\n\nSame text either way.\n",
          "chunk_payload": {"blocks": [{"id": "/page/0/Text/0", "block_type": "Text",
                                        "html": "<p>x</p>", "page": 9, "polygon": [], "bbox": [],
                                        "section_hierarchy": {}, "images": {}}],
                            "page_info": {"0": {}}},
          "chunk_raises": None}
install_fake_marker(control)

# Scenario A: chunk render succeeds.
argv_a = ["book.pdf", "--output_dir", str(control["out_dir"]), "--output_format", "markdown"]
rc_a = marker_blocks.main(argv_a)
md_a = (control["out_dir"] / "book.md").read_text(encoding="utf-8")
blocks_a = control["out_dir"] / "book.blocks.json"
check(rc_a == 0, "successful run returns 0")
check(md_a == control["markdown_text"], "markdown on disk matches exactly what save_output wrote")
check(blocks_a.is_file(), "blocks file written on a successful chunk render")

# Scenario B: chunk render RAISES. Same markdown_text, fresh out_dir.
control["out_dir"] = QUARANTINE / "b4" / "run-b"
control["chunk_raises"] = RuntimeError("simulated chunk renderer fault")
argv_b = ["book.pdf", "--output_dir", str(control["out_dir"]), "--output_format", "markdown"]
rc_b = marker_blocks.main(argv_b)
md_b = (control["out_dir"] / "book.md").read_text(encoding="utf-8")
blocks_b = control["out_dir"] / "book.blocks.json"
check(rc_b == 0, "a block-pass FAULT still returns 0 -- the book must not fail because of it")
check(md_b == control["markdown_text"], "markdown is UNCHANGED when the block pass fails")
check(md_b == md_a, "byte-identical markdown whether the block pass succeeds or fails")
check(not blocks_b.is_file(), "no (half-written) blocks file when the chunk render faults")

# Scenario C: renderer requested isn't MarkdownRenderer -> blocks lane skipped entirely.
control["out_dir"] = QUARANTINE / "b4" / "run-c"
control["chunk_raises"] = None


class OtherRenderer:
    pass


control["renderer_cls"] = OtherRenderer
argv_c = ["book.pdf", "--output_dir", str(control["out_dir"]), "--output_format", "html"]
rc_c = marker_blocks.main(argv_c)
md_c = (control["out_dir"] / "book.md").read_text(encoding="utf-8")
check(rc_c == 0, "non-markdown renderer path also returns 0")
check(md_c == control["markdown_text"],
      "markdown still written and unaffected when the requested renderer isn't MarkdownRenderer")
check(not (control["out_dir"] / "book.blocks.json").is_file(),
      "no blocks file when the renderer isn't markdown (only lane wired for this)")

# ---- watched failing: a structural regression guard on the SOURCE that guarantees B4 in
# production, not merely in this fake -- save_output must precede any block-render attempt ----
print("  [watched-failing] structural guard: save_output must precede the chunk render in source")
src_mb = (HERE / "marker_blocks.py").read_text(encoding="utf-8")
save_idx = src_mb.index("save_output(rendered")
chunk_idx = src_mb.index("ChunkRenderer)(document)")
check(save_idx < chunk_idx,
      "save_output call precedes the chunk-render call in marker_blocks.py's source order")


def _order_ok(text: str) -> bool:
    return text.index("save_output(rendered") < text.index("ChunkRenderer)(document)")


# Decoy: a genuinely reordered sample (chunk render's token appears FIRST in the text) run
# through the identical index-comparison the guard above uses on the real file.
broken_order_sample = ("chunk = converter.resolve_dependencies(ChunkRenderer)(document)\n"
                       "...\nsave_output(rendered, out_folder, fname_base)\n")
correct_order_sample = ("save_output(rendered, out_folder, fname_base)\n...\n"
                        "chunk = converter.resolve_dependencies(ChunkRenderer)(document)\n")
print(f"    broken-order sample -> guard reads: "
      f"{'RED' if not _order_ok(broken_order_sample) else 'GREEN'} (expected RED)")
check(not _order_ok(broken_order_sample),
      "the structural guard DOES flag a genuinely reordered sample -- not a tautology")
check(_order_ok(correct_order_sample), "and passes a correctly-ordered sample")


# ---------- verdict ----------
shutil.rmtree(QUARANTINE, ignore_errors=True)
n_checks = len(__import__("re").findall(r"^\s*check\(", Path(__file__).read_text(encoding="utf-8"),
                                        __import__("re").M))
total = len(FAILURES)
print(f"\n{'RED: ' + str(total) + ' tripwire(s) fired' if FAILURES else 'GREEN'} "
      f"({n_checks - total}/{n_checks})")
if FAILURES:
    print("Failed:")
    for f in FAILURES:
        print(f"  - {f}")
sys.exit(1 if FAILURES else 0)
