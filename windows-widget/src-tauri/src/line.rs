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
    let lock_path = base.join(".gpu-lock");
    let converting = fs::read_to_string(&lock_path)
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty());
    // Convert start = the lock file's mtime (no timestamp parsing needed).
    let convert_elapsed_s = fs::metadata(&lock_path)
        .and_then(|m| m.modified())
        .ok()
        .and_then(|t| t.elapsed().ok())
        .map(|d| d.as_secs());
    // S42: real convert progress the converter streams from Marker (stage + per-page count).
    // Only read while a convert holds the lock — a stale file from a crash is ignored otherwise.
    let convert_progress = converting.as_ref().and_then(|_| {
        fs::read_to_string(base.join(".convert-progress.json"))
            .ok()
            .and_then(|s| serde_json::from_str::<Value>(&s).ok())
    });
    let cp_field = |k: &str| {
        convert_progress
            .as_ref()
            .and_then(|p| p.get(k).cloned())
            .unwrap_or(Value::Null)
    };
    let events_text = fs::read_to_string(base.join("events.jsonl")).unwrap_or_default();
    let events: Vec<Value> = events_text
        .lines()
        .filter_map(|l| serde_json::from_str(l).ok())
        .collect();
    let last_shipped = events
        .iter()
        .rev()
        .find(|ev| ev["stage"] == "ship" && ev["event"] == "shipped")
        .map(|ev| json!({"bundle": ev["bundle"], "ts": ev["ts"]}));
    // S26: honest countdown for the piece in the press — pages from its probe event ×
    // the measured median s/page of past conversions, minus elapsed.
    let converting_eta_s = converting.as_ref().and_then(|name| {
        let pages = events.iter().rev().find_map(|ev| {
            (ev["stage"] == "convert"
                && ev["event"] == "probe"
                && ev["source"].as_str() == Some(name.as_str()))
            .then(|| ev["pages"].as_u64())
            .flatten()
        })?;
        let mut rates: Vec<f64> = events
            .iter()
            .filter(|ev| ev["stage"] == "convert" && ev["event"] == "converted")
            .filter_map(|ev| ev["s_per_page"].as_f64())
            .collect();
        if rates.is_empty() {
            return None;
        }
        rates.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let median = rates[rates.len() / 2];
        let total = (pages as f64 * median) as i64;
        Some((total - convert_elapsed_s.unwrap_or(0) as i64).max(0))
    });
    // S26: the newest event, verbatim — the UI's stage ticker turns it into a sentence.
    let latest = events.last().cloned();
    Ok(json!({
        "available": true,
        "drop_waiting": count_pdfs(&base.join("drop")),
        "converting": converting,
        "converting_eta_s": converting_eta_s,
        // S37: seconds since the .gpu-lock was taken — lets the face draw a live convert
        // progress bar (elapsed / (elapsed + eta)) without any per-page hook in the converter.
        "convert_elapsed_s": convert_elapsed_s,
        // S42: the REAL current stage + per-page count, streamed from Marker (docs/16 §8 #3).
        "convert_stage": cp_field("stage"),
        "convert_frac": cp_field("frac"),
        "convert_n": cp_field("n"),
        "convert_total": cp_field("total"),
        "failed_count": count_pdfs(&base.join("drop").join("failed")),
        "last_shipped": last_shipped,
        "latest": latest,
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

/// S22: persist the card's remember-my-choice rule. The widget writes user *intent*;
/// the pipeline (convert_and_ship.defer) is the one that reads and applies it.
pub fn rules_set(
    gpu_pipeline_dir: &str,
    auto_local_over_chunks: Option<u32>,
) -> Result<Value, String> {
    let rules = json!({ "auto_local_over_chunks": auto_local_over_chunks });
    fs::write(
        Path::new(gpu_pipeline_dir).join("rules.json"),
        serde_json::to_string_pretty(&rules).unwrap() + "\n",
    )
    .map_err(|e| format!("failed to write rules: {e}"))?;
    Ok(rules)
}

pub fn rules_get(gpu_pipeline_dir: &str) -> Value {
    fs::read_to_string(Path::new(gpu_pipeline_dir).join("rules.json"))
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or_else(|| json!({}))
}

/// S22: the last shipped bundle's receipt — its whole chain gathered from the event
/// stream (probe/converted/analyst/shipped). Pure projection of existing truth.
pub fn last_receipt(gpu_pipeline_dir: &str) -> Result<Value, String> {
    let text = fs::read_to_string(Path::new(gpu_pipeline_dir).join("events.jsonl"))
        .map_err(|_| "no events yet".to_string())?;
    let events: Vec<Value> = text
        .lines()
        .filter_map(|l| serde_json::from_str(l).ok())
        .collect();
    let shipped = events
        .iter()
        .rev()
        .find(|e| e["stage"] == "ship" && e["event"] == "shipped")
        .ok_or("nothing shipped yet")?;
    let bundle = shipped["bundle"].as_str().unwrap_or_default().to_string();
    let mut receipt = json!({ "bundle": bundle, "shipped_ts": shipped["ts"] });
    // Walk backwards for this bundle's convert + analyst events (newest occurrence).
    for ev in events.iter().rev() {
        if ev["bundle"] != json!(bundle.clone())
            && !ev["source"]
                .as_str()
                .is_some_and(|s| s.starts_with(&bundle))
        {
            continue;
        }
        match (ev["stage"].as_str(), ev["event"].as_str()) {
            (Some("analyst"), Some("done")) if receipt["analyst"].is_null() => {
                receipt["analyst"] = json!({
                    "backend": ev["backend"], "program": ev["program"],
                    "passed": ev["chunks_passed"], "protected": ev["chunks_rejected"],
                    "failed": ev["chunks_failed"], "duration_s": ev["duration_s"],
                });
            }
            (Some("convert"), Some("converted")) if receipt["convert"].is_null() => {
                receipt["convert"] = json!({
                    "wall_s": ev["wall_s"], "s_per_page": ev["s_per_page"], "pages": ev["pages"],
                });
            }
            _ => {}
        }
    }
    Ok(receipt)
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
