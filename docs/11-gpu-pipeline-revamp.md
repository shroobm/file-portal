# GPU Pipeline Revamp — Scope & Phase Plan

**Origin:** planning session 2026-07-18 (Desktop, post-reset), verified against the actual hardware and current upstream sources.
**Idea:** move document conversion off the ThinkPad's CPU stack (pymupdf4llm / Pandoc / tesseract) onto the Desktop's GPU with [Marker](https://github.com/datalab-to/marker), and demote the ThinkPad to enrichment (tagging, embeddings, structure). Add a local LLM (Ollama) on the Desktop and semantic sidecars on the ThinkPad.

---

## Verified hardware baseline (Desktop, 2026-07-18)

| Component | Value | Implication |
|---|---|---|
| GPU | RTX 3080 **10 GB** | Fits Marker (~5 GB peak) OR an 8B q4 model (~5–7 GB) — **never both at once** |
| Driver | 610.62 (Windows Update) | No separate CUDA toolkit needed; modern torch wheels bundle their CUDA runtime |
| System RAM | 16 GB | **One** Marker worker max; don't convert while gaming |
| CPU | i7-8700K | Fine as feeder |
| Python | Store stub only | Phase 0 installs a real Python via `uv` |

## The VRAM math

Marker peaks ~5 GB/worker (~3.5 GB average). An 8B model at q4 in Ollama takes ~5–7 GB with KV cache. Each fits alone in 10 GB with headroom; together they OOM — this is a [known Marker + local-LLM problem](https://github.com/datalab-to/marker/issues/1038). Resolution: `keep_alive: 0` on Ollama (~5–10 s model reload per generation — irrelevant for an async pipeline) plus a **tiny mutex/queue** (single worker; a lock file is enough) so a Marker job and a generation never overlap. Design item, not a risk.

## 🚩 Red flags

1. **Forgejo does not run on Windows.** [Officially unsupported since 2024](https://codeberg.org/forgejo/forgejo/issues/6103) — no binaries, no upstream interest. Options: host on the ThinkPad (Arch is first-class, and it already hosts the bare vault repo — the natural git host), WSL2/Docker on the Desktop (adds a VM layer to the most RAM-tight machine), or defer entirely (bare git over Tailscale SSH is the proven transport; Forgejo adds UI, not capability). **Recommendation: ThinkPad-hosted, and last in the build order.**
2. **The ThinkPad is unverified for the enrichment role.** phi4-mini (3.8B, ~2.5 GB q4) on CPU is plausible for async tagging; MiniLM embeddings + ChromaDB are light — but RAM and tokens/sec are unbenchmarked until it's online. Hard gate for Phase 3 only; Phases 0–2 are all Desktop-side.

## The design inversion

Today's intake converts **on the ThinkPad**. This revamp reverses the flow: PDF → Marker on the Desktop → push markdown to the ThinkPad → enrichment → vault push → back to Obsidian. The thing to protect while rewiring is everything L13/L14/L15 taught us: **SHA-based dedup (`EXPORT-SKIP`), the manifest format, atomic `.part-` transport, Windows-clean interior filenames**. Bundle-format compatibility is the single biggest design item — the new front end must not break the proven back half.

## Pre-answered small decisions

- **Embeddings:** 384d / `all-MiniLM-L6-v2`. At vault scale, re-embedding later costs minutes — fully reversible, must not gate anything.
- **8B generation model:** `qwen3:8b` or `llama3.1:8b` at q4 — both fit the budget.
- **ZenNotes:** unevaluated; revisit at Phase 3.

---

## Phases, gated by verification

- [ ] **Phase 0 — Desktop ML baseline** (~30 min): `uv`, real Python, torch cu12x.
  **Gate:** `torch.cuda.is_available()` → `True` on the 3080.
- [ ] **Phase 1 — Marker vertical slice:** convert one clean-text PDF (Beer "Designing Freedom" — the first-ever real ingest, so known ground truth) and later one scanned PDF; measure wall time and peak VRAM; compare output quality against pymupdf4llm on the same input.
  **Gate:** visibly better markdown; VRAM ≤ ~6 GB.
- [ ] **Phase 2 — VRAM handoff:** install Ollama, scripted sequence Marker → unload → generate → Marker again.
  **Gate:** no OOM; VRAM returns to baseline between stages.
- [ ] **Phase 3 — ThinkPad sidecars** (needs it online): spec check, phi4-mini tok/s benchmark, ChromaDB + MiniLM over the existing vault.
- [ ] **Phase 4 — Pipeline rewiring:** the inversion above, bundle-format compatible.
- [ ] **Phase 5 — Forgejo:** ThinkPad-hosted, or consciously dropped.

**Environment note:** the Desktop ML environment lives at `C:\Users\Bndit\ml\` — outside this repo. Only docs and (later, Phase 4) pipeline code land here.

## Phase 0+1 results

*(to be filled by the executing session)*
