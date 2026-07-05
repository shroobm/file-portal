mod config;
mod status;
mod transfer;
use config::AppConfig;
use std::sync::Mutex;
use tauri::State;
struct AppState { config: Mutex<AppConfig> }
#[tauri::command]
fn list_portals(state: State<AppState>) -> Vec<config::Portal> {
    state.config.lock().unwrap().portals.clone()
}
#[tauri::command]
fn send_to_portal(state: State<AppState>, category: String, paths: Vec<String>) -> Result<transfer::TransferReport, String> {
    let cfg = state.config.lock().map_err(|_| "lock poisoned".to_string())?;
    transfer::send_files(&cfg, &category, &paths)
}
#[tauri::command]
fn fetch_file_status(state: State<AppState>, category: String, filename: String) -> Result<Option<status::StatusEvent>, String> {
    let cfg = state.config.lock().map_err(|_| "lock poisoned".to_string())?;
    let events = status::fetch_events(&cfg.linux_host, &cfg.remote_user)?;
    Ok(status::find_event(&events, &filename, &category))
}
fn main() {
    let app_config = config::load_or_init().expect("failed to load config");
    tauri::Builder::default()
        .manage(AppState { config: Mutex::new(app_config) })
        .invoke_handler(tauri::generate_handler![list_portals, send_to_portal, fetch_file_status])
        .run(tauri::generate_context!())
        .expect("error while running File Portal widget");
}