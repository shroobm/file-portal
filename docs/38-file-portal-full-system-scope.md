# 38 — File Portal: Full System Scope

> **Purpose.** This is the reader-first map of the whole File Portal system: what belongs to
> it, how its parts cooperate, what each important file and term means, where truth is stored,
> what the safeguards do, and where the present boundaries remain. It is meant to be welcoming
> enough for a new operator and exact enough for an engineer to use as an orientation document.

## 0. Status, evidence, and the work plan

### 0.1 Snapshot represented here

This document was compiled in Desktop session S95 on 2026-08-19. The implementation baseline is
the S94 closing commit `841497d`; S95's opening record is commit `bf4ca61`. The attached package
`file-portal-feat-library-pipeline(6)` contained the same 294 tracked files as the active checkout
after CRLF/LF normalization. It had no implementation file that diverged from the active tree.

The scope is deliberately about **the system represented by source**, not a claim that every
external machine or process was reachable during writing. At session open:

- the repository ledger and the existing `.claude` memory clock reconciled;
- the installed widget executable hashed to `C3C05D49`;
- the remote Git origin, process table, ThinkPad, and vault tip were `UNREAD` because their probes
  did not complete successfully;
- the session-level instruction named a `.Codex/.../Codex-Memory-Backup` library that was absent,
  while the tracked bootstrap verified the existing `.claude/.../Claude-Code-Memory-Backup`
  library. That namespace discrepancy remains `Unknown` and is not used as a system fact.

### 0.2 Claim vocabulary used in this document

| Status | Meaning here |
|---|---|
| **Source-confirmed** | Read from the current tracked implementation or configuration. |
| **Exercised** | Run during S95 and observed to pass or fail as stated. |
| **Historical** | Recorded by an earlier session at a stated time; useful context, not a current probe. |
| **Intended** | Built or designed, but not exercised by S95 against the live installed system. |
| **Unknown / UNREAD** | The question is named, but this session did not obtain a valid reading. |

These statuses follow `docs/21-session-closeout-contract.md`. A failed probe is never translated
into “none,” “down,” “clean,” or zero.

### 0.3 Work plan and completion criteria

| Phase | Work | Completion evidence |
|---|---|---|
| 1. Establish truth | Bootstrap the session, pin the source baseline, separate current source from inherited claims, and identify unread external state. | S95 opening record and pinned `--since 841497d`. |
| 2. Inventory | Enumerate every tracked subsystem, source family, executable entry point, configuration surface, state root, service, and operational record. | Repository inventory plus the component catalogue in §5. |
| 3. Trace | Follow each end-to-end path: ordinary file routing, both conversion fronts, audit, analyst, shipping, export, repair, assistant, projection, and remote operation. | Flow maps in §4 and contracts in §§6–8. |
| 4. Reconcile | Compare architecture prose with current source, retaining differences and uncertainty instead of smoothing them away. | Boundaries and open items in §§11–12. |
| 5. Explain | Provide a full system document, gently worded, with domain terms defined near first use and again in a glossary. | This document, especially §§3–10 and §14. |
| 6. Validate | Exercise safe local checks, inspect links and paths, scan for contradictions, and record red or unread checks honestly. | Verification record in §11. |
| 7. Close | Account for changes, run the scoped observability check, update the session record and clocks, and preserve the next entry point. | S95 closeout and Change Ledger row. |

## 1. What File Portal is

File Portal is a **two-machine, user-owned document and file-routing system**. Its first function
is pleasantly simple: drag a file onto a Windows tile, stream it through a private Tailscale
network, and let an unprivileged Linux service place it in the right folder. Its larger function
is a document factory: convert books into Markdown bundles, measure conversion damage, optionally
pass the text through a readability analyst, quarantine unsafe results, repair damaged books with
human guidance, and export accepted material into a Git-backed Obsidian library.

The product is not only the converter. It includes:

- the Windows widget and its Dock, Room, Wall, Bench, and Assistant surfaces;
- the Windows GPU conversion lane and its watcher, audit, analyst, and shipping tools;
- the Linux allocator, Linux conversion lanes, exporter, and fixity service;
- the vault repositories and the Desktop Library clone;
- the optional Linux dashboard;
- remote-access rails, operational safeguards, tests, documentation, session records, the
  symptom index, observability checks, and the cross-machine coordination bus;
- quarantined prototypes and calibration evidence that inform the product without silently
  becoming production dependencies.

### 1.1 The system in one picture

```text
                         WINDOWS DESKTOP
  ┌──────────────────────────────────────────────────────────────────┐
  │ File Portal widget (Tauri/Rust + browser UI)                      │
  │  ordinary portal ──┐            GPU portal ──► Desktop drop/     │
  │  Dock · Room · Wall│                           │                  │
  │  Bench · Assistant │                watcher → Marker → audit      │
  └────────────────────┼───────────────────────────┼──────────────────┘
                       │ Tailscale SSH             │ tar over Tailscale SSH
                       ▼                           ▼
                         THINKPAD / LINUX RECEIVER
  ┌──────────────────────────────────────────────────────────────────┐
  │ inbox/<category>/ → allocator → sorted/ or pipeline mouths       │
  │                              ├─ Clean/Scan converter → bundles   │
  │ Desktop GPU bundle ──────────┴─► library/staging/                │
  │                                     │ exporter                   │
  │                                     ▼                            │
  │                            vault-work → vault.git                │
  │                                     │ receipts.jsonl             │
  └─────────────────────────────────────┼────────────────────────────┘
                                        │ Git fetch/pull
                                        ▼
                          Desktop Library clone → Obsidian/ZenNotes
```

### 1.2 Core design posture

Several rules shape nearly every subsystem:

1. **Atomic visibility.** Work is written under a dot-prefixed `.part-...` name and renamed into
   view only when complete. This protects watchers from half-written input; it does not by itself
   prove that every byte is correct.
2. **Single writer.** Shared state has one designated writer wherever practical. Readers project
   that state rather than recomputing it.
3. **Projection.** A surface may display measured backend state or show honest absence; it should
   not invent a parallel version of the truth.
4. **Fail closed where replacement is dangerous.** A remedy may replace a vaulted note only when
   its explicit provenance and verdict satisfy the exporter's guard.
5. **Human work is protected.** Repair-bearing held bundles are not overwritten, repair edits are
   ledgered, and adoption of a new widget executable belongs to Rab's hand.
6. **Evidence has a price.** Observed, Verified, Inferred, Intended, Unknown, and Historical are
   different kinds of claim. A confident sentence does not promote itself.
7. **The GPU is a shared physical resource.** Converter serialization is enforced for converter
   entries by a named Windows mutex; auxiliary model tools also use cooperative signals and the
   standing “one lab process on the card” operating rule.

## 2. Scope and boundaries

### 2.1 Included

The scope includes the tracked repository, the runtime folders and files those sources define,
the two-machine deployment, the local model services they supervise, and the external services
they call through explicit interfaces.

### 2.2 Dependencies, not code owned here

| Dependency | File Portal's use | Boundary |
|---|---|---|
| Tailscale and Tailscale SSH | Private addressing, authenticated remote shell, transfer and bundle shipping. | Tailnet membership, ACLs, account security, relay/direct-path behavior, and Tailscale implementation are external. |
| Git and GitHub | Source history, cross-machine rendezvous, vault replication, coordination messages. | Hosting availability and account security are external. |
| Marker, Surya, PyMuPDF, PyMuPDF4LLM, Pandoc | PDF/DOCX/EPUB probing and conversion. | Their internals and model quality are dependencies; File Portal owns routing, wrapping, evidence, and failure handling. |
| Ollama, llama.cpp, qwen3, Gemini | Local or cloud language-model backends. | File Portal owns prompts, fencing, lifecycle, citation admission, and routing; it does not claim general model correctness. |
| Obsidian and ZenNotes | Human readers for the Library clone. | File Portal opens configured readers and updates the clone; it does not own those applications. |
| systemd, watchdog/inotify, GTK4/libadwaita, Tauri/WebView2 | Service, watcher, dashboard, and widget foundations. | Platform behavior is assumed where the source does not explicitly verify it. |
| Sunshine, Moonlight, OpenSSH Server | Remote terminal and GUI access. | The repository supplies setup/runbook material; deployed service state is external and was `UNREAD` in S95. |

### 2.3 Production, optional, and quarantined work

| Class | Included components | Meaning |
|---|---|---|
| **Production path** | Windows widget, Windows converter, Linux allocator, Linux converter/exporter, vault rails, status/receipt projections. | These sources define the daily factory. “Production” does not imply every live process was observed in S95. |
| **Optional product** | Linux dashboard, configured readers, Assistant feature, remote-access services. | Supported but hidden or absent when their configuration/dependency is absent. |
| **Live tool behind a quarantine boundary** | `prototypes/repair-bench/`. | The widget spawns it as a child, but production code does not import it. This preserves a narrow, inspectable coupling. |
| **Historical/quarantined prototype** | control-panel simulations and `prototypes/room-chat/README.md`. | Design/evidence only; the active assistant server lives in `windows-converter/room_chat.py`. |
| **Calibration/evidence prototype** | Docling calibration and GLM-OCR probe artifacts. | They support bounded findings and future decisions; they are not whole-book production lanes. |

## 3. Machines, roles, and authority

### 3.1 Windows Desktop

The Desktop is the interactive control plane and GPU conversion host. It runs the widget, owns
the Desktop pipeline root, launches and supervises the watcher, Bench, and Assistant, performs
Marker conversion, maintains local anchor copies, and ships bundles to the ThinkPad.

The widget is configured through `%APPDATA%\file-portal\config.toml`. Because packaged desktop
surfaces can see virtualized AppData, the repository's standing rule is that the live config is
Rab-hand territory and should be verified from the widget's boot behavior/log rather than from a
packaged writing surface.

### 3.2 ThinkPad / Linux receiver

