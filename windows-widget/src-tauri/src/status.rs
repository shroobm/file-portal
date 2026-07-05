//! v2 feedback loop: reads status.json from the Linux host over tailscale ssh.

use serde::{Deserialize, Serialize};
use std::process::Command;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StatusEvent {
    pub ts: String,
    pub action: String,
    pub file: String,
    pub category: String,
    pub dest: Option<String>,
    pub reason: Option<String>,
}

#[derive(Debug, Deserialize)]
struct StatusDoc {
    events: Vec<StatusEvent>,
}

pub fn fetch_events(linux_host: &str, remote_user: &str) -> Result<Vec<StatusEvent>, String> {
    let host_arg = format!("{}@{}", remote_user, linux_host);
    let output = Command::new("tailscale")
        .args(["ssh", &host_arg, "cat ~/file-portal/logs/status.json 2>/dev/null || echo '{}'"])
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
    let doc: StatusDoc = serde_json::from_str(trimmed)
        .map_err(|e| format!("parse error: {}", e))?;
    Ok(doc.events)
}

pub fn find_event(events: &[StatusEvent], filename: &str, category: &str) -> Option<StatusEvent> {
    events.iter().rev().find(|e| e.file == filename && e.category == category).cloned()
}