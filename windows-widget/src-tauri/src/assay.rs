// S31: the Assay — the Survival Audit's read side (docs/15 §13). Pure projection: Python
// owns the `fidelity` block in each bundle's manifest.json (schema docs/15 §7) and the
// audit-mode.txt lever; this module gathers the newest verdict + its localized evidence
// (degeneration zones, omission runs) + the held queue for the widget's ◎ station and
// evidence card. Read-only, no state. Terracotta is the UI's to spend — this only reports.

use crate::vault::CREATE_NO_WINDOW;
use serde_json::{json, Value};
use std::fs;
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const AUDIT_MODES: [&str; 2] = ["report", "enforce"];

/// Remedy markers live in a dot-prefixed SUBDIRECTORY of drop/ deliberately: the watcher skips
/// non-files, dotfiles, and anything that isn't `.pdf`; `line.rs` counts only `.pdf`; and
/// `room.rs`'s drill tree lists only files. A marker is therefore invisible to every existing
/// scan, and adding it needed no change to the pipeline or to any projection.
const SUPERSEDE_DIR: &str = ".supersede";

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

/// The newest manifest (by mtime) whose `source` is this file, across anchor/pending/held —
/// every conversion leaves its as-converted record in one of those. Best-effort provenance
/// for the remedy marker: read from disk rather than taken from the frontend, so the intent
/// records what the pipeline actually holds. None when the record is gone (the remedy is
/// still authored — the click is the intent; §14.2).
fn newest_manifest_for_source(base: &Path, source: &str) -> Option<Value> {
    let mut newest: Option<(Value, SystemTime)> = None;
    for sub in ["anchor", "pending", "held"] {
        let Ok(entries) = fs::read_dir(base.join(sub)) else {
            continue;
        };
        for entry in entries.flatten() {
            let manifest = entry.path().join("manifest.json");
            let Ok(mtime) = fs::metadata(&manifest).and_then(|m| m.modified()) else {
                continue;
            };
            let parsed: Option<Value> = fs::read_to_string(&manifest)
                .ok()
                .and_then(|t| serde_json::from_str(&t).ok());
            let Some(value) = parsed else { continue };
            if value["source"].as_str() != Some(source) {
                continue;
            }
            let better = match &newest {
                Some((_, t)) => mtime > *t,
                None => true,
            };
            if better {
                newest = Some((value, mtime));
            }
        }
    }
    newest.map(|(v, _)| v)
}

/// Assay remedy (docs/15 §13 + §14.2): re-queue a source for conversion + re-audit by copying
/// it from drop/done/ back into drop/ — the watcher picks it up on its next poll — and author
/// the **supersede intent** that lets the ThinkPad exporter REPLACE the already-vaulted note
/// instead of dedup-skipping the better conversion (THE SUPERSEDE GAP).
///
/// This click is the ONLY thing in the system that authors that intent. A plain re-drop of the
/// same PDF carries no marker, so it still skips — the exporter's create-only contract holds by
/// construction, and supersede stays a named, opt-in exception.
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

    // The marker is written BEFORE the PDF lands. The watcher polls drop/ every 5 s, and a
    // convert that started before the intent existed would ship as an ordinary create and the
    // remedy would be silently lost to dedup. Dependency first, trigger second.
    let prior = newest_manifest_for_source(base, source);
    let marker_dir = base.join("drop").join(SUPERSEDE_DIR);
    fs::create_dir_all(&marker_dir).map_err(|e| format!("failed to stage remedy marker: {e}"))?;
    let marker = marker_dir.join(format!("{source}.json"));
    let body = json!({
        "reason": "audit-remedy",
        "source": source,
        // Provenance only (the exporter logs it); null when no prior record survives.
        "from_verdict": prior.as_ref().map_or(Value::Null, |m| m["fidelity"]["verdict"].clone()),
        // Guard: the converter drops the intent if the file it hashes isn't this one.
        "source_sha256": prior.as_ref().map_or(Value::Null, |m| m["source_sha256"].clone()),
        "requested_at_epoch_s": SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0),
    });
    let encoded =
        serde_json::to_string_pretty(&body).map_err(|e| format!("failed to encode marker: {e}"))?;
    fs::write(&marker, encoded).map_err(|e| format!("failed to write remedy marker: {e}"))?;

    if let Err(e) = fs::copy(&src, &dest) {
        // The trigger never landed — take the intent back down with it, so no marker can
        // outlive the click that authored it.
        let _ = fs::remove_file(&marker);
        return Err(format!("failed to re-queue: {e}"));
    }
    Ok(())
}