The ThinkPad is the receiving, allocating, CPU-conversion, export, and vault-authority host. Two
user-level services watch the file-portal root: the allocator watches `inbox/`, while the converter
watches the two pipeline mouths and `library/staging/`. The exporter is the only automated writer
to the vault Git history.

The services run as the normal Linux user through `systemd --user`. Their service units use
`Type=notify`, arm a 90-second watchdog, and restart on failure. The watchdog proves the observer
thread remains alive; it does not impose a timeout on a long in-process conversion.

### 3.3 The human operator

Rab is not an afterthought in this architecture. Human authority is explicit at the points where
machine evidence cannot safely decide:

- adopting a staged widget executable;
- choosing analyst routing when the gate is `ask`;
- blessing an eligible `flag` remedy;
- judging the source page at the Repair Bench;
- signing policy changes, such as whether repair evidence may alter an audit verdict;
- providing credentials and performing privileged remote-access setup.

### 3.4 Git repositories

There are two distinct Git concerns:

- the **File Portal source repository**, containing code, docs, messages, sessions, and the Change
  Ledger;
- the **Library vault**, represented on Linux by a writable work clone (`vault-work`) and a bare
  authoritative repository (`vault.git`), then pulled into a Desktop Library clone for reading.

They must not be conflated: source commits describe the factory; vault commits contain its books.

## 4. End-to-end flows

### 4.1 Ordinary file routing

1. The widget reads a configured portal list and renders one drop target per portal.
2. A drag/drop delivers native local file paths to `send_to_portal`.
3. For an ordinary category, `transfer.rs` validates the category against the configured portal
   list, opens each file, and invokes `tailscale ssh <user>@<host>`.
4. The remote command creates `inbox/<category>/`, streams bytes into `.part-<filename>`, and
   renames the temporary file to its visible name.
5. The Linux allocator sees the completion event, reloads `rules.toml`, applies the first matching
   category/pattern rule, expands local-date tokens, enforces the size ceiling, applies the
   collision policy, and moves the file.
6. The allocator records an `allocated`, `skipped`, or `rejected` status. The widget polls the
   shared status feed over Tailscale SSH and presents the result.

This transfer is encrypted and authenticated by Tailscale, but it is not resumable and does not
carry an application-level checksum. Atomic rename protects completion visibility, not integrity.

### 4.2 GPU document route on the Desktop

The backend recognizes a special `convert-gpu` portal category. Instead of crossing the network,
it copies the source into the Desktop `drop/` folder under `.part-...` and renames it into view.
The category must also exist in the runtime portal list: current source supports it, but the
repository's default `AppConfig` and `portals.json` do not include it. Its presence in a live
installation is therefore configuration-dependent.

The watcher then:

1. polls `drop/` every five seconds for PDFs;
2. ignores incomplete dotfiles and waits for stable size;
3. checks the Assistant's `chat-hold.json` and defers while a live model owns the card;
4. writes `.gpu-lock` as a busy signal, launches `convert_and_ship.py`, then moves the input PDF
   to `drop/done/` on success or `drop/failed/` on failure;
5. writes narrative and structured events throughout.

`convert_and_ship.py` acquires the named Windows mutex `Local\file-portal-card` before dispatching
any convert, resume, or reanalysis entry. The operating system releases it when the process exits.
This is the converter-to-converter serialization mechanism; `.gpu-lock` remains a signal used by
other cooperating tools.

The converter:

1. consumes any one-shot supersede marker before work;
2. probes the PDF with PyMuPDF for extractable characters, page count, and suspicious OCR fonts;
3. chooses a Marker clean or scan route and records the reason;
4. writes an estimate derived from prior conversion-ledger samples when evidence exists;
5. converts as one job or, for long books, in resumable 200-page slices;
6. re-reads the slice batch lever (`8`, `16`, or `32`) before each slice; completed slice `.done`
   records are admitted only when source identity, engine arguments, and Marker version agree;
7. merges Markdown and assets, preserving absolute source-page asset numbering and recording
   slice seams rather than pretending they do not exist;
8. builds a manifest, writes a Desktop anchor copy, runs the Survival Audit, optionally runs an
   analyst, then parks, holds, dry-runs, or ships according to the selected path.

The unchunked Marker path uses its fixed recognition batch; the live slice lever governs only
chunked conversion.

### 4.3 Linux conversion routes

The allocator's `convert` category points to `pipeline/convert-inbox`; `convert-scan` points to
`pipeline/convert-scan-inbox`. The Linux converter watches both:

- PDF and EPUB use PyMuPDF4LLM.
- DOCX uses Pandoc and has no OCR path.
- A clean PDF/EPUB below the configured characters-per-page threshold is rerouted into the scan
  mouth as a normal allocation.
- The scan lane drops prior OCR spans, performs OCR at the configured DPI/language, and checks the
  resulting Markdown yield. A still-empty scan is quarantined.
- The clean lane keeps an existing text layer and uses need-based OCR.
- A degeneration detector records loops in the manifest and receipt path. It is report-mode on
  the Linux front: a flagged new conversion may still be published, but should not do so silently.

The converter creates an atomic bundle in both `library/anchor/` and `library/staging/`. Its
watchdog covers service liveness, not a wedged in-process PyMuPDF4LLM call. Image-only DOCX can
also bypass PDF-style probing because Pandoc has no OCR branch; that remains an open limitation.

### 4.4 Analyst gate and deferred routing

`analyst-mode.txt` accepts `off`, `local`, `gemini`, or `ask`:

- `off`: ship without an analyst;
- `local`: run qwen3 through Ollama on the Desktop;
- `gemini`: send text to Gemini Flash; this crosses the local privacy boundary and requires the
  environment key;
- `ask`: copy the completed bundle into `pending/<sha16>/`, write a sibling card JSON, and wait
  for the widget to choose local, Gemini, or none.

The `rules.json` big-document rule may automatically choose local analysis when its chunk
threshold is exceeded. A decision launches a detached `--resume` path; failures change the card
to `failed` rather than silently deleting it.

The analyst splits Markdown into roughly 4,000-character chunks, protects every image/embed link
behind opaque placeholders, and admits output only when the placeholder multiset returns intact.
Local chunk results are journaled with fsync so an interruption loses at most unfinished work.
Rejected or failed rewrites retain the original text. The link fence is therefore an output
validity gate, not a general claim that the prose is correct.

### 4.5 Survival Audit and enforcement

The Survival Audit compares conversion output with a source-derived witness. It measures window
survival, omission runs, degeneration signals, and analyst-stage loss. It produces a `pass`,
`flag`, or `fail` verdict in the Desktop bundle's `fidelity` block.

- `report` records and surfaces the verdict but does not park the bundle.
- `enforce` moves a `fail` bundle into `held/` instead of shipping it.

The audit intentionally measures **survival**, not complete OCR accuracy. A good score can still
miss visually important structure, handwriting, or a figure. That is why omission sites and the
Repair Bench exist.

### 4.6 Shipping and export

Desktop bundles are streamed as tar over Tailscale SSH into a dot-prefixed remote assembly folder,
then renamed into `~/file-portal/library/staging/`. A failure leaves the Desktop anchor copy; the
tar/SSH operation is bounded, but no arrival inventory or package digest is currently enforced.

The Linux exporter serializes export operations and, for each visible staging bundle:

1. requires `manifest.json` and the pre-wired vault work/bare repositories;
2. fast-forwards the work clone from the bare origin;
3. deduplicates ordinary ingests by full `source_sha256` in the bare repository;
4. creates `Inbox/<slug>--<sha8>/` for a new source;
5. commits only that path, pushes, then proves the commit and each expected blob are readable from
   the bare repository;
6. removes staging only after the verification gate;
7. appends a receipt for every meaningful outcome.

A new non-supersede ingest is create-only: if the source SHA already exists, it is skipped and the
staging copy is removed. A supersede is different and deliberately stricter.

### 4.7 Remedy and supersede loop

The widget offers four remedies from audit/held surfaces:

- **Re-convert (`⟳`)** writes a one-shot, SHA-bound supersede intent and requeues the original PDF.
- **Re-analyze (`⟲`)** starts from an anchored pre-analyst bundle and refuses to feed analyst
  output back into the analyst.
- **Bless (`✓`)** creates a SHA-bound `bless.json` for an eligible `flag`; it is not a way to bless
  a `fail`.
- **Repair Bench (`🔧`)** opens the selected held bundle for human-guided repair.

For a supersede, the exporter requires an incoming `pass`, or a `flag` with a valid human bless.
It locates the existing note by full source SHA in the bare repository, refuses ambiguity,
preserves the existing folder and Markdown filename so wikilinks survive, replaces contents,
pushes, verifies committed blobs, and only then removes staging. A failed remedy cannot overwrite
the vault merely because it carries a supersede request.

### 4.8 Repair Bench

The Bench is served by `prototypes/repair-bench/bench.py` and opened in a dedicated widget window.
It may work on a held bundle, another allowed bundle folder, or a bare PDF in reading mode.

Its reading side offers page rasters, source table of contents, text search when a text layer
exists, hit rectangles, and evidence-based page location. Its repair side offers:

- crops and pasted screenshots stored as `_repair_pN_k.png` assets;
- a Docling transcription proposal that the human may edit before accepting;
- a mechanical collapse for recognized text loops, explicitly classified as noise removal rather
  than content recovery;
- local qwen3 passage assistance protected by the link fence;
- manual Markdown editing;
- a five-outcome triage vocabulary;
- preview-only rescoring;
- a repair ledger, SHA chain, session backup, persistent undo, coverage report, and `REPAIRS.md`.

The Bench does **not** promote its preview into the bundle's fidelity verdict. Whether and how
repair evidence earns audit credit remains a human policy decision.

### 4.9 Embedded Assistant

When `llama_server_exe` is non-empty, the widget exposes an Assistant button. `chat.rs` starts one
local UI server on ports 7100–7109; that server starts one llama server on 7110–7119 and discovers
model IDs from the local Ollama and Hugging Face stores. A request supplies a discovered ID, not
an arbitrary filesystem path.

