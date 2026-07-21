// S20: the widget owns the conveyor watcher's lifecycle (docs/13) — spawn, supervise,
// stop. Kills the manual console ritual. The child is watch_and_convert.py in the
// marker-env; killing it mid-conversion is safe (the in-flight convert subprocess runs
// to completion and ships; only the *watch loop* dies — restart resumes the queue).

use crate::vault::CREATE_NO_WINDOW;
use serde::Serialize;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

pub struct WatcherState(pub Mutex<Option<Child>>);

#[derive(Serialize)]
pub struct WatcherStatus {
    /// "running" | "stopped" | "unconfigured"
    pub state: String,
    pub pid: Option<u32>,
}

pub fn status(state: &WatcherState, configured: bool) -> WatcherStatus {
    if !configured {
        return WatcherStatus {
            state: "unconfigured".into(),
            pid: None,
        };
    }
    let mut guard = state.0.lock().unwrap();
    if let Some(child) = guard.as_mut() {
        match child.try_wait() {
            Ok(None) => {
                return WatcherStatus {
                    state: "running".into(),
                    pid: Some(child.id()),
                }
            }
            _ => *guard = None, // exited or unknowable — reflect reality
        }
    }
    WatcherStatus {
        state: "stopped".into(),
        pid: None,
    }
}

pub fn start(
    state: &WatcherState,
    gpu_python_exe: &str,
    gpu_converter_dir: &str,
) -> Result<WatcherStatus, String> {
    if gpu_python_exe.is_empty() || gpu_converter_dir.is_empty() {
        return Err("gpu_python_exe / gpu_converter_dir not configured".into());
    }
    let script = Path::new(gpu_converter_dir).join("watch_and_convert.py");
    if !script.is_file() {
        return Err(format!("watcher script not found: {}", script.display()));
    }
    let mut guard = state.0.lock().unwrap();
    if let Some(child) = guard.as_mut() {
        if matches!(child.try_wait(), Ok(None)) {
            return Ok(WatcherStatus {
                state: "running".into(),
                pid: Some(child.id()),
            });
        }
    }
    let child = Command::new(gpu_python_exe)
        .arg(&script)
        .env("PYTHONIOENCODING", "utf-8")
        // A Start-menu (GUI) launch has NO console, so a spawned console child inherits
        // invalid std handles and the Python watcher dies on startup before it can even log
        // ("auto-start runs but nothing converts", S31). Give it explicit null I/O — a
        // background daemon needs no streams; it logs to watcher.log. Only reproduced from a
        // windowless launch; a terminal launch has a console to inherit and masked this.
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW)
        .spawn()
        .map_err(|e| format!("failed to spawn watcher: {e}"))?;
    let pid = child.id();
    *guard = Some(child);
    Ok(WatcherStatus {
        state: "running".into(),
        pid: Some(pid),
    })
}

pub fn stop(state: &WatcherState) -> WatcherStatus {
    let mut guard = state.0.lock().unwrap();
    if let Some(mut child) = guard.take() {
        let _ = child.kill();
        let _ = child.wait();
    }
    WatcherStatus {
        state: "stopped".into(),
        pid: None,
    }
}
