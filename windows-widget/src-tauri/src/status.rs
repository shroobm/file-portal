//! v2 feedback loop: reads status.json from the Linux host over tailscale ssh.

use serde::{Deserialize, Serialize};
use std::os::windows::process::CommandExt;
use std::process::Command;

use crate::vault::CREATE_NO_WINDOW;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StatusEvent {
    pub ts: String,
    pub action: String,
    pub file: String,
    pub category: String,
    pub dest: Option<String>,
    pub reason: Option<String>,
    /// Writer identity, stamped by the allocator since S108 (`"allocator"` - see
    /// linux-receiver/allocator/status.py, SOURCE_COMPONENT). Tolerant read: every
    /// pre-S108 status.json row lacks the key and parses as "unknown" - old files are
    /// never rewritten to claim an identity, and whatever this struct feeds (the
    /// fetch_file_status projection) always sees a concrete value, never a null.
    #[serde(default = "unknown_component")]
    pub source_component: String,
}

fn unknown_component() -> String {
    "unknown".into()
}

#[derive(Debug, Deserialize)]
struct StatusDoc {
    events: Vec<StatusEvent>,
}

pub fn fetch_events(linux_host: &str, remote_user: &str) -> Result<Vec<StatusEvent>, String> {
    let host_arg = format!("{}@{}", remote_user, linux_host);
    let output = Command::new("tailscale")
        .args([
            "ssh",
            &host_arg,
            "cat ~/file-portal/logs/status.json 2>/dev/null || echo '{}'",
        ])
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .map_err(|e| format!("tailscale ssh failed: {}", e))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("ssh non-zero: {}", stderr.trim()));
    }
    let raw = String::from_utf8_lossy(&output.stdout);
    let trimmed = raw.trim();
    if trimmed.is_empty() || trimmed == "{}" {
        return Ok(vec![]);
    }
    let doc: StatusDoc =
        serde_json::from_str(trimmed).map_err(|e| format!("parse error: {}", e))?;
    Ok(doc.events)
}

pub fn find_event(events: &[StatusEvent], filename: &str, category: &str) -> Option<StatusEvent> {
    events
        .iter()
        .rev()
        .find(|e| e.file == filename && e.category == category)
        .cloned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_pre_s108_row_without_the_key_reads_unknown() {
        let doc: StatusDoc = serde_json::from_str(
            r#"{"events":[{"ts":"2026-08-01T00:00:00+00:00","action":"allocated",
                "file":"a.pdf","category":"documents","dest":"inbox/documents",
                "reason":null}]}"#,
        )
        .expect("pre-S108 rows must keep parsing");
        assert_eq!(doc.events[0].source_component, "unknown");
    }

    #[test]
    fn the_allocators_stamp_survives_the_round_trip() {
        let doc: StatusDoc = serde_json::from_str(
            r#"{"events":[{"ts":"2026-08-23T00:00:00+00:00","action":"skipped",
                "file":"b.pdf","category":"documents","dest":null,"reason":"dup",
                "source_component":"allocator"}]}"#,
        )
        .expect("stamped rows must parse");
        assert_eq!(doc.events[0].source_component, "allocator");
        // And the projection this struct feeds carries the field outward, concretely.
        let out = serde_json::to_value(&doc.events[0]).unwrap();
        assert_eq!(out["source_component"], "allocator");
    }
}
