// WHAT THIS FILE DOES: defines the widget's configuration (AppConfig, Portal) and loads it.
// load_or_init() reads %APPDATA%\file-portal\config.toml (path from config_path()), seeds it with
// AppConfig::default() when the file is absent, and returns a parse error naming the file when it
// is malformed. Every optional key is #[serde(default)] so older config files keep parsing; an
// empty path key hides the matching feature in the UI. Callers: app start-up and any command that
// needs hosts, directories or portal categories.
//
// Loads %APPDATA%\file-portal\config.toml, creating it with sane defaults on first run.
// Keeping host/category details here (instead of hardcoded) means the same binary works for
// anyone who clones the repo and points it at their own tailnet host.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

// -- config shapes --

/// One drop target shown in the widget: a category key, its display label and its icon.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Portal {
    /// Category key; also the remote inbox subfolder name.
    pub category: String,
    /// Text shown on the portal tile.
    pub label: String,
    /// Emoji shown on the portal tile.
    pub icon: String,
}

/// The whole config.toml: remote host/user/inbox, optional local paths, reader launchers, portals.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Tailscale MagicDNS name or tailnet IP of the Linux box, e.g. "mybox.tailnet.ts.net".
    pub linux_host: String,
    /// Remote user to SSH in as. Must NOT be root — see docs/06-security-model.md.
    pub remote_user: String,
    /// Remote base directory that inbox/<category> subfolders live under.
    pub remote_inbox_root: String,
    /// Local path of the Obsidian vault's Library git clone (Decision #4). Empty = the
    /// Add-to-Library button is hidden. `serde(default)` keeps pre-W8 config files parsing.
    #[serde(default)]
    pub vault_library_dir: String,

    /// Path to llama-server.exe (lives OUTSIDE the repo — docs/33 §2). Empty = the Assistant
    /// button is hidden; the feature simply does not exist on a machine that has not set it up
    /// (the ThinkPad included). S85, the graduation key.
    #[serde(default)]
    pub llama_server_exe: String,
    /// S18 GPU pipeline root (holds pending\, drop\, anchor\ — see windows-converter/).
    /// Empty = the pre-flight card is hidden; the same per-segment-toggle pattern as above.
    #[serde(default)]
    pub gpu_pipeline_dir: String,
    /// Interpreter + script dir for the Desktop converter (marker-env python; the repo's
    /// windows-converter folder). Both required for the card's route buttons to act.
    #[serde(default)]
    pub gpu_python_exe: String,
    /// The repo's windows-converter folder (holds watch_and_convert.py and room_chat.py).
    #[serde(default)]
    pub gpu_converter_dir: String,
    /// S21 reader launchers (docs/13 "the dock has doors"): exe path or URI per reader;
    /// empty = that icon is hidden. The config file is the allowlist — never page input.
    #[serde(default)]
    pub reader_obsidian: String,
    /// Launcher (exe path or URI) for the ZenNotes reader; empty hides its icon.
    #[serde(default)]
    pub reader_zennotes: String,
    /// The drop targets, in display order.
    pub portals: Vec<Portal>,
}

// -- first-run defaults --

/// First-run defaults: placeholder host/user (CHANGE_ME), empty optional paths, six portals.
impl Default for AppConfig {
    /// Build the default config that gets written to config.toml on first run.
    fn default() -> Self {
        AppConfig {
            linux_host: "CHANGE_ME.tailnet.ts.net".into(),
            remote_user: "CHANGE_ME".into(),
            remote_inbox_root: "~/file-portal/inbox".into(),
            vault_library_dir: String::new(),
            llama_server_exe: String::new(),
            gpu_pipeline_dir: String::new(),
            gpu_python_exe: String::new(),
            gpu_converter_dir: String::new(),
            reader_obsidian: String::new(),
            reader_zennotes: String::new(),
            portals: vec![
                Portal {
                    category: "documents".into(),
                    label: "Documents".into(),
                    icon: "📄".into(),
                },
                Portal {
                    category: "photos".into(),
                    label: "Photos".into(),
                    icon: "🖼".into(),
                },
                Portal {
                    category: "code".into(),
                    label: "Code".into(),
                    icon: "💻".into(),
                },
                Portal {
                    category: "archive".into(),
                    label: "Archive".into(),
                    icon: "📦".into(),
                },
                Portal {
                    category: "convert".into(),
                    label: "To Vault".into(),
                    icon: "🔁".into(),
                },
                Portal {
                    category: "convert-scan".into(),
                    label: "Force OCR → Vault".into(),
                    icon: "🔍".into(),
                },
            ],
        }
    }
}

