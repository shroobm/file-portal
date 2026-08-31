// S21: the line view's state (docs/13 grammar: Drop ▸ Convert ▸ Gate ▸ Ship ▸ Library).
// Pure projection — every field is read fresh from the filesystem the pipeline writes.

use crate::vault::CREATE_NO_WINDOW;
use serde_json::{json, Value};
use std::fs;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::Command;
use windows_sys::Win32::Foundation::{CloseHandle, STILL_ACTIVE};
use windows_sys::Win32::System::Threading::{
    GetExitCodeProcess, OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION,
};

const STATE_FRESH_S: u64 = 300;

fn pid_alive(pid: u32) -> bool {
    if pid == 0 {
        return false;
    }
    unsafe {
        let handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid);
        if handle.is_null() {
            return false;
        }
        let mut code = 0u32;
        let ok = GetExitCodeProcess(handle, &mut code) != 0 && code == STILL_ACTIVE as u32;
        CloseHandle(handle);
        ok
    }
}

fn top_level_pdfs(drop: &Path) -> Vec<(String, u64, Option<u64>)> {
    let mut rows: Vec<_> = fs::read_dir(drop)
        .map(|d| {
            d.flatten()
                .filter_map(|e| {
                    let path = e.path();
                    let meta = e.metadata().ok()?;
                    if !meta.is_file()
                        || !path
                            .extension()
                            .and_then(|x| x.to_str())
                            .is_some_and(|x| x.eq_ignore_ascii_case("pdf"))
                    {
                        return None;
                    }
                    let mtime_ns = meta
                        .modified()
                        .ok()?
                        .duration_since(std::time::UNIX_EPOCH)
                        .ok()
                        .and_then(|d| u64::try_from(d.as_nanos()).ok());
                    Some((
                        e.file_name().to_string_lossy().to_string(),
                        meta.len(),
                        mtime_ns,
                    ))
                })
                .collect()
        })
        .unwrap_or_default();
    rows.sort_by(|a, b| a.0.cmp(&b.0));
    rows
}

