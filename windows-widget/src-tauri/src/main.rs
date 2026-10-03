// WHAT THIS FILE DOES: the File Portal Windows widget's entry point (a Tauri app).
// - main() hydrates PATH from the registry, loads the config, shows a native dialog and exits if it
//   cannot be read, then builds the Tauri app: single-instance plugin, managed state, command table.
// - Every `#[tauri::command]` below is a thin wrapper the webview calls by name (invoke): most lock the
//   shared AppConfig (chat_stop, chat_status and gpu_vram do not), copy out the few paths they need, and delegate to a sibling module
//   (line, assay, bench, chat, watcher, vault, room, receipts, algedonic, preflight, events, status, transfer).
// - Reads: the config (config.rs) and, via the modules, the pipeline directory and the vault.
//   Writes: only widget-boot.log here (debug_log); all other writes happen inside the modules.
// - Network-touching commands are async + spawn_blocking so the UI thread never waits on ssh/git.
// - Called by: the operating system (exe launch) and the webview's JavaScript (main.js and the pages).

// Without this the exe is a console-subsystem binary and Windows attaches a console window
// behind the widget on every launch (visible in the W8 live test).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// -- module declarations: one file per concern --
mod algedonic;
mod assay;
mod bench;
mod chat;
mod config;
mod events;
mod line;
mod preflight;
mod receipts;
mod room;
mod status;
mod transfer;
mod vault;
mod watcher;
use config::AppConfig;
use std::sync::Mutex;
use tauri::{Manager, State};

// -- shared application state --

/// The config part of the Tauri-managed state (beside WatcherState, BenchState and ChatState, managed in main()):
/// the loaded config behind a Mutex, locked briefly by the commands that need a path from it.
struct AppState {
    config: Mutex<AppConfig>,
}

// -- commands: intake, status and preflight --

/// Command: returns a copy of the configured portals (drop categories) for the UI to render.
#[tauri::command]
fn list_portals(state: State<AppState>) -> Vec<config::Portal> {
    state.config.lock().unwrap().portals.clone()
}
/// Command: sends the given local file paths to a portal category (transfer::send_files); returns the report.
#[tauri::command]
fn send_to_portal(
    state: State<AppState>,
    category: String,
    paths: Vec<String>,
) -> Result<transfer::TransferReport, String> {
    let cfg = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?;
    transfer::send_files(&cfg, &category, &paths)
}
/// Command: fetches the remote event log (status::fetch_events, over the configured host/user) and
/// returns the event matching this filename and category, if any.
#[tauri::command]
fn fetch_file_status(
    state: State<AppState>,
    category: String,
    filename: String,
) -> Result<Option<status::StatusEvent>, String> {
    let cfg = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?;
    let events = status::fetch_events(&cfg.linux_host, &cfg.remote_user)?;
    Ok(status::find_event(&events, &filename, &category))
}
/// Command: lists the pending preflight items found in the pipeline directory, as JSON values.
#[tauri::command]
fn preflight_list(state: State<AppState>) -> Result<Vec<serde_json::Value>, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    preflight::list(&dir)
}
/// Command: records the operator's backend choice for one preflight item (preflight::decide); needs the
/// pipeline dir, the GPU python exe and the converter dir from the config.
#[tauri::command]
fn preflight_decide(state: State<AppState>, id: String, backend: String) -> Result<(), String> {
    let (dir, py, conv) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (
            cfg.gpu_pipeline_dir.clone(),
            cfg.gpu_python_exe.clone(),
            cfg.gpu_converter_dir.clone(),
        )
    };
    preflight::decide(&dir, &py, &conv, &id, &backend)
}
// -- commands: the conversion line (line.rs) --

/// Command: returns the line's current state as JSON (line::state) for the pipeline directory.
#[tauri::command]
fn line_state(state: State<AppState>) -> Result<serde_json::Value, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    line::state(&dir)
}
// S63: the Bench surface — spawn the quarantined Repair Bench server on a held bundle and
// open its dedicated window. Async + spawn_blocking: the spawn and its readiness wait must
// never sit on the UI thread (the vault_check freeze lesson); the window itself is created
// back on the main thread inside bench::open.

// -- commands: the Repair Bench --

