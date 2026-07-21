// Without this the exe is a console-subsystem binary and Windows attaches a console window
// behind the widget on every launch (visible in the W8 live test).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod assay;
mod config;
mod events;
mod line;
mod preflight;
mod status;
mod transfer;
mod vault;
mod watcher;
use config::AppConfig;
use std::sync::Mutex;
use tauri::{Manager, State};
struct AppState {
    config: Mutex<AppConfig>,
}
#[tauri::command]
fn list_portals(state: State<AppState>) -> Vec<config::Portal> {
    state.config.lock().unwrap().portals.clone()
}
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
#[tauri::command]
fn watcher_status(
    state: State<AppState>,
    watcher_state: State<watcher::WatcherState>,
) -> Result<watcher::WatcherStatus, String> {
    let configured = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        !cfg.gpu_python_exe.is_empty() && !cfg.gpu_converter_dir.is_empty()
    };
    Ok(watcher::status(&watcher_state, configured))
}
#[tauri::command]
fn watcher_start(
    state: State<AppState>,
    watcher_state: State<watcher::WatcherState>,
) -> Result<watcher::WatcherStatus, String> {
    let (py, conv) = {
        let cfg = state
            .config
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        (cfg.gpu_python_exe.clone(), cfg.gpu_converter_dir.clone())
    };
    watcher::start(&watcher_state, &py, &conv)
}
#[tauri::command]
fn watcher_stop(watcher_state: State<watcher::WatcherState>) -> watcher::WatcherStatus {
    watcher::stop(&watcher_state)
}
// vault_check / vault_pull run `git fetch` to the ThinkPad over tailscale ssh, which BLOCKS
// for the dial timeout when the box is offline. Tauri runs synchronous commands on the main
// UI thread, so a blocking fetch there freezes the whole widget ("not responding") every
// poll while the vault host is unreachable. These are `async` + `spawn_blocking` so the git
// work runs on a worker thread — a sleeping vault host can never lock the UI. The config
// lock is taken and the path cloned out BEFORE the await, so no !Send guard crosses it.
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
/// Explorer hands shortcut-launched apps the environment captured at LOGIN — every
/// PATH entry (and env var) added since is invisible until re-login. That made
/// user-launched widgets diverge from shell-launched ones all night (S22 debugging
/// saga): git→tailscale ssh hung, spawns misfired. Fix: hydrate PATH (+ the keys the
/// pipeline needs) from the registry at boot, so every launch context is identical.
fn hydrate_env_from_registry() {
    use std::os::windows::process::CommandExt;
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

fn main() {
    hydrate_env_from_registry();
    let app_config = config::load_or_init().expect("failed to load config");
    tauri::Builder::default()
        .manage(AppState {
            config: Mutex::new(app_config),
        })
        .manage(watcher::WatcherState(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            list_portals,
            send_to_portal,
            fetch_file_status,
            preflight_list,
            preflight_decide,
            line_state,
            debug_log,
            analyst_mode_get,
            analyst_mode_set,
            assay_status,
            audit_mode_get,
            audit_mode_set,
            assay_reconvert,
            open_reader,
            open_failed_tray,
            reader_config,
            rules_set,
            rules_get,
            last_receipt,
            shift_summary,
            watcher_status,
            watcher_start,
            watcher_stop,
            vault_check,
            vault_pull
        ])
        .on_window_event(|window, event| {
            // The conveyor dies with its control room — no orphaned watch loops. An
            // in-flight conversion still runs to completion (see watcher.rs header).
            if let tauri::WindowEvent::Destroyed = event {
                let state: State<watcher::WatcherState> = window.app_handle().state();
                watcher::stop(&state);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running File Portal widget");
}
