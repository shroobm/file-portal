// Stage C2 (docs/19 §3.3, Rab signed S58): the SEAM RECEIPTS — the vault's answers, brought
// home. The ThinkPad exporter is the last station and the only one whose outcomes the desktop
// could never see: `EXPORT-BLESSED`, `-SKIP`, `-SUPERSEDE-HELD` and friends existed solely in a
// systemd journal on another machine, so the widget's story of a book ended at "shipped" and
// the ending had to be fetched by a human. The exporter now appends one JSON line per outcome
// to ~/file-portal/receipts.jsonl (a plain file — the vault holds notes, not machine records)
// and this module brings the tail across.
//
// Two calls on purpose, because they cost wildly different things:
//   * `fetch` reaches over the network. The vault bar's 45 s poll drives it — the same cadence,
//     the same "is the ThinkPad awake" question, no new timer.
//   * `read_cached` is a local file read, so the Room (which re-renders every 4-9 s) can show
//     receipts without ever touching the network.
// The cache is the widget's OWN file, dot-prefixed and separate from the Python-owned
// events.jsonl: two writers would break the single-writer law, so the two streams stay two
// files and are merged only at render time.

use crate::vault::CREATE_NO_WINDOW;
use serde_json::{json, Value};
use std::fs;
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::Command;

/// Widget-owned cache of the remote tail. Dot-prefixed so every existing scan skips it (the
/// same trick `.supersede/` uses) and so nobody mistakes it for a pipeline-authored file.
const CACHE_NAME: &str = ".receipts-cache.jsonl";
const REMOTE_PATH: &str = "~/file-portal/receipts.jsonl";
/// Enough to cover any plausible session's exports; the file itself is never truncated here
/// (rotation is Stage F's job, and one line per vaulted book grows very slowly).
const TAIL_LINES: usize = 60;

fn cache_path(gpu_pipeline_dir: &str) -> PathBuf {
    Path::new(gpu_pipeline_dir).join(CACHE_NAME)
}

fn parse_rows(text: &str) -> Vec<Value> {
    text.lines()
        .filter_map(|l| serde_json::from_str::<Value>(l).ok())
        .collect()
}

