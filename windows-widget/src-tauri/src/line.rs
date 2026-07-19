// S21: the line view's state (docs/13 grammar: Drop ▸ Convert ▸ Gate ▸ Ship ▸ Library).
// Pure projection — every field is read fresh from the filesystem the pipeline writes.

use crate::vault::CREATE_NO_WINDOW;
use serde_json::{json, Value};
use std::fs;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::Command;

/// One read for the whole strip: drop-waiting, converting (lock), failed count, and the
/// last shipped bundle from the event stream's tail. Gate count comes from the existing
/// preflight_list; watcher/library state from their existing commands — no duplication.
pub fn state(gpu_pipeline_dir: &str) -> Result<Value, String> {
    if gpu_pipeline_dir.is_empty() {
        return Ok(json!({"available": false}));
    }
    let base = Path::new(gpu_pipeline_dir);
    let count_pdfs = |p: &Path| -> u32 {
        fs::read_dir(p)
            .map(|d| {
                d.flatten()
                    .filter(|e| {
                        e.path()
                            .extension()
                            .and_then(|x| x.to_str())
                            .is_some_and(|x| x.eq_ignore_ascii_case("pdf"))
                    })
                    .count() as u32
            })
            .unwrap_or(0)
    };
    let converting = fs::read_to_string(base.join(".gpu-lock"))
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty());
    // Last shipped: scan the events tail backwards for the newest ship/shipped.
    let last_shipped = fs::read_to_string(base.join("events.jsonl"))
        .ok()
        .and_then(|text| {
            text.lines().rev().find_map(|line| {
                let ev = serde_json::from_str::<Value>(line).ok()?;
                if ev["stage"] == "ship" && ev["event"] == "shipped" {
                    Some(json!({"bundle": ev["bundle"], "ts": ev["ts"]}))
                } else {
                    None
                }
            })
        });
    Ok(json!({
        "available": true,
        "drop_waiting": count_pdfs(&base.join("drop")),
        "converting": converting,
        "failed_count": count_pdfs(&base.join("drop").join("failed")),
        "last_shipped": last_shipped,
    }))
}

const MODES: [&str; 4] = ["ask", "local", "gemini", "off"];

pub fn get_analyst_mode(gpu_pipeline_dir: &str) -> String {
    let mode = fs::read_to_string(Path::new(gpu_pipeline_dir).join("analyst-mode.txt"))
        .map(|s| s.trim().to_lowercase())
        .unwrap_or_default();
    if MODES.contains(&mode.as_str()) {
        mode
    } else {
        "off".into()
    }
}

pub fn set_analyst_mode(gpu_pipeline_dir: &str, mode: &str) -> Result<String, String> {
    if !MODES.contains(&mode) {
        return Err(format!("invalid mode: {mode}"));
    }
    fs::write(
        Path::new(gpu_pipeline_dir).join("analyst-mode.txt"),
        format!("{mode}\n"),
    )
    .map_err(|e| format!("failed to write analyst-mode: {e}"))?;
    Ok(mode.into())
}

/// Launch a reader app (docs/13 "the dock has doors"). `target` is a configured exe path
/// or URI — never arbitrary input from a page; the config file is the allowlist.
pub fn open_reader(target: &str) -> Result<(), String> {
    if target.is_empty() {
        return Err("reader not configured".into());
    }
    if target.contains("://") {
        // URI scheme (obsidian://…): hand to the shell opener.
        Command::new("cmd")
            .args(["/c", "start", "", target])
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .map_err(|e| format!("failed to open uri: {e}"))?;
    } else {
        Command::new(target)
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .map_err(|e| format!("failed to launch reader: {e}"))?;
    }
    Ok(())
}

/// Open the failed tray (or any pipeline folder) in Explorer for hands-on triage.
pub fn open_folder(path: &str) -> Result<(), String> {
    Command::new("explorer.exe")
        .arg(path)
        .creation_flags(CREATE_NO_WINDOW)
        .spawn()
        .map_err(|e| format!("failed to open folder: {e}"))?;
    Ok(())
}