/// Command: starts the Bench server for a held bundle (optional `source`) and opens its window; returns the port.
#[tauri::command]
async fn bench_open(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
    bench_state: State<'_, bench::BenchState>,
    source: Option<String>,
) -> Result<u16, String> {
    let (pipe, py, conv) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (
            cfg.gpu_pipeline_dir.clone(),
            cfg.gpu_python_exe.clone(),
            cfg.gpu_converter_dir.clone(),
        )
    };
    let bstate = bench_state.inner().clone();
    let src = source.unwrap_or_default();
    tauri::async_runtime::spawn_blocking(move || bench::open(app, &bstate, &pipe, &py, &conv, &src))
        .await
        .map_err(|e| format!("bench task failed: {e}"))?
}
// Stage E (docs/19 §5): the chunk-batch lever's write side — user intent into the backend's
// own lever file, exactly the analyst-mode pattern. Python re-reads it per slice.

// -- commands: levers and settings written for the Python backend --

/// Command: writes the chunk-batch size lever (line::set_chunk_batch); returns the value stored.
#[tauri::command]
fn chunk_batch_set(state: State<AppState>, batch: u32) -> Result<u32, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    line::set_chunk_batch(&dir, batch)
}
// Stage F (docs/19 §6): the algedonic line — all three are local file reads/writes, no network.

// -- commands: the algedonic line (alerts) --

/// Command: returns the algedonic alert state as JSON (algedonic::state).
#[tauri::command]
fn algedonic_state(state: State<AppState>) -> Result<serde_json::Value, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    algedonic::state(&dir)
}
/// Command: acknowledges one alert by id (algedonic::ack).
#[tauri::command]
fn algedonic_ack(state: State<AppState>, id: String) -> Result<(), String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    algedonic::ack(&dir, &id)
}
/// Command: sets the algedonic minutes threshold `m` (algedonic::set_minutes); returns the stored value.
#[tauri::command]
fn algedonic_minutes_set(state: State<AppState>, m: u64) -> Result<u64, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    algedonic::set_minutes(&dir, m)
}
/// Command: reads the analyst-mode file's current value (line::get_analyst_mode).
#[tauri::command]
fn analyst_mode_get(state: State<AppState>) -> Result<String, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    Ok(line::get_analyst_mode(&dir))
}
/// Command: writes the analyst mode (line::set_analyst_mode); returns the mode stored or an error.
#[tauri::command]
fn analyst_mode_set(state: State<AppState>, mode: String) -> Result<String, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    line::set_analyst_mode(&dir, &mode)
}
// -- commands: the assay (audit / bless / re-run, assay.rs) --

/// Command: returns the assay status as JSON (assay::status).
#[tauri::command]
fn assay_status(state: State<AppState>) -> Result<serde_json::Value, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    assay::status(&dir)
}
/// Command: reads the audit mode (assay::get_mode).
#[tauri::command]
fn audit_mode_get(state: State<AppState>) -> Result<String, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    Ok(assay::get_mode(&dir))
}
/// Command: writes the audit mode (assay::set_mode); returns the mode stored or an error.
#[tauri::command]
fn audit_mode_set(state: State<AppState>, mode: String) -> Result<String, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    assay::set_mode(&dir, &mode)
}
/// Command: asks for a source to be converted again (assay::reconvert); synchronous, returns nothing on success.
#[tauri::command]
fn assay_reconvert(state: State<AppState>, source: String) -> Result<(), String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    assay::reconvert(&dir, &source)
}
// Stage C2 (docs/19 §3.1): the ⟲ analyst-only re-run. Synchronous like assay_reconvert — it
// only spawns a detached process; the long work happens in that child, not here.

/// Command: re-runs the analyst on a source with a chosen backend (assay::reanalyze).
#[tauri::command]
fn assay_reanalyze(state: State<AppState>, source: String, backend: String) -> Result<(), String> {
    let (dir, py, conv) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (
            cfg.gpu_pipeline_dir.clone(),
            cfg.gpu_python_exe.clone(),
            cfg.gpu_converter_dir.clone(),
        )
    };
    assay::reanalyze(&dir, &py, &conv, &source, &backend)
}
// Stage C (docs/18 §5.4): the bless click. Async + spawn_blocking because it scp's the marker
// to the ThinkPad over ssh — a blocking network call on the UI thread would freeze the widget
// exactly like the vault_check lesson.