/// Pull the tail over the tailnet and refresh the cache. Uses `tailscale ssh` — the same
/// transport `status::fetch_events` and the converter's `ship` already use — deliberately NOT
/// the plain `ssh` the bless marker rides: plain OpenSSH on this box keeps its own known_hosts
/// and can sit forever at an invisible host-key prompt (S56's nine zombies), a failure mode
/// tailscale ssh does not have.
///
/// Empty output NEVER overwrites the cache: a missing remote file (nothing exported since the
/// deploy) and an unreachable host both read as empty, and neither is a reason to forget
/// receipts already in hand.
pub fn fetch(gpu_pipeline_dir: &str, linux_host: &str, remote_user: &str) -> Result<Value, String> {
    if gpu_pipeline_dir.is_empty() {
        return Ok(json!({ "available": false }));
    }
    if linux_host.is_empty() || remote_user.is_empty() {
        return Ok(json!({ "available": false }));
    }
    let host_arg = format!("{remote_user}@{linux_host}");
    // `|| true` so "no receipts file yet" is a normal empty answer rather than a red error on
    // every poll between the deploy and the first export.
    let remote_cmd = format!("tail -n {TAIL_LINES} {REMOTE_PATH} 2>/dev/null || true");
    let output = Command::new("tailscale")
        .args(["ssh", &host_arg, &remote_cmd])
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .map_err(|e| format!("tailscale ssh failed: {e}"))?;
    if !output.status.success() {
        return Err(format!(
            "receipts fetch failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    let text = String::from_utf8_lossy(&output.stdout).to_string();
    if !text.trim().is_empty() {
        let _ = fs::write(cache_path(gpu_pipeline_dir), &text);
    }
    let rows = parse_rows(&text);
    Ok(json!({ "available": true, "source": "remote", "rows": rows }))
}

/// The cached tail, read locally. Never fails: no cache yet simply means no receipts yet.
pub fn read_cached(gpu_pipeline_dir: &str) -> Value {
    if gpu_pipeline_dir.is_empty() {
        return json!({ "available": false });
    }
    match fs::read_to_string(cache_path(gpu_pipeline_dir)) {
        Ok(text) => json!({ "available": true, "source": "cache", "rows": parse_rows(&text) }),
        Err(_) => json!({ "available": true, "source": "cache", "rows": [] }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The cross-language seam, proved on REAL BYTES: this line was produced by running the
    /// actual `Exporter._receipt` (S58 seam harness, case 1) and pasted here verbatim. Both
    /// halves therefore agree on the bytes rather than on my description of them — the same
    /// discipline as assay.rs's marker seam proof.
    #[test]
    fn reads_the_exporters_own_output() {
        let real = "{\"ts\": \"2026-07-31T18:55:09+00:00\", \"outcome\": \"exported\", \
                    \"bundle\": \"Book One\", \"note\": \"Inbox/book-one--aa11aa11\", \
                    \"commit\": \"96fbd7a6\", \"sha\": \"aa11aa11aa11aa11\"}\n";
        let rows = parse_rows(real);
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0]["outcome"], "exported");
        assert_eq!(rows[0]["bundle"], "Book One");
        assert_eq!(rows[0]["note"], "Inbox/book-one--aa11aa11");
        assert_eq!(rows[0]["commit"], "96fbd7a6");
        // The field the Room sorts the merged stream by must be present and comparable to the
        // desktop events' own `ts` (both are UTC ISO-8601 to the second).
        assert_eq!(rows[0]["ts"], "2026-07-31T18:55:09+00:00");
    }

    #[test]
    fn parses_whole_lines_and_survives_a_torn_one() {
        // A tail can start mid-line (the remote file is appended to while we read it). A
        // fragment must be dropped, never guessed at, and must not cost the good lines.
        let text = concat!(
            "ts\": \"2026-07-31T18:00:00+00:00\", \"outcome\": \"skip\"}\n",
            "{\"ts\":\"2026-07-31T18:01:00+00:00\",\"outcome\":\"exported\",\"bundle\":\"a\"}\n",
            "{\"ts\":\"2026-07-31T18:02:00+00:00\",\"outcome\":\"blessed\",\"bundle\":\"b\"}\n",
        );
        let rows = parse_rows(text);
        assert_eq!(rows.len(), 2, "the torn first line is dropped");
        assert_eq!(rows[0]["outcome"], "exported");
        assert_eq!(rows[1]["bundle"], "b");
    }

    #[test]
    fn unconfigured_and_cacheless_states_are_calm() {
        assert_eq!(read_cached("")["available"], false);
        let empty = std::env::temp_dir().join("fp-receipts-absent");
        let _ = fs::create_dir_all(&empty);
        let v = read_cached(empty.to_str().unwrap());
        assert_eq!(v["available"], true);
        assert_eq!(v["rows"].as_array().unwrap().len(), 0);
        let _ = fs::remove_dir_all(&empty);
    }

    #[test]
    fn a_cached_tail_reads_back_newest_last() {
        let dir = std::env::temp_dir().join("fp-receipts-cache");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        fs::write(
            dir.join(CACHE_NAME),
            "{\"ts\":\"2026-07-31T18:00:00+00:00\",\"outcome\":\"exported\",\"bundle\":\"one\"}\n\
             {\"ts\":\"2026-07-31T18:05:00+00:00\",\"outcome\":\"supersede-held\",\"bundle\":\"two\"}\n",
        )
        .unwrap();
        let v = read_cached(dir.to_str().unwrap());
        let rows = v["rows"].as_array().unwrap();
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[1]["outcome"], "supersede-held", "file order is preserved");
        let _ = fs::remove_dir_all(&dir);
    }
}