// -- locating and loading the file --

/// Path of config.toml under the user's config dir (%APPDATA%\file-portal). Panics if the OS
/// config dir cannot be resolved.
fn config_path() -> PathBuf {
    dirs::config_dir()
        .expect("could not resolve %APPDATA%")
        .join("file-portal")
        .join("config.toml")
}

/// Load config.toml. Returns the parsed AppConfig; seeds (and writes) the defaults only when the
/// file is absent; returns an Err string for a parse error or an unreadable file.
pub fn load_or_init() -> Result<AppConfig, String> {
    let path = config_path();

    match fs::read_to_string(&path) {
        Ok(contents) => {
            // A malformed config used to fall back silently to AppConfig::default() — i.e. the
            // CHANGE_ME placeholder host/user — so a typo in the user's own config looked like a
            // working install that mysteriously couldn't reach the box. Surface the parse error
            // instead, naming the file so it can be fixed.
            toml::from_str(&contents)
                .map_err(|e| format!("failed to parse {}: {e}", path.display()))
        }
        // Only a genuinely-absent config triggers first-run seeding; a present-but-unreadable
        // file is an error worth surfacing, not a reason to silently write defaults over it.
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            let defaults = AppConfig::default();
            let parent = path.parent().expect("config path always has a parent");
            fs::create_dir_all(parent)
                .map_err(|e| format!("failed to create {}: {e}", parent.display()))?;
            let serialized = toml::to_string_pretty(&defaults)
                .map_err(|e| format!("failed to serialize default config: {e}"))?;
            fs::write(&path, serialized)
                .map_err(|e| format!("failed to write {}: {e}", path.display()))?;
            Ok(defaults)
        }
        Err(e) => Err(format!("failed to read {}: {e}", path.display())),
    }
}

// -- tests --

#[cfg(test)]
mod tests {
    use super::*;

    /// B25's config half, pinned (S108): `llama_server_exe` is OPTIONAL — a config file
    /// written before S85 (no key) parses, and both the missing-key case and the built-in
    /// default read as "" — which HIDES the assistant (today's behavior; docs/33 §2's
    /// empty-hides-the-feature requirement, checked at chat.rs's entry). A set key
    /// round-trips untouched. The Job-Object half of B25 lives in chat.rs (adoption of the
    /// spawned chat server; its llama-server grandchild inherits job membership because the
    /// job sets no BREAKAWAY_OK) and is held by watcher.rs's supervision tripwire.
    #[test]
    fn llama_server_exe_is_optional_and_empty_hides_the_assistant() {
        let pre_s85 = r#"
            linux_host = "box.tailnet.ts.net"
            remote_user = "user"
            remote_inbox_root = "~/file-portal/inbox"
            portals = []
        "#;
        let cfg: AppConfig = toml::from_str(pre_s85).expect("a pre-S85 config must parse");
        assert_eq!(cfg.llama_server_exe, "");
        assert_eq!(AppConfig::default().llama_server_exe, "");
        let with_key = format!("{pre_s85}llama_server_exe = 'C:/ml/llama/llama-server.exe'");
        let cfg2: AppConfig = toml::from_str(&with_key).expect("a set key must parse");
        assert_eq!(cfg2.llama_server_exe, "C:/ml/llama/llama-server.exe");
    }
}