/// Command: blesses a source (assay::bless, on a worker thread; copies to the vault host over ssh); returns text.
#[tauri::command]
async fn assay_bless(state: State<'_, AppState>, source: String) -> Result<String, String> {
    let (dir, host, user) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (
            cfg.gpu_pipeline_dir.clone(),
            cfg.linux_host.clone(),
            cfg.remote_user.clone(),
        )
    };
    tauri::async_runtime::spawn_blocking(move || assay::bless(&dir, &host, &user, &source))
        .await
        .map_err(|e| format!("bless task failed: {e}"))?
}
// Stage C2 (docs/19 §3.3): the seam receipts. `receipts_fetch` crosses the network, so it is
// async + spawn_blocking and rides the vault bar's existing 45 s poll (a sleeping ThinkPad must
// never freeze the UI — the vault_check lesson). `receipts_read` is a local cache read, cheap
// enough for the Room's 4-9 s re-render.

// -- commands: seam receipts --

/// Command: fetches receipts from the remote host into the local cache (receipts::fetch, on a worker thread).
#[tauri::command]
async fn receipts_fetch(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let (dir, host, user) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (
            cfg.gpu_pipeline_dir.clone(),
            cfg.linux_host.clone(),
            cfg.remote_user.clone(),
        )
    };
    tauri::async_runtime::spawn_blocking(move || receipts::fetch(&dir, &host, &user))
        .await
        .map_err(|e| format!("receipts task failed: {e}"))?
}
/// Command: returns the locally cached receipts as JSON (receipts::read_cached); no network.
#[tauri::command]
fn receipts_read(state: State<AppState>) -> Result<serde_json::Value, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    Ok(receipts::read_cached(&dir))
}
// -- commands: openers, rules and receipts of the line --

/// Command: opens the vault in a named reader ("obsidian" or "zennotes"; anything else is an error).
/// The config lock is released before line::open_reader runs.
#[tauri::command]
fn open_reader(state: State<AppState>, reader: String) -> Result<(), String> {
    let cfg = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?;
    let target = match reader.as_str() {
        "obsidian" => cfg.reader_obsidian.clone(),
        "zennotes" => cfg.reader_zennotes.clone(),
        _ => return Err("unknown reader".into()),
    };
    drop(cfg);
    line::open_reader(&target)
}
/// Command: updates the line's rules (optional auto-local-over-chunks threshold) via line::rules_set.
#[tauri::command]
fn rules_set(
    state: State<AppState>,
    auto_local_over_chunks: Option<u32>,
) -> Result<serde_json::Value, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    line::rules_set(&dir, auto_local_over_chunks)
}
/// Command: reads the line's current rules as JSON (line::rules_get).
#[tauri::command]
fn rules_get(state: State<AppState>) -> Result<serde_json::Value, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    Ok(line::rules_get(&dir))
}
/// Command: returns the most recent conversion receipt as JSON (line::last_receipt).
#[tauri::command]
fn last_receipt(state: State<AppState>) -> Result<serde_json::Value, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    line::last_receipt(&dir)
}
// S66: engineering quick-access — a NAMED allowlist target (see line::open_engineering).

/// Command: opens a named engineering target from line::open_engineering's allowlist (folders, and files opened in
/// Notepad); returns the path it opened.
#[tauri::command]
fn open_engineering(state: State<AppState>, target: String) -> Result<String, String> {
    let (pipe, conv, vault) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (
            cfg.gpu_pipeline_dir.clone(),
            cfg.gpu_converter_dir.clone(),
            cfg.vault_library_dir.clone(),
        )
    };
    line::open_engineering(&pipe, &conv, &vault, &target)
}
/// Command: opens the `drop\failed` folder of the pipeline directory in the file explorer.
#[tauri::command]
fn open_failed_tray(state: State<AppState>) -> Result<(), String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    line::open_folder(&format!("{dir}\\drop\\failed"))
}
// S85: the assistant's lifecycle — bench_open's chassis with a stop and a death certificate.
// The model LOAD is not here: the UI server is stdlib-instant, and the slow llama load happens
// behind the page's own Load button (docs/33 §2.4 — the 6 s ceiling stays un-copied).

// -- commands: the assistant (chat.rs) --

