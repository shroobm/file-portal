// S34 — the Room surface's read side (docs/16). Pure projection, no state: fills the KPI band
// the existing commands don't cover (throughput, median s/page, survival average, vault count,
// recent audits) by reading the same event stream + manifests Python already wrote, plus a
// live GPU probe. Owns nothing, writes nothing, never touches the converter. Terracotta is the
// UI's to spend — this only reports numbers.

use crate::vault::CREATE_NO_WINDOW;
use serde_json::{json, Value};
use std::fs;
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
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

// ---- S36: the drill-down observation system — a station's real on-disk tree ----------------
// Accurate granularity: every node is read fresh from the filesystem the pipeline writes. No
// simulation. `station_tree(seg)` returns { root, children:[node] }, node =
// { id, kind: "dir"|"file"|"note"|"zone", glyph, name, meta?, size?, survival?, verdict?, children? }.

fn simple_hash(s: &str) -> u32 {
    let mut h: u32 = 2166136261;
    for b in s.bytes() {
        h = h.wrapping_mul(16777619) ^ b as u32;
    }
    h
}
fn nid(prefix: &str, name: &str) -> String {
    format!("{prefix}-{:08x}", simple_hash(name))
}
fn size_str(bytes: u64) -> String {
    if bytes >= 1_048_576 {
        format!("{:.1} MB", bytes as f64 / 1_048_576.0)
    } else if bytes >= 1024 {
        format!("{:.0} KB", bytes as f64 / 1024.0)
    } else {
        format!("{bytes} B")
    }
}
fn dir_count(p: &Path) -> u64 {
    fs::read_dir(p).map(|d| d.flatten().count() as u64).unwrap_or(0)
}
fn flen(p: &Path) -> u64 {
    fs::metadata(p).map(|m| m.len()).unwrap_or(0)
}
fn read_manifest(dir: &Path) -> Option<Value> {
    fs::read_to_string(dir.join("manifest.json"))
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
}
fn note_node(id: &str, text: &str) -> Value {
    json!({ "id": id, "kind": "note", "name": text })
}
fn dir_node(id: &str, glyph: &str, name: &str, meta: &str, children: Vec<Value>) -> Value {
    json!({ "id": id, "kind": "dir", "glyph": glyph, "name": name, "meta": meta, "children": children })
}
/// Real files in a directory as file nodes (sorted, true byte sizes).
fn file_nodes(dir: &Path, prefix: &str, glyph: &str) -> Vec<Value> {
    let mut names: Vec<(String, u64)> = match fs::read_dir(dir) {
        Ok(entries) => entries
            .flatten()
            .filter(|e| e.path().is_file())
            .map(|e| (e.file_name().to_string_lossy().to_string(), flen(&e.path())))
            .collect(),
        Err(_) => vec![],
    };
    names.sort();
    if names.is_empty() {
        return vec![note_node(&nid(prefix, "empty"), "— empty —")];
    }
    names
        .into_iter()
        .map(|(name, sz)| json!({ "id": nid(prefix, &name), "kind": "file", "glyph": glyph, "name": name, "size": size_str(sz) }))
        .collect()
}
/// A converted bundle folder (anchor / held / vault Inbox): the .md + assets/ + manifest.json,
/// plus the analyst summary and — when audited — the real degeneration zones. All from disk.
fn bundle_node(dir: &Path, prefix: &str) -> Value {
    let name = dir.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
    let id = nid(prefix, &name);
    let man = read_manifest(dir);
    let mut kids: Vec<Value> = vec![];
    let mut entries: Vec<PathBuf> = match fs::read_dir(dir) {
        Ok(e) => e.flatten().map(|x| x.path()).collect(),
        Err(_) => vec![],
    };
    entries.sort();
    for p in &entries {
        let fname = p.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
        if p.is_dir() && fname == "assets" {
            kids.push(json!({ "id": nid(&id, "assets"), "kind": "dir", "glyph": "\u{1F4C1}", "name": "assets/", "meta": format!("{} files", dir_count(p)) }));
        } else if fname.ends_with(".md") {
            kids.push(json!({ "id": nid(&id, &fname), "kind": "file", "glyph": "\u{1F4C4}", "name": fname, "size": size_str(flen(p)) }));
        } else if fname == "manifest.json" {
            let meta = man
                .as_ref()
                .map(|m| {
                    format!(
                        "lane={} · {}pp · {} · sha {}",
                        m["lane"].as_str().unwrap_or("?"),
                        m["pages"].as_u64().unwrap_or(0),
                        m["engine"].as_str().unwrap_or("?"),
                        m["source_sha256"].as_str().unwrap_or("").chars().take(8).collect::<String>()
                    )
                })
                .unwrap_or_default();
            kids.push(json!({ "id": nid(&id, "manifest"), "kind": "file", "glyph": "\u{2699}", "name": "manifest.json", "size": size_str(flen(p)), "meta": meta }));
        }
    }
    let mut verdict = Value::Null;
    let mut survival = Value::Null;
    if let Some(m) = &man {
        if !m["analyst"].is_null() {
            let a = &m["analyst"];
            kids.push(json!({
                "id": nid(&id, "analyst"), "kind": "file", "glyph": "\u{1F9E0}",
                "name": format!("analyst · {}", a["backend"].as_str().unwrap_or("?")),
                "meta": format!("{}\u{2713} {}\u{1F6E1} {}\u{2717} · {}",
                    a["chunks_passed"].as_u64().unwrap_or(0), a["chunks_rejected"].as_u64().unwrap_or(0),
                    a["chunks_failed"].as_u64().unwrap_or(0), a["program"].as_str().unwrap_or(""))
            }));
        }
        let fid = &m["fidelity"];
        if !fid.is_null() {
            verdict = fid["verdict"].clone();
            survival = fid["convert"]["doc_survival"].clone();
            let degen = &fid["convert"]["tripwires"]["degeneration_detail"];
            if let Some(zs) = degen["worst"].as_array() {
                for (i, z) in zs.iter().enumerate() {
                    kids.push(json!({
                        "id": format!("{}-z{}", id, i), "kind": "zone", "glyph": "\u{2717}",
                        "name": format!("degeneration @ line {}", z["line"].as_u64().unwrap_or(0)),
                        "meta": format!("zlib {:.3} · tri×{} · {} ch · \u{201C}{}\u{2026}\u{201D}",
                            z["zlib"].as_f64().unwrap_or(0.0), z["max_trigram"].as_u64().unwrap_or(0),
                            z["chars"].as_u64().unwrap_or(0),
                            z["excerpt"].as_str().unwrap_or("").chars().take(30).collect::<String>())
                    }));
                }
            }
        }
    }
    json!({ "id": id, "kind": "dir", "glyph": "\u{1F4E6}", "name": name, "survival": survival, "verdict": verdict, "children": kids })
}
/// Bundle folders under a pipeline subdir (anchor / held), sorted.
fn bundles_in(base: &Path, sub: &str, prefix: &str) -> Vec<Value> {
    let mut dirs: Vec<PathBuf> = match fs::read_dir(base.join(sub)) {
        Ok(e) => e.flatten().map(|x| x.path()).filter(|p| p.is_dir()).collect(),
        Err(_) => vec![],
    };
    dirs.sort();
    if dirs.is_empty() {
        return vec![note_node(&nid(prefix, "empty"), "— empty —")];
    }
    dirs.iter().map(|d| bundle_node(d, prefix)).collect()
}

