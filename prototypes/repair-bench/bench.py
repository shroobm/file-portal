#!/usr/bin/env python
"""THE REPAIR BENCH — Stage G prototype (docs/19 §7, docs/18 "the Repair Bench").

Rab's design, his words load-bearing: **"the human IS the vision model."** The audit can say
*where* a conversion went wrong (degeneration zones, omission runs) but not what the page
really held — the human can, in one glance at the source page. This bench puts the two side
by side: the source PDF page on the left, the markdown at the flagged zone on the right, and
makes the repair a single gesture — drag a rectangle on the page (or paste a screenshot) and
the crop lands in the bundle's `assets/` as `_repair_pN_k.png`, embedded at the zone with
`![[...]]` (the vault's own reference style), provenance-stamped into `manifest["repairs"]`.

QUARANTINE (prototypes/ convention): the pipeline never imports this; this imports only
`fidelity_audit` READ-ONLY for the re-score *preview*. The preview NEVER writes a fidelity
block or verdict — whether a repair image earns audit credit is an UNSIGNED policy question
that belongs to Rab (docs/19 §10: audit policy carries his signature).

Run:  python bench.py <bundle-dir | held-sha16> [--pdf X.pdf] [--sandbox] [--port 7077]
      --sandbox copies the bundle into .sandbox/ first and repairs the COPY — trial mode.

Stdlib + pymupdf (marker-env) only. Binds 127.0.0.1.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import difflib
import hashlib
import hmac
import os
import re
import shutil
import subprocess
import sys
import threading
import unicodedata
import urllib.parse
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
REPO = BENCH_DIR.parents[1]
HELD = Path(r"C:\Users\Bndit\ml\library\held")
DONE = Path(r"C:\Users\Bndit\ml\library\drop\done")
PENDING = Path(r"C:\Users\Bndit\ml\library\pending")
ANCHOR = Path(r"C:\Users\Bndit\ml\library\anchor")
# The picker (S66) may only open things inside these roots — server-side allowlist.
OPEN_ROOTS = (HELD, PENDING, ANCHOR, DONE, BENCH_DIR / ".sandbox")
RASTER_DPI = 140      # the browsing raster
CROP_DPI = 220        # repairs deserve more pixels than the browsing view
ASSET_RE = re.compile(r"^_repair_p(\d+)_(\d+)\.png$")
# S71 — the transcribe gesture (docs/23 built): granite-docling reads a crop into governed
# markdown. The model runs in ITS OWN env via a process-per-request worker — never in this
# interpreter (marker-env stays a production lane, not a lab bench).
DOCLING_PY = Path(r"C:\Users\Bndit\ml\docling-env\Scripts\python.exe")
TRANSCRIBE_WORKER = BENCH_DIR / "transcribe_worker.py"
TRANSCRIBE_DTYPE = "bf16"  # calibrated S71 (prototypes/docling-calibration/)
GPU_LOCK = Path(r"C:\Users\Bndit\ml\library\.gpu-lock")
# S76 — the COLLAPSE gesture (docs/27, signed by Rab 2026-08-14). A decoder token-loop
# ("the state of" x157) carries nothing past its first instance. These thresholds are
# MEASURED, not guessed: over the 117 substantial paragraphs of the S76 Beer the loop scored
# TTR 0.0147 and the cleanest legitimate prose 0.5190 — a 35x chasm with nothing in it.
# S76/docs/28 §4 — the five outcomes a located defect can reach. Three are DERIVED from
# provenance (the machine can see them); `dismissed-noise` is a human judgment and the only
# one an operator sets by hand — on a scan lane the witness is itself OCR, so a "loss" may be
# the converter correctly declining to reproduce garbage.
OUTCOMES = ("open", "collapsed", "image-restored", "text-restored", "dismissed-noise")
OUTCOMES_MANUAL = ("open", "dismissed-noise")
LEDGER_CONTEXT = 3         # S76/docs/28: lines of margin kept either side of a change
LEDGER_VERBATIM_MAX = 20000  # chars of changed text stored verbatim before truncating
TTR_LOOP_MAX = 0.10        # type-token ratio below this = a loop, not language
MIN_CYCLE_REPEATS = 8      # fewer repeats is emphasis or a refrain, not a stuck decoder
MAX_CYCLE_PERIOD = 12      # tokens; the longest cycle we are willing to call a loop


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def type_token_ratio(text: str) -> float:
    """Unique tokens / tokens. The acute loop signature (docs/27 §3) — more discriminating
    than zlib, which needs the trigram AND-gate to avoid firing on dense tables (a table
    repeats STRUCTURE but varies its WORDS, so its ratio stays high)."""
    toks = text.lower().split()
    if len(toks) < 5:                      # CJK / space-free block
        toks = list(re.sub(r"\s", "", text))
    return len(set(toks)) / len(toks) if toks else 1.0


def find_cycle(text: str):
    """The dominant CONSECUTIVE repetition, or None. Returns (period, first_tok, last_tok,
    repeats). Period is in tokens; the run is the maximal stretch where tok[i] == tok[i+p].
    Shortest period wins (ties break on coverage) so "the state of" is found rather than
    an accidental multiple of it."""
    toks = [m.group().lower() for m in re.finditer(r"\S+", text)]
    n = len(toks)
    if n < 20:
        return None
    best = None
    for p in range(1, MAX_CYCLE_PERIOD + 1):
        i = 0
        while i + p < n:
            if toks[i] != toks[i + p]:
                i += 1
                continue
            j = i
            while j + p < n and toks[j] == toks[j + p]:
                j += 1
            covered = j - i + p
            repeats = covered // p
            if repeats >= MIN_CYCLE_REPEATS and (
                    best is None or p < best[0] or (p == best[0] and covered > best[4])):
                best = (p, i, j + p - 1, repeats, covered)
            i = j + 1
    return best


def split_frontmatter(text: str) -> tuple[str, str]:
    """(frontmatter incl. fences, body). The audit scored the BODY, so every zone line number
    indexes body lines — same split idiom as convert_and_ship.apply_analyst."""
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            return "---\n" + parts[1] + "---\n", parts[2]
    return "", text


class Bench:
    """The testable core: all state + mutation, no HTTP. The acceptance harness drives this
    directly AND over the wire, so the logic is proven twice."""

    def __init__(self, bundle_dir: Path, pdf: Path | None = None, sandbox: bool = False):
        src_dir = Path(bundle_dir)
        if not src_dir.is_dir() and (HELD / str(bundle_dir)).is_dir():
            src_dir = HELD / str(bundle_dir)  # bare sha16 convenience
        if not src_dir.is_dir() and not (src_dir.is_file() and src_dir.suffix.lower() == ".pdf"):
            raise SystemExit(f"not a bundle dir or a PDF: {bundle_dir}")
        self.sandbox = bool(sandbox) and src_dir.is_dir()  # a bare PDF is read-only anyway
        if self.sandbox:
            dest = BENCH_DIR / ".sandbox" / f"{src_dir.name}--{datetime.now():%Y%m%d-%H%M%S}"
            dest.parent.mkdir(exist_ok=True)
            shutil.copytree(src_dir, dest)
            self.dir = dest
        else:
            self.dir = src_dir
        self.manifest_path = self.dir / "manifest.json"
        # S64 (folder mode, Rab: "ITS ONLY THE FOLDER THAT MATTERS"): any folder holding one
        # .md is benchable — anchor copies, pending cards, mid-conversions. No manifest means
        # no audit zones and no source lookup, and the bench says so instead of refusing.
        if self.manifest_path.is_file():
            self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        else:
            self.manifest = {}
        # S66 reader mode: a bare PDF (no bundle) opens honestly read-only — pages, contents,
        # search, ⌖-style browsing; no markdown, no repairs, no AI. self.md_path is None then,
        # and every write path guards on it.
        self.md_path: Path | None
        # REPAIRS.md is the ledger's final report (docs/28 §3), generated BESIDE the bundle — it
        # is an artifact about the body, never the body. Without this exclusion, declaring a
        # patient done makes that patient permanently un-openable on the bench: the scan below
        # demands exactly one .md and the report is the second. Found S79 by generating a report
        # and then trying to reopen the bundle. It had not bitten in production only because no
        # patient has been declared done yet — the real held Valentine still carries one .md.
        GENERATED_MD = {"REPAIRS.md"}
        mds = [p for p in self.dir.iterdir()
               if p.suffix == ".md" and p.name not in GENERATED_MD] if self.dir.is_dir() else []
        if self.dir.is_file() and self.dir.suffix.lower() == ".pdf":
            self.pdf_only = True
            self.md_path = None
            self.assets = None  # type: ignore[assignment]
            self.pdf = self.dir
            self.dir = self.dir.parent
            self._finish_init()
            return
        self.pdf_only = False
        if len(mds) != 1:
            raise SystemExit(f"expected exactly one .md in {self.dir}, found {len(mds)}")
        self.md_path = mds[0]
        self.assets = self.dir / "assets"
        self.assets.mkdir(exist_ok=True)
        # The source PDF: the caller's, or the pipeline's done-tray copy of manifest.source.
        self.pdf: Path | None = None
        cand = Path(pdf) if pdf else DONE / self.manifest.get("source", "")
        if cand and cand.is_file():
            self.pdf = cand
        self._finish_init()

    def _finish_init(self) -> None:
        self._doc = None
        self._bak_done = False
        # S62b (the Okular pass): lazy per-page text index + TOC + zone-location votes.
        self._texts: list[str] | None = None
        self._toc: list | None = None
        self._zone_loc: dict[int, dict] = {}
        # OK-7 (docs/49 §1 c7, signed 2026-08-30): per-page trim boxes, measured lazily.
        self._trim: dict[int, dict] = {}
        # OK-5 (signed 2026-08-31): the raster pane's text layer — per-page word rects,
        # lazy + LRU-bounded (a 1,377-pp book must never hold 1,377 pages of rects).
        self._textlayer: OrderedDict[int, dict] = OrderedDict()
        # OK-1 review fix (2026-08-30): a bare PDF's view identity, hashed once on demand.
        self._pdf_view_sha: str | None = None
        # OK-15 (signed 2026-08-31): read-only quarantine evidence. The report is held only
        # in this process; it is never written into a bundle or manifest under the S112 gate.
        self._ok15_report: dict | None = None
        self._ok15_lock = threading.Lock()
        self._page_labels: list[str | None] | None = None
        # S64: the AI assist's undo stack (body snapshots, newest last) + line-drift ledger so
        # zone anchors stay honest after an edit changes the line count below them.
        self._undo: list[str] = []
        self._ai_drift: list[tuple[int, int]] = []  # (edit start line, lines added - removed)

    # ---- read side --------------------------------------------------------------------------
    def body(self) -> str:
        if self.md_path is None:
            return ""
        return split_frontmatter(self.md_path.read_text(encoding="utf-8"))[1]

    def zones(self) -> list[dict]:
        det = (self.manifest.get("fidelity", {}).get("convert", {})
               .get("tripwires", {}).get("degeneration_detail", {}))
        return list(det.get("worst") or [])

    def runs(self) -> list[dict]:
        return list(self.manifest.get("fidelity", {}).get("convert", {}).get("runs") or [])

    # ── THE SIGNATURE BANK (S78 §8.5, signed by Rab 2026-08-14; built S79) ────────────────
    #
    # Rab: "any time a zone pops up, there needs to be given a reason of what's the issue, the
    # highlight of it and a comment that contains the solution… banked… to reduce latency
    # between decision making and editing." And the why: "new operators in the future would not
    # be able to discern critically without investigating the tool itself… the program should
    # already provide that."
    #
    # A zone arrives from the convert-time audit carrying MEASUREMENTS and no meaning. The bank
    # supplies the meaning — as an INFERENCE with its evidence attached, never as an observation.
    # `matched_on` is the load-bearing field: a diagnosis with no evidence is a label, and a
    # label is the proxy this project keeps mistaking for a property (docs/32).
    _BANK: list[dict] | None = None

    # Detector order is CONSEQUENCE order, never confidence order. F (the matrix) is checked
    # BEFORE A and D, which are the two that would tell an operator "the content is all present,
    # only its shape is wrong". On S78 that exact mis-ranking is what made 13 populated columns
    # look phantom: they carried 418 • marks, two cells were sampled, and the edit preceded the
    # look. A signature that has already cost real data outranks a tidier explanation.
    _ORDER = ("E", "C", "F", "B", "D", "A")

    @classmethod
    def _bank(cls) -> list[dict]:
        if cls._BANK is None:
            try:
                raw = (Path(__file__).parent / "signatures.json").read_text(encoding="utf-8")
                cls._BANK = json.loads(raw).get("signatures", [])
            except Exception:  # noqa: BLE001 — a missing bank degrades to unclassified, never crashes the bench
                cls._BANK = []
        return cls._BANK

    def _detect(self, rule: str, site: dict, win: list[str]) -> str | None:
        """Return the EVIDENCE that fired this rule, or None. Never a bare True: the operator
        is owed what the machine actually saw, in the same breath as the conclusion."""
        if rule == "degeneration":
            mx, zl = site.get("max_trigram") or 0, site.get("zlib")
            if mx >= 40:
                return f"max_trigram {mx} ≥ 40 — the audit's own threshold"
            if zl is not None and zl <= 0.20:
                return f"zlib {zl} ≤ 0.20 — the audit's own threshold"
            return None
        if rule == "embed_between_header_and_delimiter":
            for i, ln in enumerate(win):
                if ln.lstrip().startswith("![["):
                    prev = next((w for w in reversed(win[:i]) if w.strip()), "")
                    nxt = next((w for w in win[i + 1:] if w.strip()), "")
                    if prev.lstrip().startswith("|") and not re.match(r"^\s*\|[\s:|-]+\|\s*$", nxt):
                        return "an ![[…]] embed sits between a | header | row and its |---| delimiter"
            return None
        if rule == "bullet_matrix":
            worst = max((ln.count("•") for ln in win), default=0)
            if worst >= 3:
                # Evidence only. The interpretation lives in the entry and the caution — a
                # `matched_on` that argues its own case reads as a fragment wherever it is quoted.
                return f"a row carrying {worst} • marks, {sum(ln.count('•') for ln in win)} in this window"
            return None
        if rule == "one_letter_rows":
            run = 0
            for ln in win:
                s = ln.strip().strip("|").strip()
                if 1 <= len(s) <= 2 and s.isalpha():
                    run += 1
                    if run >= 3:
                        return f"{run}+ consecutive rows whose whole content is one character"
                else:
                    run = 0
            return None
        if rule == "row_merge":
            for ln in win:
                if ln.lstrip().startswith("|") and ln.count("<br>") >= 3:
                    return f"one table row carrying {ln.count('<br>')} <br> separators"
            return None
        if rule == "br_inside_cells":
            n = sum(1 for ln in win if ln.lstrip().startswith("|") and "<br>" in ln)
            if n:
                return f"{n} table row(s) with <br> inside a cell"
            return None
        return None

    def diagnose(self, site: dict, line: int | None = None) -> dict:
        """reason · highlight · solution for one damage site, from the bank. Every field here is
        rendered on the zone card (bench.html renderDiagnosis) — docs/29 §5.4: the commit that
        adds a projected field renders it in the same commit."""
        lines = self.body().split("\n")
        at = max(1, int(line or site.get("line") or 1)) - 1
        win = lines[max(0, at - 4): at + 12]
        bank = {s["id"]: s for s in self._bank()}
        hits = [(sid, bank[sid], ev) for sid in self._ORDER if sid in bank
                for ev in [self._detect(bank[sid].get("detect", ""), site, win)] if ev]
        if not hits:
            # An honest Unknown. Do NOT add a catch-all signature: a diagnosis that always
            # matches carries no information and would be the tautology of docs/32 rule 2.
            return {"signature": None, "name": "unclassified", "tag": "Unknown", "auto": "no",
                    "reason": "No banked signature matched this site.",
                    "highlight": "Read the markdown at the zone line beside the source page, and print every cell of any row before editing it.",
                    "solution": "Diagnose by hand, then add the signature to signatures.json so the next operator does not start cold. That is what the bank is for.",
                    "matched_on": "", "caution": "", "also": [], "cite": "S78 §8.5"}
        sid, s, ev = hits[0]
        # E is not a competing hypothesis for a zone — every member of `worst[]` IS a
        # degeneration block by construction, so E's detector has zero discriminating power
        # here and will almost always take the primary slot. That is correct (it is what the
        # audit MEASURED, hence `Observed`) but it would bury the specific structural findings
        # underneath it — including F, whose whole entry is a warning against the edit that
        # destroyed 418 • marks in S78. A secondary signature that has already cost data does
        # not get to be a footnote, so it is lifted into its own field the UI renders loudly.
        caution = ""
        if sid != "F" and any(h[0] == "F" for h in hits):
            f = next(h[1] for h in hits if h[0] == "F")
            fev = next(h[2] for h in hits if h[0] == "F")
            # Say what is on the page and what breaks — not which session learned it. Rab read
            # the first version of this line and asked "what the hell does this mean": it named
            # a signature letter and cited an incident, so only someone who had already read the
            # closeout could act on it. That is the failure the bank exists to prevent, printed
            # by the bank itself. `cite` carries the provenance; this carries the meaning.
            caution = (f"This site also looks like a GRID whose column headings were lost — {fev}. "
                       f"The blank-looking columns are not empty: each • is content, marking which "
                       f"source covers which row. The headings are printed sideways on the page and "
                       f"the converter could not read them. Count the marks and print the whole row "
                       f"before you delete anything here — sampling two cells is how thirteen "
                       f"populated columns once got removed as 'empty'.")
        return {"signature": sid, "name": s["name"], "tag": s.get("tag", "Inferred"),
                "reason": s["reason"], "highlight": s["highlight"], "solution": s["solution"],
                "auto": s.get("auto", ""), "matched_on": ev, "cite": s.get("cite", ""),
                "caution": caution, "also": [h[0] for h in hits[1:]]}

    def state(self) -> dict:
        body_lines = self.body().count("\n") + 1
        pages = int(self.manifest.get("pages") or 0)
        if not pages:
            # Folder mode: no manifest — the PDF itself (if present) is the page authority.
            try:
                pages = self.doc().page_count if self.pdf else 1
            except Exception:  # noqa: BLE001
                pages = 1
        det_md_lines = (self.manifest.get("fidelity", {}).get("convert", {})
                        .get("tripwires", {}).get("degeneration_detail", {}).get("md_lines"))
        md_lines = int(det_md_lines or body_lines)
        reps = self.manifest.get("repairs", [])
        runs = []
        for r in self.runs()[:40]:
            at = self._resolve_run_line(r)
            oc, why = self._outcome(self.run_key(r), at)
            runs.append({**r, "anchor_line": at, "key": self.run_key(r),
                         "outcome": oc, "outcome_reason": why,
                         "diagnosis": self.diagnose(r, at),
                         "repaired": at is not None
                         and any(rec.get("zone_line") == at for rec in reps)})
        zones = []
        for z in self.zones():
            guess = max(1, min(pages, round(z["line"] / md_lines * pages))) if md_lines else 1
            at, anchor = self._resolve_zone_line(z)
            zoc, zwhy = self._outcome(self.zone_key(z), z["line"])
            zones.append({**z, "page_guess": guess, "key": self.zone_key(z),
                          "outcome": zoc, "outcome_reason": zwhy,
                          "diagnosis": self.diagnose(z, at),
                          # the server is the ONE authority on line adjustment (insertions shift
                          # everything below them) — the UI never re-derives this
                          "adjusted_line": at,
                          "anchor": anchor,   # "excerpt" = found in the live body; "drift" = estimated
                          # S76: a collapse removes noise but restores nothing, so it is
                          # reported separately — calling it "repaired" would overclaim
                          "repaired": any(r.get("zone_line") == z["line"]
                                          and r.get("mode") != "collapse"
                                          for r in self.manifest.get("repairs", [])),
                          "collapsed": any(r.get("zone_line") == z["line"]
                                           and r.get("mode") == "collapse"
                                           for r in self.manifest.get("repairs", []))})
        return {
            "bundle": self.dir.name,
            "dir": str(self.dir),
            "sandbox": self.sandbox,
            "source": self.manifest.get("source"),
            "lane": self.manifest.get("lane"),
            "pages": pages,
            "md_lines": md_lines,
            "verdict": self.manifest.get("fidelity", {}).get("verdict"),
            "zones": zones,
            # S76 (SYM-026): omission runs are damage too — the audit located 18 on the Beer
            # while the chip row showed 2. Each gets an anchor_line where one can be found, so
            # a crop has somewhere to land; `repaired` uses the same zone_line key the repair
            # records already carry.
            "runs": runs,
            "repairs": self.manifest.get("repairs", []),
            "pdf_available": self.pdf is not None,
            "pdf": str(self.pdf) if self.pdf else None,
            "manifest_present": self.manifest_path.is_file(),
            "undo_depth": self.undo_depth(),   # docs/28: ledger-derived, survives a restart
            # S66 accuracy pass — everything the info popover states, straight from source:
            "pdf_only": self.pdf_only,
            "md_name": self.md_path.name if self.md_path else None,
            # OK-1: the client keys per-book view state on this. Reader mode derives one
            # from the PDF bytes — review 2026-08-30: without it every bare PDF in one
            # folder shared a single view store (marks/position/trim cross-pollution).
            "source_sha16": (self.manifest.get("source_sha256") or "")[:16]
                            or self._pdf_view_id(),
            "page_labels": self.page_labels(),
            "doc_survival": (self.manifest.get("fidelity", {}).get("convert", {})
                             .get("doc_survival")),
            "audit_kind": self.manifest.get("fidelity", {}).get("convert", {}).get("kind"),
            "converted_at": self.manifest.get("converted_at"),
        }

    def _pdf_view_id(self) -> str | None:
        """OK-1 (review fix): a stable identity for reader-mode books — sha256 of the PDF
        bytes, first 16 hex, computed once per open and cached. None outside pdf_only."""
        if not (self.pdf_only and self.pdf and self.pdf.is_file()):
            return None
        return self._pdf_sha256()[:16]

    def _pdf_sha256(self) -> str:
        """Actual opened PDF identity, cached; never trust a bundle name as evidence."""
        if not (self.pdf and self.pdf.is_file()):
            raise RuntimeError("no source PDF on the bench")
        if self._pdf_view_sha is None:
            h = hashlib.sha256()
            with self.pdf.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            self._pdf_view_sha = h.hexdigest()
        return self._pdf_view_sha

    def page_labels(self) -> list[str | None]:
        """Physical page index -> logical PDF label (i, ii, 1, ...), read-only and cached."""
        if self.pdf is None:
            return []
        if self._page_labels is None:
            labels: list[str | None] = []
            try:
                page_count = self.doc().page_count
            except Exception:  # noqa: BLE001 - identity-only harnesses may use non-PDF bytes
                self._page_labels = []
                return self._page_labels
            for index in range(page_count):
                try:
                    labels.append(self.doc().load_page(index).get_label() or str(index + 1))
                except Exception:  # noqa: BLE001 - a missing label is UNREAD, not ordinal 0
                    labels.append(None)
            self._page_labels = labels
        return self._page_labels

    def ok15_evidence(self) -> dict:
        """Run the signed OK-15 probe once, retaining its report only in process memory."""
        if self.pdf is None:
            raise RuntimeError("no source PDF on the bench")
        actual = self._pdf_sha256()
        expected = str(self.manifest.get("source_sha256") or "").lower()
        if expected and expected != actual:
            raise RuntimeError(
                f"source identity mismatch: manifest {expected[:16]} != opened PDF {actual[:16]}"
            )
        if self._ok15_report is None:
            with self._ok15_lock:
                if self._ok15_report is None:
                    self._ok15_report = self._collect_ok15_evidence(actual)
        return self._ok15_report

    def _collect_ok15_evidence(self, actual: str) -> dict:
        """Isolated child collector; caller holds _ok15_lock to collapse concurrent GETs."""
        # MuPDF's warning buffer is process-global while this server is threaded: page
        # image requests would contaminate per-page attribution if the probe ran here.
        # One isolated child owns every PDF operation and returns JSON on stdout only.
        try:
            proc = subprocess.run(
                [sys.executable, "-B", str(BENCH_DIR / "ok15_evidence.py"),
                 "--pdf", str(self.pdf), "--source-sha256", actual],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("OK-15 evidence exceeded its 900 s quarantine bound") from exc
        if proc.returncode != 0:
            raise RuntimeError(
                f"OK-15 evidence exited {proc.returncode}: {(proc.stderr or proc.stdout)[-300:]}"
            )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OK-15 evidence returned no valid JSON") from exc

    def _require_md(self) -> None:
        if self.md_path is None:
            raise ValueError("reading mode — this is a bare PDF; there is no markdown to edit")

    def doc(self):
        if self.pdf is None:
            raise RuntimeError("no source PDF on the bench")
        if self._doc is None:
            import fitz  # pymupdf — marker-env
            self._doc = fitz.open(str(self.pdf))
        return self._doc

    def page_png(self, n: int, dpi: int = RASTER_DPI) -> bytes:
        page = self.doc().load_page(max(0, min(self.doc().page_count - 1, n - 1)))
        return page.get_pixmap(dpi=dpi).tobytes("png")

    # ---- OK-7 (docs/49 §1 c7, signed by Rab 2026-08-30): trim margins ----------------------
    # Okular's recipe, ported: the content box is MEASURED from the rendered raster (no PDF
    # metadata — works on scans; core/utils.cpp:90 isPaperColor), expanded 4% of the box's
    # mean dimension (ui/pageview.cpp:3385 cropExpandRatio) and never allowed to crop either
    # dimension below half the page (ui/pageview.cpp:3396 minCropRatio).
    TRIM_DPI = 30          # lever-waiver: Rab signed OK-7 2026-08-30; the thumb raster the bench already pays for
    TRIM_THRESHOLD = 40    # lever-waiver: Rab signed OK-7; per-channel paper distance, docs/49 §1 c7
    TRIM_PAD = 0.04        # lever-waiver: Rab signed OK-7; Okular's field-tuned cropExpandRatio (pageview.cpp:3385)
    TRIM_MIN_KEEP = 0.5    # lever-waiver: Rab signed OK-7; Okular's minCropRatio (pageview.cpp:3396)

    @staticmethod
    def bbox_from_samples(samples: bytes, w: int, h: int, stride: int, ncomp: int = 3,
                          threshold: int = TRIM_THRESHOLD) -> list[float] | None:
        """Normalized [x0,y0,x1,y1] content box of an RGB(A) raster, or None for a blank
        page. Paper color is estimated as the per-channel median of the four 3x3 corner
        patches — Okular compares against a CONFIGURED paper color; the corner median
        survives one dark corner and off-white scans. Pure function so the stdlib-only
        harness can feed it synthetic rasters (test_bench_page.py — its tripwire)."""
        if w < 8 or h < 8:
            return None

        def px(x: int, y: int) -> tuple[int, int, int]:
            o = y * stride + x * ncomp
            return samples[o], samples[o + 1], samples[o + 2]

        corners = [px(cx + dx, cy + dy)
                   for cx, cy in ((0, 0), (w - 3, 0), (0, h - 3), (w - 3, h - 3))
                   for dx in range(3) for dy in range(3)]
        paper = tuple(sorted(c[i] for c in corners)[len(corners) // 2] for i in range(3))

        def content(x: int, y: int) -> bool:
            p = px(x, y)
            return (abs(p[0] - paper[0]) > threshold or abs(p[1] - paper[1]) > threshold
                    or abs(p[2] - paper[2]) > threshold)

        top = next((y for y in range(h) if any(content(x, y) for x in range(w))), None)
        if top is None:
            return None
        bottom = next(y for y in range(h - 1, -1, -1) if any(content(x, y) for x in range(w)))
        left = next(x for x in range(w)
                    if any(content(x, y) for y in range(top, bottom + 1)))
        right = next(x for x in range(w - 1, -1, -1)
                     if any(content(x, y) for y in range(top, bottom + 1)))
        return [left / w, top / h, (right + 1) / w, (bottom + 1) / h]

    @staticmethod
    def pad_and_cap(box: list[float], pad: float = TRIM_PAD,
                    min_keep: float = TRIM_MIN_KEEP) -> list[float]:
        """Expand the tight box by pad x its mean dimension, clamp to the page, and refuse
        to crop either dimension below min_keep (expanding around the box center) — the two
        tuned constants that stop over-crop on noisy scans."""
        x0, y0, x1, y1 = box
        # review 2026-08-30: garbage in must raise, not center a plausible half-page —
        # the same rect discipline repair() applies to crop rects
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError(f"bad trim box {box} (fractions, x0<x1, y0<y1)")
        m = pad * ((x1 - x0) + (y1 - y0)) / 2
        x0, y0 = max(0.0, x0 - m), max(0.0, y0 - m)
        x1, y1 = min(1.0, x1 + m), min(1.0, y1 + m)

        def cap(lo: float, hi: float) -> tuple[float, float]:
            if hi - lo >= min_keep:
                return lo, hi
            c = (lo + hi) / 2
            lo, hi = c - min_keep / 2, c + min_keep / 2
            if lo < 0:
                return 0.0, min_keep
            if hi > 1:
                return 1 - min_keep, 1.0
            return lo, hi

        x0, x1 = cap(x0, x1)
        y0, y1 = cap(y0, y1)
        return [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)]

    def trimbox(self, n: int) -> dict:
        """The page's content box for margin-trimming, normalized to the page, cached per
        page. `cropped` False means the box is (near) the whole page — the client then
        applies no crop rather than a cosmetic sliver."""
        n = max(1, min(self.doc().page_count, n))
        if n in self._trim:
            return self._trim[n]
        pm = self.doc().load_page(n - 1).get_pixmap(dpi=self.TRIM_DPI)
        # constants passed EXPLICITLY: bound as defaults they freeze at class-definition
        # time and tuning Bench.TRIM_* would silently do nothing (review, 2026-08-30)
        box = self.bbox_from_samples(pm.samples, pm.width, pm.height,
                                     pm.stride, pm.n, self.TRIM_THRESHOLD)
        out = {"n": n, "box": [0.0, 0.0, 1.0, 1.0], "cropped": False}
        if box:
            padded = self.pad_and_cap(box, self.TRIM_PAD, self.TRIM_MIN_KEEP)
            bw, bh = padded[2] - padded[0], padded[3] - padded[1]
            if bw < 0.98 or bh < 0.98:
                out["box"], out["cropped"] = padded, True
        self._trim[n] = out
        return out

    # ---- the reader side (S62b, the Okular pass: contents, search, locate) ------------------
    def toc(self) -> list:
        """The PDF's own table of contents: [[level, title, page], …]. Empty for books that
        carry none (raw scans usually) — the UI says so instead of inventing one."""
        if self._toc is None:
            try:
                self._toc = [[int(l), str(t)[:120], int(p)] for l, t, p in
                             self.doc().get_toc(simple=True) if p > 0]
            except Exception:  # noqa: BLE001 — a bad outline is an empty outline
                self._toc = []
        return self._toc

    def _index(self) -> list[str]:
        """Lazy per-page text (lowercased). One-time cost on first search — honest seconds on
        a 1,356-pp book, then every search is instant. Empty strings for pages with no text
        layer (raw scans), which makes 'search unavailable' a measured fact, not a guess."""
        if self._texts is None:
            # Whitespace-normalized: PDF text carries hard newlines mid-sentence, and a
            # multi-word needle must match across them (found live on Damodaran — every
            # needle missed until this join). "- " is the linebreak-hyphen artifact after
            # the join ("invest- ment") — removed so needles match rejoined words.
            # OK-4: NFKC on top — PDFs carry ligatures (ﬁ, ﬂ) and width variants that a
            # keyboard can never type; the index and the query normalize identically.
            self._texts = [
                unicodedata.normalize(
                    "NFKC",
                    " ".join(self.doc().load_page(i).get_text("text").lower().split()))
                .replace("- ", "")
                for i in range(self.doc().page_count)
            ]
        return self._texts

    def find(self, q: str, limit: int = 40) -> dict:
        q = unicodedata.normalize("NFKC", " ".join(q.strip().lower().split()))
        if len(q) < 3:
            return {"q": q, "pages": [], "searchable": True, "error": "need 3+ characters"}
        idx = self._index()
        searchable = any(idx)
        hits = []
        for i, text in enumerate(idx):
            n = text.count(q)
            if n:
                at = text.find(q)
                excerpt = text[max(0, at - 40):at + len(q) + 40].replace("\n", " ")
                hits.append({"page": i + 1, "count": n, "excerpt": excerpt})
                if len(hits) >= limit:
                    break
        return {"q": q, "pages": hits, "searchable": searchable,
                "total_hits": sum(h["count"] for h in hits)}

    @staticmethod
    def match_in_words(words: list[list], query: str, limit: int = 20) -> list[list[float]]:
        """OK-4's hyphenation repair, pure: find `query` in the page's WORD STREAM and return
        one box per text line each occurrence crosses. A token ending in '-' joins the next
        with no space (the line-break hyphen: "invest-" + "ment" matches "investment");
        everything is NFKC + lowercase on both sides. Empty = genuinely not present as a
        word sequence — never a guess."""
        q = unicodedata.normalize("NFKC", " ".join(query.lower().split()))
        if not q or not words:
            return []
        parts: list[str] = []
        owner: list[int] = []  # stream char -> word index (-1 for separators)
        prev_hyphen = False
        for i, w in enumerate(words):
            t = unicodedata.normalize("NFKC", str(w[4]).lower())
            if parts and not prev_hyphen:
                parts.append(" ")
                owner.append(-1)
            if t.endswith("-") and len(t) > 1:
                core, prev_hyphen = t[:-1], True
            else:
                core, prev_hyphen = t, False
            parts.append(core)
            owner.extend([i] * len(core))
        stream = "".join(parts)
        boxes: list[list[float]] = []
        at = stream.find(q)
        while at >= 0 and len(boxes) < limit:
            idxs = sorted({owner[j] for j in range(at, at + len(q)) if owner[j] >= 0})
            if idxs:
                cluster = [words[idxs[0]]]
                for wi in idxs[1:]:
                    w, last = words[wi], cluster[-1]
                    h = max(w[3] - w[1], last[3] - last[1], 1e-6)
                    # same text line = y-centers within half a word height; a match that
                    # crosses the line break gets one box PER LINE, never a page-wide slab
                    if abs((w[1] + w[3]) / 2 - (last[1] + last[3]) / 2) < h / 2:
                        cluster.append(w)
                    else:
                        boxes.append([min(x[0] for x in cluster), min(x[1] for x in cluster),
                                      max(x[2] for x in cluster), max(x[3] for x in cluster)])
                        cluster = [w]
                boxes.append([min(x[0] for x in cluster), min(x[1] for x in cluster),
                              max(x[2] for x in cluster), max(x[3] for x in cluster)])
            # review (2026-08-31): advance past the whole match — at+1 made self-overlapping
            # queries ("no no") emit duplicate boxes that double-multiplied the blend
            at = stream.find(q, at + len(q))
        return boxes

    # ---- OK-6 (signed 2026-08-31): the table divider tool ---------------------------------
    # The humane SYM-003 repair: drag a region over a wrecked table, the tool guesses the
    # dividers from ink coverage, you correct them by click, and the cells come back as a
    # pipe table nobody had to hand-type. The guessing and bucketing are pure (harness-
    # tested); only the char fetch touches fitz.

    @staticmethod
    def guess_dividers(spans: list[tuple[float, float]], lo: float, hi: float,
                       min_gap: float = 0.006) -> list[float]:
        """1-D divider guessing: merge the occupied spans, and every gap wider than min_gap
        between them is a divider (at the gap's midpoint — the tick-sweep's valley). Bounds
        lo..hi are the dragged region's edges; returns interior dividers only, sorted."""
        occ: list[list[float]] = []
        for a, b in sorted((max(lo, a), min(hi, b)) for a, b in spans if b > lo and a < hi):
            if occ and a <= occ[-1][1] + 1e-9:
                occ[-1][1] = max(occ[-1][1], b)
            else:
                occ.append([a, b])
        return [round((occ[i][1] + occ[i + 1][0]) / 2, 5)
                for i in range(len(occ) - 1)
                if occ[i + 1][0] - occ[i][1] >= min_gap]

    @staticmethod
    def bucket_cells(words: list[list], chars: list[list], rect: list[float],
                     col_divs: list[float], row_divs: list[float]) -> list[list[str]]:
        """Central-pixel cell extraction: every word lands in the (row, col) whose bounds
        contain its CENTER. A word that CROSSES a column divider is the words-only failure
        the audit named — it is split by its chars (synthetic-space rects included) and each
        char re-bucketed, so kerned columns tighter than a word gap still come apart. Cells
        join left-to-right in reading order; pipes are escaped so the table can't eat its
        own syntax."""
        x0, y0, x1, y1 = rect
        cbounds = [x0, *sorted(col_divs), x1]
        rbounds = [y0, *sorted(row_divs), y1]

        def bucket(bounds: list[float], v: float) -> int:
            for i in range(len(bounds) - 1):
                if v < bounds[i + 1]:
                    return i
            return len(bounds) - 2

        grid: dict[tuple[int, int], list[list]] = {}
        char_pool = list(chars)
        # review CRITICAL (2026-08-31): the containment epsilon must DOMINATE the 5-decimal
        # rounding normalize_words bakes into word boxes (up to 5e-6 per edge) — at 1e-6 a
        # boundary char failed containment about half the time, silently dropping digits
        # from the extracted table or silently skipping the char-split entirely.
        EPS = 2e-5
        for w in words:
            wx0, wy0, wx1, wy1, text = w[0], w[1], w[2], w[3], str(w[4])
            crossed = any(wx0 < d < wx1 for d in col_divs)
            pieces = []
            if crossed:
                mine = [c for c in char_pool
                        if c[0] >= wx0 - EPS and c[2] <= wx1 + EPS
                        and c[1] >= wy0 - EPS and c[3] <= wy1 + EPS]
                if mine:
                    part: dict[int, list] = {}
                    for c in sorted(mine, key=lambda c: c[0]):
                        ci = bucket(cbounds, (c[0] + c[2]) / 2)
                        part.setdefault(ci, []).append(c)
                    for ci, cs in part.items():
                        pieces.append((cs[0][0], (wy0 + wy1) / 2, ci,
                                       "".join(str(c[4]) for c in cs).strip()))
            if not pieces:
                pieces = [(wx0, (wy0 + wy1) / 2, bucket(cbounds, (wx0 + wx1) / 2), text)]
            for px, py, ci, ptext in pieces:
                if not ptext:
                    continue
                ri = bucket(rbounds, py)
                grid.setdefault((ri, ci), []).append((px, ptext))
        rows_n, cols_n = len(rbounds) - 1, len(cbounds) - 1
        return [[" ".join(t for _, t in sorted(grid.get((r, c), []))).replace("|", "\\|")
                 for c in range(cols_n)] for r in range(rows_n)]

    @staticmethod
    def table_markdown(cells: list[list[str]]) -> str:
        if not cells or not cells[0]:
            return ""
        head, *body = cells
        lines = ["| " + " | ".join(head) + " |",
                 "|" + "|".join(" --- " for _ in head) + "|"]
        lines += ["| " + " | ".join(r) + " |" for r in body]
        return "\n".join(lines)

    def table(self, n: int, rect: list[float],
              col_divs: list[float] | None = None,
              row_divs: list[float] | None = None) -> dict:
        """The table tool's one entry point: words + chars inside the dragged region, guessed
        (or caller-corrected) dividers, cells, markdown. Row gaps are usually tighter than
        column gaps, so the row sweep uses a smaller valley threshold."""
        layer = self.textlayer(n)
        words = [w for w in layer["words"]
                 if w[2] > rect[0] and w[0] < rect[2] and w[3] > rect[1] and w[1] < rect[3]]
        page = self.doc().load_page(max(0, min(self.doc().page_count - 1, n - 1)))
        r = page.rect
        chars: list[list] = []
        try:
            for block in page.get_text("rawdict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        for ch in span.get("chars", []):
                            bb = ch["bbox"]
                            chars.append([bb[0] / r.width, bb[1] / r.height,
                                          bb[2] / r.width, bb[3] / r.height, ch["c"]])
        except Exception:  # noqa: BLE001 — chars refine, words still stand
            chars = []
        if col_divs is None:
            col_divs = self.guess_dividers([(w[0], w[2]) for w in words],
                                           rect[0], rect[2], min_gap=0.006)
        if row_divs is None:
            row_divs = self.guess_dividers([(w[1], w[3]) for w in words],
                                           rect[1], rect[3], min_gap=0.003)
        cells = self.bucket_cells(words, chars, rect, col_divs, row_divs)
        return {"page": n, "rect": rect, "col_divs": col_divs, "row_divs": row_divs,
                "rows": len(cells), "cols": len(cells[0]) if cells else 0,
                "words": len(words), "markdown": self.table_markdown(cells)}

    def rects(self, n: int, q: str) -> list[list[float]]:
        """Highlight rectangles for q on page n, as page-fraction boxes the UI overlays.
        OK-4: pymupdf's own matcher first (exact glyph spans); when it finds nothing, the
        match usually crossed a line-break hyphen or a ligature — rebuilt from the OK-5
        word stream instead of shrugging, which ends a whole class of false "not found"."""
        page = self.doc().load_page(max(0, min(self.doc().page_count - 1, n - 1)))
        r = page.rect
        out = []
        for hit in page.search_for(q)[:60]:
            out.append([hit.x0 / r.width, hit.y0 / r.height,
                        hit.x1 / r.width, hit.y1 / r.height])
        if not out:
            out = self.match_in_words(self.textlayer(n)["words"], q)
        return out

    TEXTLAYER_LRU = 16  # pages held at once; ~50-200 words each, so tens of KB, never GBs

    @staticmethod
    def normalize_words(raw_words: list, width: float, height: float) -> list[list]:
        """OK-5, the pure half: pymupdf `get_text("words")` tuples → page-fraction word boxes
        `[x0,y0,x1,y1,"text"]`, clamped to 0..1. Separated from the fitz call so the stdlib
        harness can exercise the math (the OK-7 pattern). Degenerate page geometry returns
        an empty layer rather than dividing by zero — no text layer is a measured fact here,
        never an exception."""
        if width <= 0 or height <= 0:
            return []
        out = []
        for w in raw_words:
            try:
                x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], str(w[4])
            except (IndexError, TypeError):
                continue  # a malformed tuple loses one word, never the layer
            if not text.strip():
                continue
            out.append([
                round(min(1.0, max(0.0, x0 / width)), 5),
                round(min(1.0, max(0.0, y0 / height)), 5),
                round(min(1.0, max(0.0, x1 / width)), 5),
                round(min(1.0, max(0.0, y1 / height)), 5),
                text,
            ])
        return out

    def textlayer(self, n: int) -> dict:
        """OK-5: every word on page n with its normalized rect — the one address type the
        drag-select, precise highlights, and future zone anchors all share. words-mode now;
        char rects deliberately deferred (rawdict is ~10× the payload and words carry
        selection today; OCR boxes later ride the same shape, the DjVu sidecar pattern)."""
        n = max(1, min(self.doc().page_count, n))
        if n in self._textlayer:
            self._textlayer.move_to_end(n)  # LRU refresh
            return self._textlayer[n]
        page = self.doc().load_page(n - 1)
        r = page.rect
        words = self.normalize_words(page.get_text("words"), r.width, r.height)
        out = {"page": n, "words": words, "count": len(words),
               "searchable": bool(words)}
        self._textlayer[n] = out
        while len(self._textlayer) > self.TEXTLAYER_LRU:
            self._textlayer.popitem(last=False)  # evict oldest — lazy stays bounded
        return out

    def locate_zone(self, zi: int) -> dict:
        """THE SMART PART: find a zone's TRUE page by evidence, not ratio. The zone line itself
        is degenerate junk, but the prose immediately around it is real text that also exists
        on the source page — so mine needles from the surrounding lines, search the text
        layer, and let the pages vote. Falls back to the ratio guess (and says so) when the
        book has no text layer (raw scans) or the votes disagree."""
        zones = self.zones()
        if not (0 <= zi < len(zones)):
            raise ValueError(f"no zone {zi}")
        if zi in self._zone_loc:
            return self._zone_loc[zi]
        z = zones[zi]
        st = self.state()
        guess = st["zones"][zi]["page_guess"]
        idx = self._index()
        if not any(idx):
            res = {"page": guess, "method": "ratio", "confidence": 0.0,
                   "note": "no text layer (raw scan) — ratio guess only"}
            self._zone_loc[zi] = res
            return res
        lines = self.body().split("\n")
        at = st["zones"][zi]["adjusted_line"]
        # Mine clean prose near the zone: skip table junk, embeds, headings, short fragments.
        # Zones live in table thickets, so the window WIDENS until enough prose is found, and
        # long lines contribute several 5-word shingles (short shingles survive the PDF's own
        # typography better than one long one — measured on Damodaran).
        needles: list[str] = []
        for reach in (10, 25, 45):
            needles.clear()
            for ln in lines[max(0, at - reach):min(len(lines), at + reach // 2)]:
                if ln.count("|") >= 3 or ln.startswith("!["):
                    continue
                t = re.sub(r"[#*_`>\[\]!|<]+", " ", ln)
                t = " ".join(w for w in t.lower().split() if len(w) > 2)
                words = t.split(" ")
                for s in range(0, max(1, len(words) - 4), 5):
                    if len(words) - s >= 5:
                        needles.append(" ".join(words[s:s + 5]))
                if len(needles) >= 12:
                    break
            if len(needles) >= 4:
                break
        needles = needles[:12]
        votes: dict[int, int] = {}
        for nd in needles:
            for i, text in enumerate(idx):
                if nd in text:
                    votes[i + 1] = votes.get(i + 1, 0) + 1
        if votes:
            best = max(votes, key=lambda p: (votes[p], -abs(p - guess)))
            res = {"page": best, "method": "text-evidence", "needles": len(needles),
                   "confidence": round(votes[best] / max(1, len(needles)), 2),
                   "votes": {str(k): v for k, v in sorted(votes.items())[:8]}}
        else:
            res = {"page": guess, "method": "ratio", "confidence": 0.0,
                   "note": f"none of {len(needles)} needles matched — ratio guess kept"}
        self._zone_loc[zi] = res
        return res

    # ---- write side -------------------------------------------------------------------------
    def _backup_once(self) -> None:
        bak = self.md_path.with_suffix(".md.bench-bak")
        if not self._bak_done and not bak.exists():
            shutil.copy2(self.md_path, bak)
        self._bak_done = True

    # ---- THE CHOKEPOINT + the repair ledger (S76, docs/28 — signed by Rab) ------------------
    @property
    def ledger_path(self) -> Path:
        return self.dir / "repairs.jsonl"

    def ledger(self) -> list[dict]:
        """Every recorded change to this body, oldest first. A torn final line (power cut
        mid-append) costs that one event, never the history — the S60 lesson."""
        if not self.ledger_path.is_file():
            return []
        out = []
        for ln in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    out.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
        return out

    @staticmethod
    def _sha(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _cap(lines: list[str]) -> tuple[list[str], bool]:
        """Changed text is stored VERBATIM so the ledger archives what left the document —
        capped, because a pathological edit must not make the ledger unreadable."""
        total = sum(len(x) for x in lines)
        if total <= LEDGER_VERBATIM_MAX:
            return lines, False
        keep, used = [], 0
        for ln in lines:
            if used + len(ln) > LEDGER_VERBATIM_MAX:
                break
            keep.append(ln)
            used += len(ln)
        keep.append(f"…[{total - used} more chars truncated · full-region sha "
                    f"{hashlib.sha256(chr(10).join(lines).encode()).hexdigest()[:16]}]")
        return keep, True

    def _write_body(self, new_body: str, *, gesture: str, zone_line: int | None = None,
                    note: str = "", extra: dict | None = None) -> list[dict]:
        """THE chokepoint. No body write in this class may bypass it (docs/28 §2).

        Diffs old→new, classifies every changed region as removal/addition/edit, files the
        events, and only then writes. Recording FIRST is deliberate — the same ordering law
        the supersede marker follows (docs/15 §14.7): an action whose intent cannot be filed
        must not happen. If the body write then fails, the sha chain surfaces it at the next
        read, which is far better than a change nobody can name."""
        self._require_md()
        old_body = self.body()
        if new_body == old_body:
            return []                       # a no-op burns no history
        self._backup_once()
        old_lines, new_lines = old_body.split("\n"), new_body.split("\n")
        sha_before, sha_after = self._sha(old_body), self._sha(new_body)
        seq = len(self.ledger())
        events = []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, old_lines, new_lines, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            removed, added = old_lines[i1:i2], new_lines[j1:j2]
            rem_kept, rem_trunc = self._cap(removed)
            add_kept, add_trunc = self._cap(added)
            events.append({
                "ts": _now_iso(), "seq": seq + len(events), "gesture": gesture,
                "kind": {"delete": "removal", "insert": "addition", "replace": "edit"}[tag],
                "zone_line": zone_line, "note": note,
                "at": {"before": [i1 + 1, i2], "after": [j1 + 1, j2]},
                "chars": {"removed": sum(len(x) for x in removed),
                          "added": sum(len(x) for x in added)},
                "margin": {
                    "context_before": old_lines[max(0, i1 - LEDGER_CONTEXT):i1],
                    "removed": rem_kept, "added": add_kept,
                    "context_after": old_lines[i2:i2 + LEDGER_CONTEXT],
                    "truncated": rem_trunc or add_trunc,
                },
                "sha_before": sha_before, "sha_after": sha_after,
                **(extra or {}),
            })
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            for ev in events:
                fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())    # S71: a record not fsynced is a record you may lose
        fm, _ = split_frontmatter(self.md_path.read_text(encoding="utf-8"))
        self.md_path.write_text(fm + new_body, encoding="utf-8")
        return events

    def writes(self) -> list[list[dict]]:
        """Ledger events grouped by the write that produced them (one write can change several
        regions), oldest first."""
        out: list[list[dict]] = []
        for e in self.ledger():
            if out and (out[-1][0]["sha_before"], out[-1][0]["sha_after"]) == \
                    (e["sha_before"], e["sha_after"]):
                out[-1].append(e)
            else:
                out.append([e])
        return out

    def undo_depth(self) -> int:
        """How many changes could still be walked back. Ledger-derived, so a bench restart no
        longer resets it to zero and pretends nothing ever happened."""
        ws = self.writes()
        reverted = {e["reverts"] for w in ws for e in w if e.get("reverts")}
        return len([w for w in ws
                    if w[0]["gesture"] != "undo" and w[0]["sha_after"] not in reverted])

    def undo_ledger(self) -> dict:
        """ctrl-Z, ledger-driven (docs/28 §5.2) — survives a bench restart, which the
        in-memory stack never could. Reverting is exact rather than approximate: each event
        knows the lines it produced and the lines it displaced, so applying
        `lines[after] = removed` in reverse order is the inverse of the write.

        An undo is itself recorded and names what it reverted, so pressing it repeatedly walks
        back through history instead of redoing itself."""
        self._require_md()
        ws = self.writes()
        if not ws:
            raise ValueError("nothing to undo — the ledger is empty")
        reverted = {e["reverts"] for w in ws for e in w if e.get("reverts")}
        target = None
        for w in reversed(ws):
            if w[0]["gesture"] == "undo" or w[0]["sha_after"] in reverted:
                continue
            target = w
            break
        if target is None:
            raise ValueError("nothing left to undo — every change has been reverted")
        body = self.body()
        if self._sha(body) != target[0]["sha_after"]:
            raise ValueError("the body no longer matches that change — refusing to guess "
                             "(restore from .bench-bak if you need to go further back)")
        if any(e["margin"].get("truncated") for e in target):
            raise ValueError("that change archived too much text to reconstruct exactly — "
                             "the ledger holds a truncated copy; restore by hand")
        lines = body.split("\n")
        for e in sorted(target, key=lambda x: x["at"]["after"][0], reverse=True):
            a1, a2 = e["at"]["after"]
            lines[a1 - 1:a2] = e["margin"]["removed"]
        gesture = target[0]["gesture"]
        self._write_body("\n".join(lines), gesture="undo",
                         note=f"reverted a {gesture}",
                         extra={"reverts": target[0]["sha_after"]})
        # provenance must not survive the body it described (the transcribe law, generalised)
        reps = self.manifest.get("repairs", [])
        if reps and reps[-1].get("mode") in ("transcribe", "collapse", "crop", "paste") \
                and gesture in ("transcribe", "collapse", "crop", "paste"):
            reps.pop()
            self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n",
                                          encoding="utf-8")
        return {"undone": True, "gesture": gesture, "regions": len(target),
                "chars_restored": sum(e["chars"]["removed"] for e in target),
                "remaining": len([w for w in self.writes()
                                  if w[0]["gesture"] != "undo"
                                  and w[0]["sha_after"] not in reverted]) - 1}

    def ledger_audit(self) -> dict:
        """The chain check: each event's sha_before must equal the previous sha_after, and the
        newest sha_after must equal the body on disk. A break means something wrote around the
        chokepoint — the ledger's whole purpose is to be able to say so."""
        evs = self.ledger()
        if not evs:
            return {"events": 0, "writes": 0, "intact": True, "breaks": [],
                    "matches_disk": None}
        # ONE _write_body call can emit several events (a diff with several changed regions);
        # they all share the write's sha pair, so the chain is checked per WRITE, not per event.
        writes: list[tuple[str, str]] = []
        for e in evs:
            pair = (e["sha_before"], e["sha_after"])
            if not writes or writes[-1] != pair:
                writes.append(pair)
        breaks = [{"at_write": i, "expected": writes[i - 1][1], "found": writes[i][0]}
                  for i in range(1, len(writes)) if writes[i][0] != writes[i - 1][1]]
        return {"events": len(evs), "writes": len(writes), "intact": not breaks,
                "breaks": breaks,
                "matches_disk": self._sha(self.body()) == writes[-1][1]}

    def _next_asset(self, page: int) -> str:
        ks = [int(m.group(2)) for p in self.assets.iterdir()
              if (m := ASSET_RE.match(p.name)) and int(m.group(1)) == page]
        return f"_repair_p{page}_{max(ks, default=0) + 1}.png"

    @staticmethod
    def _record_shift(r: dict) -> int:
        """Lines a persisted repair record moved everything below it. Crop/paste insert a
        fixed 3 ("", embed, comment); transcribe carries its own count; collapse carries a
        SIGNED delta (negative — it removes lines). Collapse deliberately uses `delta` rather
        than reusing `lines`, because the UI renders `r.lines || 0` and a negative there would
        corrupt the repairs chip."""
        if r.get("mode") == "transcribe":
            return r.get("lines") or 0
        if r.get("mode") == "collapse":
            return r.get("delta") or 0
        return 3

    def _adjusted_line(self, zone_line: int) -> int:
        """Each prior repair moved everything below ITS zone (see _record_shift), and each
        AI edit may have grown or shrunk its range — a zone below those changes has shifted by
        their sum. Transcriptions and collapses deliberately do NOT ride the drift ledger:
        their shift lives in the manifest record, which survives a bench restart (the ledger
        does not)."""
        prior = sum(self._record_shift(r)
                    for r in self.manifest.get("repairs", [])
                    if r.get("zone_line") is not None and r["zone_line"] < zone_line)
        drift = sum(d for (at, d) in self._ai_drift if at < zone_line)
        return zone_line + prior + drift

    # ---- outcome triage (S76, docs/28 §4) ---------------------------------------------------
    @staticmethod
    def zone_key(z: dict) -> str:
        return f"z{z['line']}"

    @staticmethod
    def run_key(r: dict) -> str:
        """Stable across re-orderings: page + a hash of the witness excerpt."""
        h = hashlib.sha256((r.get("excerpt") or "").encode("utf-8")).hexdigest()[:8]
        return f"r{r.get('page')}-{h}"

    def _outcome(self, key: str, at: int | None) -> tuple[str, str]:
        """(outcome, reason). An explicit operator judgment always wins over derivation —
        the human is allowed to know something the provenance cannot show."""
        t = (self.manifest.get("triage") or {}).get(key)
        if t and t.get("outcome") and t["outcome"] != "open":
            return t["outcome"], t.get("reason", "")
        if at is None:
            return "open", ""
        modes = {r.get("mode") for r in self.manifest.get("repairs", [])
                 if r.get("zone_line") == at}
        # strongest claim first: real text beats an image, an image beats mere noise removal
        for mode, outcome in (("transcribe", "text-restored"), ("crop", "image-restored"),
                              ("paste", "image-restored"), ("collapse", "collapsed")):
            if mode in modes:
                return outcome, ""
        return "open", ""

    def triage(self, key: str, outcome: str, reason: str = "") -> dict:
        """Record the operator's judgment on one located defect. Only the human-only outcomes
        may be set here; the derived ones are read from provenance and cannot be asserted."""
        if outcome not in OUTCOMES_MANUAL:
            raise ValueError(f"{outcome!r} is derived from provenance, not declared — "
                             f"settable: {list(OUTCOMES_MANUAL)}")
        if outcome == "dismissed-noise" and not reason.strip():
            raise ValueError("dismissing located damage requires a reason — an unexplained "
                             "dismissal is indistinguishable from ignoring it")
        t = self.manifest.setdefault("triage", {})
        if outcome == "open":
            t.pop(key, None)
        else:
            t[key] = {"outcome": outcome, "reason": reason.strip()[:300],
                      "ts": _now_iso(), "by": "repair-bench"}
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n",
                                      encoding="utf-8")
        return {"key": key, "outcome": outcome, "reason": reason.strip()[:300]}

    def coverage(self) -> dict:
        """docs/28 §4 question 2: has a human addressed every located defect? Provenance, not
        measurement — reported BESIDE the metrics and never blended into them."""
        st = self.state()
        tally: dict[str, int] = {o: 0 for o in OUTCOMES}
        sites = []
        for z in st["zones"]:
            tally[z["outcome"]] = tally.get(z["outcome"], 0) + 1
            sites.append({"kind": "zone", "key": self.zone_key(z), "at": z["adjusted_line"],
                          "outcome": z["outcome"], "reason": z.get("outcome_reason", "")})
        for r in st["runs"]:
            tally[r["outcome"]] = tally.get(r["outcome"], 0) + 1
            sites.append({"kind": "omission", "key": self.run_key(r), "page": r.get("page"),
                          "outcome": r["outcome"], "reason": r.get("outcome_reason", "")})
        total = len(sites)
        return {"sites": sites, "total": total, "tally": tally,
                "open": tally.get("open", 0),
                "addressed": total - tally.get("open", 0)}

    def _resolve_run_line(self, run: dict) -> int | None:
        """S76 (SYM-026): an omission run is PAGE-anchored — the audit knows what the witness
        had and the output lost, but not a line. Its excerpt however BEGINS with text the
        output still has (the loss starts partway in), so the opening words locate where the
        missing material belongs. Short prefixes only: the tail of the excerpt is precisely
        the part that is gone, so a long needle can never match."""
        words = (run.get("excerpt") or "").split()
        if len(words) < 3:
            return None
        body_norm = [" ".join(ln.split()).lower() for ln in self.body().split("\n")]
        for n in (6, 5, 4, 3):
            if len(words) < n:
                continue
            needle = " ".join(words[:n]).lower().strip("-—•* ")
            if len(needle) < 8:
                continue
            hits = [i + 1 for i, ln in enumerate(body_norm) if needle in ln]
            if hits:
                return hits[0]
        return None

    def _resolve_zone_line(self, z: dict) -> tuple[int, str]:
        """SYM-025: a zone's `line` was recorded by the CONVERT-phase audit, but the analyst
        phase rewrites the body afterwards (S76 Beer: md_lines 3013 → live body 2997), so that
        number can point at an unrelated passage — and _adjusted_line has no term for an edit
        made before the bench ever opened. The EXCERPT is the durable anchor; the line number
        is the fragile one.

        A live-body hit ALREADY reflects every shift from every source, so it must NOT also
        take the drift terms — that would double-count. Fall back to the arithmetic only when
        the excerpt is gone (a repaired or collapsed zone), and say which was used."""
        excerpt = (z.get("excerpt") or "").strip()
        adj = self._adjusted_line(z["line"])
        if excerpt:
            hits = [i + 1 for i, ln in enumerate(self.body().split("\n"))
                    if excerpt in " ".join(ln.split())]
            if hits:
                return min(hits, key=lambda h: abs(h - adj)), "excerpt"
        return adj, "drift"

    def repair(self, zone_line: int, page: int, rect: list[float] | None = None,
               image_b64: str | None = None, note: str = "") -> dict:
        """The one gesture: capture (crop or paste) → assets/ → ![[embed]] at the zone →
        provenance. Raises on anything invalid — the HTTP layer reports, never guesses."""
        self._require_md()
        if rect is not None:
            import fitz
            page_obj = self.doc().load_page(page - 1)
            r = page_obj.rect
            x0, y0, x1, y1 = rect
            if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                raise ValueError(f"bad crop rect {rect} (fractions, x0<x1, y0<y1)")
            clip = fitz.Rect(x0 * r.width, y0 * r.height, x1 * r.width, y1 * r.height)
            png = page_obj.get_pixmap(dpi=CROP_DPI, clip=clip).tobytes("png")
            mode = "crop"
        elif image_b64:
            raw = image_b64.split(",", 1)[-1]  # tolerate a data: URL
            png = base64.b64decode(raw)
            if png[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("pasted image is not a PNG")
            mode = "paste"
        else:
            raise ValueError("need rect (crop) or image_b64 (paste)")

        asset = self._next_asset(page)
        self._backup_once()
        (self.assets / asset).write_bytes(png)

        fm, body = split_frontmatter(self.md_path.read_text(encoding="utf-8"))
        lines = body.split("\n")
        at = min(self._adjusted_line(zone_line), len(lines))  # insert AFTER this body line
        caption = f"repair p{page}" + (f" — {note}" if note else "")
        lines[at:at] = ["", f"![[assets/{asset}]]", f"<!-- {caption} · repair-bench -->"]
        self._write_body("\n".join(lines), gesture=mode, zone_line=zone_line, note=note,
                         extra={"asset": asset, "page": page})

        # OK-0 (docs/49 §1 c0, signed 2026-08-30): every NEW record gets a UUID at creation —
        # line numbers shift under edits; the id is the durable key later features (review
        # index, undo re-binding) resolve against. Existing records are never rewritten.
        rec = {"id": "fpr-" + uuid.uuid4().hex,
               "ts": _now_iso(), "zone_line": zone_line, "page": page, "asset": asset,
               "mode": mode, "note": note, "by": "repair-bench",
               "dpi": CROP_DPI if mode == "crop" else None,
               "rect": rect}
        self.manifest.setdefault("repairs", []).append(rec)
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n",
                                      encoding="utf-8")
        return {"asset": asset, "inserted_after_line": at, "record": rec}

    # ---- the transcribe gesture (S71, docs/23 built): the crop gains a reading eye ----------
    def transcribe(self, zone_line: int, page: int, rect: list[float]) -> dict:
        """Crop the region (the repair gesture's own crop path, same 220 dpi), hand it to the
        granite-docling worker in docling-env, and return a PROPOSAL — markdown + gate
        receipts + the crop image. Nothing is applied here; the human is the final gate.
        Refuses while .gpu-lock is held (serialization law) and when the worker env is absent
        (honest setup message, never a traceback)."""
        self._require_md()
        if GPU_LOCK.exists():
            raise RuntimeError("the line holds the GPU (.gpu-lock) — transcribe after the "
                               "conversion finishes (serialization law)")
        if not DOCLING_PY.is_file():
            raise RuntimeError("docling-env not found — run the S71 setup "
                               "(uv venv C:\\Users\\Bndit\\ml\\docling-env; see "
                               "prototypes/docling-calibration/README.md)")
        import subprocess
        import tempfile
        import fitz
        page_obj = self.doc().load_page(page - 1)
        r = page_obj.rect
        x0, y0, x1, y1 = rect
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError(f"bad crop rect {rect} (fractions, x0<x1, y0<y1)")
        clip = fitz.Rect(x0 * r.width, y0 * r.height, x1 * r.width, y1 * r.height)
        png = page_obj.get_pixmap(dpi=CROP_DPI, clip=clip).tobytes("png")
        # Witness text for the same clip — exists on clean-lane pages, empty on scans; the
        # worker computes the numeric-multiset + window gates only when it has one.
        witness = page_obj.get_text(clip=clip) or ""
        tmp_png = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_png.write(png)
        tmp_png.close()
        tmp_wit = None
        try:
            if witness.strip():
                tmp_wit = tempfile.NamedTemporaryFile(suffix=".txt", delete=False,
                                                      mode="w", encoding="utf-8")
                tmp_wit.write(witness)
                tmp_wit.close()
            cmd = [str(DOCLING_PY), str(TRANSCRIBE_WORKER), "--image", tmp_png.name,
                   "--dtype", TRANSCRIBE_DTYPE]
            if tmp_wit:
                cmd += ["--witness", tmp_wit.name]
            # 360 s: calibration measured dense TABLE crops at 84-182 s (output-bound decode;
            # those runs were also GPU-contended) — 240 was too tight for the exact crops
            # this gesture exists for. The UI's live clock keeps the wait honest.
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=360,
                                  encoding="utf-8", errors="replace")
            try:
                res = json.loads(proc.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                raise RuntimeError(f"worker spoke no JSON (exit {proc.returncode}): "
                                   f"{(proc.stderr or proc.stdout)[-200:]}") from None
            if not res.get("ok"):
                raise RuntimeError(f"transcribe refused: {res.get('error', 'unknown')} — "
                                   "the ✂ image embed remains the floor")
            return {"proposal": True, "zone_line": zone_line, "page": page, "rect": rect,
                    "markdown": res["markdown"], "gates": res["gates"],
                    "secs": res["secs"], "load_s": res["load_s"],
                    "vram_mib": res["vram_mib"], "model": res["model"],
                    "crop_b64": base64.b64encode(png).decode("ascii")}
        finally:
            os.unlink(tmp_png.name)
            if tmp_wit:
                os.unlink(tmp_wit.name)

    def transcribe_apply(self, zone_line: int, page: int, markdown: str,
                         gates: dict | None = None, secs: float | None = None,
                         rect: list[float] | None = None) -> dict:
        """Apply an ACCEPTED proposal: insert the (possibly human-edited) markdown at the
        zone, snapshot-first so ↩ undo restores byte-identical, provenance to
        manifest.repairs with mode:'transcribe'. Same drift ledger as the AI assist —
        zone anchors below the insertion stay honest."""
        self._require_md()
        markdown = (markdown or "").strip("\n")
        if not markdown.strip():
            raise ValueError("nothing to insert — an empty proposal is a discard")
        self._backup_once()
        fm, body = split_frontmatter(self.md_path.read_text(encoding="utf-8"))
        self._undo.append(("transcribe", body))
        del self._undo[:-20]  # the assist's bounded stack, shared philosophy
        lines = body.split("\n")
        at = min(self._adjusted_line(zone_line), len(lines))
        inserted = ["", *markdown.split("\n"),
                    f"<!-- transcribed p{page} · granite-docling-258M · repair-bench -->"]
        lines[at:at] = inserted
        self._write_body("\n".join(lines), gesture="transcribe", zone_line=zone_line,
                         note=f"granite-docling p{page}", extra={"page": page})
        # NO drift-ledger entry: the shift travels in the record's `lines` (restart-safe),
        # and undo_ai pairs the snapshot with the record so provenance can never desync.
        rec = {"id": "fpr-" + uuid.uuid4().hex,   # OK-0: identity at creation
               "ts": _now_iso(), "zone_line": zone_line, "page": page, "asset": None,
               "mode": "transcribe", "model": "granite-docling-258M", "lines": len(inserted),
               "gates": gates or {}, "secs": secs, "by": "repair-bench",
               "dpi": CROP_DPI, "rect": rect}
        self.manifest.setdefault("repairs", []).append(rec)
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n",
                                      encoding="utf-8")
        return {"inserted_after_line": at, "lines": len(inserted),
                "undo_depth": self.undo_depth(), "record": rec}

    # ---- the AI assist (S64): local qwen3 fixes a passage; every change is undoable --------
    # The analyst's non-negotiable link-fence applies here too: qwen3 once INVENTED image URLs
    # on an unfenced prompt, so every embed becomes an opaque token before the model sees the
    # text, and a reply that damages the token multiset is REFUSED, never patched.
    _EMBED_RE = re.compile(r"!\[\[[^\]]*\]\]|!\[[^\]]*\]\([^)]*\)")
    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    AI_MODEL = "qwen3:8b"

    # ---- the collapse gesture (S76, docs/27 — signed by Rab) --------------------------------
    def _zone_paragraph(self, at: int) -> tuple[int, int, str]:
        """The blank-line-delimited block containing body line `at`, 1-indexed inclusive."""
        lines = self.body().split("\n")
        i = min(max(at, 1), len(lines)) - 1
        while i < len(lines) - 1 and not lines[i].strip():
            i += 1                                   # a blank anchor belongs to what follows
        a = b = i
        while a > 0 and lines[a - 1].strip():
            a -= 1
        while b < len(lines) - 1 and lines[b + 1].strip():
            b += 1
        return a + 1, b + 1, "\n".join(lines[a:b + 1])

    def collapse(self, zone_line: int, preview: bool = False) -> dict:
        """Reduce a decoder token-loop to one instance, keeping the paragraph's head and tail.
        Mechanical: no crop, no model, no GPU — the loop carries no information past its first
        instance (docs/27). It removes NOISE and does NOT restore the lost content, which still
        lives only in the page image; that is why a collapsed zone is reported `collapsed`,
        never `repaired`. Refuses anything that still reads as language."""
        self._require_md()
        z = next((x for x in self.zones() if x["line"] == zone_line), None)
        if z is None:
            raise ValueError(f"no zone recorded at line {zone_line}")
        at, anchor = self._resolve_zone_line(z)
        first, last, para = self._zone_paragraph(at)
        ttr = type_token_ratio(para)
        if ttr >= TTR_LOOP_MAX:
            raise ValueError(f"refused: type-token ratio {ttr:.4f} >= {TTR_LOOP_MAX} — this "
                             f"paragraph still reads as language, not a loop")
        found = find_cycle(para)
        if not found:
            raise ValueError("refused: no consecutive repeating cycle found")
        p, i0, i1, repeats, _covered = found
        spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", para)]
        lo, hi = spans[i0][0], spans[min(i1, len(spans) - 1)][1]
        one = para[lo:spans[min(i0 + p - 1, len(spans) - 1)][1]]
        removed = (hi - lo) - len(one)
        marker = (f"<!-- repair-bench collapse: a {p}-token loop repeated ~{repeats}x "
                  f"({removed} chars) reduced to one instance · the lost content is still "
                  f"only in the page image -->")
        new_para = f"{para[:lo]}{one}{para[hi:]}\n{marker}"
        delta = new_para.count("\n") - para.count("\n")   # SIGNED: the marker adds a line,
        # a multi-line loop removes many — either way the record carries the truth
        head, tail = para[:lo], para[hi:]
        if preview:
            return {"zone_line": zone_line, "at": at, "anchor": anchor,
                    "para_lines": [first, last], "ttr": round(ttr, 4),
                    "period_tokens": p, "repeats": repeats, "chars_removed": removed,
                    "cycle": one[:80], "head_kept": head[-70:], "tail_kept": tail[:70],
                    "chars_before": len(para), "chars_after": len(new_para),
                    "delta_lines": delta, "preview": new_para[:400]}

        self._backup_once()
        fm, body = split_frontmatter(self.md_path.read_text(encoding="utf-8"))
        self._undo.append(("collapse", body))
        del self._undo[:-20]              # the same bounded stack the other gestures share
        lines = body.split("\n")
        lines[first - 1:last] = new_para.split("\n")
        self._write_body("\n".join(lines), gesture="collapse", zone_line=zone_line,
                         note=f"{p}-token loop x{repeats}",
                         extra={"period_tokens": p, "repeats": repeats})

        rec = {"id": "fpr-" + uuid.uuid4().hex,   # OK-0: identity at creation
               "ts": _now_iso(), "zone_line": zone_line, "page": None, "asset": None,
               "mode": "collapse", "by": "repair-bench", "delta": delta,
               "chars_removed": removed, "period_tokens": p, "repeats": repeats,
               "cycle": one[:80], "anchor": anchor}
        self.manifest.setdefault("repairs", []).append(rec)
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n",
                                      encoding="utf-8")
        return {"record": rec, "undo_depth": self.undo_depth(), "chars_removed": removed,
                "delta_lines": delta, "at": at, "para_lines": [first, last]}

    def _fence(self, text: str) -> tuple[str, list[str]]:
        tokens: list[str] = []

        def sub(m: re.Match) -> str:
            tokens.append(m.group(0))
            return f"⟦IMG-{len(tokens)}⟧"

        return self._EMBED_RE.sub(sub, text), tokens

    @staticmethod
    def _unfence(text: str, tokens: list[str]) -> str | None:
        """Every token exactly once, none invented — else None (the fence held; refuse)."""
        found = re.findall(r"⟦IMG-(\d+)⟧", text)
        if sorted(found) != sorted(str(i + 1) for i in range(len(tokens))):
            return None
        for i, tok in enumerate(tokens):
            text = text.replace(f"⟦IMG-{i + 1}⟧", tok)
        return text

    def assist(self, start: int, end: int, instruction: str) -> dict:
        """Rewrite body lines start..end (1-based, inclusive — the UI's visible slice) per the
        instruction, via LOCAL qwen3 (the Gemini API stays off by Rab's standing rule).
        Snapshot-first: every applied change is one ↩ away from gone."""
        self._require_md()
        instruction = instruction.strip()
        if not instruction:
            raise ValueError("tell the model what to fix")
        fm, body = split_frontmatter(self.md_path.read_text(encoding="utf-8"))
        lines = body.split("\n")
        start = max(1, min(start, len(lines)))
        end = max(start, min(end, len(lines)))
        excerpt = "\n".join(lines[start - 1:end])
        fenced, tokens = self._fence(excerpt)
        prompt = (
            "You are the Repair Bench assistant fixing conversion damage in a book's markdown "
            "(OCR loops, mangled tables, broken headings, garbled sentences).\n"
            "Rewrite the EXCERPT according to the INSTRUCTION.\n"
            "Rules: output ONLY the revised excerpt — no commentary, no code fences. Keep every "
            "⟦IMG-n⟧ token exactly once, in a sensible position. Repair, don't invent: "
            "add no content the instruction does not call for.\n\n"
            f"INSTRUCTION: {instruction}\n\nEXCERPT:\n{fenced}\n\nREVISED EXCERPT:"
        )
        import urllib.request
        req = urllib.request.Request(
            self.OLLAMA_URL,
            data=json.dumps({
                "model": self.AI_MODEL, "stream": False, "keep_alive": 0,
                "prompt": prompt, "options": {"num_ctx": 8192}, "think": False,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                reply = json.loads(r.read().decode("utf-8"))
        except OSError as exc:
            raise RuntimeError(f"Ollama unreachable ({exc}) — is it running?") from exc
        if reply.get("error"):
            raise RuntimeError(f"ollama: {reply['error']}")
        out = reply.get("response", "").strip()
        out = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()  # belt over "think":False
        if out.startswith("```"):
            out = re.sub(r"^```[a-z]*\n|\n```$", "", out).strip()
        if not out:
            raise RuntimeError("the model returned nothing — change refused")
        restored = self._unfence(out, tokens)
        if restored is None:
            raise RuntimeError("the model damaged an image embed — change REFUSED (link-fence)")
        if restored == excerpt:
            # A no-op is an honest answer ("nothing to fix") — report it, burn no undo slot.
            return {"applied": False, "unchanged": True, "undo_depth": self.undo_depth()}
        self._backup_once()
        self._undo.append(("assist", body))
        del self._undo[:-20]  # bounded stack — twenty regrets is plenty
        new_lines = restored.split("\n")
        self._ai_drift.append((start, len(new_lines) - (end - start + 1)))
        lines[start - 1:end] = new_lines
        self._write_body("\n".join(lines), gesture="assist",
                         note=f"qwen3 rewrote lines {start}–{end}")
        return {"applied": True, "start": start, "lines_before": end - start + 1,
                "lines_after": len(new_lines), "undo_depth": self.undo_depth()}

    def undo_ai(self) -> dict:
        """The ctrl-Z button: restore the body exactly as it was before the last AI change.
        Kind-aware (S71): undoing an assist pops its drift entry; undoing a transcription
        pops its manifest.repairs record too — body and provenance can never disagree."""
        self._require_md()
        if not self._undo:
            raise ValueError("nothing to undo")
        kind, body = self._undo.pop()
        # docs/28: an undo is itself a change, and history records it rather than erasing —
        # the ledger is append-only, so "what was here before" stays answerable forever.
        self._write_body(body, gesture="undo", note=f"reverted a {kind}")
        if kind == "assist" and self._ai_drift:
            self._ai_drift.pop()
        if kind in ("transcribe", "collapse"):
            reps = self.manifest.get("repairs", [])
            if reps and reps[-1].get("mode") == kind:
                reps.pop()
                self.manifest_path.write_text(
                    json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8")
        return {"undone": True, "undo_depth": self.undo_depth(), "kind": kind}

    # ---- the re-score PREVIEW (never writes; audit policy is Rab's signature) ---------------
    def rescore_preview(self) -> dict:
        self._require_md()
        sys.path.insert(0, str(REPO / "windows-converter"))
        try:
            import fidelity_audit as fa
        finally:
            sys.path.pop(0)
        det = fa.degeneration(self.body())
        orig = self.zones()
        repaired_lines = {r["zone_line"] for r in self.manifest.get("repairs", [])}
        cov = self.coverage()
        # docs/28 §4 — TWO questions, never merged into one number.
        #  1. does the TEXT still match its source?  Measurement. Degeneration genuinely
        #     clears when a loop goes; an omission does NOT clear because an image was placed
        #     — cropping page 114 restores content to a READER and nothing to a comparison.
        #  2. has a human addressed every located defect?  Provenance, reported beside it.
        open_sites = cov["open"]
        eligible = (not det.get("flagged")) and open_sites == 0
        if det.get("flagged"):
            why = "degeneration is still present in the text"
        elif open_sites:
            why = f"{open_sites} located defect(s) still open"
        else:
            why = ("nothing left open — but image-restored and dismissed-noise are HUMAN "
                   "assertions, so this is a recommendation for the bless rail, not a pass")
        return {
            "preview": True,
            "note": ("PREVIEW ONLY — the shipping audit re-runs in the pipeline, and whether a "
                     "repair earns audit credit THERE is still unsigned policy (docs/19 §10). "
                     "The two answers below are deliberately not blended: the metric measures "
                     "text, the coverage counts judgments."),
            # --- 1. measurement: recomputed from the current body, meaning unchanged --------
            "degeneration_now": {
                "flagged": det.get("flagged"),
                "zones": (det.get("worst") or [])[:6],
            },
            "original_zones": len(orig),
            "zones_with_repairs": sum(1 for z in orig if z["line"] in repaired_lines),
            "repairs": len(self.manifest.get("repairs", [])),
            # --- 2. provenance: what a human has actually done about it --------------------
            "coverage": cov,
            # --- 3. a recommendation that reads both, and claims no more than it may -------
            "vault_recommendation": {
                "eligible": eligible,
                "why": why,
                "route": "bless rail (S56) — the machine never credits an image as text; "
                         "the operator signs that the images carry what the text cannot",
            },
        }

    # ---- the final report (S76, docs/28 §3) --------------------------------------------------
    def repairs_report(self, write: bool = False) -> dict:
        """Walk the ledger and the triage into the artifact that should travel with the vault
        note: what was done to this book, by whom, and what is still open."""
        self._require_md()
        evs, cov = self.ledger(), self.coverage()
        body_chars = len(self.body())
        removed = sum(e["chars"]["removed"] for e in evs if e["gesture"] != "undo")
        added = sum(e["chars"]["added"] for e in evs if e["gesture"] != "undo")
        by_gesture: dict[str, int] = {}
        for e in evs:
            by_gesture[e["gesture"]] = by_gesture.get(e["gesture"], 0) + 1
        aud = self.ledger_audit()
        lines = [
            f"# Repairs — {self.manifest.get('source') or self.dir.name}",
            "",
            f"- bundle: `{self.dir.name}`",
            f"- generated: {_now_iso()}",
            f"- ledger: {len(evs)} event(s) across {aud['writes']} write(s); "
            f"chain {'intact' if aud['intact'] else 'BROKEN — a write bypassed the ledger'}"
            f"; body {'matches' if aud['matches_disk'] else 'DOES NOT MATCH'} the newest event",
            "",
            "## What changed",
            "",
            f"- characters removed: **{removed}** "
            f"({removed / max(1, body_chars + removed) * 100:.3f}% of the document)",
            f"- characters added: **{added}**",
            "- gestures: " + (", ".join(f"{k} ×{v}" for k, v in sorted(by_gesture.items()))
                              or "none"),
            "",
            "## Located damage",
            "",
            "| site | where | outcome | reason |",
            "|---|---|---|---|",
        ]
        for s in cov["sites"]:
            where = f"line {s['at']}" if s["kind"] == "zone" else f"p{s['page']}"
            lines.append(f"| {s['kind']} | {where} | `{s['outcome']}` | {s['reason'] or '—'} |")
        lines += [
            "",
            f"**{cov['addressed']} of {cov['total']} addressed · {cov['open']} still open.**",
            "",
            "## What this report does and does not claim",
            "",
            "- `text-restored` was verified by re-measurement; the text genuinely exists now.",
            "- `image-restored` means a human placed the page image. A reader can read it; a",
            "  text comparison still counts the passage missing, and that is correct.",
            "- `collapsed` removed noise. Nothing was recovered and nothing is claimed.",
            "- `dismissed-noise` is an operator judgment that the witness itself was garbage —",
            "  on a scan lane the witness is OCR too, so a 'loss' can be the converter",
            "  correctly declining to reproduce nonsense.",
        ]
        text = "\n".join(lines) + "\n"
        if write:
            (self.dir / "REPAIRS.md").write_text(text, encoding="utf-8")
        return {"markdown": text, "written": bool(write),
                "path": str(self.dir / "REPAIRS.md") if write else None,
                "chars_removed": removed, "chars_added": added,
                "entropy_pct": round(removed / max(1, body_chars + removed) * 100, 3)}


# ---- the picker (S66): what the ◆ icon can open, and the switch itself ----------------------
def library_listing() -> dict:
    """Server-side enumeration for the picker — the browser can never hand us a real path,
    so the bench offers the pipeline's own places, newest first."""
    def bundles(root: Path, cap: int = 30) -> list[dict]:
        out: list[dict] = []
        if not root.is_dir():
            return out
        dirs = sorted((d for d in root.iterdir() if d.is_dir()),
                      key=lambda d: d.stat().st_mtime, reverse=True)[:cap]
        for d in dirs:
            mds = [p for p in d.iterdir() if p.suffix == ".md"]
            if len(mds) != 1:
                continue
            man: dict = {}
            try:
                man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — a folder without a manifest still lists
                pass
            out.append({
                "path": str(d), "name": d.name, "source": man.get("source"),
                "verdict": (man.get("fidelity") or {}).get("verdict"),
                "repairs": len(man.get("repairs") or []), "pages": man.get("pages"),
            })
        return out
    pdfs = []
    if DONE.is_dir():
        for p in sorted(DONE.glob("*.pdf"), key=lambda q: q.stat().st_mtime, reverse=True)[:30]:
            pdfs.append({"path": str(p), "name": p.name,
                         "mb": round(p.stat().st_size / 1048576, 1)})
    return {"held": bundles(HELD), "pending": bundles(PENDING),
            "anchor": bundles(ANCHOR), "pdfs": pdfs}


def open_target(path_str: str) -> Bench:
    """Open a picker choice — allowlist-contained: only paths inside the pipeline's own
    roots (or the bench sandbox) may be opened, and only as the types we know."""
    p = Path(path_str).resolve()
    if not any(str(p).lower().startswith(str(root.resolve()).lower() + os.sep)
               or p == root.resolve() for root in OPEN_ROOTS):
        raise ValueError("path is outside the bench's allowed roots")
    return Bench(p)


# ---- the loopback token (S108 Lane D) --------------------------------------------------------
#
# docs/38 §9.4: "Loopback is a network boundary, not authentication; another local process may
# still be hostile. Any future route that mutates files requires the same path/authority
# scrutiny as a native command." Until now NOTHING here checked who was POSTing — any local
# process, or a hostile web page firing a preflight-free cross-origin POST at 127.0.0.1:7077,
# could rewrite the bundle body (the security wiki measured the absence: zero Origin/token/CSRF
# checks in this file). Every POST route below either writes (body / assets / manifest /
# REPAIRS.md), swaps server state (/api/open), or spends the GPU (/api/transcribe, /api/assist),
# so the WHOLE POST verb sits behind one gate — a route added later cannot forget it.
MUTATING_POSTS = (
    "/api/repair",            # writes assets/ + body + manifest
    "/api/md",                # rewrites the body (manual ✎ save)
    "/api/open",              # swaps the served bundle (server state)
    "/api/transcribe",        # spawns the docling worker (GPU + temp files)
    "/api/transcribe_apply",  # writes body + manifest
    "/api/collapse_preview",  # computes only, but the POST verb keeps one uniform gate
    "/api/collapse",          # writes body + manifest
    "/api/assist",            # ships body text to the local model, then writes the body
    "/api/undo",              # writes the body (and may pop a manifest record)
    "/api/triage",            # writes the manifest
    "/api/report",            # writes REPAIRS.md when {"write": true}
)

# In-process harnesses (acceptance.py) construct the handler directly and are already on the
# trusted side of the process boundary — the gate exists for NETWORK callers, and every
# network-reachable server goes through main(), which always passes the operator's choice.
_NO_GATE = object()


def token_gate(presented: str | None, expected) -> str | None:
    """None = admitted. A string = the honest 403 reason. Constant-time compare."""
    if expected is _NO_GATE:
        return None
    if expected is None:
        return ("mutating routes are disabled: bench.py was started without --token. "
                "Restart it as `bench.py <bundle> --token <secret>` (the widget does this "
                "itself) and open the page as /?token=<secret>.")
    if not presented or not hmac.compare_digest(
            presented.encode("utf-8"), str(expected).encode("utf-8")):
        return ("X-FP-Token missing or wrong — reload the page with ?token=<the value passed "
                "to --token> so the UI attaches it to every mutating request.")
    return None


# ---- the thin HTTP layer ---------------------------------------------------------------------
def make_handler(bench: Bench, token=_NO_GATE):
    bench0 = bench

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200):
            self._send(code, json.dumps(obj).encode("utf-8"))

        def do_GET(self):
            bench = getattr(self.server, "bench", bench0)  # S66: the picker can swap it
            try:
                url = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(url.query)
                if url.path == "/":
                    # Read fresh per request (S65): a UI update reaches the user on F5,
                    # not on the next server respawn — the help must never be stale.
                    self._send(200, (BENCH_DIR / "bench.html").read_bytes(),
                               "text/html; charset=utf-8")
                elif url.path == "/api/state":
                    self._json(bench.state())
                elif url.path == "/api/md":
                    self._json({"text": bench.body()})
                elif url.path == "/api/page":
                    n = int(q.get("n", ["1"])[0])
                    dpi = int(q.get("dpi", [str(RASTER_DPI)])[0])
                    self._send(200, bench.page_png(n, min(dpi, 300)), "image/png")
                elif url.path == "/api/asset":
                    name = Path(q.get("name", [""])[0]).name  # basename only — no traversal
                    p = bench.assets / name
                    if p.is_file():
                        self._send(200, p.read_bytes(), "image/png")
                    else:
                        self._json({"error": "no such asset"}, 404)
                elif url.path == "/api/ledger":
                    self._json({"events": bench.ledger(), "audit": bench.ledger_audit(),
                                "coverage": bench.coverage()})
                elif url.path == "/api/rescore":
                    self._json(bench.rescore_preview())
                elif url.path == "/api/evidence":  # OK-15 — read-only, in-memory quarantine
                    # Expensive GETs still need the loopback capability: a hostile page can
                    # fire no-CORS localhost requests and otherwise spawn unbounded 900 s
                    # render/Xpdf children. _ok15_lock collapses concurrent admitted calls.
                    deny = token_gate(self.headers.get("X-FP-Token"), token)
                    if deny:
                        self._json({"error": deny}, 403)
                    else:
                        self._json(bench.ok15_evidence())
                # ---- the reader (S62b, Okular pass) -------------------------------------
                elif url.path == "/api/toc":
                    self._json({"toc": bench.toc()})
                elif url.path == "/api/find":
                    self._json(bench.find(q.get("q", [""])[0]))
                elif url.path == "/api/rects":
                    self._json({"rects": bench.rects(int(q.get("n", ["1"])[0]),
                                                     q.get("q", [""])[0])})
                elif url.path == "/api/locate":
                    self._json(bench.locate_zone(int(q.get("i", ["0"])[0])))
                elif url.path == "/api/trimbox":   # OK-7 — read-only, computes + caches
                    self._json(bench.trimbox(int(q.get("n", ["1"])[0])))
                elif url.path == "/api/textlayer":  # OK-5 — read-only, lazy + LRU-bounded
                    self._json(bench.textlayer(int(q.get("n", ["1"])[0])))
                elif url.path == "/api/table":      # OK-6 — read-only extraction preview
                    rect = [float(x) for x in q.get("rect", ["0,0,1,1"])[0].split(",") if x]
                    if len(rect) != 4:
                        self._json({"error": f"rect needs 4 numbers, got {len(rect)}"}, 400)
                        return
                    # "none" = the caller DELETED the last divider — an empty list, which a
                    # blank query value cannot carry (parse_qs drops blanks; review MAJOR)
                    def _divs(key):
                        if key not in q:
                            return None
                        v = q[key][0]
                        return [] if v in ("", "none") else [float(x) for x in v.split(",") if x]
                    self._json(bench.table(int(q.get("n", ["1"])[0]), rect,
                                           _divs("cols"), _divs("rows")))
                elif url.path == "/api/library":
                    self._json(library_listing())
                else:
                    self._json({"error": "unknown path"}, 404)
            except Exception as exc:  # noqa: BLE001 — report, never crash the bench
                self._json({"error": str(exc)[:300]}, 500)

        def do_POST(self):
            bench = getattr(self.server, "bench", bench0)  # S66: the picker can swap it
            # The loopback-token gate, BEFORE any dispatch (see MUTATING_POSTS above).
            deny = token_gate(self.headers.get("X-FP-Token"), token)
            if deny:
                # Drain the request body first: answering while the client is still sending
                # makes Windows abort the socket (WinError 10053, measured by this file's own
                # test suite) and the remedy text never reaches the caller.
                try:
                    self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
                except (OSError, ValueError):
                    pass
                self._json({"error": deny}, 403)
                return
            try:
                n = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(n) or b"{}")
                if self.path == "/api/repair":
                    self._json(bench.repair(
                        zone_line=int(payload["zone_line"]),
                        page=int(payload["page"]),
                        rect=payload.get("rect"),
                        image_b64=payload.get("image_b64"),
                        note=str(payload.get("note", ""))[:120],
                    ))
                elif self.path == "/api/md":
                    # docs/28: the manual ✎ save was the one path that left NO trace at all —
                    # it now goes through the same chokepoint as every gesture.
                    bench._require_md()
                    prev_body = bench.body()
                    evs = bench._write_body(str(payload["text"]), gesture="manual-edit",
                                            note="✎ edit")
                    if evs:                      # a no-op save must not burn an undo slot
                        bench._undo.append(("manual-edit", prev_body))
                        del bench._undo[:-20]
                    self._json({"saved": True, "events": len(evs),
                                "chars_removed": sum(e["chars"]["removed"] for e in evs),
                                "chars_added": sum(e["chars"]["added"] for e in evs),
                                "undo_depth": len(bench._undo)})
                elif self.path == "/api/open":
                    new_bench = open_target(str(payload["path"]))
                    self.server.bench = new_bench
                    self._json(new_bench.state())
                elif self.path == "/api/transcribe":
                    self._json(bench.transcribe(
                        zone_line=int(payload["zone_line"]), page=int(payload["page"]),
                        rect=payload["rect"]))
                elif self.path == "/api/transcribe_apply":
                    self._json(bench.transcribe_apply(
                        zone_line=int(payload["zone_line"]), page=int(payload["page"]),
                        markdown=str(payload.get("markdown", "")),
                        gates=payload.get("gates"), secs=payload.get("secs"),
                        rect=payload.get("rect")))
                elif self.path == "/api/collapse_preview":
                    self._json(bench.collapse(zone_line=int(payload["zone_line"]),
                                              preview=True))
                elif self.path == "/api/collapse":
                    self._json(bench.collapse(zone_line=int(payload["zone_line"])))
                elif self.path == "/api/assist":
                    self._json(bench.assist(
                        start=int(payload["start"]), end=int(payload["end"]),
                        instruction=str(payload.get("instruction", ""))[:500],
                    ))
                elif self.path == "/api/undo":
                    # docs/28 §5.2: ledger-driven, so ctrl-Z survives a bench restart
                    self._json(bench.undo_ledger())
                elif self.path == "/api/triage":
                    self._json(bench.triage(str(payload["key"]),
                                            str(payload["outcome"]),
                                            str(payload.get("reason", ""))))
                elif self.path == "/api/report":
                    self._json(bench.repairs_report(write=bool(payload.get("write"))))
                else:
                    self._json({"error": "unknown path"}, 404)
            except Exception as exc:  # noqa: BLE001
                self._json({"error": str(exc)[:300]}, 500)

    return Handler


def main():
    # The console may be cp1252 (the preview launcher's is; PowerShell's usually isn't) —
    # the banner's ✓/· glyphs must never crash the server. errors="replace" keeps whatever
    # encoding the console really has and degrades glyphs to '?' instead of dying — the
    # machine's known encode class (S48's pipe lesson, print side). Found live 2026-08-03.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="The Repair Bench (prototype)")
    ap.add_argument("bundle", help="bundle dir, or a bare sha16 resolved against held/")
    ap.add_argument("--pdf", type=Path, help="source PDF (default: drop/done/<manifest.source>)")
    ap.add_argument("--sandbox", action="store_true",
                    help="repair a COPY under .sandbox/ — trial mode, originals untouched")
    ap.add_argument("--port", type=int, default=7077)
    # CONTRACT (the widget half is Lane G, windows-widget/src-tauri/src/bench.rs): the widget
    # generates a random secret per spawn, passes it here as `--token <secret>`, and appends
    # `?token=<secret>` to the WebviewUrl so bench.html can read it at load and attach it as
    # X-FP-Token on every mutating request. Without --token the mutating routes FAIL CLOSED
    # (403 with the remedy in the body) — see token_gate above.
    ap.add_argument("--token", default=None,
                    help="shared secret; every POST route requires a matching X-FP-Token "
                         "header (no --token = mutating routes answer 403)")
    args = ap.parse_args()
    bench = Bench(args.bundle, pdf=args.pdf, sandbox=args.sandbox)
    st = bench.state()
    print(f"REPAIR BENCH · {st['bundle']}{'  [SANDBOX]' if st['sandbox'] else ''}")
    print(f"  verdict {st['verdict']} · {len(st['zones'])} zone(s) · {st['pages']} pp · "
          f"pdf {'✓ ' + str(bench.pdf) if st['pdf_available'] else 'NOT FOUND (markdown-only)'}")
    print("  mutating routes: " + ("token-gated (--token)" if args.token else
                                   "DISABLED — started without --token, POSTs answer 403"))
    print(f"  → http://127.0.0.1:{args.port}/   (Ctrl+C to close)")
    ThreadingHTTPServer(("127.0.0.1", args.port),
                        make_handler(bench, token=args.token)).serve_forever()


if __name__ == "__main__":
    main()