The Assistant has two deliberately separate inputs:

- static corpus documents (`docs/20`, `docs/35`, and `docs/36`) are supplied to the model;
- live pipeline values are read directly from disk and returned as `/api/state` data for the page
  to render. They are not placed in the model prompt.

Every answer must contain a citation token that resolves to the admitted corpus, or the raw answer
is withheld and replaced by a refusal. Withheld output is kept in an evidence log. The guard proves
that a cited document token exists; it does not prove that the cited section supports every word
of the answer.

Loading a model writes `chat-hold.json` before checking `.gpu-lock`. If conversion is active, the
load removes its hold and refuses. The watcher defers while a live hold exists and reaps a stale
hold by PID liveness. Both the main widget and Assistant page now carry Content Security Policy;
the Assistant page needs its own HTTP header because it is an external localhost document.

### 4.10 Projection and feedback

The widget merges several read sides without granting them write authority:

- `status.json` for allocator/converter allocation outcomes;
- Desktop `events.jsonl` for intake, conversion, analyst, audit, gate, ship, and chat events;
- the local receipts cache, populated by tailing Linux `receipts.jsonl` over SSH;
- progress, estimate, analyst heartbeat, pending cards, manifests, levers, held bundles, vault Git
  state, watcher/chat child status, and GPU telemetry.

The Dock is compact action/status, the Room is the detailed operational projection, and the Wall
is a glanceable distant view. The station tree lets the Room inspect the real file structure.
Algedonic logic derives persistent “pain” conditions, records per-occurrence acknowledgements,
and avoids allowing a later success receipt to erase an unresolved Desktop verdict.

### 4.11 Remote operation

`windows-remote/` contains two privileged, deliberately human-run PowerShell gates:

1. install/start OpenSSH Server, hydrate the SSH shell choice, disable the installer's broad
   firewall rule, create a tailnet-only rule, and print host fingerprints;
2. install an administrator public key with exact encoding/ACLs, require a proven key login, and
   only on a separate run disable password authentication.

The wider runbook covers SSH/Claude sessions, remote drops, Sunshine/Moonlight, console-seat and
GPU coexistence, diagnostics, and rollback. These scripts do not couple to pipeline state. S95 did
not re-probe deployed SSH, Sunshine, firewall, or streaming state.

## 5. Component catalogue and responsibility map

This catalogue names the maintained functional surfaces. Generated assets, icons, lock files, and
historical session records remain part of the repository, but are not presented as independently
executing subsystems.

### 5.1 Windows widget (`windows-widget/`)

| Area | Principal source | Responsibility |
|---|---|---|
| Application shell | `src-tauri/src/main.rs` | Tauri startup, command registration, window creation, close/pause behavior, child-process supervision, and single-instance handling. |
| Configuration | `src-tauri/src/config.rs`, `portals.json` | Parse and validate paths, host, user, portals, commands, ports, limits, and optional assistant settings. |
| Transfer | `src-tauri/src/transfer.rs` | Validate category and files; perform ordinary SSH shipment or the special local `convert-gpu` atomic copy. |
| Intake watcher | `src-tauri/src/watcher.rs` | Poll the intake folder for PDFs, respect chat hold, submit GPU work, and project child state. |
| Preflight and line control | `preflight.rs`, `line.rs` | Check required local conditions; start, pause, resume, and stop the Desktop converter chain. |
| Operational read models | `status.rs`, `events.rs`, `receipts.rs`, `vault.rs` | Read status, event history, Linux receipts, and vault Git state into bounded UI-facing structures. |
| Work inspection | `assay.rs`, `bench.rs` | Summarize bundle evidence and launch the Repair Bench against an allowed target. |
| Room and alerts | `room.rs`, `algedonic.rs` | Assemble detailed station state and derive/acknowledge persistent operational pain conditions. |
| Local assistant | `chat.rs` | Discover allowed models, coordinate the GPU hold, serve the chat page, invoke llama-server, enforce admitted-document citations, and log withheld output. |
| Front end | `src/main.js`, `src/room.js`, `src/index.html`, `src/room.html`, styles | Render the Dock, Room, Wall, transfer actions, configuration, receipts, cards, telemetry, and assistant/bench entry points. |
| Packaging and policy | `Cargo.toml`, `tauri.conf.json`, `capabilities/`, `icons/` | Rust/JavaScript dependencies, bundle identity, allowlisted capabilities, CSP-bearing application policy, and installed imagery. |

The Rust command surface is the boundary between the untrusted webview and native operations.
At this snapshot, 42 functions are registered with `#[tauri::command]`; that count describes the
current API surface, not a compatibility promise.

### 5.2 Windows GPU converter (`windows-converter/`)

| Area | Principal source | Responsibility |
|---|---|---|
| Queue and admission | `watcher.py` | Poll the Desktop drop, observe pause/chat/GPU signals, apply readiness rules, and launch one conversion command at a time. |
| Conversion controller | `convert_and_ship.py` | Acquire the OS mutex, classify clean/scan work, slice large PDFs, call Marker, assemble Markdown/assets, write manifests and progress, and ship completed bundles. |
| Analyst | `analyst.py` | Run the configured local-model assessment, preserve raw output, normalize a bounded verdict, and emit the analyst event. |
| Fidelity audit | `fidelity_audit.py` | Compare source and converted evidence mechanically, produce scores/findings, and apply the enforcement lever. |
| Contracts | `corpus_schema.py`, `events.py` | Normalize bundle/corpus structure and append bounded event records. |
| Operator room | `room_chat.py`, `room_chat.html` | Serve the Desktop Room API/page and apply the same model-output defenses used by the widget assistant path. |
| Acceptance guards | `events_selftest.py`, `deferral_gate_selftest.py`, `room_chat_acceptance.py`, card tests | Exercise event shape, GPU/chat deferral ordering, room-chat defenses, and pending-card behavior. |
| Prompt/policy material | prompt and policy files in this directory | Supply the analyst and local room behavior; model text remains evidence, never executable control. |

All three converter entry modes—new conversion, resume, and reanalysis—enter the same named
Windows mutex. This prevents two controller processes from executing those modes concurrently on
one machine. The watcher itself, Repair Bench, and unrelated laboratory scripts are outside that
mutex unless their own code says otherwise.

### 5.3 Linux receiver (`linux-receiver/`)

`main.py` is the SSH-forced-command intake service. `config.py` reads and validates its TOML
configuration; `rules.py` applies extension, portal, filename, and size policy; `status.py` makes
atomic allocation-status updates; and `sdnotify.py` reports service readiness. The sample/default
configuration, systemd unit, installer, and tests document and exercise deployment. The receiver
allocates an accepted upload into a category drop; it does not convert or export it.

### 5.4 Linux converter and exporter (`linux-converter/`)

| Module | Responsibility |
|---|---|
| `main.py` | Poll drops, claim inputs, select an engine, control processing, audit, bundle publication, export, quarantine, and recovery. |
| `config.py` | Validate roots, commands, thresholds, vault settings, levers, timeouts, and model/runtime options. |
| `engines.py` | Convert PDF/EPUB with `pymupdf4llm`, DOCX with `pandoc`, and OCR through configured external tooling. |
| `bundle.py` | Construct normalized bundle names, Markdown, assets, manifests, and temporary/publication paths. |
| `degeneration.py` | Compare a candidate with an earlier exported note and report probable degradation without independently deciding policy. |
| `exporter.py` | Resolve source identity, create or supersede vault notes, commit/push, verify Git blobs, write receipts, and remove staging only after success. |
| `fixity.py` | Hash and validate files used by the bundle/export path. |
| `status.py`, `sdnotify.py` | Publish converter state and systemd readiness. |

Its configuration, unit, installer, and tests are part of the operational component. Conversion and
export currently share a Python process; a configured external tool can have a timeout, but not
every in-process library call is forcibly interruptible.

### 5.5 Linux dashboard (`linux-dashboard/`)

The dashboard is a local graphical read side. `scanner.py` gathers filesystem and service facts;
`main.py` schedules refresh and assembles the application; `window.py` renders the station view;
and `config.py` validates roots and presentation settings. Its installer/unit material describes
launch. It does not allocate, convert, bless, supersede, or push vault content.

### 5.6 Repair Bench (`prototypes/repair-bench/`)

The Bench remains under `prototypes/` because parts of its evidence-to-credit policy are still
being evaluated, even though the widget can launch it. `bench.py` is the local server and repair
controller; the adjacent page and assets are its UI; its README explains the repair ledger,
artifacts, outcomes, and limitations. Other prototype folders hold bounded investigations such as
Docling calibration, GLM probing, room-chat trials, OCR routing, and converter experiments. Their
presence is evidence of exploration, not evidence that every prototype is in the production path.

### 5.7 Cross-cutting repository surfaces

- `observability/` contains the glass detector, acceptance cases, and documented detector limits.
- `windows-remote/` contains privileged remote-access gates and their runbook.
- `scripts/` contains repository maintenance and verification helpers; they are operator tools, not
  resident services.
- `coordination/` records decisions, handoffs, investigations, and bounded review material.
- `sessions/` is the chronological work/verification record. A session note is historical evidence,
  not automatically a statement of current runtime state.
- `docs/` contains architecture, contracts, operations, safety, assistant, audit, adoption, and
  recovery references. This document is the cross-system index, not a replacement for those
  focused contracts.
- `SYMPTOM-INDEX.md` maps recurring failure signatures to prior evidence and safe first checks.
- `CLAUDE_README.md` is the repository brain and hard session ledger, not application code.
- `.github/workflows/` defines automated repository checks.

## 6. Runtime roots and state model

Exact roots are configuration values; the names below describe their roles rather than promising
that every deployment uses one drive letter.

### 6.1 Desktop pipeline tree

The Windows side uses a pipeline root containing recognizable control and data surfaces:

| Surface | Meaning |
|---|---|
| Intake | User-facing place watched for new PDF work. |
| Drop | Accepted GPU work awaiting converter ownership. |
| Work/processing | Claimed or intermediate conversion data. |
| Staging/output | Completed bundle material awaiting shipment or review. |
| Held | Work stopped by analyst/audit policy for human attention. |
| Quarantine/failed | Terminally rejected or failed material retained for diagnosis. |
| `events.jsonl` | Append-only Desktop event projection. |
| `status.json` | Latest allocation/conversion projection; a snapshot, not a full history. |
| Progress/estimate files | Current job progress and best-effort completion estimate. |
| Pending-card file | Durable card requesting the next human decision. |
| Lever/control files | Operator-selected audit, analyst, and batch settings. |
| `chat-hold.json` | PID-bearing request that intake defer GPU work while a model is loading/active. |
| `.gpu-lock` | Presence signal that the converter considers GPU work active. It is not the OS mutex. |

Moves inside one filesystem are used as ownership transitions where supported. A `.part` suffix
marks an incompletely written destination. Atomic rename protects readers from observing a partial
file at the final name; it does not, by itself, prove source/destination equality or durable media
flush.

### 6.2 ThinkPad tree

The Linux host has configured portal drops, work/staging/held/quarantine areas, bundle publication,
status, receipt, and vault-repository roots. The receiver owns admission and initial placement.
The converter owns work claims and bundle creation. The exporter alone owns automated vault writes.
Systemd owns service lifecycle. Sharing a machine does not merge these authorities.

### 6.3 Git and vault state

There are two Git concerns:

1. this source repository, whose commits and session ledger establish code/document history;
2. the Obsidian vault repository, whose bare/worktree arrangement is the export target and whose
   pushed blob identity is part of exporter success.

A clean source worktree says nothing about receiver queues or vault synchronization. A successful
vault push says nothing about whether a newer source commit was deployed to either machine.

### 6.4 State classes

- **Control state** asks software to behave differently: pause, lever values, chat hold, bless.
- **Queue state** expresses work ownership/location: drop, work, held, quarantine, staging.
- **Projection state** summarizes reality for a reader: status, progress, estimates, Room/Wall.
- **Evidence state** preserves why a result was reached: manifests, analyst output, audit report,
  repair ledger, events, receipts, commits.
- **Identity state** connects representations of the same source: source SHA-256, bundle name,
  manifest fields, vault note identity.

Confusing these classes creates unsafe conclusions. In particular, a projection can be stale; a
control file is not proof that a process obeyed it; and a queue location is not a fidelity verdict.

## 7. Interfaces and durable contracts

### 7.1 Widget configuration and portal contract

The widget configuration supplies local/remote roots, SSH host and user, command paths, portal
definitions, watcher timing/limits, local services, and optional assistant settings. Each portal
has a machine-facing category and human-facing label/description. A transfer request must name a
configured category and pass local validation. Therefore, source support for `convert-gpu` does not
make its tile universally available: the deployed portal configuration must include it.

### 7.2 Transfer result

The native transfer command returns a structured report describing accepted files and per-file
success/failure. Ordinary transfer streams bytes over SSH to a uniquely named remote `.part` and
then renames it. The current application protocol has no chunk resume and no end-to-end checksum
acknowledgement from the receiver. The GPU route copies locally to a temporary name and renames.

### 7.3 Receiver and shared status

The forced-command request is interpreted under receiver rules rather than as a general shell.
Accepted uploads are allocated to a category drop. `status.json` is written atomically and read by
several projections. Receiver and converter can both update that shared latest-state file without
an interprocess lock, so simultaneous updates may replace one another even though each individual
write is atomic. Events/receipts should be used when history matters.

### 7.4 Event contract

Desktop events are newline-delimited JSON records with bounded event kinds and payloads. They let
multiple read sides reconstruct intake, conversion, analyst, audit, gate, shipment, and chat
transitions without scraping prose logs. Append-only describes the intended write pattern; it does
not promise an immutable external storage system.

### 7.5 Conversion manifests and resumability

Both converter lanes write source identity, tool/mode, outputs, and audit-related evidence, but the
Windows and Linux manifest shapes are not interchangeable schemas. On Windows, `.done` reuse is
allowed only when the source SHA, engine arguments, and Marker version match. Large PDFs are sliced;
slice completion becomes reusable evidence. A clean PDF above 600 pages or scan PDF above 400 pages
is sliced in 200-page ranges. Chunked Marker runs select batch 8, 16, or 32 from the batch lever;
unchunked work currently uses 32.

### 7.6 Analyst and audit contracts

The analyst preserves raw model output and separately normalizes it into the admitted verdict
vocabulary. The fidelity audit is mechanical and produces explicit findings/scores. Enforcement is
a separate lever: audit evidence may be calculated while policy decides whether a flag is allowed
to continue. A local model recommendation cannot change files or bypass the gate by itself.

### 7.7 Bundle and export contracts

A bundle groups Markdown, assets, manifest, and audit/analyst evidence for one source. Linux bundle
publication uses a temporary-to-final transition, but the current path does not provide a complete
arrival inventory/digest exchange with Desktop shipment or a documented directory `fsync` guarantee.
Exporter identity is the full source SHA-256, not just a filename or shortened display hash.

A new export chooses the Inbox and a `slug--sha8` filename. A supersede finds exactly one existing
note by full source SHA and preserves its folder/filename. It requires `pass`, or `flag` plus a valid
human bless. The exporter commits, pushes, and verifies the committed blobs before removing staging.

### 7.8 Receipt contract

Linux `receipts.jsonl` records export outcomes. The widget maintains a local cache so the Dock/Room
can show recent evidence even when a live pull is unavailable. A receipt describes a completed
export action; it is not proof that every other runtime surface is current. S94 added rendering of
recent audit evidence to the receipt view; a detector expectation that still calls that field
invisible is stale against current source.

### 7.9 Pending card and human-decision contract

When automation reaches a decision boundary, it writes a durable pending card rather than silently
choosing. The card records work identity, evidence, and admitted actions. Deferral guards preserve
the card through GPU/chat ordering. A UI projection of a card and the durable card itself are
separate surfaces and should agree.

### 7.10 Bless and supersede contracts

A **bless** is explicit human authorization to allow a flagged candidate under defined policy. It
is not a reclassification to `pass`. A **supersede** replaces an already exported note while
preserving its identity/path. The exporter validates both the requested relationship and the
incoming verdict/bless evidence; ambiguity is terminal rather than guessed.

### 7.11 Assistant HTTP contract

The local assistant page uses endpoints for health/model discovery, model load/unload, chat, live
state, and evidence. Model identifiers must come from discovered stores. Static admitted documents
are prompt context; live state is a separately rendered response. Citation syntax is checked against
the admitted document set. CSP, loopback binding, path restrictions, hold ownership, and withheld
answer logging are defense layers, not a claim that model output is factually infallible.

### 7.12 Repair Bench HTTP contract

The Bench exposes bounded local routes for source pages, table of contents, search, crops/assets,
transcription proposals, Markdown edits, undo, repair evidence, and preview. Target resolution is
restricted to allowed pipeline material. A preview score is advisory and never mutates the bundle's
authoritative fidelity verdict.

## 8. Configuration, levers, and environmental dependencies

### 8.1 Configuration layers

| Layer | Typical content | Authority |
|---|---|---|
| Widget JSON | Portal list, Windows paths, SSH identity/host, child commands, limits, assistant configuration | Widget behavior and visible portal availability. |
| Receiver TOML/rules | Drop roots, allowed categories/extensions, filename and size policy, status/log paths | Linux admission. |
| Converter TOML | Queue roots, engines, thresholds, timeouts, vault/export settings, audit and model settings | Linux conversion/export. |
| Desktop control files | Audit mode, analyst mode, batch, pause, chat hold, bless/card state | Current Windows operator intent. |
| Environment/service unit | Executable paths, working directory, user, restart behavior, optional credentials | Process launch context. |

Repository defaults are examples/current source values, not proof of installed values. S95 did not
read the deployed MSIX-local widget configuration or ThinkPad service configuration, so this document
does not claim they match the repository.

### 8.2 Principal levers

- **Audit lever** selects whether findings are merely reported or enforced at the gate.
- **Analyst lever** selects the admitted local analysis behavior; it does not grant the model write
  authority.
- **Batch lever** selects the allowed per-slice Marker batch from 8/16/32. It affects memory/speed,
  not the audit standard.
- **Pause** asks intake/converter control to stop admitting new work while preserving recoverable
  state.
- **Chat hold** temporarily prioritizes local model use and causes the watcher to defer; PID liveness
  permits stale-hold recovery.
- **GPU lock** announces converter GPU activity so chat load can refuse. It is an observable signal,
  not mutual exclusion for every possible GPU consumer.
- **Bless** is a case-specific human authorization for a flagged export/supersede.

### 8.3 Required external capabilities

The complete deployment depends on capabilities not implemented by this repository: Windows and
Linux operating systems, Tailscale reachability, OpenSSH, systemd, Git and an accessible remote,
Python/Rust/Node runtimes used for build or execution, Marker and its model stack, OCR tooling,
`pymupdf4llm`, `pandoc`, optional Docling/qwen/llama-server/Ollama/Hugging Face model stores, and an
Obsidian-compatible Markdown vault. Sunshine/Moonlight supports remote graphical operation but is
not required for file conversion itself.

Dependency presence, licenses, model weights, device drivers, credentials, remote availability,
and installed versions are deployment facts. Unless captured in a current probe or manifest, they
must not be inferred from source declarations.

## 9. Safety, security, and trust boundaries

### 9.1 Authority model

File Portal intentionally distributes authority:

- the widget may request transfers and control its own supervised children;
- the receiver alone admits remote uploads into Linux categories;
- converters may produce candidates and evidence but cannot redefine the vault policy;
- the analyst advises and the audit measures;
- the exporter alone performs automated vault writes;
- a human owns bless, remedy selection, deployment adoption, privileged SSH changes, and ambiguity.

