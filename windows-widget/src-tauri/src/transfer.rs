// Moves files to the Linux box over Tailscale SSH.
//
// Earlier version tried to drive `rsync`/`scp` through `tailscale ssh` as a transport. That
// doesn't hold up in practice: `rsync` isn't installed on Windows by default, and `scp`/plain
// `ssh` fail host-key verification against Tailscale SSH's managed host keys (only the
// `tailscale ssh` wrapper itself knows how to verify those against the coordination server).
//
// So instead: shell out to the one command that's already proven to work end to end
// (`tailscale ssh user@host -- ...`) and stream the file's bytes directly into a remote
// `cat > destination`, piped through this process's stdin. No rsync/scp dependency, no extra
// host-key handling. Tradeoff: no resumable/checksummed transfer for very large files — see
// docs/01-architecture.md for the rationale and docs/08-roadmap.md for revisiting this later.

use crate::config::AppConfig;
use serde::Serialize;
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;
use std::process::{Command, Stdio};

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

    let mut sent = Vec::new();
    let mut failed = Vec::new();

    for path in paths {
        match send_one_file(cfg, category, path) {
            Ok(()) => sent.push(path.clone()),
            Err(e) => failed.push(FailedTransfer {
                path: path.clone(),
                error: e,
            }),
        }
    }

    Ok(TransferReport { sent, failed })
}

/// Wraps a string in single quotes for safe interpolation into a remote POSIX shell command,
/// escaping any embedded single quotes. Needed because filenames can contain spaces, quotes, etc.
fn shell_quote(s: &str) -> String {
    format!("'{}'", s.replace('\'', "'\\''"))
}

/// Builds a shell-safe expression for a path that may start with `~/`. Tilde expansion only
/// happens for an *unquoted* leading `~`, so a path like `~/file-portal/inbox` can't just be
/// wrapped in `shell_quote` wholesale -- that would search for a literal directory named `~`.
/// Instead the leading `~/` is left bare (still trusted, app-controlled) and only the remainder
/// (which may include the untrusted filename) is quoted; adjacent quoted/unquoted shell words
/// concatenate into one path.
fn remote_path_expr(path: &str) -> String {
    match path.strip_prefix("~/") {
        Some(rest) => format!("~/{}", shell_quote(rest)),
        None => shell_quote(path),
    }
}

fn send_one_file(cfg: &AppConfig, category: &str, local_path: &str) -> Result<(), String> {
    let filename = Path::new(local_path)
        .file_name()
        .ok_or_else(|| format!("could not determine filename for {local_path}"))?
        .to_string_lossy()
        .into_owned();

    let remote_dir = format!("{}/{}", cfg.remote_inbox_root, category);
    let remote_path = format!("{remote_dir}/{filename}");
    let remote_cmd = format!(
        "mkdir -p {} && cat > {}",
        remote_path_expr(&remote_dir),
        remote_path_expr(&remote_path)
    );

    let mut local_file =
        File::open(local_path).map_err(|e| format!("failed to open {local_path}: {e}"))?;

    // No "--" and no separate "sh"/"-c" arguments: `tailscale ssh` (like plain `ssh`) joins all
    // trailing arguments with spaces and hands the result to the remote login shell itself, so
    // passing our own "sh -c <cmd>" as extra argv entries double-wraps it and breaks parsing.
    // Confirmed by testing directly against a live host before wiring this up.
    let mut child = Command::new("tailscale")
        .args([
            "ssh",
            &format!("{}@{}", cfg.remote_user, cfg.linux_host),
            &remote_cmd,
        ])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("failed to spawn tailscale ssh: {e}"))?;

    {
        let mut stdin = child.stdin.take().expect("stdin was piped");
        let mut buf = Vec::new();
        local_file
            .read_to_end(&mut buf)
            .map_err(|e| format!("failed to read {local_path}: {e}"))?;
        stdin
            .write_all(&buf)
            .map_err(|e| format!("failed to stream file to remote: {e}"))?;
        // `stdin` drops here, closing the pipe so the remote `cat` sees EOF.
    }

    let output = child
        .wait_with_output()
        .map_err(|e| format!("failed to wait on tailscale ssh: {e}"))?;

    if output.status.success() {
        Ok(())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}
