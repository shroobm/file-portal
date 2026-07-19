// Loads %APPDATA%\file-portal\config.toml, creating it with sane defaults on first run.
// Keeping host/category details here (instead of hardcoded) means the same binary works for
// anyone who clones the repo and points it at their own tailnet host.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Portal {
    pub category: String,
    pub label: String,
    pub icon: String,
}

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
    /// S18 GPU pipeline root (holds pending\, drop\, anchor\ — see windows-converter/).
    /// Empty = the pre-flight card is hidden; the same per-segment-toggle pattern as above.
    #[serde(default)]
    pub gpu_pipeline_dir: String,
    /// Interpreter + script dir for the Desktop converter (marker-env python; the repo's
    /// windows-converter folder). Both required for the card's route buttons to act.
    #[serde(default)]
    pub gpu_python_exe: String,
    #[serde(default)]
    pub gpu_converter_dir: String,
    /// S21 reader launchers (docs/13 "the dock has doors"): exe path or URI per reader;
    /// empty = that icon is hidden. The config file is the allowlist — never page input.
    #[serde(default)]
    pub reader_obsidian: String,
    #[serde(default)]
    pub reader_zennotes: String,
    pub portals: Vec<Portal>,
}

impl Default for AppConfig {
    fn default() -> Self {
        AppConfig {
            linux_host: "CHANGE_ME.tailnet.ts.net".into(),
            remote_user: "CHANGE_ME".into(),
            remote_inbox_root: "~/file-portal/inbox".into(),
            vault_library_dir: String::new(),
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

fn config_path() -> PathBuf {
    dirs::config_dir()
        .expect("could not resolve %APPDATA%")
        .join("file-portal")
        .join("config.toml")
}

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