/// Command: starts the assistant UI server and opens its window (chat::open, on a worker thread); returns the port.
#[tauri::command]
async fn chat_open(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
    chat_state: State<'_, chat::ChatState>,
) -> Result<u16, String> {
    let (pipe, py, conv, llama) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (
            cfg.gpu_pipeline_dir.clone(),
            cfg.gpu_python_exe.clone(),
            cfg.gpu_converter_dir.clone(),
            cfg.llama_server_exe.clone(),
        )
    };
    let cstate = chat_state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        chat::open(app, &cstate, &pipe, &py, &conv, &llama)
    })
    .await
    .map_err(|e| format!("chat task failed: {e}"))?
}

/// Command: stops the assistant server; returns whether something was stopped (chat::stop).
#[tauri::command]
fn chat_stop(chat_state: State<chat::ChatState>) -> Result<bool, String> {
    chat::stop(&chat_state)
}

/// Command: returns the assistant's lifecycle status as JSON (chat::status).
#[tauri::command]
fn chat_status(chat_state: State<chat::ChatState>) -> Result<serde_json::Value, String> {
    chat::status(&chat_state)
}

// The reader_config idiom: a BOOLEAN, never the path — the page learns whether the feature
// exists, not where the binary lives.

/// Command: returns {"configured": bool} - whether a llama server exe path is set; never the path itself.
#[tauri::command]
fn chat_config(state: State<AppState>) -> Result<serde_json::Value, String> {
    let cfg = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?;
    Ok(serde_json::json!({ "configured": !cfg.llama_server_exe.is_empty() }))
}

// -- commands: config flags, debug log, Room projections --

/// Command: returns which readers (obsidian, zennotes) are configured, as booleans only.
#[tauri::command]
fn reader_config(state: State<AppState>) -> Result<serde_json::Value, String> {
    let cfg = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?;
    Ok(serde_json::json!({
        "obsidian": !cfg.reader_obsidian.is_empty(),
        "zennotes": !cfg.reader_zennotes.is_empty(),
    }))
}
/// Command: appends "<unix seconds> <msg>" to widget-boot.log in the pipeline dir; best effort, no result.
#[tauri::command]
fn debug_log(state: State<AppState>, msg: String) {
    // S22 debug channel: boot beacons from the webview, appended where no crop or
    // transparency can hide them. Best-effort; never fails the caller.
    if let Ok(cfg) = state.config.lock() {
        if !cfg.gpu_pipeline_dir.is_empty() {
            let path = std::path::Path::new(&cfg.gpu_pipeline_dir).join("widget-boot.log");
            let line = format!(
                "{} {}\n",
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_secs())
                    .unwrap_or(0),
                msg
            );
            let _ = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
                .and_then(|mut f| std::io::Write::write_all(&mut f, line.as_bytes()));
        }
    }
}
/// Command: returns the shift summary as JSON (events::shift_summary).
#[tauri::command]
fn shift_summary(state: State<AppState>) -> Result<serde_json::Value, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .gpu_pipeline_dir
        .clone();
    events::shift_summary(&dir)
}
// S34 — the Room's KPI band (read-only projection: throughput / median s-per-page / survival
// average / vault count / recent audits, from the same events + manifests Python writes).

/// Command: returns the Room's KPI metrics as JSON (room::metrics) from the pipeline and vault dirs.
#[tauri::command]
fn room_metrics(state: State<AppState>) -> Result<serde_json::Value, String> {
    let (pipeline, vault) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (cfg.gpu_pipeline_dir.clone(), cfg.vault_library_dir.clone())
    };
    room::metrics(&pipeline, &vault)
}
// S34 — live GPU memory via nvidia-smi (null when there is no probe).

/// Command: returns live GPU memory as JSON (room::gpu_vram); takes no state.
#[tauri::command]
fn gpu_vram() -> serde_json::Value {
    room::gpu_vram()
}
// S36 — the drill-down observation system: a station's real on-disk tree (read-only projection).

/// Command: returns the on-disk tree of station `seg` as JSON (room::station_tree); read only.
#[tauri::command]
fn station_tree(state: State<AppState>, seg: String) -> Result<serde_json::Value, String> {
    let (pipeline, vault) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (cfg.gpu_pipeline_dir.clone(), cfg.vault_library_dir.clone())
    };
    room::station_tree(&pipeline, &vault, &seg)
}
// -- commands: the watcher (drop-folder conveyor, watcher.rs) --