/// Accept the watcher receipt only when its schema, writer, age, ordering, count, and ground
/// all agree.  Anything else is explicitly UNREAD; the directory fallback never invents a phase.
fn intake_projection(
    base: &Path,
) -> (String, Option<u64>, Option<String>, u32, Vec<Value>, String) {
    let state_path = base.join(".intake-state.json");
    let age = fs::metadata(&state_path)
        .and_then(|m| m.modified())
        .ok()
        .and_then(|t| t.elapsed().ok())
        .map(|d| d.as_secs());
    let actual = top_level_pdfs(&base.join("drop"));
    let parsed = age
        .filter(|n| *n <= STATE_FRESH_S)
        .and_then(|_| fs::read_to_string(&state_path).ok())
        .and_then(|s| serde_json::from_str::<Value>(&s).ok());
    if let Some(v) = parsed {
        let pid = v["writer_pid"].as_u64().and_then(|n| u32::try_from(n).ok());
        let active = v["active"].as_str().map(str::to_string);
        let card_state = v["card_state"].as_str();
        let items = v["items"].as_array();
        let valid_phase = |s: &str| {
            matches!(
                s,
                "receiving" | "settling" | "ready" | "deferred" | "running"
            )
        };
        if v["v"].as_u64() == Some(1)
            && pid.is_some_and(pid_alive)
            && items.is_some()
            && card_state.is_some_and(|s| matches!(s, "idle" | "busy" | "UNREAD"))
        {
            let Some(items) = items else { unreachable!() };
            let names: Vec<_> = items
                .iter()
                .filter_map(|row| row["name"].as_str().map(str::to_string))
                .collect();
            let actual_names: Vec<_> = actual.iter().map(|(n, _, _)| n.clone()).collect();
            let ground_ok = items
                .iter()
                .zip(actual.iter())
                .all(|(row, (_, bytes, mtime_ns))| {
                    row["bytes"].as_u64() == Some(*bytes) && row["mtime_ns"].as_u64() == *mtime_ns
                });
            let phases_ok = items
                .iter()
                .all(|row| row["phase"].as_str().is_some_and(valid_phase));
            let active_ok = active.as_ref().is_none_or(|name| names.contains(name));
            let waiting = items
                .iter()
                .filter(|row| row["name"].as_str() != active.as_deref())
                .count() as u32;
            if names.len() == items.len()
                && names.windows(2).all(|w| w[0] < w[1])
                && names == actual_names
                && ground_ok
                && phases_ok
                && active_ok
                && v["waiting"].as_u64() == Some(waiting as u64)
            {
                let queue = items
                    .iter()
                    .filter(|row| row["name"].as_str() != active.as_deref())
                    .take(15)
                    .cloned()
                    .collect();
                return (
                    "fresh".into(),
                    age,
                    active,
                    waiting,
                    queue,
                    card_state.unwrap().into(),
                );
            }
        }
    }
    let active = None;
    let waiting = actual.len() as u32;
    let queue: Vec<Value> = actual.iter()
        .take(15)
        .map(|(name, bytes, mtime_ns)| json!({"name": name, "bytes": bytes, "mtime_ns": mtime_ns, "phase": "UNREAD", "wait_s": null}))
        .collect();
    (
        "UNREAD".into(),
        age,
        active,
        waiting,
        queue,
        "UNREAD".into(),
    )
}

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
    let raw_lock = fs::read_to_string(&lock_path)
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty());
    let (intake_state, intake_state_age_s, intake_active, drop_waiting, queue, intake_card_state) =
        intake_projection(base);
    // `.gpu-lock` is a signal, never authority (SYM-032). A positive conversion claim needs
    // the fresh watcher receipt, kernel card ownership, and the same active name to agree.
    let converting = raw_lock.filter(|name| {
        intake_state == "fresh"
            && intake_card_state == "busy"
            && intake_active.as_deref() == Some(name.as_str())
    });
    // Convert start = the lock file's mtime (no timestamp parsing needed).
    let convert_elapsed_s = converting.as_ref().and_then(|_| {
        fs::metadata(&lock_path)
            .and_then(|m| m.modified())
            .ok()
            .and_then(|t| t.elapsed().ok())
            .map(|d| d.as_secs())
    });
    // S42: real convert progress the converter streams from Marker (stage + per-page count).
    // Only read while a convert holds the lock — a stale file from a crash is ignored otherwise.
    let raw_convert_progress = converting.as_ref().and_then(|_| {
        fs::read_to_string(base.join(".convert-progress.json"))
            .ok()
            .and_then(|s| serde_json::from_str::<Value>(&s).ok())
    });
    let progress_schema = raw_convert_progress.as_ref().map(|p| {
        if p["v"].as_u64() == Some(2) {
            let pid = p["writer_pid"].as_u64().and_then(|n| u32::try_from(n).ok());
            let tuple_ok = p["stage"].is_string() && p["n"].is_u64() && p["total"].is_u64();
            if pid.is_some_and(pid_alive) && tuple_ok {
                "v2"
            } else {
                "UNREAD"
            }
        } else {
            "legacy"
        }
    });
    let convert_progress = raw_convert_progress.filter(|_| progress_schema != Some("UNREAD"));
    let cp_field = |k: &str| {
        convert_progress
            .as_ref()
            .and_then(|p| p.get(k).cloned())
            .unwrap_or(Value::Null)
    };
    // Stage B (docs/18 §4B): the progress file's AGE while the lock is held — the exact
    // liveness derivative the Stage A stall detector kills on at 900 s. Projected so a human
    // sees a freeze forming long before the killer acts. None when idle or nothing written.
    let progress_age_s = converting.as_ref().and_then(|_| {
        fs::metadata(base.join(".convert-progress.json"))
            .and_then(|m| m.modified())
            .ok()
            .and_then(|t| t.elapsed().ok())
            .map(|d| d.as_secs())
    });
    // Stage C (docs/18 §4C): analyst per-chunk liveness — analyst.py overwrites this file every
    // chunk; projected only while fresh (<300 s) so a crashed analyst can't leave a stale claim.
    let analyst_progress = fs::metadata(base.join(".analyst-progress.json"))
        .ok()
        .and_then(|m| m.modified().ok())
        .and_then(|t| t.elapsed().ok())
        .map(|d| d.as_secs())
        .filter(|age| *age <= 300)
        .and_then(|age| {
            let v: Value = serde_json::from_str(
                &fs::read_to_string(base.join(".analyst-progress.json")).ok()?,
            )
            .ok()?;
            Some((v, age))
        });
    // Stage E: the conversion's PROMISE — written once by Python at convert start
    // (.convert-estimate.json, estimate_from_ledger's output verbatim). Projected only while
    // the lock names the same source, so a stale promise can never dress a different book.
    let estimate = converting.as_ref().and_then(|name| {
        fs::read_to_string(base.join(".convert-estimate.json"))
            .ok()
            .and_then(|s| serde_json::from_str::<Value>(&s).ok())
            .filter(|e| e["source"].as_str() == Some(name.as_str()))
    });
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
        // NUM-4 / review M4: PREFER the converter's own filed promise — it is scoped to the
        // pages THIS run must convert (resume-aware), while the recompute below promises the
        // full book on a resumed run. The estimate is projected only while the lock names
        // the same source (the staleness guard above), so this cannot dress another book.
        if let Some(eta) = estimate.as_ref().and_then(|e| e["eta_s"].as_i64()) {
            return Some((eta - convert_elapsed_s.unwrap_or(0) as i64).max(0));
        }
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
        // review m3: TRUE median — the middle-index pick returned the LARGER of an even
        // pair, the exact bias census N056 repaired in estimate_from_ledger
        let n = rates.len();
        let median = if n % 2 == 1 {
            rates[n / 2]
        } else {
            (rates[n / 2 - 1] + rates[n / 2]) / 2.0
        };
        let total = (pages as f64 * median) as i64;
        Some((total - convert_elapsed_s.unwrap_or(0) as i64).max(0))
    });
    // S26: the newest event, verbatim — the UI's stage ticker turns it into a sentence.
    let latest = events.last().cloned();
    Ok(json!({
        "available": true,
        "drop_waiting": drop_waiting,
        "intake_state": intake_state,
        "intake_state_age_s": intake_state_age_s,
        "intake_card_state": intake_card_state,
        "intake_active": intake_active,
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
        "convert_progress_schema": progress_schema,
        "convert_slice": cp_field("slice"),
        "convert_slices": cp_field("slices"),
        "convert_attempt": cp_field("attempt"),
        "convert_attempts": cp_field("attempts"),
        "convert_batch": cp_field("batch"),
        "convert_page_range": cp_field("page_range"),
        "convert_split_depth": cp_field("split_depth"),
        "convert_split_side": cp_field("split_side"),
        // Stage B: liveness age of the progress stream (see above).
        "progress_age_s": progress_age_s,
        // Stage C: analyst per-chunk heartbeat (None unless fresh).
        "analyst_n": analyst_progress.as_ref().map_or(Value::Null, |(v, _)| v["n"].clone()),
        "analyst_total": analyst_progress.as_ref().map_or(Value::Null, |(v, _)| v["total"].clone()),
        "analyst_s_per_chunk": analyst_progress.as_ref().map_or(Value::Null, |(v, _)| v["s_per_chunk"].clone()),
        "analyst_age_s": analyst_progress.as_ref().map(|(_, age)| *age),
        "failed_count": count_pdfs(&base.join("drop").join("failed")),
        "last_shipped": last_shipped,
        "latest": latest,
        // Stage D: the slice recognition-batch lever, so the Convert station's policy row can
        // state what a long book will actually do instead of describing the default.
        "chunk_batch": get_chunk_batch(gpu_pipeline_dir),
        // Stage E: the waiting queue in watcher order + the ledger's promise for the piece
        // in the press (docs/19 §5). Both read-only projections.
        "queue": queue,
        "estimate": estimate,
    }))
}

