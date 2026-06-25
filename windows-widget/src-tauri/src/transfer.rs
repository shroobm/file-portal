// Moves files to the Linux box over Tailscale SSH.
//
// Preferred path: `tailscale ssh <user>@<host> -- rsync ...` is not how rsync works over a
// remote shell in practice — rsync needs its own `-e` transport flag, so the real invocation is:
//   rsync -av --progress -e "tailscale ssh" <local files> <user>@<host>:<remote_dir>/
// This lets rsync drive the transfer (resumable, checksummed) while `tailscale ssh` supplies the
// authenticated transport in place of plain `ssh`.
//
// Fallback path (if rsync isn't installed on the remote): plain `scp` through the same transport.

use crate::config::AppConfig;
use serde::Serialize;
use std::process::Command;

#[derive(Debug, Serialize)]
pub struct TransferReport {
    pub sent: Vec<String>,
    pub failed: Vec<FailedTransfer>,
}

#[derive(Debug, Serialize)]
pub struct FailedTransfer {
    pub path: String,
    pub error: String,
}

pub fn send_files(
    cfg: &AppConfig,
    category: &str,
    paths: &[String],
) -> Result<TransferReport, String> {
    if !cfg.portals.iter().any(|p| p.category == category) {
        return Err(format!("unknown portal category: {category}"));
    }

    let remote_dir = format!(
        "{}@{}:{}/{}/",
        cfg.remote_user, cfg.linux_host, cfg.remote_inbox_root, category
    );

    let mut sent = Vec::new();
    let mut failed = Vec::new();

    for path in paths {
        match send_one_file(path, &remote_dir) {
            Ok(()) => sent.push(path.clone()),
            Err(e) => failed.push(FailedTransfer {
                path: path.clone(),
                error: e,
            }),
        }
    }

    Ok(TransferReport { sent, failed })
}

fn send_one_file(local_path: &str, remote_dir: &str) -> Result<(), String> {
    let rsync_result = Command::new("rsync")
        .args(["-av", "--progress", "-e", "tailscale ssh"])
        .arg(local_path)
        .arg(remote_dir)
        .output();

    match rsync_result {
        Ok(output) if output.status.success() => return Ok(()),
        Ok(output) => {
            // rsync ran but failed (e.g. not installed remotely) — fall through to scp.
            let _ = String::from_utf8_lossy(&output.stderr);
        }
        Err(_) => {
            // rsync binary not found locally — fall through to scp.
        }
    }

    let scp_result = Command::new("scp")
        .arg("-o")
        .arg("ProxyCommand=tailscale ssh -W %h:%p")
        .arg(local_path)
        .arg(remote_dir)
        .output()
        .map_err(|e| format!("failed to spawn scp: {e}"))?;

    if scp_result.status.success() {
        Ok(())
    } else {
        Err(String::from_utf8_lossy(&scp_result.stderr).to_string())
    }
}