/// Command: returns the watcher's status; "configured" means a GPU python exe and converter dir are both set.
#[tauri::command]
fn watcher_status(
    state: State<AppState>,
    watcher_state: State<watcher::WatcherState>,
) -> Result<watcher::WatcherStatus, String> {
    let (configured, pipe) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (
            !cfg.gpu_python_exe.is_empty() && !cfg.gpu_converter_dir.is_empty(),
            cfg.gpu_pipeline_dir.clone(),
        )
    };
    Ok(watcher::status(&watcher_state, configured, Some(&pipe)))
}
/// Command: starts the watcher with the configured python exe, converter dir and pipeline dir; returns its status.
#[tauri::command]
fn watcher_start(
    state: State<AppState>,
    watcher_state: State<watcher::WatcherState>,
) -> Result<watcher::WatcherStatus, String> {
    let (py, conv, pipe) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (
            cfg.gpu_python_exe.clone(),
            cfg.gpu_converter_dir.clone(),
            cfg.gpu_pipeline_dir.clone(),
        )
    };
    watcher::start(&watcher_state, &py, &conv, &pipe)
}
/// Command: stops the watcher; an unreadable config falls back to an empty pipeline dir. Returns its status.
#[tauri::command]
fn watcher_stop(
    state: State<AppState>,
    watcher_state: State<watcher::WatcherState>,
) -> watcher::WatcherStatus {
    let pipe = state
        .config
        .lock()
        .map(|cfg| cfg.gpu_pipeline_dir.clone())
        .unwrap_or_default();
    watcher::stop(&watcher_state, Some(&pipe))
}
// vault_check / vault_pull run `git fetch` to the ThinkPad over tailscale ssh, which BLOCKS
// for the dial timeout when the box is offline. Tauri runs synchronous commands on the main
// UI thread, so a blocking fetch there freezes the whole widget ("not responding") every
// poll while the vault host is unreachable. These are `async` + `spawn_blocking` so the git
// work runs on a worker thread — a sleeping vault host can never lock the UI. The config
// lock is taken and the path cloned out BEFORE the await, so no !Send guard crosses it.

// -- commands: the vault (git over ssh, vault.rs) --

/// Command: checks the vault repo's status on a worker thread (vault::check); returns VaultStatus.
#[tauri::command]
async fn vault_check(state: State<'_, AppState>) -> Result<vault::VaultStatus, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .vault_library_dir
        .clone();
    tauri::async_runtime::spawn_blocking(move || vault::check(&dir))
        .await
        .map_err(|e| format!("vault check task failed: {e}"))
}
/// Command: pulls the vault repo on a worker thread (vault::pull); returns the resulting VaultStatus.
#[tauri::command]
async fn vault_pull(state: State<'_, AppState>) -> Result<vault::VaultStatus, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .vault_library_dir
        .clone();
    tauri::async_runtime::spawn_blocking(move || vault::pull(&dir))
        .await
        .map_err(|e| format!("vault pull task failed: {e}"))
}
// -- startup: environment, config failure dialog, main() --

/// Explorer hands shortcut-launched apps the environment captured at LOGIN — every
/// PATH entry (and env var) added since is invisible until re-login. That made
/// user-launched widgets diverge from shell-launched ones all night (S22 debugging
/// saga): git→tailscale ssh hung, spawns misfired. Fix: hydrate PATH (+ the keys the
/// pipeline needs) from the registry at boot, so every launch context is identical.
fn hydrate_env_from_registry() {
    use std::os::windows::process::CommandExt;
    // Helper: runs `reg query <key> /v <value>` with no console window and parses the value text from its output.
    let read_reg = |hive_key: &str, value: &str| -> Option<String> {
        let out = std::process::Command::new("reg")
            .args(["query", hive_key, "/v", value])
            .creation_flags(vault::CREATE_NO_WINDOW)
            .output()
            .ok()?;
        let text = String::from_utf8_lossy(&out.stdout).to_string();
        text.lines().find_map(|l| {
            let idx = l.find("REG_")?;
            let (_, after_type) = l[idx..].split_once(char::is_whitespace)?;
            let v = after_type.trim();
            (!v.is_empty()).then(|| v.to_string())
        })
    };
    // Expand %VAR% references (REG_EXPAND_SZ values keep them literal).
    let expand = |s: &str| -> String {
        let mut out = String::new();
        let mut rest = s;
        while let Some(start) = rest.find('%') {
            out.push_str(&rest[..start]);
            if let Some(end_rel) = rest[start + 1..].find('%') {
                let name = &rest[start + 1..start + 1 + end_rel];
                out.push_str(&std::env::var(name).unwrap_or_else(|_| format!("%{name}%")));
                rest = &rest[start + 1 + end_rel + 1..];
            } else {
                out.push_str(&rest[start..]);
                rest = "";
            }
        }
        out.push_str(rest);
        out
    };
    // Rebuild PATH as machine Path followed by user Path, each with %VAR% expanded.
    let machine = read_reg(
        r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        "Path",
    )
    .map(|v| expand(&v))
    .unwrap_or_default();
    let user = read_reg(r"HKCU\Environment", "Path")
        .map(|v| expand(&v))
        .unwrap_or_default();
    if !machine.is_empty() || !user.is_empty() {
        std::env::set_var("PATH", format!("{machine};{user}"));
    }
    // The Gemini analyst backend reads this from its environment (never from disk).
    if std::env::var("GEMINI_API_KEY").is_err() {
        if let Some(key) = read_reg(r"HKCU\Environment", "GEMINI_API_KEY") {
            std::env::set_var("GEMINI_API_KEY", key);
        }
    }
}

