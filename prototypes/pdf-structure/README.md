# prototypes/pdf-structure — the structure-tree probes (quarantine)

**Category:** pdf-structure · **Name:** probes · **Written:** 2026-09-02 (S114) by the Opus mapper,
the Opus designer and the Fable verifier of the docs/52 fleet. **Nothing in the live system imports,
spawns, or reads any of this.** Safe to delete.

`probes/` holds the read-only scripts behind `docs/52-pdf-structure-study/` — every number in
`mapping.md`, `design.md` and `VERIFIED.md` was produced by one of these and can be re-run with the
marker-env interpreter (`C:\Users\Bndit\ml\marker-env\Scripts\python.exe`), CPU only, no GPU, no
`.gpu-lock` interaction. Run with `PYTHONIOENCODING=utf-8`: `gate_real.py` dies on the bojieli row under
a cp1252 console and the one positive vanishes silently (verifier residue).

| probe | what it measures |
|---|---|
| `probe_a_api.py` … `probe_l_artifact.py` | the mapper's twelve: pymupdf's two doors into the tree, element→bbox, tables from the tree, reading order declared vs geometric, artifact boundary vs the 40 %-repeat heuristic, the Downloads survey |
| `corpus_probe.py` · `doora_probe.py` · `gate_real.py` · `ledger_read.py` · `roles.py` | the designer's: the T0–T3 gate on Rab's real anchor corpus, density, roles, the conversion ledger |
| `cost_probe.py` | per-page cost of tree reading on real books (the `+0.42 ms/page` in mapping.md is one run on a 57-page spec; real books are +3.7 to +116 ms/page) |
| `decoy.py` | the planted-`/Alt` negative control — four hand-built PDFs, sentinel in an attribute no glyph reader can see; 4/4 GREEN, D4 watched failing |
| `cdx0043_probe.py` | Codex's two `evidence_count` controls |
| `parse_table5.py` · `render_table5.js` · `verify_table5.js` | the TS 32005 Table 5 reconstruction and its 1,193-check cross-validation |
| `verify/` | the verifier's own re-runs (`survey_rerun.tsv`, `markinfo_and_manifest.py`) |
| `survey.tsv` | the Downloads survey — **`Marked` column poisoned, see ERROR-BIN ERR-049** |

Graduation of anything here into `windows-converter/` is a separate signed decision (J27 as scoped in
`design.md` §6). The quarantine convention is `prototypes/README.md`.