/// The station's real on-disk tree. `seg` ∈ intake/convert/gate/assay/ship/vault.
pub fn station_tree(gpu_pipeline_dir: &str, vault_library_dir: &str, seg: &str) -> Result<Value, String> {
    if gpu_pipeline_dir.is_empty() {
        return Ok(json!({ "root": "pipeline not configured", "children": [] }));
    }
    let base = Path::new(gpu_pipeline_dir);
    let out = match seg {
        "vault" => {
            let inbox = Path::new(vault_library_dir).join("Inbox");
            let mut dirs: Vec<PathBuf> = match fs::read_dir(&inbox) {
                Ok(e) => e.flatten().map(|x| x.path()).filter(|p| p.is_dir()).collect(),
                Err(_) => vec![],
            };
            dirs.sort();
            let children: Vec<Value> = if dirs.is_empty() {
                vec![note_node("v-empty", "— Library empty (or vault clone unreachable) —")]
            } else {
                dirs.iter().map(|d| bundle_node(d, "v")).collect()
            };
            json!({ "root": format!("{} · vault.git clone \u{2192} Library/Inbox/", vault_library_dir), "children": children })
        }
        "assay" => {
            let mode = crate::assay::get_mode(gpu_pipeline_dir);
            let held = bundles_in(base, "held", "h");
            let held_n = fs::read_dir(base.join("held")).map(|d| d.flatten().filter(|e| e.path().is_dir()).count()).unwrap_or(0);
            let mut recent: Vec<(SystemTime, Value)> = vec![];
            for sub in ["anchor", "held", "pending"] {
                if let Ok(entries) = fs::read_dir(base.join(sub)) {
                    for e in entries.flatten() {
                        let manifest = e.path().join("manifest.json");
                        if let (Ok(mt), Some(m)) = (fs::metadata(&manifest).and_then(|x| x.modified()), read_manifest(&e.path())) {
                            if m["fidelity"].is_null() {
                                continue;
                            }
                            let nm = m["source"].as_str().unwrap_or("").to_string();
                            recent.push((mt, json!({ "id": nid("rv", &nm), "kind": "file", "glyph": "\u{25CE}", "name": nm,
                                "survival": m["fidelity"]["convert"]["doc_survival"], "verdict": m["fidelity"]["verdict"] })));
                        }
                    }
                }
            }
            recent.sort_by_key(|a| std::cmp::Reverse(a.0));
            let recent_nodes: Vec<Value> = recent.into_iter().take(8).map(|(_, v)| v).collect();
            json!({ "root": format!("Survival Audit · mode={} · flag: zlib<0.20 OR tri\u{2265}40 (docs/15)", mode), "children": [
                dir_node("as-held", "\u{1F4C1}", "held/", &format!("{} awaiting remedy · enforce parks fails here", held_n), held),
                dir_node("as-recent", "\u{1F4C1}", "recent verdicts", &format!("{} scored", recent_nodes.len()), recent_nodes),
                note_node("as-mode", &format!("audit-mode.txt = {}", mode)),
            ] })
        }
        "convert" => {
            let lock = base.join(".gpu-lock");
            let converting = fs::read_to_string(&lock).ok().map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
            let active = match &converting {
                Some(name) => json!({ "id": "cv-active", "kind": "file", "glyph": "\u{2699}", "name": name, "meta": "converting now · .gpu-lock held" }),
                None => note_node("cv-idle", "\u{2699} converting: idle · no .gpu-lock"),
            };
            json!({ "root": format!("{}  ·  converter (Marker, policy-routed)", gpu_pipeline_dir), "children": [
                dir_node("cv-drop", "\u{1F4C1}", "drop/", "waiting for the engine", file_nodes(&base.join("drop"), "cv-drop", "\u{1F4C4}")),
                active,
                dir_node("cv-done", "\u{1F4C1}", "drop/done/", "converted originals (kept for re-convert)", file_nodes(&base.join("drop").join("done"), "cv-done", "\u{1F4C4}")),
                dir_node("cv-anchor", "\u{1F4C1}", "anchor/", "immutable as-converted snapshots + manifest", bundles_in(base, "anchor", "a")),
            ] })
        }
        "gate" => {
            let mode = crate::line::get_analyst_mode(gpu_pipeline_dir);
            let cards = file_nodes(&base.join("pending"), "gate", "\u{2733}");
            json!({ "root": format!("pending/ · analyst-mode.txt = {} (ask parks routing cards here)", mode), "children": [
                dir_node("gate-pending", "\u{1F4C1}", "pending/", "routing decisions awaiting your hand", cards),
                note_node("gate-mode", &format!("analyst-mode.txt = {} · ask | local | gemini | off", mode)),
            ] })
        }
        "ship" => {
            let text = fs::read_to_string(base.join("events.jsonl")).unwrap_or_default();
            let last = text.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok())
                .rfind(|e| e["stage"] == "ship" && e["event"] == "shipped");
            let last_node = match last {
                Some(e) => json!({ "id": "sh-last", "kind": "file", "glyph": "\u{21C8}", "name": e["bundle"].as_str().unwrap_or("(unknown)").to_string(), "meta": format!("shipped {}", e["ts"].as_str().unwrap_or("")) }),
                None => note_node("sh-none", "— nothing shipped yet —"),
            };
            json!({ "root": "vault-work/ (clone) \u{2192} vault.git (bare) · Tailscale SSH".to_string(), "children": [
                last_node,
                note_node("sh-verify", "staging deleted only after push + cat-file blob verify (L12)"),
                note_node("sh-dedup", "re-ship of a vaulted sha \u{2192} EXPORT-SKIP (cross-machine dedup)"),
            ] })
        }
        _ => {
            let failed = file_nodes(&base.join("drop").join("failed"), "in-failed", "\u{2717}");
            json!({ "root": format!("{}/drop  ·  allocator + watcher (poll 5s)", gpu_pipeline_dir), "children": [
                dir_node("in-belt", "\u{1F4C1}", "drop/", "on the belt \u{2014} watched for new PDFs", file_nodes(&base.join("drop"), "in-belt", "\u{1F4C4}")),
                dir_node("in-quarantine", "\u{1F4C1}", "drop/failed/", "quarantine \u{2014} oversized / unconverted", failed),
            ] })
        }
    };
    Ok(out)
}