/// S157 E55 (B32 U02, Codex's 2026-08-27 audit, probed at HEAD S157 E51): the text the operator sees when the
/// config cannot be read. `load_or_init` already names the file and the parse error; this adds the remedy and is
/// pure so a test can read it. Kept separate from the dialog call, which a test cannot exercise.
fn config_failure_text(why: &str) -> String {
    format!(
        "File Portal cannot start.\n\n{why}\n\nFix the file, or move it aside to get a fresh default on the next \
         launch, then start File Portal again."
    )
}

/// The one native dialog in the widget: a release build runs with `windows_subsystem = "windows"` (no console),
/// so `expect(...)` on the config used to die where nobody could read it — U02's "console-less panic with no
/// operator-visible remedy". MessageBoxW blocks until dismissed; the process exits after it.
fn fatal_config_dialog(why: &str) {
    use windows_sys::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONERROR, MB_OK};
    let text: Vec<u16> = config_failure_text(why)
        .encode_utf16()
        .chain(std::iter::once(0))
        .collect();
    let caption: Vec<u16> = "File Portal — config"
        .encode_utf16()
        .chain(std::iter::once(0))
        .collect();
    // a debug build still has a console; say it there too
    eprintln!("{why}");
    // SAFETY: both strings are NUL-terminated UTF-16 buffers that outlive the call; a null owner window is
    // documented as valid for MessageBoxW.
    unsafe {
        MessageBoxW(
            std::ptr::null_mut(),
            text.as_ptr(),
            caption.as_ptr(),
            MB_OK | MB_ICONERROR,
        );
    }
}

