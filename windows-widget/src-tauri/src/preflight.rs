// S18: the pre-flight analyst card's backend. The Desktop converter parks bundles in
// <gpu_pipeline_dir>\pending\ with a <id>.json card (written by convert_and_ship.py
// --defer-analyst); this module lists those cards for the UI and, on the user's click,
// spawns the converter's --resume path detached (analyst can run 10+ minutes — the widget
// must never block on it). The card JSON is produced Python-side by analyst.preflight():
// measured ETAs, free-tier window warning, privacy labels, recommendation.

use crate::vault::CREATE_NO_WINDOW;
use serde_json::Value;
use std::fs;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::Command;

/// All pending/failed cards, raw JSON straight through to the UI (the schema lives in
/// Python, the single writer; the widget renders what it gets).
pub fn list(gpu_pipeline_dir: &str) -> Result<Vec<Value>, String> {
    if gpu_pipeline_dir.is_empty() {
        return Ok(vec![]); // feature hidden until configured, same pattern as vault_library_dir
    }
    let pending = Path::new(gpu_pipeline_dir).join("pending");
    let mut cards = vec![];
    let entries = match fs::read_dir(&pending) {
        Ok(e) => e,
        Err(_) => return Ok(vec![]), // no queue dir yet = nothing pending
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        if let Ok(text) = fs::read_to_string(&path) {
            if let Ok(card) = serde_json::from_str::<Value>(&text) {
                cards.push(card);
            }
        }
    }
    cards.sort_by(|a, b| {
        a["created_at"]
            .as_str()
            .unwrap_or("")
            .cmp(b["created_at"].as_str().unwrap_or(""))
    });
    Ok(cards)
}

/// The user's routing click. `backend` is "local", "gemini", or "none" (ship as-is).
/// Spawns the resume detached and returns immediately; the card's state file tracks
/// progress and the poll loop watches it disappear (success) or flip to failed.
pub fn decide(
    gpu_pipeline_dir: &str,
    gpu_python_exe: &str,
    gpu_converter_dir: &str,
    id: &str,
    backend: &str,
) -> Result<(), String> {
    if !id.chars().all(|c| c.is_ascii_hexdigit()) || id.len() != 16 {
        return Err("invalid pending id".into());
    }
    if !matches!(backend, "local" | "gemini" | "none") {
        return Err("invalid backend".into());
    }
    if gpu_python_exe.is_empty() || gpu_converter_dir.is_empty() {
        return Err("gpu_python_exe / gpu_converter_dir not configured".into());
    }
    let script = Path::new(gpu_converter_dir).join("convert_and_ship.py");
    if !script.is_file() {
        return Err(format!("converter script not found: {}", script.display()));
    }
    let json_path = Path::new(gpu_pipeline_dir)
        .join("pending")
        .join(format!("{id}.json"));
    if !json_path.is_file() {
        return Err("pending card no longer exists".into());
    }
    Command::new(gpu_python_exe)
        .arg(&script)
        .args(["--resume", id, "--backend", backend])
        .env("PYTHONIOENCODING", "utf-8")
        .creation_flags(CREATE_NO_WINDOW)
        .spawn()
        .map_err(|e| format!("failed to spawn resume: {e}"))?;
    Ok(())
}