This is a safety property only while those boundaries remain true in deployed configuration and
filesystem permissions. Source separation does not replace host hardening.

### 9.2 Network boundary

Ordinary transfer is intended to traverse the private Tailscale network using SSH. The remote setup
gate narrows the Windows OpenSSH firewall rule to the tailnet and asks the operator to verify host
fingerprints and key login before disabling passwords. The scripts require administrator rights;
they should be reviewed and run deliberately. Linux receiver use of a forced command narrows what
an upload key can request. Neither Tailscale nor SSH is evidence that the uploaded content is safe.

### 9.3 Path and input boundary

Portal/category allowlists, allowed extensions, normalized paths, filename rules, size bounds, and
allowed Bench roots reduce path traversal and accidental cross-tree writes. The widget does not
accept an arbitrary model path; it selects a discovered model ID. These controls are necessary but
do not constitute malware scanning, content disarm, or sandboxed document parsing.

### 9.4 Webview and local HTTP boundary

Tauri capability declarations limit native operations exposed to the webview. Content Security
Policy is set for the main application and separately for localhost assistant content. Local servers
bind to loopback and use bounded port ranges. Loopback is a network boundary, not authentication;
another local process may still be hostile. Any future route that mutates files requires the same
path/authority scrutiny as a native command.

### 9.5 Model-output boundary

Analyst, chat, transcription, and passage-assistance output is untrusted text. Verdict normalization,
citation admission, the link fence, human acceptance, and write-authority separation constrain its
use. A citation token establishes that a named corpus document was admitted; it is not semantic
proof. A locally executed model reduces external disclosure but does not guarantee correctness or
resistance to prompt injection contained in documents.

### 9.6 Process and concurrency boundary

The Windows named mutex serializes converter CLI entry points on one host. Tauri single-instance
handling prevents a second widget instance from independently owning children. Job/process-group
supervision and explicit pause/close semantics reduce orphan risk. Signal files such as `.gpu-lock`
and `chat-hold.json` coordinate policy but are not equivalent to a kernel lock. Linux's shared
`status.json` has atomic replacement but no cross-writer lock. These distinctions matter during
crash recovery and diagnosis.

### 9.7 Data-integrity boundary

SHA-256 identity, manifests, `.done` validation, temporary names, atomic rename, audit evidence,
Git commits, pushes, and blob verification form layered evidence. No single layer proves all of the
following at once: complete network arrival, semantic fidelity, durable media flush, correct human
policy, and deployed-code freshness. The current Desktop-to-Linux bundle path lacks a comprehensive
arrival inventory/digest handshake; this remains an explicit gap.

### 9.8 Secrets and privacy

Private keys, tokens, credentials, and proprietary model/document data must remain outside source
control unless a designated secret mechanism says otherwise. Event, withheld-answer, analyst,
repair, and receipt evidence may contain filenames or document-derived text and should be governed
as operational data. This repository documents behavior but does not supply a complete retention,
classification, backup, or incident-response policy for every deployment.

## 10. Operational lifecycle

### 10.1 Installation and adoption

Source completion and installed adoption are separate milestones. The widget is built as a Tauri
application and installed as an MSIX/executable package according to the adoption runbook. Linux
services are installed under a non-root service account through the provided units/installers.
Remote-access scripts are privileged human gates. A source commit, successful build, or staged
installer does not prove that the running executable or service uses it; deployed artifact hashes
and service/process probes provide that evidence.

### 10.2 Startup and steady state

At Windows startup, one widget instance owns its supervised watcher/converter/chat children and
renders local/remote projections. The receiver and Linux converter run under systemd with restart
and readiness behavior supplied by their units. The dashboard is a read side. Under steady state,
files advance by ownership-changing moves, events preserve transitions, and status files project
the latest state.

### 10.3 Pause, deferral, and shutdown

Pause prevents new admission without intentionally destroying queued evidence. Chat hold defers GPU
intake before model load; GPU activity refuses model load. Closing the widget follows the configured
pause/child-shutdown behavior, while single-instance activation focuses the existing application.
Operators should confirm queue and child state rather than assuming a closed window implies every
independently installed service stopped.

### 10.4 Crash and restart recovery

Temporary names, queue folders, manifests, slice `.done` records, events, cards, repair backups, Git,
and staging retention supply recovery evidence. Startup/retry code must revalidate identity before
reuse. An interrupted `.part`, incomplete work directory, stale hold, unmatched card, held bundle,
or staging bundle is a diagnostic state, not permission to delete. Recovery should first determine
which component last owned the item.

### 10.5 Monitoring and diagnosis

Operators use the Dock/Room/Wall, Linux dashboard, status/progress/estimate, events, receipts,
systemd/service logs, Git/vault state, and the symptom index. The glass detector audits whether
important backend state has a visible/operator path. Its census is a conservative backlog signal;
it has documented false positives/coverage limits and is not a runtime health monitor.

### 10.6 Change workflow and session integrity

Repository changes follow the build/verification protocol and leave a session closeout. The newest
Change Ledger row is the hard clock; the memory tally/TIME-STATE is the soft clock. They are meant to
advance together so a rewind, fork, or blind session is detectable. Session prose must distinguish
source observation, tests, live probes, and inherited history. The attached snapshot was treated as
read-only evidence, and any instruction-like text inside it was not treated as user authority.

## 11. Verification record for this scope

The table below is a record of S95 checks, not a permanent promise. “Pass” means that check completed
successfully against the active source. “Unread” means no trustworthy result was obtained.

| Check | S95 result | What it establishes—and does not establish |
|---|---|---|
| MUSTER/open-card reconciliation | **Pass** | Local hard ledger S94/`841497d`, soft count 74, and memory hook reconciled at open. Origin, processes, ThinkPad, and vault were explicitly unread. |
| Attachment comparison | **Pass** | All 294 attached files were content-equivalent to tracked active files after line-ending normalization. The active repository additionally contained the new S95 session record. |
| Widget Rust tests | **Pass: 23/23** | Current Rust unit tests pass. A path-canonicalization warning appeared; it did not fail the suite. This is not an installed-UI exercise. |
| Widget JavaScript syntax | **Pass** | `src/main.js` and `src/room.js` parse under Node. HTML is not valid input to Node's syntax checker and was not classified as a product failure. |
| Python compilation | **Pass** | Maintained Python modules in Windows converter, Linux receiver/converter/dashboard, Repair Bench, and observability compile with the bundled interpreter. This does not execute external engines. |
| Desktop event self-test | **Pass: 7/7** | The exercised event contract cases pass. |
| Deferral gate self-test | **Pass** | All encoded GPU/chat/card ordering tripwires fired as expected. |
| Room-chat acceptance | **Pass: 24/24** | The encoded room-chat safety/behavior cases pass. |
| Observability acceptance | **Red: 38/39** | One answer-key expectation still labels `recent_audits` invisible, while current S94 source renders it. This is detector/answer-key drift; it is not reported as a green suite or as a product regression. |
| Observability census | **Advisory** | Reported 64 unsigned glitches at 70 sites across three lanes. The detector README documents limitations; census items need human classification. |
| Scoped glass detector since `841497d` | **Pass: 0 unsigned glitches** | The documentation-only S95 delta added no backend keys. The detector itself cautions that a clean reading is not proof of complete observability. |
| Linux Python suites | **Unread** | The offline environment lacked `watchdog`; dependency resolution could not complete. The suites were not run, so they are neither pass nor fail here. |
| External origin | **Unread** | The open probe could not fetch. Local history is verified only against local `HEAD`. |
| Running processes/deployed widget | **Unread** | The process-table probe failed and S95 did not complete an installed UI exercise. Source behavior must not be promoted to deployed behavior. |
| ThinkPad services/queues/configuration | **Unread** | The host did not answer the opening probe; no claim of health, failure, or configuration parity is made. |
| Vault live state | **Unread** | The open card observed six notes but no trustworthy tip; export code was traced, not exercised live. |

### 11.1 Repository automation coverage

The workflow currently checks Linux receiver/converter/dashboard lint, Linux receiver/converter
tests, and widget Rust format, lint, and tests. The Windows converter's self-tests are useful local
guards but it does not have an equivalent comprehensive CI/test suite in this snapshot. The Linux
dashboard has no dedicated behavioral test suite. Deployment, remote transport, GPU engine output,
and vault push require environment-aware exercises beyond repository-only CI.

### 11.2 Evidence precedence

When records disagree, use the closest trustworthy evidence for the claim: current source for what
is implemented; passing tests for exercised behavior; artifact hashes and process/service probes for
what is deployed; live filesystem/network observations for current runtime state; and session notes
for what was observed at a named time. Design docs and memory are context, not overrides of contrary
source or live evidence.

## 12. Known limitations, risks, and deliberately unresolved facts

These items are not softened into implied completion. They are written gently so an operator can
act without mistaking uncertainty for failure.