/// Stage E: the chunk-batch lever's WRITE side — same shape as `set_analyst_mode`: the widget
/// writes user intent into the backend's own lever file; Python re-reads it per slice. The
/// whitelist here must stay identical to `chunk_batch()`'s in convert_and_ship.py, or the glass
/// could set a number Marker would silently ignore.
pub fn set_chunk_batch(gpu_pipeline_dir: &str, batch: u32) -> Result<u32, String> {
    if ![8, 16, 32].contains(&batch) {
        return Err(format!("invalid slice batch: {batch} (8 | 16 | 32)"));
    }
    fs::write(
        Path::new(gpu_pipeline_dir).join("chunk-batch.txt"),
        format!("{batch}\n"),
    )
    .map_err(|e| format!("failed to write chunk-batch: {e}"))?;
    Ok(batch)
}

/// Stage D (docs/18 §5.2): the slice recognition batch. Python owns the file and re-reads it per
/// slice; this is the read-only projection of the same value, validated identically so the glass
/// can never advertise a number Marker would not be given.
pub fn get_chunk_batch(gpu_pipeline_dir: &str) -> u32 {
    fs::read_to_string(Path::new(gpu_pipeline_dir).join("chunk-batch.txt"))
        .ok()
        .and_then(|s| s.trim().parse::<u32>().ok())
        .filter(|n| [8, 16, 32].contains(n))
        .unwrap_or(16)
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

/// S66 (Rab: "make it easy for anyone via the widget to access and open important files for
/// engineering purposes"): open a NAMED engineering target — never an arbitrary path; the
/// match below IS the allowlist. Files open in Notepad, folders in Explorer.
pub fn open_engineering(
    gpu_pipeline_dir: &str,
    gpu_converter_dir: &str,
    vault_library_dir: &str,
    target: &str,
) -> Result<String, String> {
    let pipe = Path::new(gpu_pipeline_dir);
    let (path, is_dir): (std::path::PathBuf, bool) = match target {
        "pipeline" => (pipe.to_path_buf(), true),
        "drop" => (pipe.join("drop"), true),
        "held" => (pipe.join("held"), true),
        "pending" => (pipe.join("pending"), true),
        "anchor" => (pipe.join("anchor"), true),
        "events" => (pipe.join("events.jsonl"), false),
        "ledger" => (pipe.join("conversion-ledger.jsonl"), false),
        "watcher-log" => (pipe.join("watcher.log"), false),
        "watcher-stderr" => (pipe.join("watcher-stderr.log"), false),
        // S77 (docs/29 §7.7): built in S76 to cure traceless failure (SYM-024) and then left
        // unreachable — it inherited the disease it was made to cure. Its two sibling logs
        // were both already here.
        "resume-stderr" => (pipe.join("resume-stderr.log"), false),
        "bench-stderr" => (pipe.join("bench-stderr.log"), false),
        "boot-log" => (pipe.join("widget-boot.log"), false),
        "receipts-cache" => (pipe.join(".receipts-cache.jsonl"), false),
        "repo" => (
            Path::new(gpu_converter_dir)
                .parent()
                .ok_or("converter dir has no parent")?
                .to_path_buf(),
            true,
        ),
        "library" => (Path::new(vault_library_dir).to_path_buf(), true),
        _ => return Err(format!("unknown engineering target: {target}")),
    };
    if !path.exists() {
        return Err(format!("not there yet: {}", path.display()));
    }
    let shown = path.display().to_string();
    Command::new(if is_dir {
        "explorer.exe"
    } else {
        "notepad.exe"
    })
    .arg(&path)
    .creation_flags(CREATE_NO_WINDOW)
    .spawn()
    .map_err(|e| format!("failed to open {target}: {e}"))?;
    Ok(shown)
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

#[cfg(test)]
mod conveyor_state_tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn scratch(label: &str) -> std::path::PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root =
            std::env::temp_dir().join(format!("fp-line-{label}-{}-{nonce}", std::process::id()));
        fs::create_dir_all(root.join("drop")).unwrap();
        root
    }

    fn write_intake(root: &Path, active: Option<&str>, card_state: &str, mut items: Value) {
        for row in items.as_array_mut().unwrap() {
            if let Ok(meta) = fs::metadata(root.join("drop").join(row["name"].as_str().unwrap())) {
                row["bytes"] = json!(meta.len());
                row["mtime_ns"] = json!(meta
                    .modified()
                    .unwrap()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos() as u64);
            }
        }
        let waiting = items
            .as_array()
            .unwrap()
            .iter()
            .filter(|row| row["name"].as_str() != active)
            .count();
        fs::write(
            root.join(".intake-state.json"),
            serde_json::to_string(&json!({
                "v": 1,
                "writer_pid": std::process::id(),
                "card_state": card_state,
                "active": active,
                "waiting": waiting,
                "items": items,
            }))
            .unwrap(),
        )
        .unwrap();
    }

    #[test]
    fn active_pdf_is_not_counted_as_waiting() {
        let root = scratch("active-once");
        fs::write(root.join("drop").join("book.pdf"), b"pdf").unwrap();
        write_intake(
            &root,
            Some("book.pdf"),
            "busy",
            json!([
                {"name":"book.pdf", "bytes":3, "phase":"running", "wait_s":4}
            ]),
        );
        let (status, _, active, waiting, queue, _) = intake_projection(&root);
        assert_eq!(status, "fresh");
        assert_eq!(active.as_deref(), Some("book.pdf"));
        assert_eq!(waiting, 0);
        assert!(queue.is_empty());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn malformed_or_ground_mismatched_receipt_is_unread() {
        let root = scratch("unread");
        fs::write(root.join("drop").join("real.pdf"), b"pdf").unwrap();
        write_intake(
            &root,
            None,
            "idle",
            json!([
                {"name":"ghost.pdf", "bytes":3, "phase":"ready", "wait_s":4}
            ]),
        );
        let (status, _, _, waiting, queue, _) = intake_projection(&root);
        assert_eq!(status, "UNREAD");
        assert_eq!(waiting, 1);
        assert_eq!(queue[0]["phase"], "UNREAD");
        fs::write(root.join(".intake-state.json"), b"{torn").unwrap();
        assert_eq!(intake_projection(&root).0, "UNREAD");
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn raw_lock_cannot_override_fresh_idle_receipt() {
        let root = scratch("stale-lock");
        fs::write(root.join("drop").join("book.pdf"), b"pdf").unwrap();
        write_intake(
            &root,
            None,
            "idle",
            json!([{"name":"book.pdf", "bytes":3, "phase":"ready", "wait_s":9}]),
        );
        fs::write(root.join(".gpu-lock"), "book.pdf").unwrap();
        let projected = state(root.to_str().unwrap()).unwrap();
        assert!(projected["intake_active"].is_null());
        assert!(projected["converting"].is_null());
        assert_eq!(projected["drop_waiting"], 1);
        fs::write(root.join(".gpu-lock"), "ghost.pdf").unwrap();
        let ghost = state(root.to_str().unwrap()).unwrap();
        assert!(ghost["converting"].is_null());
        assert_eq!(ghost["drop_waiting"], 1);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn progress_v2_requires_live_writer_and_legacy_keeps_mtime_fallback() {
        let root = scratch("progress");
        fs::write(root.join("drop").join("book.pdf"), b"pdf").unwrap();
        write_intake(
            &root,
            Some("book.pdf"),
            "busy",
            json!([{"name":"book.pdf", "bytes":3, "phase":"running", "wait_s":1}]),
        );
        fs::write(root.join(".gpu-lock"), "book.pdf").unwrap();
        fs::write(
            root.join(".convert-progress.json"),
            r#"{"stage":"legacy","n":1,"total":2,"frac":0.5}"#,
        )
        .unwrap();
        let legacy = state(root.to_str().unwrap()).unwrap();
        assert_eq!(legacy["convert_progress_schema"], "legacy");
        assert!(legacy["progress_age_s"].is_number());
        fs::write(
            root.join(".convert-progress.json"),
            serde_json::to_string(&json!({
                "v":2, "writer_pid":std::process::id(), "stage":"layout", "n":2, "total":3,
                "frac":0.66, "slice":1, "slices":2, "attempt":1, "attempts":3, "batch":8
            }))
            .unwrap(),
        )
        .unwrap();
        let v2 = state(root.to_str().unwrap()).unwrap();
        assert_eq!(v2["convert_progress_schema"], "v2");
        assert_eq!(v2["convert_slice"], 1);
        fs::write(
            root.join(".convert-progress.json"),
            r#"{"v":2,"writer_pid":0,"stage":"x","n":1,"total":2}"#,
        )
        .unwrap();
        assert_eq!(
            state(root.to_str().unwrap()).unwrap()["convert_progress_schema"],
            "UNREAD"
        );
        fs::remove_dir_all(root).unwrap();
    }
}
