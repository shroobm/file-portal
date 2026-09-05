# Third-party components and their licences

This repository's own code is MIT (see `LICENSE`). The running system depends on the components
below, each under its own licence. The Python rows were read from the installed packages' metadata
on the desktop on 2026-09-05 (`marker-env`); the other rows are the projects' published licences at
that date. Versions are the ones installed and measured, not minimums.

## Conversion and audit (desktop, `windows-converter/`)

| Component | Version installed | Licence | Note |
|---|---|---|---|
| marker-pdf | 1.10.2 | GPL-3.0-or-later | Model weights under a modified AI Pubs OpenRAIL-M: free for research, personal use, and startups under $2M in funding or revenue; other commercial use needs Datalab's licence (https://www.datalab.to/pricing). |
| surya-ocr | 0.17.1 | GPL-3.0-or-later | Marker's layout, OCR and table models; the same weights terms as marker-pdf. |
| PyMuPDF (pymupdf) | 1.28.0 | AGPL-3.0, or a commercial licence from Artifex | The survival audit's witness reader and the Repair Bench's page renderer. AGPL obligations apply to any network-served use. |
| pdftext | 0.6.3 | Apache-2.0 | Marker's text extraction layer. |
| transformers | 4.57.6 | Apache-2.0 | Model runtime for Marker's models. |
| torch | 2.11.0+cu128 | BSD-3-Clause for PyTorch's own code | GPU runtime. This `+cu128` wheel bundles 24 NVIDIA DLLs in `torch/lib` (CUDA runtime, cuBLAS, cuFFT, cuRAND, cuSOLVER, cuSPARSE, NVRTC, CUPTI, cuDNN); those are NVIDIA's proprietary redistributables under the CUDA Toolkit EULA and the cuDNN licence, not BSD. |
| rapidfuzz | 3.14.5 | MIT | Fuzzy containment in the survival audit. |

## Analyst (desktop)

| Component | Version | Licence | Note |
|---|---|---|---|
| Ollama | 0.33.2 | MIT | Serves the local model over localhost. |
| qwen3:8b | as pulled by Ollama | Apache-2.0 | The default analyst model. Licence read from `ollama show qwen3:8b`. |

## Linux services (`linux-converter/`, `linux-receiver/`, `linux-dashboard/`)

Versions as declared in the manifests, not measured on the ThinkPad; the vault's own manifests record
pymupdf4llm 1.28.0 in use. Licences read from the desktop's `pymu-env` copies and from PyPI on 2026-09-05.

| Component | Version | Licence | Note |
|---|---|---|---|
| pymupdf4llm | >=1.28,<2 as declared; 1.28.0 in the vault's manifests | AGPL-3.0, or a commercial licence from Artifex | The Linux converter's engine (`converter/engines.py`); depends on PyMuPDF under the same terms. |
| pymupdf-layout | 1.28.x, pinned by pymupdf4llm | Polyform Noncommercial, or a commercial licence from Artifex | Hard dependency of pymupdf4llm 1.28, imported by `engines.py`; noncommercial use only without Artifex's licence. |
| GTK4 · libadwaita · PyGObject | system packages (pacman), in no manifest | LGPL-2.1-or-later | The optional dashboard's toolkit, loaded through `gi`. |
| watchdog · tomli-w | >=4,<5 · >=1,<2 | Apache-2.0 · MIT | File watching in all three services; the dashboard's settings writer. |

## Desktop application and transport

| Component | Version | Licence | Note |
|---|---|---|---|
| Tauri | 2.11.5 | MIT or Apache-2.0 | The widget's application framework (`windows-widget/src-tauri/`); the version is the crate in the desktop's `Cargo.lock`, which is gitignored. |
| Tailscale | 1.102.2 | BSD-3-Clause | The tailnet and `tailscale ssh` transport between the two machines. |

## What this means in practice

- Personal use of everything above, as this project does it, is within every licence listed.
- Redistributing or deploying the converter for an organisation is governed by the GPL-3.0 code
  licences, the OpenRAIL-M weights terms of marker and surya, PyMuPDF's AGPL and, for the Linux
  converter, pymupdf-layout's Polyform Noncommercial. Those are the four to read first; `LICENSE`
  covers only this repository's own files.
- The Rust and JavaScript dependencies of the widget are declared in `Cargo.toml` and `package.json`
  and are permissive apart from MPL-2.0 on five of the 263 crates read from the local cargo registry
  (`cssparser`, `cssparser-macros`, `dtoa-short`, `option-ext`, `selectors`); the other 218 crates in
  the lock were not on this machine to read. The Linux services' Python dependencies are declared in
  their `pyproject.toml` files and listed in the Linux table above; `linux-converter`'s are not
  permissive.

Corrections to this file follow the repository's rule: measured, dated, appended, never silently
rewritten.
