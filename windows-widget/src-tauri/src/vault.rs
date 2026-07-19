// W8: the Add-to-Library button's backend. Checks whether the local Library clone (the
// Obsidian vault's git subfolder, Decision #4) is behind the ThinkPad's bare repo, and pulls
// on demand. All network transport rides the clone's own persisted
// `core.sshCommand = "tailscale ssh"` — this module just runs git; it never talks to the
// remote host directly and never initializes a repo (Decision #4: exactly one side does).

use serde::Serialize;
use std::collections::BTreeSet;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::Command;

/// CREATE_NO_WINDOW: without it, every process a windows-subsystem app spawns opens a
/// console window — the 45s vault poll flashed a black box on the user's screen each cycle.
pub const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Debug, Serialize)]
pub struct VaultStatus {
    /// "disabled" | "up-to-date" | "updates" | "pulled" | "offline" | "error"
    pub state: String,
    /// Commits behind origin/main ("updates") or pulled ("pulled"); 0 otherwise.
    pub behind: u32,
    /// New bundle slugs under Inbox/ (from added manifest.json paths), newest last.
    pub bundles: Vec<String>,
    /// Human-readable detail for the status line (error text, "already up to date", ...).
    pub detail: String,
}

impl VaultStatus {
    fn simple(state: &str, detail: &str) -> Self {
        VaultStatus {
            state: state.into(),
            behind: 0,
            bundles: vec![],
            detail: detail.into(),
        }
    }
}

fn git(dir: &str, args: &[&str]) -> Result<String, String> {
    // core.longpaths: bundle-interior filenames (200-byte clamped stems + asset names) push
    // full vault paths past Windows' 260-char MAX_PATH — without this, checkout fails with
    // "Filename too long" (hit live on the first real book, 2026-07-12). Passed per-call so
    // the widget works against a fresh clone regardless of machine git config.
    let output = Command::new("git")
        .args(["-c", "core.longpaths=true"])
        .arg("-C")
        .arg(dir)
        .args(args)
        // Never let git or the ssh under it sit waiting on an interactive prompt a
        // windowless app can't show — fail fast instead (the S22 "Checking…" hang).
        .env("GIT_TERMINAL_PROMPT", "0")
        .stdin(std::process::Stdio::null())
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .map_err(|e| format!("failed to spawn git: {e}"))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).trim().to_string())
    }
}

/// Distinct `Inbox/<slug>/` bundle slugs among a diff's added manifest.json paths. Filing
/// moves and removals don't count as "new notes" — only a manifest arriving under Inbox/.
fn new_bundle_slugs(dir: &str, range: &str) -> Vec<String> {
    let diff = git(dir, &["diff", "--name-only", "--diff-filter=A", range]).unwrap_or_default();
    let slugs: BTreeSet<String> = diff
        .lines()
        .filter_map(|p| {
            let mut parts = p.split('/');
            match (parts.next(), parts.next(), parts.next(), parts.next()) {
                (Some("Inbox"), Some(slug), Some("manifest.json"), None) => Some(slug.to_string()),
                _ => None,
            }
        })
        .collect();
    slugs.into_iter().collect()
}

pub fn check(vault_library_dir: &str) -> VaultStatus {
    if vault_library_dir.is_empty() {
        return VaultStatus::simple("disabled", "vault_library_dir not configured");
    }
    if !Path::new(vault_library_dir).join(".git").exists() {
        return VaultStatus::simple("error", "vault_library_dir is not a git clone");
    }
    // fetch reaches the ThinkPad over tailscale ssh; treat failure as "offline", not an error
    // state — the box may simply be asleep, and the next poll retries.
    if let Err(e) = git(vault_library_dir, &["fetch", "--quiet", "origin"]) {
        return VaultStatus::simple("offline", &e);
    }
    let behind = git(
        vault_library_dir,
        &["rev-list", "--count", "HEAD..origin/main"],
    )
    .ok()
    .and_then(|s| s.parse::<u32>().ok())
    .unwrap_or(0);
    if behind == 0 {
        return VaultStatus::simple("up-to-date", "");
    }
    VaultStatus {
        state: "updates".into(),
        behind,
        bundles: new_bundle_slugs(vault_library_dir, "HEAD..origin/main"),
        detail: String::new(),
    }
}

pub fn pull(vault_library_dir: &str) -> VaultStatus {
    if vault_library_dir.is_empty() {
        return VaultStatus::simple("disabled", "vault_library_dir not configured");
    }
    let before = match git(vault_library_dir, &["rev-parse", "HEAD"]) {
        Ok(sha) => sha,
        Err(e) => return VaultStatus::simple("error", &e),
    };
    // fetch and merge split on purpose: a fetch failure is the network/host ("offline",
    // retry later), while a merge failure is a real local problem whose git message the
    // user needs to see — the first live click conflated the two and reported a Windows
    // "Filename too long" checkout failure as "vault host unreachable".
    if let Err(e) = git(vault_library_dir, &["fetch", "--quiet", "origin"]) {
        return VaultStatus::simple("offline", &e);
    }
    // --ff-only: the converter only ever appends on top of what this clone pushes/pulls, so a
    // non-fast-forward means something is genuinely wrong — surface it, never auto-merge.
    if let Err(e) = git(
        vault_library_dir,
        &["merge", "--ff-only", "--quiet", "origin/main"],
    ) {
        return VaultStatus::simple("error", &e);
    }
    let after = git(vault_library_dir, &["rev-parse", "HEAD"]).unwrap_or_else(|_| before.clone());
    if before == after {
        return VaultStatus::simple("up-to-date", "already up to date");
    }
    let behind = git(
        vault_library_dir,
        &["rev-list", "--count", &format!("{before}..{after}")],
    )
    .ok()
    .and_then(|s| s.parse::<u32>().ok())
    .unwrap_or(0);
    VaultStatus {
        state: "pulled".into(),
        behind,
        bundles: new_bundle_slugs(vault_library_dir, &format!("{before}..{after}")),
        detail: String::new(),
    }
}
