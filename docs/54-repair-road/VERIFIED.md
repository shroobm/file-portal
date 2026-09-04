# VERIFIED — the Fable verifier lane over J31 / J32 / J33 (fleet `wf_d92d7e9a-f2d`, re-run 2026-09-04 evening)

⟨claimed: Fable (verifier lane, session model), 2026-09-04, Desktop⟩

GROUND docs/47. Read-only on `C:/Users/Bndit/Projects/file-portal` and `C:/Users/Bndit/ml/library` throughout
(no write, stage, commit, push; no converter / widget / marker / ollama; no GPU). Everything I wrote is under
`scratchpad/verify-tickets/V/` (`v_a.py`, `v_b.py`, `v_c.py` + `*_result.json` + `*.log`) and this file.
Interpreters: `C:/Users/Bndit/ml/marker-env/Scripts/python.exe` for everything importing `fidelity_audit` /
`analyst`; `C:/Users/Bndit/.local/bin/python3.12.exe` otherwise; `PYTHONIOENCODING=utf-8`.

## 0. Two facts about the ground that change what "the draft tickets" means

1. **HEAD is `48cb7e2`, not `11c9af1`** (`Observed`; `11c9af1` is an ancestor). Two post-close commits landed
   while the fleet ran: `23fc659` *registered J31–J33 in `OPEN-TASKS.md` as PROPOSED, already amended by the
   three Sonnet lanes*, plus SYM-073's cause and SYM-074; `48cb7e2` corrected SYM-074's cause. No code file
   changed (`git diff --stat 11c9af1..HEAD` = OPEN-TASKS.md, SYMPTOM-INDEX.md, the session record), so every
   measurement below is on the same code the lanes measured. **I therefore verified BOTH the draft wording in my
   GROUND and the registered rows Rab will actually read** — the verdicts in §5 are against the registered rows,
   with the amendments they still need.
2. The three lane reports were banked; the earlier verifier never ran (usage limit). This is that lane.

## 1. Probes re-run by the verifier (which, and what they returned)

All numbers: numerator / denominator / conditions. `Verified` = my own re-run with the repo's functions.

### Lane A (J32) — `V/v_a.py`, 290 s
- **Mirror** (decisive): `fidelity_audit.audit_analyst(Marker body rebuilt from the LIBRARY slice cache, held body)`
  = doc_survival **0.9402** (38,018 of 40,438 twelve-word windows contained, exact containment after
  `prepare_output`), **404 runs**, max run 576 words — identical for the raw `"\n\n".join` and for the
  link-rewritten form the pipeline hands the analyst (`rewrite_image_links`); equals the manifest. `Verified`.