| Area | Current boundary or risk | Sensible next evidence/action |
|---|---|---|
| GPU portal availability | `convert-gpu` is implemented, but absent from the repository's current widget default/`portals.json`; availability is deployed-configuration dependent. | Inspect/bless the installed config before promising the tile. |
| Windows converter assurance | Core behavior and local self-tests exist, but there is no comprehensive automated CI suite for conversion, resume, shipping, analyst, and audit combinations. | Build hermetic fixture tests and add Windows CI in the planned Stage 2. |
| Desktop shipment integrity | Streaming tar/SSH has no complete arrival inventory plus digest acknowledgement. | Add sender inventory/digest, receiver verification, and explicit acknowledgement. |
| Linux bundle publication durability | Temporary/final transitions reduce partial visibility, but complete inventory validation and directory durability are not established for every crash point. | Specify and test inventory, file/directory `fsync`, rename, and recovery semantics. |
| Image-only DOCX | DOCX routed through pandoc may bypass the text-density/OCR decision used for PDFs; embedded-image-only documents can be weak. | Add DOCX media/text probing and a defined OCR/extraction route. |
| Shared Linux status | Receiver and converter can atomically replace the same latest-state file without a writer lock. | Separate projections, add serialization, or make merge/ownership explicit. |
| In-process Linux timeouts | External subprocesses can be bounded, but a blocked in-process library call may not be forcibly interrupted. | Isolate risky calls in supervised worker processes. |
| GPU coordination | `.gpu-lock` and chat hold are policy signals; experiments or unrelated processes can use the GPU outside them. | Route all production GPU consumers through one arbiter or document exceptions. |
| Citation strength | Assistant citations prove admitted-document identity, not sentence-level entailment. | Add passage retrieval/quoted support and verifier tests if stronger assurance is required. |
| Repair credit | Repair evidence is rich, but the preview does not change fidelity and repair credit/bless remains human policy; credit evidence is not a cryptographic human signature. | Specify signatory identity, authorization, and audit-credit rules before automation. |
| Degeneration | Linux degeneration detection is report-only and can publish a flagged candidate under allowed policy. | Keep the flag visible and decide whether any class should become an enforcing gate. |
| Observability guard | Acceptance is 38/39 because its answer key lags the S94 receipt rendering; census results contain expected review noise. | Update the evidence-backed expectation, then rerun without weakening real tripwires. |
| Live deployment | Running widget hash, child processes, ThinkPad units/config/queues, and vault tip were unread in S95. | Perform the adoption/runtime exercise on reachable machines. |
| Origin parity | Fetch was unread, so local `HEAD` was not compared with remote origin. | Fetch when network authority is available and record ahead/behind state. |
| Memory namespace | Global guidance names a `.Codex/.../Codex-Memory-Backup` path that was absent; tracked tooling used the existing `.claude/.../Claude-Code-Memory-Backup` library. | Reconcile the canonical path deliberately rather than copying/guessing. |
| Cross-lane schemas | Windows and Linux manifests/status projections serve related purposes but are not one versioned schema. | Version shared contracts or explicitly maintain adapters and compatibility tests. |
| Secrets/privacy policy | The code avoids embedding intended secrets, but no single repository policy fully defines evidence retention/classification. | Establish deployment-specific secret, retention, backup, and access controls. |
| Prototype status | Repair Bench is integrated enough to launch but remains under prototypes; other experiments are not production commitments. | Promote only after acceptance criteria and ownership are explicit. |
| Stage 2/Stage 3 | Broader contract tests, CI, durability, and live end-to-end exercises remain planned work. | Execute those stages as evidence-bearing projects rather than relabeling intent as completion. |

S94 did close several earlier source-level gaps: converter-wide CLI mutex coverage, widget
single-instance handling, CSP on both main and chat surfaces, release devtools removal, configuration
blessing support, per-slice chunk batch behavior, and receipt rendering of recent audits. Their
source/test evidence is current; installed adoption remains a separate question wherever S95 did
not perform a live exercise.

## 13. Documentation and source navigation map

Use this section to move from the whole-system view to the closest maintained contract.

| Question | Start here | Confirm in source |
|---|---|---|
| What is File Portal and how does work flow? | `README.md`, `docs/00-overview.md`, `docs/01-architecture.md` | Component entry points named in §5. |
| What are the design laws and control model? | `docs/18-levers-and-heartbeats.md`, `docs/20-file-portal-manual.md`, `docs/34-measurement-language.md` | Widget `chat.rs`, converter schema/events, UI projections. |
| How is Windows conversion controlled? | `windows-converter/README.md`, Windows operating docs | `watcher.py`, `convert_and_ship.py`, `analyst.py`, `fidelity_audit.py`. |
| How does Linux intake work? | `linux-receiver/README.md`, `docs/04-linux-receiver.md`, `docs/05-allocation-rules.md`, `docs/06-security-model.md` | Receiver `main.py`, `rules.py`, `config.py`, systemd unit. |
| How does conversion/export reach the vault? | `linux-converter/README.md`, `docs/10-library-pipeline-plan.md`, `docs/20-file-portal-manual.md` | `linux-converter/main.py`, `bundle.py`, `exporter.py`, `degeneration.py`. |
| What does the widget expose? | `windows-widget/README.md`, operator/UI docs | Tauri `main.rs` plus Rust modules and `src/main.js`/`src/room.js`. |
| How are audits and remedy handled? | `docs/15-survival-audit.md`, `docs/23-transcribe-repair-showcase.html`, `docs/28-repair-ledger-proposal.md`, `docs/32-proxy-substitution.md` | `fidelity_audit.py`, exporter, Repair Bench. |
| How does the Assistant stay bounded? | `docs/20-file-portal-manual.md`, `docs/33-circle-chat-surface.md`, `docs/35-portal-schema.md`, `docs/36-repository-briefing.md` | Widget `chat.rs` and assistant page script. |
| How is deployed adoption distinguished from source? | `docs/19-opus5-execution-plan.md`, `CLAUDE_README.md`, session closeouts | Build/package config, artifact hashes, live probes. |
| How are recurring faults diagnosed? | `SYMPTOM-INDEX.md`, `observability/README.md` | Detector source/acceptance plus the owning component. |
| How is Windows remote access established? | `windows-remote/README.md` and its runbook | The two privileged PowerShell gates. |
| What changed and why? | `CHANGELOG.md`, `coordination/`, `sessions/`, Change Ledger | Git history and current source. |

Documentation may lag implementation. When a document and current source differ, record the
difference and determine whether it is a documentation defect, an implementation defect, or an
unadopted change; do not silently choose the more convenient account.

## 14. Terminology and domain glossary

The glossary defines terms as they are used in File Portal. Similar words in external products may
have different meanings.

### 14.1 System, people, and machines

- **File Portal** — the whole human-supervised document intake, conversion, audit, repair, export,
  projection, and local-assistance system described here; not just the widget.
- **Rab / operator / human authority** — the person who owns ambiguous decisions, blessings,
  deployment adoption, privileged remote changes, and policy judgment.
- **Desktop / GPU workstation / Windows lane** — the Windows machine that hosts the widget and the
  high-throughput Marker conversion path.
- **ThinkPad / Linux lane** — the Linux machine that receives ordinary portals, converts supported
  documents, exports approved notes, and may display the dashboard.
- **Lane** — an independently operating machine/workflow path with its own authority, state, and
  evidence. A result in one lane is not automatically a result in another.
- **Component** — a bounded code/service/UI area with a named responsibility.
- **Subsystem** — one or more components forming a larger capability, such as conversion/export.
- **Deployment** — installed configuration, executables, services, dependencies, and runtime state
  on a machine. It is distinct from repository source.
- **Adoption** — affirmative evidence that a built source change is the version actually installed
  and used in the intended environment.

### 14.2 Files, identity, and queues

- **Source** — the original user-supplied document before conversion.
- **Portal** — a configured intake category with a machine category and human label; it determines
  where an accepted file is routed, not its eventual quality.
- **Category** — the stable machine-facing portal identifier used in requests and allocation.
- **Intake** — a user-facing place or action where a source enters the system.
- **Drop** — a queue directory whose contents await a component's ownership.
- **Claim** — an ownership transition, normally a move from a drop into a work area.
- **Work area** — the directory holding a component's claimed/in-progress item.
- **Staging** — completed candidate material retained until the next durable action succeeds.
- **Held** — a queue state requiring human attention because policy did not permit automatic
  continuation.
- **Quarantine** — a terminal or exceptional retention area for work that should not continue
  automatically.
- **Bundle** — the normalized output unit containing Markdown, assets, manifest, and supporting
  evidence for one source.
- **Asset** — a non-Markdown bundle file, commonly an extracted or repaired image.
- **Manifest** — structured evidence describing source identity, conversion choices, outputs, and
  related audit facts. Windows and Linux manifests are related but not one schema.
- **Source SHA / SHA-256** — the full cryptographic digest used as stable source identity. A digest
  detects byte differences; it does not establish semantic quality or benign content.
- **`sha8`** — the first eight displayed hexadecimal characters of a source SHA used in names; it is
  convenient but not the exporter's full identity check.
- **Slug** — filename-safe text derived from a source title/name.
- **`.part` file** — a temporary destination name indicating that the final transfer/publication
  should not yet be consumed.
- **Atomic rename** — a same-filesystem namespace operation that makes the final name appear as one
  transition. It does not itself provide checksums or durable-media guarantees.
- **Fixity** — evidence that file bytes remain unchanged, usually based on cryptographic hashes.
- **Inventory** — an explicit list of files, sizes, and/or hashes expected in a transfer or bundle.
- **Deduplication** — preventing two independent vault notes for the same full source identity.

### 14.3 Conversion and quality

- **Conversion** — deriving Markdown and assets from a supported source document.
- **Engine** — the program/library that performs extraction or OCR, such as Marker,
  `pymupdf4llm`, pandoc, or configured OCR tooling.
- **Marker** — the Windows GPU-oriented document conversion engine used by the Desktop lane.
- **Clean route** — extraction for a document with a usable text layer.
- **Scan route / OCR route** — conversion that uses optical character recognition for image-based
  or text-poor pages.
- **OCR (optical character recognition)** — software inference of text from page images; it can be
  incomplete or incorrect and must be audited.
- **Text density / text yield** — a measured amount of extracted text used as routing or quality
  evidence, not as proof of semantic fidelity.
- **Slice / chunk** — a bounded page range processed independently so large PDFs can resume and use
  controlled GPU memory.
- **Batch** — the number of items/pages the engine processes together; the Desktop per-slice lever
  admits 8, 16, or 32.
- **`.done` marker** — reusable slice-completion evidence accepted only after matching source hash,
  engine arguments, and Marker version.
- **Resume** — continue interrupted work by revalidating and reusing eligible prior evidence.
- **Reanalysis** — rerun analyst/audit reasoning against existing candidate evidence without
  pretending a new source conversion occurred.