/// Program entry: hydrates the environment, loads the config (fatal dialog + exit code 2 on failure), then
/// builds and runs the Tauri app (single-instance plugin, managed state, command table, window-close hook).
fn main() {
    // -- boot: environment and config --
    hydrate_env_from_registry();
    let app_config = match config::load_or_init() {
        Ok(cfg) => cfg,
        Err(why) => {
            fatal_config_dialog(&why);
            std::process::exit(2);
        }
    };
    tauri::Builder::default()
        // SYM-033 (signed docs/37 §3.2): nothing prevented a second full instance — two
        // watcher chains on one drop folder, SYM-022's crash precondition a double-click
        // away. First plugin registered, per the plugin's own contract. A second launch
        // now fronts the ONE widget instead of becoming a second factory.
        .plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {
            if let Some(w) = app.get_webview_window("main") {
                // set_focus alone no-ops on a MINIMIZED window (tao skips it) — and the
                // minimized widget is the ONE state where a user relaunches to bring it
                // back (the titlebar has a dedicated minimize button, main.js). Restore
                // first; both calls are no-ops when already visible. S94 review catch.
                let _ = w.unminimize();
                let _ = w.show();
                let _ = w.set_focus();
            }
            // OK-14 (signed Rab 2026-08-31): forward-instead-of-die (OBS-10). The losing
            // launch's open request — its first non-flag argument, e.g. a bundle name on a
            // shortcut or a path dropped onto the exe — opens the Bench on the WINNER
            // instead of evaporating with the loser. No argument = S94's front-the-window
            // behavior alone. Same spawn_blocking chassis as bench_open: the readiness
            // wait must never sit on the UI thread.
            if let Some(req) = argv.iter().skip(1).find(|a| !a.starts_with('-')) {
                let app = app.clone();
                let req = req.clone();
                tauri::async_runtime::spawn_blocking(move || {
                    let (pipe, py, conv) = {
                        let state: State<AppState> = app.state();
                        let cfg = match state.config.lock() {
                            Ok(c) => c,
                            Err(_) => return,
                        };
                        (
                            cfg.gpu_pipeline_dir.clone(),
                            cfg.gpu_python_exe.clone(),
                            cfg.gpu_converter_dir.clone(),
                        )
                    };
                    let bstate = app.state::<bench::BenchState>().inner().clone();
                    let _ = bench::open(app.clone(), &bstate, &pipe, &py, &conv, &req);
                });
            }
        }))
        // -- managed state shared with the commands --
        .manage(AppState {
            config: Mutex::new(app_config),
        })
        .manage(watcher::WatcherState(
            Mutex::new(None),
            Mutex::new(None),
            Mutex::new(None),
        ))
        .manage(bench::BenchState::default())
        .manage(chat::ChatState::default())
        // -- the command table: every name here is callable from the webview --
        .invoke_handler(tauri::generate_handler![
            list_portals,
            send_to_portal,
            fetch_file_status,
            preflight_list,
            preflight_decide,
            line_state,
            debug_log,
            bench_open,
            chunk_batch_set,
            algedonic_state,
            algedonic_ack,
            algedonic_minutes_set,
            analyst_mode_get,
            analyst_mode_set,
            assay_status,
            audit_mode_get,
            audit_mode_set,
            assay_reconvert,
            assay_reanalyze,
            assay_bless,
            receipts_fetch,
            receipts_read,
            open_reader,
            open_engineering,
            open_failed_tray,
            reader_config,
            rules_set,
            rules_get,
            last_receipt,
            shift_summary,
            room_metrics,
            gpu_vram,
            station_tree,
            watcher_status,
            watcher_start,
            watcher_stop,
            vault_check,
            vault_pull,
            chat_open,
            chat_stop,
            chat_status,
            chat_config
        ])
        // -- window close hook: the main window's death stops the watcher and closes the other windows --
        .on_window_event(|window, event| {
            // The conveyor dies with its control room — no orphaned watch loops. An
            // in-flight conversion still runs to completion (see watcher.rs header).
            //
            // S76 (SYM-023): this hook fires for EVERY window, and it was written in the
            // one-window era (S37). When the Bench window (S63, "repair-bench") was closed
            // while the widget lived, this arm assassinated the watcher — first fired
            // 2026-08-13. Only the MAIN window's death is the widget's death; any window
            // added later inherits this guard by construction.
            if let tauri::WindowEvent::Destroyed = event {
                if window.label() == "main" {
                    let state: State<watcher::WatcherState> = window.app_handle().state();
                    watcher::stop(&state, None);
                    // A3 (signed Rab 2026-08-31): the job's KILL_ON_JOB_CLOSE fires only
                    // when the PROCESS exits, and tauri exits on the LAST window — so a
                    // live Bench or Chat window deferred the kill and left a half-dead
                    // factory (watcher stopped, servers alive, no control room). The main
                    // window's death closes the house.
                    for (label, w) in window.app_handle().webview_windows() {
                        if label != "main" {
                            let _ = w.close();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running File Portal widget");
}

// -- tests --

/// Unit tests for the config-failure dialog text.
#[cfg(test)]
mod config_failure_tests {
    use super::config_failure_text;

    /// S157 E55 (B32 U02): the operator's text names the failure it was given AND a remedy; the negative control is
    /// the old shape — a bare `why` with no remedy sentence — which this test would refuse.
    #[test]
    fn the_failure_text_carries_the_why_and_a_remedy() {
        let why = r"failed to parse C:\Users\x\AppData\Roaming\file-portal\config.toml: expected `=` at line 3";
        let text = config_failure_text(why);
        assert!(
            text.contains(why),
            "the parse error and the file path reach the operator verbatim"
        );
        assert!(text.contains("move it aside"), "the remedy is spelled out");
        assert!(text.starts_with("File Portal cannot start."));
        assert!(
            !why.contains("move it aside"),
            "negative control: the bare error has no remedy of its own"
        );
    }
}