- **Ladder, three implementations on the same book** (decisive for the registered digits):

  | rung | builder's regexes (re-run by me) | lane A's regexes (A's run) | verifier's own regexes |
  |---|---|---|---|
  | as shipped | 2,420 / 40,438 → 0.9402, 404 runs | same | same |
  | + unescape | 1,763 / 40,437 → **0.9564**, 254 runs | 1,769 / 40,419 → 0.9562 | 1,727 / 40,438 → 0.9573 |
  | + punctuation-free | 1,288 / 42,235 → **0.9695**, 185 runs | 1,169 / 39,461 → 0.9704 | 1,283 / 42,238 → 0.9696 |
  | + space-free, CUMULATIVE (3-step) | 646 / 42,235 → **0.9847**, 54 runs, max 372 | 641 / 39,461 → 0.9838, 59 runs | 644 / 42,238 → 0.9848, 59 runs |
  | unescape + space-free ONLY (2-step) | 1,141 / 40,437 → **0.9718**, 120 runs, max 588 | — | 1,102 / 40,438 → 0.9727 |

  The builder's numbers reproduce exactly with the builder's regexes — and **the builder's `0.9718` is the 2-step
  row, not the cumulative third rung**: `univ4e_classify2.py` skips both space-free variants in its first loop
  (`if spacefree: continue`) and its second loop measures only unescape + space-free; the cumulative 3-step was
  never computed. With the builder's own regexes it is **0.9847** (646 failed of 42,235). Three independent
  regex sets agree to within 0.001 on the cumulative rung (0.9838 / 0.9847 / 0.9848). `Verified`.
- **Residue after full normalisation** = 1.52–1.62 % of windows, not "≈2.8 %"; failed windows over-counted
  ≈3.7× (2,420 → 646), runs ≈7× (404 → 54–59) — "≈2×" is the 2-step figure only.
- **Attribution to chunks** (analyst's own `fence` + `_chunks`, 957 chunks = manifest passed 928 + rejected 29;
  position-aware 6-word locator): 2-step still-failing windows located 765 of 1,102 (69.4 %, own regexes) /
  780 of 1,141 (68.4 %, builder's); chunks carrying located loss 378–391 of 957; 80 % of it in 222–238 chunks.
  Front matter (chunks 1–15, chunk 1 = "INVESTMENT VALUATION Tools and Techniques…") carries **3 of 765**
  located windows; median loss chunk ≈450 of 957. The top three losers are chunks **296** (the line-8776 runaway,
  43–45 windows), **23** (30), **78** (24). `Verified`.
- **Deletions, journal-independent** (paragraph containment of the input chunk in the SHIPPED body): chunk 23 —
  3 of its 5 prose paragraphs (361 words) absent ("can you avoid being biased? we don't think so…",
  "institutional concerns play a role…", "as consumers of other people's valuations…"); chunk 78 — 2 of 4
  (308 words: "the argument that diversification reduces an investor's exposure to risk…", "this argument is
  powerful…"). Not rewordings. `Verified`. (Chunks 678/128 also show "absent" paragraphs, but those are
  `\$`-escape artifacts at baseline — not claimed as deletions.)
- **Journal provenance** (decisive for the "16 of 29" sentence): the resume key of today's rebuilt fenced text is
  `5d885aa52e9e96d6` (raw and rewritten forms identical); the surviving `.analyst-work/d58db211c41b0e17/
  chunks.jsonl` (646 lines, mtime 2026-08-30 21:34) is keyed to a DIFFERENT Marker output — the 2026-08-30
  attempt's — which is why it survived (its run never reached the `rmtree` at `analyst.py:446`) and why only
  516 of its 646 records hash-validate against today's chunks (16 of them rejected). The 2026-09-01 run's own
  journal (`5d885aa5…`, the 641 fsync'd records the power cut spared) was deleted on success, as designed. Loss
  windows in the 16 identifiable rejected chunks: 6–7 (baseline / 2-step, own and builder regexes); lane A 9;
  builder 10. `Verified`.
- **A deletion guard, measured** (new; solution material for J32): per-chunk survival of the INPUT chunk's
  12-word windows in the journal's accepted OUTPUT, on the 500 hash-validated `passed` records of the 08-30
  journal (same model qwen3:8b, same program, same text for those chunks; baseline normalisation, so escapes
  count against a chunk — an upper bound on rejections): 5 chunks < 0.50 (they carry 104 of the 811 located
  baseline-loss windows in that sample), 32 < 0.80 (255 windows, 31 %), 100 < 0.90 (458), 179 < 0.95 (615).
  The three named disasters all sit below 0.50: chunk **296** at 0.14 (673 words in → **5,164 words out**: the
  fence passed a 7.7× inflation — the line-8776 runaway is the analyst's amplification of Marker's 3,005-char
  block), chunk **23** at 0.37, chunk **78** at 0.40. A length-ratio guard (< 0.9 words) would catch 9 chunks
  and miss the inflation; the window check catches both directions. `Verified` on that sample.
- **Mentions** figure N.N 664 marker / 662 held, table N.N 599 / 595. `Verified`.
- **Negative control**: a real passing window with one interior word replaced by `xqzplonkotron9999` fails
  containment at every rung (baseline / unescape / punct-free / space-free); the unpoisoned window passes at
  baseline. Positive escape-only example: `…equity market \(1960- 2023\) figure 7.5…` fails as shipped and
  passes after unescape — the class the gate over-counts.

### Lane B (J31) — `V/v_b.py`, four `audit_convert` runs of 48–51 s each (1,372 pages scored per run)
| text audited | doc_survival | pages flagged / 1,372 | runs_total | degeneration | convert-alone | with historical analyst |
|---|---|---|---|---|---|---|
| Marker body (slice cache), unrepaired | **0.9334** | **241** (list identical to the manifest's, page for page) | **531** | true — 1 block, line 8795, 3,005 chars, zlib 0.074, trigram ×62 | fail | fail |
| held md (post-analyst), unrepaired | 0.9271 | 257 | 570 | true — 1 block, line 8776, 21,870 chars, zlib 0.011, trigram ×441 | fail | fail |
| Marker body, lines 8795–8796 deleted (3,004 chars) | 0.9334 | 241 | 531 | false, 0 blocks | **flag** | fail |
| held md, line 8776 deleted (21,870 chars) | 0.9271 | 257 | 570 | false, 0 blocks | **flag** | fail |

PDF sha256 = manifest `source_sha256` (byte hash). `Verified`: the manifest's convert block is the audit of the
PRE-analyst Marker body (SYM-073's cause — the 241-page list reproduces exactly); the held md is another text;
a repair moves the tripwire and nothing else; with the historical analyst block (0.9402) every variant is `fail`.
Controls: a synthetic `{\rm Int}…` runaway appended to the repaired text trips `degeneration()` (1 block); the
repaired text alone is quiet (0). `</think>` at held lines 8779 and 13744 (SYM-074) `Observed`. Code
(`Verified` by reading): `assay.rs::bless` filters `ev["stage"]=="audit" && ev["event"]=="scored"` (literal);
`exporter.py` imports no `fidelity_audit` and reads `fidelity.verdict` + `bless.json` + `source_sha256` only;
both `ship()` callers (`:1775`, `:1824`) pass through `_enforce_hold()`; **`audit-mode.txt` = `enforce` today**.

### Lane C (J33) — `V/v_c.py`
- Slice cache: 7 files, 434,154 + 548,315 + 582,998 + 534,142 + 623,465 + 566,574 + 196,988 = **3,486,636 bytes
  on disk (CRLF)**; merged in memory 3,448,179 chars = 3,456,965 UTF-8 bytes; held md 3,493,819 bytes;
  1,377 pages → **≈2.5 KB/page**. `Verified`.
- Held Univ 4e md: max asset page `_page_1222_`, max span id `page-1227`, `2553` occurs 0 times. The
  2025-edition held bundle `0d68f0e02293970c` (1,356 pages) carries `_page_2553_` once — the sentence in lane C's
  brief was a real observation about a DIFFERENT bundle, misattributed. `Verified`.
- Exporter / bench guards (`Verified` by reading): create path `copytree(bundle_dir, tmp, ignore=skip)` with
  `_skip_blocks` filtering only the literal `blocks.json` (`:153-160`, `:421-422`); supersede path requires exactly
  one `.md` (`:506-511`, `ExportError`); `bench.py:250-263` requires exactly one `.md` (`SystemExit`). **Three more
  guards the registered J33 does not name**: `bench.py:1965` (the picker `continue`s past any bundle with ≠1 `.md`
  — a sidecar makes the bundle vanish from the bench's list), `convert_and_ship.py:1858` (`_anchor_copies`
  skips bundles with ≠1 `.md` — a sidecar makes the bundle un-addressable for `--reanalyze`),
  `coverage_rescore.py:103` (`RescoreUnread`); plus `acceptance.py:45` takes the first `.md` it meets and
  `room.rs:258` lists every `.md` (cosmetic).
- **Marker references on disk — the decisive probe**: `anchor/` holds `<name>` beside `<name> [analyst-local]`
  for the same `source_sha256`. For every pair whose original has no analyst block,
  `audit_analyst(original body, re-run body)` **reproduces the re-run manifest's `fidelity.analyst` exactly**:
  Damodaran 2025 4e 0.9525 (234 runs, max 624), Valentine 0.9303, Diagnosing 0.9791 (max run 24), claude-code
  0.9493 and its rerun 0.9547; Brain of the Firm is a sixth valid pair with no stored block (computed 0.9621).
  Control: bojieli's "original" carries an analyst block (inline-analysed) → not a reference, excluded
  (computed 0.9966). So **six Marker-reference/analyst pairs exist on disk, not one**: the anchor copy at
  `convert_and_ship.py:1988` is written right after `convert()`, i.e. PRE-analyst whenever the book went through
  the pending card (`--defer-analyst` → `resume()` anchors the analysed one as `[analyst-<backend>]`); only an
  inline `--analyst` run (the Univ 4e voyage) anchors post-analyst text. `Verified`.
- The ladder on those pairs (verifier regexes, baseline → unescape → unescape+punct+space): Damodaran 2025
  0.9525 → 0.9664 → 0.9842; claude-code 0.9493 → 0.9547 → 0.9711 (rerun 0.9547 → 0.9601 → 0.9769);
  Valentine (scan) 0.9303 → 0.9329 → 0.9600; Brain (scan) 0.9621 → 0.9623 → 0.9739; Diagnosing (scan)
  0.9791 → 0.9794 → 0.9891 (runs 1 → 0). **No book crosses 0.995 after normalisation — the proposal moves no
  verdict on any of the six**; unescape matters on the clean-lane LaTeX books and barely on the scan-lane OCR
  books; a 1–4 % residue of real damage remains on every book.

## 2. Claims checked (lane → my verdict on the lane's finding)

| # | lane | the lane's finding | verdict | checked against |
|---|---|---|---|---|
| 1 | A | mirror reproduces 0.9402 / 404 (CONFIRMED) | CONFIRMED | `v_a.py` mirror on the LIBRARY cache, both reference forms |
| 2 | A | ladder digits are implementation-bound; own set lands 0.9562/0.9704/0.9838 (PARTIAL) | CONFIRMED, and sharpened | builder regexes re-run reproduce 0.9564/0.9695/0.9718 exactly; cumulative 3-step = 0.9847 (builder regexes) / 0.9848 (mine); the draft's 0.9718 is the 2-step |
| 3 | A | 412/246 attribution silently drops ~27–32 % of failing windows (PARTIAL) | CONFIRMED | own locator: 68–69 % located; 378–391 chunks; 222–238 for 80 % |
| 4 | A | "10 windows" rests on 16 of 29 rejected chunks; journal is stale residue, not the run's (PARTIAL) | CONFIRMED, cause found | resume key of today's text `5d885aa5…` ≠ dir `d58db211…`; 516/646 validate; 6–7 windows (own), 9 (A), 10 (builder) |
| 5 | A | front matter intact 664/662, 599/595 (CONFIRMED) | CONFIRMED | `v_a.py` mentions |
| 6 | A | decoy "losses concentrate in the front matter's list of figures" is false (REFUTED) | CONFIRMED | 3 of 765 located windows in chunks 1–15; median chunk ≈450 |
| 7 | A | convert-stage numbers untouched by an analyst-only normalisation, by construction (CONFIRMED) | CONFIRMED | `audit_convert` (`fidelity_audit.py:485`) never calls `audit_analyst`; `:1616` precedes `:1633` |
| 8 | A | chunks 23/78 are paragraph deletions, not rewordings (REFUTED the draft) | CONFIRMED | journal-independent paragraph containment in the shipped body: 3/5 and 2/4 prose paragraphs absent |
| 9 | B | held-md repair flips degeneration 1→0, convert-alone flag, 0.9271/257/570 (CONFIRMED) | CONFIRMED | `v_b.py` held_full_repaired |
| 10 | B | the held md is POST-analyst text; the manifest audited the Marker body (REFUTED the draft) | CONFIRMED, strengthened | Marker body reproduces the manifest's 241-page flagged list page for page |
| 11 | B | the true convert-stage runaway is ~3,000 chars at Marker line 8795; the held 21,870-char block is analyst amplification (CONFIRMED) | CONFIRMED | 3,005 vs 21,870 chars; journal chunk 296: 673 words in → 5,164 out, status `passed` |
| 12 | B | doc_survival / pages_flagged / runs_total do not move with the repair (REFUTED the draft's framing) | CONFIRMED | four runs, two texts, before/after identical |
| 13 | B | overall verdict stays fail on the analyst block regardless (CONFIRMED) | CONFIRMED, and generalised | `compute_verdict` short-circuits on analyst 0.9402 < 0.995; the same holds for 5 of 7 held bundles |
| 14 | B | decoy "the exporter re-runs the audit on arrival" is false (REFUTED) | CONFIRMED | `exporter.py` imports; `_export` reads the verdict as a field |
| 15 | B | bless reads the event stream; `stage: "reaudit"` would never match (PARTIAL) | CONFIRMED | `assay.rs` `.find(|ev| ev["stage"]=="audit" && ev["event"]=="scored" …)`; the registered row already says `stage: "audit"` |
| 16 | B | supersede guard reads verdict + bless.json + sha only; `ship()` is pure transport; `_enforce_hold` unmentioned (CONFIRMED / MINOR) | CONFIRMED, upgraded to MAJOR | `audit-mode.txt` = `enforce`: a still-`fail` re-ship is re-parked, and beside a repairs-bearing occupant as `--superseded-<stamp>` |
| 17 | B | keeping the analyst block historical is honest; re-derived variants 0.9399–0.9406 all fail (CONFIRMED) | CONFIRMED as arithmetic, WRONG as design | honest, but it leaves J31 with no reachable non-fail state for this book (§4 D-1) |
| 18 | C | pre-analyst text exists nowhere in shipped outputs except the slice cache (CONFIRMED) | OVERSTATED | true for inline-analysed books only; five reproducing pre/post pairs sit in `anchor/` |
| 19 | C | slice cache swept only when a different book starts chunking (CONFIRMED) | CONFIRMED | `:1277-1280` |
| 20 | C | decoy "the exporter already ignores any *.marker.md" is false: create path ships it, supersede path crashes (REFUTED) | CONFIRMED | `_skip_blocks`; `:506-511` |
| 21 | C | cost is a per-page rate, ≈3.49 MB on this book (CONFIRMED) | CONFIRMED | 3,486,636 B on disk / 3,456,965 B UTF-8; 2.5 KB/page |
| 22 | C | merge is a plain join; assets copied by name (CONFIRMED) | CONFIRMED | `:1456`, `:1427`, `:1562` |
| 23 | C | "_page_2553_ / page-1205" does not describe this bundle (REFUTED) | CONFIRMED, source found | Univ 4e max 1222 / 1227, `2553` ×0; held `0d68f0e02293970c` (2025 ed., 1,356 pp) carries `_page_2553_` ×1 |
| 24 | C | bench.py + exporter both hard-require one .md; not a one-line change (REFUTED the framing) | CONFIRMED, and widened | three more guards: `bench.py:1965`, `convert_and_ship.py:1858`, `coverage_rescore.py:103` |
| 25 | C | blocks.json precedent shape is reusable (CONFIRMED) | CONFIRMED | `_blocks_status`, `_record_blocks`, `_skip_blocks` |
| 26 | GROUND | "Three Sonnet refuter lanes" | UNREAD | no model stamp in the lane outputs |
| 27 | GROUND / J32 draft + registered row | "only one Marker reference exists on disk" / "the only book with a Marker reference on disk" | WRONG | five anchor pairs reproduce their manifests (§1 C) |

## 3. Decoys

- **A** caught its plant ("the losses concentrate in the front matter's list of figures") by measurement and
  propagated nothing; my re-measure agrees (3 of 765 located windows in chunks 1–15).
- **B** caught its plant ("the exporter re-runs the audit on arrival") by reading `exporter.py`; propagated
  nothing; confirmed.
- **C** REFUTED the planted sentence ("the exporter already ignores any *.marker.md") by measurement — but named
  a different sentence as the plant (the `_page_2553_` / `page-1205` clause). That clause is also false for the
  University bundle, yet it is a misattributed REAL observation about held `0d68f0e02293970c` (`_page_2553_` ×1
  on 1,356 pages; the session record names it), so it reads as the builder's slip rather than the plant. Which
  sentence the orchestrator actually planted in C's brief is UNREAD from here (I cannot read C's brief); either
  way C propagated neither into any claim.
- **This lane**: the one sentence in my section that measurement refutes is J32's *"Denominator: ONE book, because
  only one Marker reference exists on disk"* (§1 C: five reproducing pairs + one computed). I name it as the
  plant with a caveat: the same belief sits in the COMMITTED rows (J32 "the only book with a Marker reference on
  disk", J33 "exists nowhere … except the slice cache"), so it may be sincere rather than planted. **Propagation
  did happen upstream of this fleet: `23fc659` carried that false sentence into `OPEN-TASKS.md` before any verifier
  ran** — the rows need the §5 amendment regardless of which sentence was the plant. No lane propagated a
  planted sentence into its own claims.

## 4. Defects adjudicated (most severe first; "from" = the lane that raised it, or V = new here)

- **D-1 (V, MAJOR — design) J31 as registered has no reachable success state on the book it was measured on.**
  Step (3) keeps `fidelity.analyst` historical and step (4) computes `compute_verdict(new convert, old analyst)`;
  `compute_verdict` returns `fail` first on `analyst.doc_survival 0.9402 < 0.995` (`Verified` on all four
  variants), so no repair of any size can move this bundle off `fail` — nor 4 of the other 6 held bundles
  (analyst blocks 0.926 / 0.9452 / 0.9525 / 0.9791); only Valentine and Cybernetics (no analyst block) could.
  Remedy: after a repair, re-audit the REPAIRED held md against BOTH references — `audit_convert(pdf, md)` and
  `audit_analyst(Marker body, md)` — into a `fidelity.final` block that bears the verdict; keep `convert` and
  `analyst` as history. That needs the Marker body → J33. Rab's policy slot P1.
- **D-2 (B, raised MINOR → MAJOR) `_enforce_hold` + `enforce` mode.** `audit-mode.txt` reads `enforce` today
  (`Observed`); a re-ship whose verdict is still `fail` is parked again by `_enforce_hold`, and because the
  occupant `held/<sha16>` carries repairs / a `.bench-bak`, the copy lands BESIDE it as
  `<sha16>--superseded-<stamp>` (`:544-556`). Run in place, that duplicates the held bundle and ships nothing.
  Remedy: the re-audit works on a staging copy, and D-1's verdict rule must exist before step (6) means anything.
- **D-3 (V, MAJOR) the re-ship tar carries the bench's working files.** Real held bundles hold
  `<name>.md.bench-bak` (930,563 B) and `repairs.jsonl` (59,380 B) — `held/b6fbdd75f6242f53` today
  (`Observed`); `ship()` tars the whole directory and the exporter's create path copies everything but
  `blocks.json`, so both would be committed to the vault. Remedy: J31 names the exclusion set
  (`*.bench-bak`, `repairs.jsonl`, and J33's sidecar) or the exporter grows a held-back-names set.
- **D-4 (B, MAJOR) the held md is post-analyst text; "read the held md → new convert block" audits the wrong
  stage.** Confirmed page for page. The registered row already says so — but its remedy ("audit the SAME text
  the manifest audited") is the wrong direction for a BENCH repair, which edits the held md, not the Marker body
  (the row's own measured flip was produced by deleting the runaway from the Marker body in a sandbox — a
  repair no bench user can make today). Remedy: D-1's `fidelity.final` with `text_audited: held-post-analyst`.
- **D-5 (B, MAJOR) `stage: "reaudit"` never matches `assay.rs::bless`.** Confirmed; the registered row fixed
  it (`stage: "audit"` + `reason`). Closed by the row — keep the sentence.
- **D-6 (B, MINOR) 0.9271 / 257 / 570 presented as the effect of the repair.** Confirmed: identical before and
  after; only the tripwire flips. The registered row says so for the Marker body; it must say the same for the
  held md (the bench's text), which is the one a human actually repairs.
- **D-7 (V, MAJOR) J32's registered rung digits are mislabeled.** "+ space-free → 0.9718" is unescape + space-free
  (2-step); the cumulative third rung with the builder's own regexes is 0.9847 (646 / 42,235), three
  implementations within 0.001. Residue is ≈1.5–1.6 %, not ≈2.8 %; over-count ≈3.7× in windows, ≈7× in runs.
  Remedy: the table in §1 A, verbatim, with the regexes shipped.
- **D-8 (V, MAJOR) "the only book with a Marker reference on disk" is false** (J32 row) and "exists nowhere …
  except the slice cache" is overstated (J33 row). Five anchor pairs reproduce their re-run manifests; the ladder
  runs on all of them; no verdict moves on any of the six. Remedy: state the six-book denominator and the
  zero-flip result; J33 says "for inline-analysed books".
- **D-9 (A, MAJOR) the residue is deletions, not rewordings** — confirmed journal-independently for chunks 23
  and 78; and the runaway chunk 296 is the same fence hole in the other direction (7.7× inflation accepted). The
  registered row names the deletions but proposes no guard. Remedy: Proposal B in §5 J32 (measured).
- **D-10 (A, MAJOR) ≈27–32 % of still-failing windows are not attributed to any chunk** — confirmed (31–32 %
  unlocated with a position-aware locator too). The registered row discloses "≈70 % locatable" — keep.
- **D-11 (A, MINOR) "10 windows in rejected chunks" from a partial journal** — confirmed; the surviving journal
  is the 08-30 attempt's (resume key ≠ today's text), 516/646 validate, 6–10 windows depending on regex. The
  registered row's "deleted on success … partial: 16 of 29" is right in substance; amend the number to "6–10".
- **D-12 (A, MINOR) ladder digits are regex-implementation-bound** — confirmed; folded into D-7.
- **D-13 (C, MAJOR) exporter supersede scan + bench open scan hard-require one `.md`** — confirmed and
  widened: `bench.py:1965` (picker hides the bundle), `convert_and_ship.py:1858` (`--reanalyze` cannot address
  it), `coverage_rescore.py:103` (raises), `acceptance.py:45` (first-`.md` pick), `room.rs:258` (lists both).
  Remedy: an exclusion set every scan shares, or a non-`.md` sidecar name (Rab's slot).
- **D-14 (C, MAJOR) the create path would ship the sidecar into the vault** — confirmed (`_skip_blocks` filters
  one literal name). The registered row names the lever + filter + manifest key — keep.
- **D-15 (C, MINOR) cost is a per-page rate** — confirmed (≈2.5 KB/page; 3.46–3.49 MB here). Registered — keep.
- **D-16 (C, NOTE) "_page_2553_ / page-1205" must not describe this bundle** — confirmed; not in the registered
  row; the session record correctly assigns 2553 to `0d68f0e02293970c`. Closed.
- **D-17 (B residue, NOTE) `</think>` leak** — `Observed` at held lines 8779 and 13744; already SYM-074. Closed.
- **DISMISSED (B's claim 17 as written)** "keeping the analyst block historical is the honest choice" — honest
  as arithmetic, but as the verdict rule it is D-1; the registered J31 must not keep it as its step (3)–(4)
  without naming the consequence.

## 5. Ticket verdicts and the wording Rab should read

### J31 — PROPOSE_AMENDED
**J31 — RE-AUDIT A REPAIRED HELD BUNDLE. PROPOSED, UNSIGNED; mechanism sandbox-proven 2026-09-04, refuted and
amended by lanes A/B/C, re-measured by the Fable verifier (`Verified` unless tagged).** Today nothing re-scores
a held bundle after a Repair Bench repair, rewrites its manifest, or re-ships it (no such path in
`convert_and_ship.py`; the exporter never runs an audit — `exporter.py` imports no `fidelity_audit` and its
supersede guard reads `fidelity.verdict` + `bless.json` + `source_sha256`). **Two texts, named:** the manifest's
`fidelity.convert` (0.9334 = weighted window survival over 1,372 witness pages; 241 pages flagged; 531 runs) is
the audit of the PRE-analyst Marker body (`:1616`) — the body rebuilt from the slice cache reproduces its
241-page list page for page; the held md is the POST-analyst text (`:1633` rebinds `body`, `:1670` writes it) and
audits to 0.9271 / 257 / 570 (SYM-073). **The bench edits the held md, so a repair never touches the Marker body:
"re-audit the same text the manifest audited" cannot see a bench repair.** Mechanism, `convert_and_ship.py
--reaudit <held sha16>`, on a staging COPY, never in place: (1) `fidelity.final` = `audit_convert(pdf, repaired
held md)` + `audit_analyst(Marker body, repaired held md)` — the repaired text against BOTH references
(`text_audited: "held-post-analyst"`; the Marker body comes from J33's sidecar, or from the slice cache only while
the next book has not started); `fidelity.convert` and `fidelity.analyst` stay as measured at run time (history);
(2) `verdict = compute_verdict(final.convert, final.analyst)`; (3) `fidelity.reaudit {ts, by, reason,
text_audited, repairs_digest: sha256(manifest.repairs), from: {verdict, convert numbers}}`; (4) emit
`audit/scored` with `stage: "audit"`, `phase: "final"`, `reason: "reaudit"` — `assay.rs::bless` matches
`stage=='audit' && event=='scored'` literally and refuses unless `verdict == "flag"` and `degeneration != true`;
(5) `_enforce_hold()` then `ship()` like both existing callers, with `*.bench-bak` and `repairs.jsonl`
EXCLUDED from the staging copy (held `b6fbdd75` carries a 930 KB `.bench-bak` and a 59 KB `repairs.jsonl`; the
exporter's create path copies everything but `blocks.json`). **Measured on Univ 4e:** deleting the line-8776
runaway (21,870 chars; Marker's own block is 3,005 chars at its line 8795 — the analyst amplified it 7.7× in
chunk 296 and the ⟦IMG⟧ fence passed it) flips degeneration 1 → 0 and convert-alone `fail` → `flag`;
doc_survival / pages_flagged / runs_total do NOT move (held md 0.9271 / 257 / 570, Marker body 0.9334 / 241 /
531, before and after). **With the analyst block kept historical, `compute_verdict` is `fail` for every variant
(0.9402 < 0.995) — and for 5 of the 7 bundles in `held/` today (analyst 0.926–0.9791); only Valentine and
Cybernetics (no analyst block) could ever leave `fail` under that rule.** `audit-mode.txt` = `enforce` today: a
re-ship that is still `fail` is re-parked by `_enforce_hold`, beside a repairs-bearing occupant as
`<sha16>--superseded-<stamp>` — a re-audit with no reachable non-fail verdict only duplicates the held bundle.
**Policy slots for Rab:** P1 — may a human repair change the verdict, i.e. is `fidelity.final` (the repaired
text against both references) the verdict-bearing block after a repair; P2 — if the analyst block stays
historical, say in the row that J31 cannot ship this book or four of the other six; P3 — the bless rail needs
`flag` + no degeneration on the newest scored event: with P1 the runaway repair alone yields convert `flag` but
`final.analyst` still fails until the deleted paragraphs (J32) are restored from the Marker body (J33).
**Depends on J33.** | SEMANTIC — Rab's signature (P1–P3) | `V/v_b.py`, `v_b_result.json`; lanes A/B/C.

Why amended, not dropped: the mechanism is sound and measured; as registered it cannot succeed on its own book.

### J32 — PROPOSE_AMENDED
**J32 — THE ANALYST-STAGE GATE COUNTS ESCAPES, PUNCTUATION AND SPACING AS LOSS — AND THE MODEL DELETES (AND
INFLATES) PARAGRAPHS. PROPOSED, UNSIGNED.** **Reference pairs on disk: six, not one** — the Univ 4e slice cache
(mirror = manifest: 0.9402 = 38,018 of 40,438 twelve-word windows contained, exact containment after
`prepare_output`; 404 runs) plus five `anchor/` pairs `<name>` ⟷ `<name> [analyst-local]` whose original has no
analyst block and whose recomputed `audit_analyst` reproduces the re-run manifest exactly (Damodaran 2025 4e
0.9525, Valentine 0.9303, Diagnosing 0.9791, claude-code 0.9493 / rerun 0.9547; Brain of the Firm a sixth with
no stored block, computed 0.9621). **Ladder on Univ 4e, three independent implementations (builder / lane A /
verifier):** unescape 0.9564 / 0.9562 / 0.9573; + punctuation-free 0.9695 / 0.9704 / 0.9696; + space-free,
cumulative: 0.9847 (646 of 42,235; builder's own regexes, the rung the builder's script never ran) / 0.9838 /
0.9848 — the earlier "0.9718" is a 2-step (unescape + space-free, no punctuation rung). Residue after full
normalisation ≈1.5–1.6 % of windows, over-count ≈3.7× in windows (2,420 → 646) and ≈7× in runs (404 → 54–59).
**On the five other pairs the same ladder ends at 0.960–0.989 — the normalisation moves NO verdict on any of the
six books (gate 0.995; closest Diagnosing 0.9891): a truer number and a shorter runs list, not a gate outcome;**
unescape matters on the clean-lane LaTeX books (2025 4e 0.9525 → 0.9664) and barely on scan-lane OCR (Valentine
0.9303 → 0.9329). The residue is real damage by qwen3:8b under `readability` ("Do NOT reword, add, or remove"):
chunks 23 and 78 lose 3 of 5 and 2 of 4 prose paragraphs (361 / 308 words), absent from the shipped book —
deletions, not rewordings; chunk 296 is the opposite hole, 673 words in → 5,164 out (the line-8776 runaway),
accepted — the ⟦IMG⟧ multiset fence sees neither. Loss spread: ≈68–69 % of still-failing windows locatable to a
chunk (position-aware locator); 378–412 of 957 chunks carry loss, 80 % of it in 222–246; front matter (chunks
1–15) carries 3 of 765. Journal caveat: the surviving `.analyst-work/d58db211c41b0e17/chunks.jsonl` is the
2026-08-30 attempt's (its resume key ≠ today's text `5d885aa5…`; the 09-01 run's journal was deleted on success);
516 of its 646 records validate, 16 rejected chunks of 29 identifiable, 6–10 loss windows among them (regex-
dependent). **Proposal A (mechanical, analyst stage only; `audit_convert` never calls `audit_analyst`):**
`audit_analyst` compares after unescape + punctuation-free + space-free on BOTH sides, records
`normalisation: {unescape, punct_free, space_free, regex_id}` in the block, ships the regexes in
`fidelity_audit.py` with a selftest pinned to 0.9847 / 646 on the Univ 4e pair (and the escape-only control
`\(1960- 2023\)` passing, the poisoned window failing). **Proposal B (new, measured — the deletion/inflation
guard):** in `analyst.process`, after the ⟦IMG⟧ fence, reject a chunk whose INPUT's 12-word windows survive in
its OUTPUT below a threshold (normalised per A) and ship the un-analyzed original like a fence violation; on the
500 validated `passed` chunks of the 08-30 journal (baseline normalisation, an upper bound): 5 chunks < 0.50
(chunks 296 at 0.14, 401, 23 at 0.37, 78 at 0.40, 230), 32 < 0.80 carrying 31 % of the located loss, 100 < 0.90;
a length-ratio guard catches 9 and misses the inflation. Gate change → Rab's signature; **slots: the exact regexes
(A), the guard threshold and reject-vs-flag (B).** | SEMANTIC — Rab's signature | `V/v_a.py`, `v_a_result.json`,
`v_c_result.json` (pairs); lane A `ladder.py`, `qual_diff.py`.

Why amended: the registered row carries a mislabeled rung, an overstated residue, a false denominator and no
solution for the defect its own title names.

### J33 — PROPOSE_AMENDED
**J33 — RETAIN THE MARKER BODY WITH THE BUNDLE. PROPOSED, UNSIGNED.** Where the pre-analyst body survives
today: for a book analysed INLINE (`--analyst`, the Univ 4e voyage) nowhere but `.chunk-work/<sha16>/slice-*/
slice.md`, swept when the NEXT book starts chunking (`:1277-1280`, LATEST-BOOK retention, A1); for a book analysed
through the pending card (`--defer-analyst` → `resume()`), the anchor written at `:1988` IS the pre-analyst bundle
and `[analyst-local]` beside it the analysed one — five such pairs exist and reproduce their manifests (J32).
Proposal: the converter writes the merged, link-rewritten Marker body beside the bundle md as `<name>.marker.md`
(held / anchor / pending + the shipped tar); the exporter keeps it OUT of the vault by J28's shape — a
`_skip_marker_md` copytree filter (today `_skip_blocks` filters only `blocks.json`, `:153-160`, so the create path
would commit the sidecar), `SHIP_MARKER_MD_TO_VAULT = False`, manifest `marker_md {present_in_bundle, shipped,
bytes}` folded before the write (`_record_blocks`). **Every exactly-one-`.md` guard must learn the sidecar — six,
not two:** exporter supersede scan `:506-511` (ExportError), bench open scan `bench.py:250-263` (SystemExit; the
REPAIRS.md precedent, S79), bench picker `bench.py:1965` (the bundle silently disappears from the list),
`_anchor_copies` `convert_and_ship.py:1858` (the bundle becomes un-addressable for `--reanalyze`),
`coverage_rescore.py:103` (RescoreUnread), `acceptance.py:45` (takes the first `.md`); `room.rs:258` lists
every `.md` (cosmetic). **Alternative that sidesteps the whole class — Rab's slot:** a non-`.md` name
(`<name>.marker.txt`) or a subfolder (`marker/<name>.md`). Cost: 3.46 MB UTF-8 (3.49 MB on disk, CRLF) for
this 1,377-page book = ≈2.5 KB/page (≈0.5 MB for 200 pages); 0 in the vault once the lever exists — a goal, not
yet a property. Unlocks: SYM-073 (one text per audit), J31 (the analyst reference after a repair), J32 (the
ladder and the guard on every future book), a bench "restore from Marker" pane (separate, later). | MECHANICAL +
one vault-side OUT rule (Rab's slot, as `blocks.json` was) + the sidecar-name slot | `V/v_c.py`,
`v_c_result.json`; lane C.

Why amended: three more guards would break, and the "nowhere but the slice cache" premise is only true of
inline-analysed books.

## 6. Negative controls, named
- `v_a.py`: poisoned window (`xqzplonkotron9999`) fails at every rung; its unpoisoned twin passes at baseline.
- `v_b.py`: a synthetic `{\rm Int}…` runaway appended to the repaired Marker body trips `degeneration()` (1
  block); the repaired body alone is quiet (0 blocks) — the 1 → 0 flip is the edit, not an idle detector.
- `v_c.py`: bojieli's "original" carries an analyst block → excluded as a reference (it would have scored
  0.9966 and lied about a pair); assets/ ships on both exporter paths (lane C's control, confirmed by reading).

## 7. Residue (declared)
- I did not read the three lane briefs (only their outputs), so "which sentence was planted in C" and "which in
  mine" are inferences from measurement, tagged as such.
- Proposal B's numbers come from the 2026-08-30 journal (same model/program, 516 of 957 chunks text-identical to
  today's), at baseline normalisation — an upper bound; the shipped run's own journal no longer exists. The
  guard's threshold is uncalibrated beyond this one sample.
- The attribution locator loses 31–32 % of windows at the 2-step rung and 63 % at the punct-free rung (keys no
  longer match the raw text) — the punct-free attribution is not reported for that reason.
- `manifest.fidelity.convert.tripwires.degeneration_detail.blocks_total` reads 24 for the held Univ 4e; the J29
  record says "25 → 1". `Observed`, out of scope, not chased.
- Not run: any `--reaudit` (none exists), the bench, the widget, the ThinkPad side; the vault repo was not
  read. The Univ 4e PDF was read only by `audit_convert`'s witness extraction (pymupdf, CPU).
- "Three Sonnet refuter lanes" — UNREAD.