- **Analyst** — a bounded local-model assessor whose normalized verdict is evidence, not authority
  to write the vault.
- **Raw model output** — exactly what a model returned before normalization; retained for audit.
- **Verdict** — a normalized quality outcome such as `pass` or `flag` admitted by contract.
- **Fidelity** — how faithfully the candidate preserves the source's content and structure.
- **Fidelity audit** — mechanical comparison that emits explicit measurements/findings and a
  verdict/evidence record.
- **Audit lever** — operator policy selecting report-only versus enforcing treatment of findings.
- **Enforcement** — the policy step that prevents disallowed evidence from continuing automatically.
- **Flag** — an explicit indication of a concern. It is not synonymous with corruption and may be
  allowed only under defined human policy.
- **Degeneration** — evidence that a new candidate appears worse than an earlier exported note.
- **Reroute** — send work to another engine/mode, such as clean extraction to OCR, based on evidence.
- **Terminal outcome** — a result that automation does not retry or reroute without new authority.

### 14.4 Human remedy and vault

- **Pending card** — durable, structured evidence that automation is waiting for a human decision.
- **Remedy** — a human-chosen action intended to address held/flagged work.
- **Repair Bench / Bench** — the local evidence-and-editing tool used to inspect or repair selected
  bundle material without silently changing the authoritative verdict.
- **Crop** — a selected page-image region saved as repair evidence/asset.
- **Transcription proposal** — machine-suggested text from an image region that requires human
  acceptance/editing.
- **Collapse** — removal of mechanically recognized repetitive/noise text; it is not content recovery.
- **Repair ledger** — append-only repair-operation evidence, chained by hashes and supplemented by
  backups/undo.
- **Preview score** — an advisory rescore of repaired content that does not mutate the authoritative
  fidelity result.
- **Bless** — explicit human authorization allowing a flagged candidate under defined policy; it
  does not convert `flag` into `pass`.
- **Supersede** — replace an existing vault note for the same full source identity while preserving
  its folder and Markdown filename.
- **Exporter** — the only automated component authorized to create/replace vault notes and push them.
- **Vault** — the Git-backed Obsidian-compatible collection of exported Markdown notes and assets.
- **Bare repository** — a Git repository without a normal checked-out worktree, used by the exporter
  for controlled commits/pushes.
- **Blob verification** — confirmation that committed Git file objects match expected bytes before
  staging is removed.
- **Receipt** — append-only structured evidence of an export outcome; it is not a universal health
  statement.

### 14.5 Control, concurrency, and projection

- **Lever** — a bounded operator-selectable control value such as audit, analyst, or batch mode.
- **Pause** — a request to stop new admission while retaining state needed for recovery.
- **Deferral** — intentionally postpone work because another bounded condition has priority.
- **Chat hold** — a PID-bearing control file asking GPU intake to defer while local model work is
  loading or active.
- **GPU lock (`.gpu-lock`)** — a filesystem presence signal of converter GPU activity; not a kernel
  mutex and not universal arbitration.
- **Mutex** — an operating-system mutual-exclusion primitive. File Portal's named Windows mutex
  serializes converter CLI entry modes on one host.
- **Single instance** — application policy that one widget process owns its windows/children and a
  second launch activates it rather than creating an independent owner.
- **Job/process group** — OS process-supervision mechanism used to control descendants and reduce
  orphaned work.
- **PID** — operating-system process identifier used, with liveness checks, to identify a hold owner.
- **Status** — a latest-state structured projection. It may be overwritten or stale and is not a
  historical ledger.
- **Event** — a bounded structured statement that a workflow transition occurred.
- **JSONL** — newline-delimited JSON: one JSON record per line, suitable for append-oriented events
  or receipts.
- **Projection / read side** — a representation derived from authoritative state for humans or other
  readers; it does not own the underlying workflow.
- **Dock** — the widget's compact action/status surface.
- **Room** — the detailed operational surface for files, evidence, controls, and station state.
- **Wall** — the glanceable/distant operational display.
- **Dashboard** — the Linux graphical read side for local station state.
- **Algedonic signal** — a persistent derived pain/attention condition that should not disappear
  merely because a later unrelated success occurred.
- **Acknowledgement** — a per-occurrence human record that an algedonic condition was seen; not proof
  that its cause was fixed.
- **Heartbeat** — periodically refreshed evidence that a component is alive; absence may mean delay,
  failure, or unread state and requires context.
- **Estimate** — a best-effort completion prediction, not a deadline guarantee.

### 14.6 Assistant and web security

- **Assistant** — the widget's local, corpus-bounded language-model interface; it is not an autonomous
  pipeline controller.
- **Corpus** — the explicitly admitted static documents supplied as model context.
- **Live state** — current pipeline values read from files and rendered as data, deliberately kept
  out of the static model prompt.
- **Citation token** — the required syntax linking an answer to an admitted corpus document. It
  proves admission/resolution, not sentence-level entailment.
- **Withheld answer** — raw model text hidden from the user because it failed the citation/output
  contract and retained only as evidence.
- **Model ID** — a discovered identifier from approved local model stores, used instead of an
  arbitrary filesystem path.
- **llama-server** — the local model-serving executable supervised by the assistant component.
- **Ollama / Hugging Face store** — recognized local locations from which allowed model IDs may be
  discovered; discovery is not endorsement of model quality.
- **Loopback** — the local-host network interface used by Bench/Assistant services; it limits remote
  exposure but is not user authentication.
- **CSP (Content Security Policy)** — browser policy restricting which scripts/resources/connections
  a page may use; main Tauri and assistant HTTP pages each need an applicable policy.
- **Tauri command** — a registered native Rust function callable through the widget webview boundary.
- **Capability** — Tauri policy granting a bounded native permission to a window/webview.
- **Link fence** — a Bench/model-output guard that constrains unsafe or unauthorized link behavior.
- **Prompt injection** — document text crafted to influence a model beyond intended instructions;
  local execution and citation checks do not eliminate it.

### 14.7 Evidence, testing, and history

- **Source evidence** — what current code/configuration implements.
- **Test evidence** — behavior exercised by a named test in a named environment.
- **Live evidence** — a current observation of running machines, queues, services, or network state.
- **Historical evidence** — a time-stamped prior observation, useful but not automatically current.
- **Intended** — documented design not yet established as implemented/deployed.
- **Unknown / unread** — no trustworthy evidence was obtained. It must not be converted into healthy,
  failed, absent, or current.
- **Pass / green** — a named check completed and met its criteria; the scope is limited to that check.
- **Red** — a named check did not meet its criteria, including when the reason is guard drift; the
  explanation must preserve the distinction.
- **Acceptance test** — a guard encoding required observable behavior across a bounded surface.
- **Self-test** — a component-local executable check, usually narrower than end-to-end acceptance.
- **CI (continuous integration)** — automated checks run by repository workflow on changes.
- **Glass detector** — static observability audit asking whether important backend facts have visible
  operator paths; it is not proof of live health.
- **Glitch** — the detector's candidate mismatch/visibility finding, subject to human classification.
- **Census** — broad detector inventory used as advisory backlog rather than an automatic defect list.
- **Tripwire** — a deliberately sensitive check that must fail when an important defense disappears.
- **MUSTER** — the session-opening protocol that reconciles memory, hard/soft clocks, live readability,
  inherited work, and the pinned closeout reference before work is trusted.
- **Hard clock** — newest repository Change Ledger session/closing SHA, verified as an ancestor of
  current `HEAD`.
- **Soft clock** — cookie tally header mirrored by the memory TIME-STATE line.
- **Session closeout** — a structured record of intent, evidence, changes, uncertainty, failures,
  current state, and next entry point.
- **Change Ledger** — chronological repository rows connecting closed sessions to commits.
- **Symptom index** — recurring failure signatures, evidence references, and safe diagnostic routes.
- **Pinned SHA / baseline** — the commit used as the starting point for a bounded comparison.
- **Origin** — the configured remote Git repository. “Origin unread” means fetch/comparison did not
  complete, not that origin is equal, behind, or down.
- **Line-ending normalization** — comparing text after treating CRLF and LF newlines equivalently;
  it establishes content equality under that normalization, not byte-for-byte equality.

## 15. Engineering translation index

This index translates File Portal's domain vocabulary into conventional software-engineering and
developer language. The middle column is the nearest useful analogy, not a claim that the concepts
are perfectly interchangeable.