/// Human-bless (docs/18 §5.4; Rab signed S56: **"pass, or flag with bless"**): certify that the
/// newest audit of `source` was `flag` WITHOUT degeneration — the figure-heavy ceiling, not
/// disease — and place a sha-bound `bless.json` into the bundle's ThinkPad staging dir over the
/// existing ssh channel. The exporter's amended supersede guard honors it on its next sweep;
/// a degeneration fail can never be blessed from either side (that is Repair Bench territory).
///
/// This click is the ONLY author of bless markers. Eligibility is validated HERE, backend-side,
/// against the event stream — the desktop's own record of the staged bundle's audit (its good
/// manifest lives only in ThinkPad staging, kept there by the guard's earlier refusal, so local
/// manifests may be an older generation; the sha they all share is the source PDF's).
pub fn bless(gpu_pipeline_dir: &str, source: &str) -> Result<String, String> {
    if gpu_pipeline_dir.is_empty() {
        return Err("pipeline not configured".into());
    }
    if source.is_empty() || source.contains(['/', '\\', ':']) {
        return Err("invalid source name".into());
    }
    let base = Path::new(gpu_pipeline_dir);
    let events = fs::read_to_string(base.join("events.jsonl"))
        .map_err(|e| format!("events.jsonl unreadable: {e}"))?;
    let parsed: Vec<Value> = events
        .lines()
        .filter_map(|l| serde_json::from_str(l).ok())
        .collect();
    let scored = parsed
        .iter()
        .rev()
        .find(|ev| {
            ev["stage"] == "audit"
                && ev["event"] == "scored"
                && ev["source"].as_str() == Some(source)
        })
        .ok_or("no audit record for this source")?;
    if scored["verdict"] != "flag" {
        return Err(format!(
            "bless refused: newest audit for {source} ({}) has verdict {} — flag only",
            scored["ts"], scored["verdict"]
        ));
    }
    if scored["degeneration"] == Value::Bool(true) {
        return Err("bless refused: degeneration is disease, not a ceiling (Repair Bench)".into());
    }
    let manifest = newest_manifest_for_source(base, source)
        .ok_or("no local manifest records this source")?;
    let sha = manifest["source_sha256"]
        .as_str()
        .ok_or("manifest lacks source_sha256")?
        .to_string();
    let sha16: String = sha.chars().take(16).collect();
    let bundle = parsed
        .iter()
        .rev()
        .find(|ev| {
            ev["stage"] == "ship"
                && ev["event"] == "shipped"
                && ev["sha"].as_str() == Some(sha16.as_str())
        })
        .and_then(|ev| ev["bundle"].as_str())
        .ok_or("no shipped record — bless targets bundles already held in ThinkPad staging")?
        .to_string();
    let marker = json!({
        "source": source,
        "source_sha256": sha,
        "by": "rab",
        "reason": "human-bless (figure-heavy ceiling, docs/18 §5.4)",
        "ts": SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0),
    });
    let local = base.join(format!(".bless-{sha16}.json"));
    fs::write(
        &local,
        serde_json::to_string_pretty(&marker).map_err(|e| e.to_string())?,
    )
    .map_err(|e| format!("failed to write bless marker: {e}"))?;
    // Modern OpenSSH scp runs in SFTP mode: NO remote shell, so the path after the colon is
    // taken literally — spaces are fine and embedded quotes would become literal filename
    // characters (the S56 first-flight bug). Plain path, no quoting.
    let remote = format!("rab@archlinux:file-portal/library/staging/{bundle}/bless.json");
    // System32 OpenSSH keeps its OWN known_hosts (git ships a separate ssh — the S56
    // realization: the widget's first scp sat forever at an invisible host-key prompt).
    // BatchMode makes prompting impossible, accept-new is trust-on-first-use for the
    // tailnet-internal host, and the timeout makes failures fail fast instead of hanging
    // the invoke.
    let out = Command::new("scp")
        .arg("-o")
        .arg("BatchMode=yes")
        .arg("-o")
        .arg("StrictHostKeyChecking=accept-new")
        .arg("-o")
        .arg("ConnectTimeout=10")
        .arg(local.as_os_str())
        .arg(&remote)
        .creation_flags(CREATE_NO_WINDOW)
        .output();
    let _ = fs::remove_file(&local); // the local copy never outlives the attempt
    match out {
        Ok(o) if o.status.success() => Ok(bundle),
        Ok(o) => Err(format!(
            "scp failed: {}",
            String::from_utf8_lossy(&o.stderr).trim()
        )),
        Err(e) => Err(format!("scp not runnable: {e}")),
    }
}

