// S18: the pre-flight analyst card's backend. The Desktop converter parks bundles in
// <gpu_pipeline_dir>\pending\ with a <id>.json card (written by convert_and_ship.py
// --defer-analyst); this module lists those cards for the UI and, on the user's click,
// spawns the converter's --resume path fire-and-forget (analyst can run 10+ minutes — the
// widget must never block on it), SUPERVISED since S108: the child joins the kill-on-close
// Job Object, so it dies with the widget by any exit (SYM-047 class closed for this site). The card JSON is produced Python-side by analyst.preflight():
// measured ETAs, free-tier window warning, privacy labels, recommendation.

use crate::vault::CREATE_NO_WINDOW;
use crate::watcher::spawn_supervised;
use serde_json::Value;
use std::fs;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::{Command, Stdio};

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
/// Spawns the resume fire-and-forget and returns immediately; the card's state file tracks
/// progress and the poll loop watches it disappear (success) or flip to failed. The spawn is
/// SUPERVISED (S108): a widget exit — clean, crash, or force-kill — ends an in-flight resume
/// with it. That trade is the S37 doctrine: no orphaned GPU work, ever.
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
    // S76 (SYM-024): stderr goes to a LAST-WORDS FILE, never null — a resume that dies
    // before flipping the card's state used to vanish without a trace (observed 2026-08-13:
    // a routed card stayed "pending", no analyst, no evidence anywhere). The bench-stderr.log
    // idiom (S63); an open file handle is safe where an inherited console handle was not (S31).
    let last_words = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(Path::new(gpu_pipeline_dir).join("resume-stderr.log"))
        .map(Stdio::from)
        .unwrap_or_else(|_| Stdio::null());
    let mut cmd = Command::new(gpu_python_exe);
    cmd.arg(&script)
        .args(["--resume", id, "--backend", backend])
        .env("PYTHONIOENCODING", "utf-8")
        // Null stdin/stdout so the detached resume survives a windowless (Start-menu) launch —
        // same dead-inherited-handle crash the watcher hit (S31). It's fire-and-forget; the
        // card JSON state file, not stdout, is how the widget tracks it.
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(last_words)
        .creation_flags(CREATE_NO_WINDOW);
    // S108: supervised — this was one of the census's two un-adopted GPU spawns (the wiki's
    // "the two that matter"); a force-killed widget used to leave the whole conversion
    // running on the card.
    spawn_supervised(&mut cmd).map_err(|e| format!("failed to spawn resume: {e}"))?;
    Ok(())
}
