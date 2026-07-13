// Without this the exe is a console-subsystem binary and Windows attaches a console window
// behind the widget on every launch (visible in the W8 live test).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod config;
mod status;
mod transfer;
mod vault;
use config::AppConfig;
use std::sync::Mutex;
use tauri::State;
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
        .invoke_handler(tauri::generate_handler![
            list_portals,
            send_to_portal,
            fetch_file_status,
            vault_check,
            vault_pull
        ])
        .run(tauri::generate_context!())
        .expect("error while running File Portal widget");
}
