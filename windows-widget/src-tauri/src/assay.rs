// S31: the Assay — the Survival Audit's read side (docs/15 §13). Pure projection: Python
// owns the `fidelity` block in each bundle's manifest.json (schema docs/15 §7) and the
// audit-mode.txt lever; this module gathers the newest verdict + its localized evidence
// (degeneration zones, omission runs) + the held queue for the widget's ◎ station and
// evidence card. Read-only, no state. Terracotta is the UI's to spend — this only reports.

use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

const AUDIT_MODES: [&str; 2] = ["report", "enforce"];

/// report (default) = the audit observes but ships anyway; enforce = a `fail` verdict
/// parks the bundle. Mirrors line::get_analyst_mode.
pub fn get_mode(gpu_pipeline_dir: &str) -> String {
    let mode = fs::read_to_string(Path::new(gpu_pipeline_dir).join("audit-mode.txt"))
        .map(|s| s.trim().to_lowercase())
        .unwrap_or_default();
    if AUDIT_MODES.contains(&mode.as_str()) {
        mode
    } else {
        "report".into()
    }
}

pub fn set_mode(gpu_pipeline_dir: &str, mode: &str) -> Result<String, String> {
    if !AUDIT_MODES.contains(&mode) {
        return Err(format!("invalid audit mode: {mode}"));
    }
    fs::write(
        Path::new(gpu_pipeline_dir).join("audit-mode.txt"),
        format!("{mode}\n"),
    )
    .map_err(|e| format!("failed to write audit-mode: {e}"))?;
    Ok(mode.into())
}

/// The newest manifest.json (by mtime) across anchor/, pending/, held/ — the most recently
/// audited bundle. Each of those dirs holds <bundle>/manifest.json.
fn newest_manifest(base: &Path) -> Option<PathBuf> {
    let mut newest: Option<(PathBuf, SystemTime)> = None;
    for sub in ["anchor", "pending", "held"] {
        let Ok(entries) = fs::read_dir(base.join(sub)) else {
            continue;
        };
        for entry in entries.flatten() {
            let manifest = entry.path().join("manifest.json");
            let Ok(mtime) = fs::metadata(&manifest).and_then(|m| m.modified()) else {
                continue;
            };
            let better = match &newest {
                Some((_, t)) => mtime > *t,
                None => true,
            };
            if better {
                newest = Some((manifest, mtime));
            }
        }
    }
    newest.map(|(p, _)| p)
}

/// Bundles parked by the enforce lever (docs/15 §12): held/<sha16>/manifest.json.
fn held_list(base: &Path) -> Vec<Value> {
    let Ok(entries) = fs::read_dir(base.join("held")) else {
        return vec![];
    };
    let mut out = vec![];
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        let m: Value = match fs::read_to_string(path.join("manifest.json")) {
            Ok(t) => match serde_json::from_str(&t) {
                Ok(v) => v,
                Err(_) => continue,
            },
            Err(_) => continue,
        };
        out.push(json!({
            "id": path.file_name().and_then(|n| n.to_str()).unwrap_or_default(),
            "bundle": m["source"],
            "verdict": m["fidelity"]["verdict"],
        }));
    }
    out
}

/// The ◎ station + evidence card state: the newest audited verdict with its localized
/// evidence, plus the held queue and the current lever. Everything comes from the manifest
/// Python already wrote — the widget invents nothing.
pub fn status(gpu_pipeline_dir: &str) -> Result<Value, String> {
    if gpu_pipeline_dir.is_empty() {
        return Ok(json!({ "available": false }));
    }
    let base = Path::new(gpu_pipeline_dir);
    let mode = get_mode(gpu_pipeline_dir);
    let held = held_list(base);

    let Some(manifest_path) = newest_manifest(base) else {
        return Ok(json!({ "available": true, "mode": mode, "verdict": Value::Null, "held": held }));
    };
    let manifest: Value = fs::read_to_string(&manifest_path)
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or_else(|| json!({}));
    let fid = &manifest["fidelity"];
    if fid.is_null() {
        return Ok(json!({ "available": true, "mode": mode, "verdict": Value::Null, "held": held }));
    }
    let conv = &fid["convert"];
    let degen = &conv["tripwires"]["degeneration_detail"];
    Ok(json!({
        "available": true,
        "mode": mode,
        "verdict": fid["verdict"],
        "bundle": manifest["source"],
        "kind": conv["kind"],
        "doc_survival": conv["doc_survival"],
        "pages_scored": conv["pages_scored"],
        "degeneration": conv["tripwires"]["degeneration"],
        "md_lines": degen["md_lines"],
        "zones": degen["worst"],
        "runs": conv["runs"],
        "analyst": fid["analyst"],
        "held": held,
    }))
}

/// Assay remedy (docs/15 §13): re-queue a source for conversion + re-audit by copying it
/// from drop/done/ back into drop/ — the watcher picks it up on its next poll. The vault
/// SWAP after a clean re-audit is manual (THE SUPERSEDE GAP); this only re-runs the audit.
pub fn reconvert(gpu_pipeline_dir: &str, source: &str) -> Result<(), String> {
    if gpu_pipeline_dir.is_empty() {
        return Err("pipeline not configured".into());
    }
    // `source` is a bare filename from the manifest — never a path. Reject separators.
    if source.is_empty() || source.contains(['/', '\\', ':']) {
        return Err("invalid source name".into());
    }
    let base = Path::new(gpu_pipeline_dir);
    let src = base.join("drop").join("done").join(source);
    if !src.is_file() {
        return Err(format!("source not in drop/done: {source}"));
    }
    let dest = base.join("drop").join(source);
    if dest.exists() {
        return Err("already queued for re-convert".into());
    }
    fs::copy(&src, &dest).map_err(|e| format!("failed to re-queue: {e}"))?;
    Ok(())
}
