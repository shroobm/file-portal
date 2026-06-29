// File Portal widget backend.
//
// Responsibilities: load config, expose `send_to_portal` to the frontend, and shell out to
// `tailscale ssh` to stream files to the Linux box — a remote `cat >` into a dotfile temp, then
// an atomic `mv` into place (see transfer.rs for why this, and not rsync/scp). No elevated
// privileges are ever requested — see docs/06-security-model.md for why that's a property of the
// whole design, not just this file.

mod config;
mod transfer;

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
    let cfg = state.config.lock().unwrap().clone();
    transfer::send_files(&cfg, &category, &paths)
}

fn main() {
    let app_config = config::load_or_init().unwrap_or_else(|e| {
        eprintln!("File Portal: {e}");
        std::process::exit(1);
    });

    tauri::Builder::default()
        .manage(AppState {
            config: Mutex::new(app_config),
        })
        .invoke_handler(tauri::generate_handler![list_portals, send_to_portal])
        .run(tauri::generate_context!())
        .expect("error while running File Portal widget");
}