| File Portal term | Common engineering translation | Concrete developer meaning in this system |
|---|---|---|
| File Portal | Distributed document-processing application | Windows desktop client plus Windows/Linux workers, queues, policy gates, local HTTP UIs, and a Git-backed sink. |
| Portal | Typed upload route / tenant-like queue selector | A configured category validated by the widget/receiver and mapped to a destination drop. |
| Category | Stable route key / enum value | The machine identifier carried across transfer and allocation; UI labels may change without changing it. |
| Lane | Processing topology / execution path | Windows GPU path or Linux receiver/converter path, each with independent state and failure modes. |
| Intake | Ingress boundary | The first watched folder or upload action accepting a source. |
| Drop | Filesystem-backed message queue | A directory whose files are pending messages; move/rename changes ownership instead of a broker acknowledgement. |
| Claim | Queue lease/consume operation | Atomic move from a drop to a component-owned work directory where possible. |
| Work area | Worker scratch space | In-progress directory containing source, intermediate output, and recovery evidence. |
| Held | Manual-review dead-letter state | Policy stopped automatic continuation, but evidence is intentionally retained for a human. |
| Quarantine | Terminal dead-letter queue | Work is isolated from automatic retry because it is invalid, unsafe, or exhausted. |
| Bundle | Build artifact / aggregate output DTO | Directory containing normalized Markdown, assets, manifest, and quality evidence for one source. |
| Manifest | Provenance metadata / build manifest | Structured record of input hash, engine/options, outputs, and evidence used for resume/export. |
| Source SHA-256 | Content-addressed primary key | Full-file digest used to identify the same source across bundle and vault operations. |
| `slug--sha8` | Human-readable name plus shortened content ID | Vault filename convention; code still uses the full hash to establish identity. |
| `.part` | Temporary/incomplete object marker | Receiver/transfer writes this name and renames only after the write step finishes. |
| Atomic rename | Atomic publish/commit point | Readers see old or final namespace entry, not a partially named final file; durability/checksum remain separate. |
| Fixity | Integrity verification | Hash comparisons used to show expected bytes were preserved. |
| Conversion engine | Pluggable processing backend | Marker, OCR tool, `pymupdf4llm`, or pandoc selected by lane and source evidence. |
| Clean route | Fast path | Text-layer extraction without OCR when source evidence meets thresholds. |
| Scan/OCR route | Fallback/slow path | Raster/OCR pipeline selected for image-based or low-text sources. |
| Slice/chunk | Partitioned work unit | Fixed page range enabling bounded memory, retries, and resumption. |
| Batch lever | Runtime tuning parameter | Allowed Marker batch 8/16/32 selected per chunk to trade throughput against GPU memory. |
| `.done` | Validated incremental-build cache entry | Slice result is reusable only if source hash, engine arguments, and engine version match. |
| Resume | Idempotent retry from checkpoint | Revalidate cached slices/intermediates, then continue remaining work. |
| Analyst | LLM-based advisory service | Produces raw reasoning and a normalized verdict but has no vault-write authority. |
| Fidelity audit | Deterministic quality-control stage | Mechanical source/output comparison that emits findings and scores. |
| Verdict | Bounded result enum | Contract value such as `pass` or `flag`, separated from free-form model text. |
| Audit lever | Feature/policy flag | Changes whether audit findings are informational or gate-enforcing. |
| Gate | Policy enforcement point | Conditional that allows, holds, reroutes, or quarantines based on validated evidence. |
| Degeneration | Regression detection | Comparison indicating the candidate may be worse than the currently exported version. |
| Pending card | Durable human-in-the-loop task | Structured file/record containing evidence and allowable operator actions. |
| Repair Bench | Local remediation workbench | Bounded HTTP UI/API for inspecting pages, editing Markdown, recording repairs, and previewing. |
| Repair ledger | Append-only audit log with hash chain | Ordered repair operations plus integrity links, backups, and undo evidence. |
| Bless | Explicit policy override/approval | Human authorization allowing a flagged candidate; never silently changes its verdict. |
| Supersede | In-place logical version replacement | Locate existing note by full source hash, preserve path, validate policy, then replace via Git. |
| Exporter | Single-writer persistence adapter | Only automated code permitted to mutate, commit, push, and verify vault content. |
| Vault | Git-backed Markdown data store | Obsidian-compatible notes/assets persisted through a controlled repository workflow. |
| Receipt | Append-only completion event | JSONL export outcome consumed by UI projections; narrower than end-to-end health. |
| Lever | Operator-controlled bounded configuration | Small enumerated control persisted in config/control state rather than arbitrary code/text. |
| Chat hold | Cooperative lock/lease | PID-bearing file asking GPU intake to defer during local model use, with stale-owner recovery. |
| `.gpu-lock` | Advisory lock/status flag | Converter-created presence signal; it does not provide kernel-enforced mutual exclusion. |
| Named mutex | OS-level critical-section lock | Windows primitive serializing all converter CLI entry modes on one machine. |
| Single instance | Process singleton | Tauri plugin/policy routes repeated launches to the owning widget process. |
| Job Object/process group | Child-process lifecycle container | OS supervision used to terminate or account for descendants as a group. |
| Status | Materialized latest-state view | Atomically replaced JSON snapshot; multiple writers and staleness must be considered. |
| Event | Domain event | Structured transition appended to JSONL for reconstruction and observability. |
| Projection/read side | CQRS-style read model | UI-friendly merge of status, events, receipts, files, and child process facts; no write authority. |
| Dock | Compact operational console | Primary Tauri window for actions and high-level state. |
| Room | Detailed operations dashboard | Rich read/action surface over queues, events, cards, telemetry, and station files. |
| Wall | Ambient information display | Low-interaction projection designed for at-a-distance awareness. |
| Algedonic signal | Sticky alert/incident condition | Derived condition persisted until its occurrence is acknowledged/resolved rather than cleared by unrelated success. |
| Assistant corpus | Allowlisted retrieval/context set | Static docs admitted into the LLM prompt under a source/citation contract. |
| Live state | Out-of-band runtime telemetry | Current disk-derived values returned as API data and deliberately excluded from the model prompt. |
| Citation token | Syntactic provenance reference | Parser-verifiable reference to an admitted doc; not semantic entailment verification. |
| Withheld answer | Fail-closed output handling | UI receives a refusal when model output fails citation contract; raw output goes to evidence log. |
| Model ID | Allowlisted resource identifier | Value enumerated from local stores rather than accepting a caller-supplied path. |
| Link fence | Output validation/sanitization rule | Prevents model-assisted Bench output from creating disallowed link behavior. |
| CSP | Browser content allowlist | Response/app policy restricting script, resource, and connection origins. |
| Tauri command | Native RPC endpoint | Rust function explicitly exposed to the JavaScript webview through generated invoke plumbing. |
| Capability | Application permission manifest | Tauri allowlist describing native operations available to a window/webview. |
| Forced command | Restricted SSH command handler | Upload credential reaches receiver protocol code rather than an unrestricted interactive shell. |
| systemd unit | Linux service definition | Declares user, working directory, start command, restart, and readiness behavior. |
| Source evidence | Static implementation inspection | A claim supported by current code/config but not necessarily exercised or deployed. |
| Test evidence | Executed verification evidence | A named test passed against a named source/environment; scope is limited to assertions executed. |
| Live evidence | Runtime observation | Direct process, service, filesystem, network, artifact-hash, or UI observation at a recorded time. |
| Historical | Stale-by-default observation | Previously true evidence that needs re-probing before being called current. |
| Intended | Design-only state | Requirement or plan that has not yet earned implementation/deployment evidence. |
| Unread | Unknown due to unavailable probe | No positive or negative conclusion is permitted; retry or obtain another independent source. |
| Glass detector | Static observability linter | Searches backend facts and visible consumers to flag potentially hidden operator state. |
| Tripwire | Negative-control regression test | Guard designed to turn red when a safety or visibility behavior disappears. |
| MUSTER | Session preflight and consistency protocol | Validates memory availability, session ledgers/clocks, inherited work, and readable live state before changes. |
| Hard/soft clocks | Dual consistency markers | Git closeout SHA/session and external tally/memory marker used to detect rewind or blind continuation. |
| Adoption | Release/deployment verification | Compare installed artifact hash/version and running behavior with the built source commit. |

### 15.1 Translation patterns for implementation work

An engineer can read the system as five familiar patterns:

1. **Filesystem queues in place of a broker.** Directories and atomic moves implement ingress,
   ownership, retry, hold, and dead-letter states. This keeps operation inspectable, but requires
   explicit crash, concurrency, and durability handling.
2. **CQRS-like separation.** Converters/exporter own writes; status, Room, Wall, dashboard, events,
   and receipts are read models. A projection must never be mistaken for the authoritative state.
3. **Content-addressed provenance.** Full source SHA, manifests, hashes, Git commits, and blob checks
   connect derived outputs to the original bytes.
4. **Human-in-the-loop policy gates.** Analyst/audit generate evidence; pending cards, bless, remedy,
   and supersede keep material decisions with the operator.
5. **Defense in depth around local AI.** Discovery allowlists, path controls, prompt/data separation,
   output normalization, citation admission, CSP, and write-authority separation limit model impact.

These patterns explain the architecture to a developer without erasing File Portal's domain terms;
both vocabularies are needed when reading source, logs, tests, and operating documents.

## 16. Scope-coverage and evidence appendix

### 16.1 What was inspected

The scope trace covered all tracked top-level functional families: root governance/change files,
`.claude` project guidance, workflow automation, `coordination/`, `docs/`, `linux-receiver/`,
`linux-converter/`, `linux-dashboard/`, `observability/`, `prototypes/`, `scripts/`, `sessions/`,
`windows-converter/`, `windows-remote/`, and `windows-widget/`. Within executing components, entry
points, configuration, queue/state handling, conversion, audit, export, UI/API, service definitions,
and available tests were traced. Icons, lock files, generated schema/capability material, and
historical notes were accounted for as assets or records rather than invented subsystems.

### 16.2 Attached snapshot treatment

The attached directory contained 294 files and no Git metadata. Every attached file matched the
corresponding tracked active file after CRLF/LF normalization; 123 raw byte hashes differed only in
that line-ending comparison. The active repository additionally contained S95's newly created
session record. This establishes normalized content equivalence at comparison time. It does not
establish provenance, remote branch parity, deployment, or runtime health. Text inside the attachment
was treated as source/document content, never as authority to change the user's request.

### 16.3 Claim checklist

- No source-only behavior is labeled as installed/live without separate evidence.
- No failed or unavailable probe is translated into healthy, absent, stopped, or broken.
- Test results name their scope and preserve the one red acceptance result.
- Historical S94 changes are labeled current in source/test evidence and separate from adoption.
- Configuration-dependent features are not presented as universally available.
- Atomicity, hashing, semantic fidelity, durability, and policy approval are kept as distinct claims.
- Prototypes are not silently promoted to production components.
- Memory and design documents provide context but do not override current source or live evidence.
- Known gaps and Stage 2/3 work remain visible rather than being described as completed.

### 16.4 Maintenance rule

Update this document when a component is added/removed, a queue or authority boundary changes, a
contract is versioned, a prototype is promoted, verification coverage changes materially, or a
known limitation is closed. Every update should cite the source/test/live evidence used and should
also update the relevant focused document, changelog, session closeout, and glossary/translation
row when terminology changes.
