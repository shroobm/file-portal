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
import os
import re
import shutil
import sys
import urllib.parse
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
        mds = [p for p in self.dir.iterdir() if p.suffix == ".md"] if self.dir.is_dir() else []
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
        zones = []
        for z in self.zones():
            guess = max(1, min(pages, round(z["line"] / md_lines * pages))) if md_lines else 1
            at, anchor = self._resolve_zone_line(z)
            zones.append({**z, "page_guess": guess,
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
            "runs": self.runs()[:40],
            "repairs": self.manifest.get("repairs", []),
            "pdf_available": self.pdf is not None,
            "pdf": str(self.pdf) if self.pdf else None,
            "manifest_present": self.manifest_path.is_file(),
            "undo_depth": len(self._undo),
            # S66 accuracy pass — everything the info popover states, straight from source:
            "pdf_only": self.pdf_only,
            "md_name": self.md_path.name if self.md_path else None,
            "source_sha16": (self.manifest.get("source_sha256") or "")[:16] or None,
            "doc_survival": (self.manifest.get("fidelity", {}).get("convert", {})
                             .get("doc_survival")),
            "audit_kind": self.manifest.get("fidelity", {}).get("convert", {}).get("kind"),
            "converted_at": self.manifest.get("converted_at"),
        }

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
            self._texts = [
                " ".join(self.doc().load_page(i).get_text("text").lower().split())
                .replace("- ", "")
                for i in range(self.doc().page_count)
            ]
        return self._texts

    def find(self, q: str, limit: int = 40) -> dict:
        q = " ".join(q.strip().lower().split())
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

    def rects(self, n: int, q: str) -> list[list[float]]:
        """Highlight rectangles for q on page n, as page-fraction boxes the UI overlays."""
        page = self.doc().load_page(max(0, min(self.doc().page_count - 1, n - 1)))
        r = page.rect
        out = []
        for hit in page.search_for(q)[:60]:
            out.append([hit.x0 / r.width, hit.y0 / r.height,
                        hit.x1 / r.width, hit.y1 / r.height])
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
        self.md_path.write_text(fm + "\n".join(lines), encoding="utf-8")

        rec = {"ts": _now_iso(), "zone_line": zone_line, "page": page, "asset": asset,
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
        self.md_path.write_text(fm + "\n".join(lines), encoding="utf-8")
        # NO drift-ledger entry: the shift travels in the record's `lines` (restart-safe),
        # and undo_ai pairs the snapshot with the record so provenance can never desync.
        rec = {"ts": _now_iso(), "zone_line": zone_line, "page": page, "asset": None,
               "mode": "transcribe", "model": "granite-docling-258M", "lines": len(inserted),
               "gates": gates or {}, "secs": secs, "by": "repair-bench",
               "dpi": CROP_DPI, "rect": rect}
        self.manifest.setdefault("repairs", []).append(rec)
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n",
                                      encoding="utf-8")
        return {"inserted_after_line": at, "lines": len(inserted),
                "undo_depth": len(self._undo), "record": rec}

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
        self.md_path.write_text(fm + "\n".join(lines), encoding="utf-8")

        rec = {"ts": _now_iso(), "zone_line": zone_line, "page": None, "asset": None,
               "mode": "collapse", "by": "repair-bench", "delta": delta,
               "chars_removed": removed, "period_tokens": p, "repeats": repeats,
               "cycle": one[:80], "anchor": anchor}
        self.manifest.setdefault("repairs", []).append(rec)
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n",
                                      encoding="utf-8")
        return {"record": rec, "undo_depth": len(self._undo), "chars_removed": removed,
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
            return {"applied": False, "unchanged": True, "undo_depth": len(self._undo)}
        self._backup_once()
        self._undo.append(("assist", body))
        del self._undo[:-20]  # bounded stack — twenty regrets is plenty
        new_lines = restored.split("\n")
        self._ai_drift.append((start, len(new_lines) - (end - start + 1)))
        lines[start - 1:end] = new_lines
        self.md_path.write_text(fm + "\n".join(lines), encoding="utf-8")
        return {"applied": True, "start": start, "lines_before": end - start + 1,
                "lines_after": len(new_lines), "undo_depth": len(self._undo)}

    def undo_ai(self) -> dict:
        """The ctrl-Z button: restore the body exactly as it was before the last AI change.
        Kind-aware (S71): undoing an assist pops its drift entry; undoing a transcription
        pops its manifest.repairs record too — body and provenance can never disagree."""
        self._require_md()
        if not self._undo:
            raise ValueError("nothing to undo")
        kind, body = self._undo.pop()
        fm, _ = split_frontmatter(self.md_path.read_text(encoding="utf-8"))
        self.md_path.write_text(fm + body, encoding="utf-8")
        if kind == "assist" and self._ai_drift:
            self._ai_drift.pop()
        if kind in ("transcribe", "collapse"):
            reps = self.manifest.get("repairs", [])
            if reps and reps[-1].get("mode") == kind:
                reps.pop()
                self.manifest_path.write_text(
                    json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8")
        return {"undone": True, "undo_depth": len(self._undo), "kind": kind}

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
        return {
            "preview": True,
            "note": ("PREVIEW ONLY — the shipping audit re-runs in the pipeline, and whether a "
                     "repair image earns credit is an unsigned policy (Rab signs; docs/19 §10)"),
            "degeneration_now": {
                "flagged": det.get("flagged"),
                "zones": (det.get("worst") or [])[:6],
            },
            "original_zones": len(orig),
            "zones_with_repairs": sum(1 for z in orig if z["line"] in repaired_lines),
            "repairs": len(self.manifest.get("repairs", [])),
        }


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


# ---- the thin HTTP layer ---------------------------------------------------------------------
def make_handler(bench: Bench):
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
                elif url.path == "/api/rescore":
                    self._json(bench.rescore_preview())
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
                elif url.path == "/api/library":
                    self._json(library_listing())
                else:
                    self._json({"error": "unknown path"}, 404)
            except Exception as exc:  # noqa: BLE001 — report, never crash the bench
                self._json({"error": str(exc)[:300]}, 500)

        def do_POST(self):
            bench = getattr(self.server, "bench", bench0)  # S66: the picker can swap it
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
                    bench._require_md()
                    bench._backup_once()
                    fm, _ = split_frontmatter(bench.md_path.read_text(encoding="utf-8"))
                    bench.md_path.write_text(fm + str(payload["text"]), encoding="utf-8")
                    self._json({"saved": True})
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
                    self._json(bench.undo_ai())
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
    args = ap.parse_args()
    bench = Bench(args.bundle, pdf=args.pdf, sandbox=args.sandbox)
    st = bench.state()
    print(f"REPAIR BENCH · {st['bundle']}{'  [SANDBOX]' if st['sandbox'] else ''}")
    print(f"  verdict {st['verdict']} · {len(st['zones'])} zone(s) · {st['pages']} pp · "
          f"pdf {'✓ ' + str(bench.pdf) if st['pdf_available'] else 'NOT FOUND (markdown-only)'}")
    print(f"  → http://127.0.0.1:{args.port}/   (Ctrl+C to close)")
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(bench)).serve_forever()


if __name__ == "__main__":
    main()
