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
    pub portals: Vec<Portal>,
}

impl Default for AppConfig {
    fn default() -> Self {
        AppConfig {
            linux_host: "CHANGE_ME.tailnet.ts.net".into(),
            remote_user: "CHANGE_ME".into(),
            remote_inbox_root: "~/file-portal/inbox".into(),
            portals: vec![
                Portal { category: "documents".into(), label: "Documents".into(), icon: "📄".into() },
                Portal { category: "photos".into(), label: "Photos".into(), icon: "🖼".into() },
                Portal { category: "code".into(), label: "Code".into(), icon: "💻".into() },
                Portal { category: "archive".into(), label: "Archive".into(), icon: "📦".into() },
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

pub fn load_or_init() -> Result<AppConfig, std::io::Error> {
    let path = config_path();

    if let Ok(contents) = fs::read_to_string(&path) {
        let cfg: AppConfig = toml::from_str(&contents)
            .unwrap_or_else(|_| AppConfig::default());
        return Ok(cfg);
    }

    let defaults = AppConfig::default();
    fs::create_dir_all(path.parent().unwrap())?;
    fs::write(&path, toml::to_string_pretty(&defaults).unwrap())?;
    Ok(defaults)
}