// The widget crate carried no tests before S44. These cover the one path here that can cause a
// vault note to be REPLACED rather than created, so it earns them: the marker is the entire
// difference between a remedy and an accidental re-drop (docs/15 §14.2).
#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};


    static N: AtomicU32 = AtomicU32::new(0);

    /// A throwaway pipeline root with drop/done/<source> present.
    fn fixture(source: &str) -> PathBuf {
        let unique = format!(
            "fp-assay-{}-{}",
            std::process::id(),
            N.fetch_add(1, Ordering::SeqCst)
        );
        let base = std::env::temp_dir().join(unique);
        let _ = fs::remove_dir_all(&base);
        fs::create_dir_all(base.join("drop").join("done")).unwrap();
        fs::write(base.join("drop").join("done").join(source), b"%PDF-1.7 fake").unwrap();
        base
    }

    fn write_manifest(base: &Path, sub: &str, bundle: &str, manifest: Value) {
        let dir = base.join(sub).join(bundle);
        fs::create_dir_all(&dir).unwrap();
        fs::write(
            dir.join("manifest.json"),
            serde_json::to_string(&manifest).unwrap(),
        )
        .unwrap();
    }

    fn marker_of(base: &Path, source: &str) -> PathBuf {
        base.join("drop").join(SUPERSEDE_DIR).join(format!("{source}.json"))
    }

    #[test]
    fn authors_the_intent_from_the_on_disk_record() {
        let source = "brain-of-the-firm.pdf";
        let base = fixture(source);
        let sha = "7de1c31a".repeat(8); // 64 hex chars
        write_manifest(
            &base,
            "anchor",
            "brain",
            json!({
                "source": source,
                "source_sha256": sha,
                "fidelity": { "verdict": "fail" },
            }),
        );

        reconvert(base.to_str().unwrap(), source).unwrap();

        let marker: Value =
            serde_json::from_str(&fs::read_to_string(marker_of(&base, source)).unwrap()).unwrap();
        assert_eq!(marker["reason"], "audit-remedy");
        assert_eq!(marker["source"], source);
        assert_eq!(marker["from_verdict"], "fail", "provenance read from disk");
        assert_eq!(marker["source_sha256"], sha, "sha guard for the converter");
        assert!(
            base.join("drop").join(source).is_file(),
            "the PDF is queued for the watcher"
        );
        let _ = fs::remove_dir_all(&base);
    }

    #[test]
    fn authors_the_intent_even_with_no_prior_record() {
        // The click IS the intent (§14.2). A missing anchor record only costs provenance.
        let source = "orphaned.pdf";
        let base = fixture(source);

        reconvert(base.to_str().unwrap(), source).unwrap();

        let marker: Value =
            serde_json::from_str(&fs::read_to_string(marker_of(&base, source)).unwrap()).unwrap();
        assert_eq!(marker["reason"], "audit-remedy");
        assert!(marker["from_verdict"].is_null());
        assert!(marker["source_sha256"].is_null(), "no sha to guard against");
        assert!(base.join("drop").join(source).is_file());
        let _ = fs::remove_dir_all(&base);
    }

    #[test]
    fn refusals_leave_neither_intent_nor_trigger() {
        let source = "paper.pdf";
        let base = fixture(source);
        let dir = base.to_str().unwrap();

        assert!(reconvert(dir, "../escape.pdf").is_err(), "path separators");
        assert!(reconvert(dir, "absent.pdf").is_err(), "not in drop/done");
        assert!(reconvert("", source).is_err(), "pipeline not configured");
        assert!(
            !base.join("drop").join(SUPERSEDE_DIR).exists(),
            "a refused remedy must not author intent"
        );

        // Already queued: the first call succeeds, the second must refuse.
        reconvert(dir, source).unwrap();
        assert!(reconvert(dir, source).is_err(), "already queued");
        let _ = fs::remove_dir_all(&base);
    }

    #[test]
    fn refuses_to_queue_when_the_intent_cannot_be_recorded() {
        // If the marker cannot be written, queueing the convert anyway would burn a GPU run
        // that silently does nothing (the exporter would dedup-skip it). Refuse instead.
        let source = "paper.pdf";
        let base = fixture(source);
        fs::write(base.join("drop").join(SUPERSEDE_DIR), b"not a directory").unwrap();

        assert!(reconvert(base.to_str().unwrap(), source).is_err());
        assert!(
            !base.join("drop").join(source).exists(),
            "no trigger without intent"
        );
        let _ = fs::remove_dir_all(&base);
    }

    #[test]
    fn the_marker_is_invisible_to_every_existing_scan() {
        // Mirrors the three skips it relies on: the watcher's (dotfile / non-file / non-pdf),
        // line.rs's count_pdfs (extension), and room.rs's file_nodes (files only).
        let source = "paper.pdf";
        let base = fixture(source);
        reconvert(base.to_str().unwrap(), source).unwrap();

        let holder = base.join("drop").join(SUPERSEDE_DIR);
        assert!(holder.is_dir(), "a directory, so file-only scans skip it");
        assert!(
            holder.file_name().unwrap().to_str().unwrap().starts_with('.'),
            "dot-prefixed, so the watcher's dotfile skip also covers it"
        );
        let stray_pdfs = fs::read_dir(base.join("drop"))
            .unwrap()
            .flatten()
            .filter(|e| e.path().is_file())
            .filter(|e| e.path().extension().is_some_and(|x| x == "pdf"))
            .count();
        assert_eq!(stray_pdfs, 1, "only the re-queued PDF is visible in drop/");
        let _ = fs::remove_dir_all(&base);
    }

    /// Leaves ONE real marker on disk for the cross-language seam check against the
    /// converter's `_take_supersede_marker` — proving both halves agree on the actual bytes,
    /// not on my description of them. Artifact path is printed by `cargo test -- --nocapture`.
    #[test]
    fn seam_proof_artifact_for_the_converter() {
        let source = "seam-proof.pdf";
        let base = std::env::temp_dir().join("fp-s44-seam-proof");
        let _ = fs::remove_dir_all(&base);
        fs::create_dir_all(base.join("drop").join("done")).unwrap();
        fs::write(base.join("drop").join("done").join(source), b"%PDF-1.7 fake").unwrap();
        write_manifest(
            &base,
            "held",
            "seam",
            json!({
                "source": source,
                "source_sha256": "ab".repeat(32),
                "fidelity": { "verdict": "fail" },
            }),
        );
        reconvert(base.to_str().unwrap(), source).unwrap();
        println!("SEAM ARTIFACT: {}", marker_of(&base, source).display());
    }
}
