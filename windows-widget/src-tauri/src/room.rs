// S34 — the Room surface's read side (docs/16). Pure projection, no state: fills the KPI band
// the existing commands don't cover (throughput, median s/page, survival average, vault count,
// recent audits) by reading the same event stream + manifests Python already wrote, plus a
// live GPU probe. Owns nothing, writes nothing, never touches the converter. Terracotta is the
// UI's to spend — this only reports numbers.

use crate::vault::CREATE_NO_WINDOW;
use serde_json::{json, Value};
use std::fs;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::Command;
use std::time::SystemTime;

/// The KPI band, derived from events.jsonl + the anchor/pending/held manifests + the vault
/// Library clone. Everything here already exists on disk; the widget invents nothing.
pub fn metrics(gpu_pipeline_dir: &str, vault_library_dir: &str) -> Result<Value, String> {
    if gpu_pipeline_dir.is_empty() {
        return Ok(json!({ "available": false }));
    }
    let base = Path::new(gpu_pipeline_dir);

    // --- from the event stream: throughput + median s/page + the sparkline series ---
    let events_text = fs::read_to_string(base.join("events.jsonl")).unwrap_or_default();
    let mut spp: Vec<f64> = Vec::new();
    let (mut total_pages, mut total_wall) = (0f64, 0f64);
    for line in events_text.lines() {
        let Ok(ev) = serde_json::from_str::<Value>(line) else { continue };
        if ev["stage"] == "convert" && ev["event"] == "converted" {
            if let Some(s) = ev["s_per_page"].as_f64() {
                spp.push(s);
            }
            if let (Some(p), Some(w)) = (ev["pages"].as_f64(), ev["wall_s"].as_f64()) {
                total_pages += p;
                total_wall += w;
            }
        }
    }
    let median_spp = if spp.is_empty() {
        Value::Null
    } else {
        let mut s = spp.clone();
        s.sort_by(|a, b| a.partial_cmp(b).unwrap());
        json!(s[s.len() / 2])
    };
    let throughput = if total_wall > 0.0 {
        json!(total_pages / total_wall)
    } else {
        Value::Null
    };
    // the last dozen s/page, oldest→newest, for the sparkline
    let series: Vec<f64> = spp.iter().rev().take(12).rev().copied().collect();

    // --- from every manifest: survival average + the recent verdicts list ---
    let mut audits: Vec<(SystemTime, Value)> = Vec::new();
    let mut surv_sum = 0f64;
    let mut surv_n = 0u32;
    for sub in ["anchor", "pending", "held"] {
        let Ok(entries) = fs::read_dir(base.join(sub)) else { continue };
        for entry in entries.flatten() {
            let manifest = entry.path().join("manifest.json");
            let Ok(mtime) = fs::metadata(&manifest).and_then(|m| m.modified()) else { continue };
            let Ok(text) = fs::read_to_string(&manifest) else { continue };
            let Ok(m) = serde_json::from_str::<Value>(&text) else { continue };
            let fid = &m["fidelity"];
            if fid.is_null() {
                continue; // pre-audit anchor (converted before S28) — skip, don't count
            }
            let verdict = fid["verdict"].clone();
            let survival = fid["convert"]["doc_survival"].clone();
            if let Some(v) = survival.as_f64() {
                surv_sum += v;
                surv_n += 1;
            }
            let name = m["source"].as_str().unwrap_or("").to_string();
            audits.push((mtime, json!({ "name": name, "survival": survival, "verdict": verdict })));
        }
    }
    audits.sort_by_key(|a| std::cmp::Reverse(a.0));
    let recent_audits: Vec<Value> = audits.iter().take(6).map(|(_, v)| v.clone()).collect();
    let survival_avg = if surv_n > 0 { json!(surv_sum / surv_n as f64) } else { Value::Null };

    // --- vault count: notes in the Library clone (Library/Inbox/<slug>--<sha8>/) ---
    // Falls back to the anchor snapshot count if the vault clone isn't reachable/configured.
    let vault_count = count_library(vault_library_dir)
        .or_else(|| dir_child_count(&base.join("anchor")))
        .unwrap_or(0);

    Ok(json!({
        "available": true,
        "median_spp": median_spp,
        "throughput_pp_s": throughput,
        "spp_series": series,
        "survival_avg": survival_avg,
        "recent_audits": recent_audits,
        "vault_count": vault_count,
    }))
}

/// Count bundle folders under the vault Library. The exporter lays notes down as
/// Library/Inbox/<slug>--<sha8>/; count those, else count top-level Library entries.
fn count_library(vault_library_dir: &str) -> Option<u64> {
    if vault_library_dir.is_empty() {
        return None;
    }
    let lib = Path::new(vault_library_dir);
    let inbox = lib.join("Inbox");
    dir_child_count(&inbox).or_else(|| dir_child_count(lib))
}

fn dir_child_count(p: &Path) -> Option<u64> {
    fs::read_dir(p)
        .ok()
        .map(|d| d.flatten().filter(|e| e.path().is_dir()).count() as u64)
}

/// Live GPU memory via nvidia-smi. Returns { used, total } in GB, or null when there is no
/// probe (no NVIDIA GPU / driver) so the UI shows "—" rather than a fake gauge.
pub fn gpu_vram() -> Value {
    let out = Command::new("nvidia-smi")
        .args([
            "--query-gpu=memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ])
        .creation_flags(CREATE_NO_WINDOW)
        .output();
    let Ok(out) = out else { return Value::Null };
    if !out.status.success() {
        return Value::Null;
    }
    let text = String::from_utf8_lossy(&out.stdout);
    let first = text.lines().next().unwrap_or("");
    let parts: Vec<&str> = first.split(',').map(|s| s.trim()).collect();
    if parts.len() < 2 {
        return Value::Null;
    }
    let (Ok(used_mib), Ok(total_mib)) = (parts[0].parse::<f64>(), parts[1].parse::<f64>()) else {
        return Value::Null;
    };
    // round to 1 decimal GB
    let gb = |mib: f64| (mib / 1024.0 * 10.0).round() / 10.0;
    json!({ "used": gb(used_mib), "total": gb(total_mib) })
}
