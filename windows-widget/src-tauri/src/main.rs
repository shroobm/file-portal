// Without this the exe is a console-subsystem binary and Windows attaches a console window
// behind the widget on every launch (visible in the W8 live test).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
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
#[tauri::command]
fn vault_check(state: State<AppState>) -> Result<vault::VaultStatus, String> {
    // Clone the path out so the git fetch (seconds over tailscale ssh) runs lock-free.
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .vault_library_dir
        .clone();
    Ok(vault::check(&dir))
}
#[tauri::command]
fn vault_pull(state: State<AppState>) -> Result<vault::VaultStatus, String> {
    let dir = state
        .config
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .vault_library_dir
        .clone();
    Ok(vault::pull(&dir))
}
fn main() {
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
            analyst_mode_get,
            analyst_mode_set,
            open_reader,
            open_failed_tray,
            reader_config,
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
