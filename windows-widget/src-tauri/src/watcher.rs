// S20: the widget owns the conveyor watcher's lifecycle (docs/13) — spawn, supervise,
// stop. Kills the manual console ritual. The child is watch_and_convert.py in the marker-env.
//
// S37 — no orphans, ever. Before, `stop()` only ran on a GRACEFUL shutdown (the ⏻ button or the
// window-Destroyed event). A force-kill (`Stop-Process -Force`) or a crash skipped it, so the
// Python watcher lived on, kept polling drop/, and kept spawning converts — and several such
// orphans racing the same file thrashed the GPU (found by the S36 live PDF test). Fix: the
// watcher (and, by inheritance, its Marker convert subprocesses) is assigned to a Windows Job
// Object with KILL_ON_JOB_CLOSE. The widget holds the only handle to that job for its whole life,
// so when the widget process ends by ANY means — clean close, force-kill, or crash — the OS
// closes the handle and terminates the whole job tree. The ⏻ "pause intake" path is unchanged:
// it kills the watch loop while the widget keeps running, so the job handle stays open and an
// in-flight convert still finishes; only widget EXIT tears everything down.

use crate::vault::CREATE_NO_WINDOW;
use serde::Serialize;
use std::os::windows::io::AsRawHandle;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::{Mutex, OnceLock};
use windows_sys::Win32::Foundation::HANDLE;
use windows_sys::Win32::System::JobObjects::{
    AssignProcessToJobObject, CreateJobObjectW, SetInformationJobObject,
    JobObjectExtendedLimitInformation, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
};

// A single process-wide job, created once and held for the widget's whole life (never closed
// explicitly — it closes when the process exits, which is exactly when we want the kill). Stored
// as isize so the pointer-typed HANDLE can live in a Sync static.
static JOB: OnceLock<isize> = OnceLock::new();

fn kill_on_close_job() -> HANDLE {
    let raw = *JOB.get_or_init(|| unsafe {
        let job = CreateJobObjectW(std::ptr::null(), std::ptr::null());
        if !job.is_null() {
            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const core::ffi::c_void,
                std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );
        }
        job as isize
    });
    raw as HANDLE
}

/// Put the watcher into the kill-on-close job so it (and any convert it spawns) dies with the
/// widget. Best-effort: if the job or assignment fails, the watcher still runs — we just lose the
/// force-kill guarantee for that launch, never correctness.
fn adopt_into_job(child: &Child) {
    let job = kill_on_close_job();
    if !job.is_null() {
        unsafe { AssignProcessToJobObject(job, child.as_raw_handle() as HANDLE) };
    }
}

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
    adopt_into_job(&child); // dies with the widget even on a force-kill / crash (S37)
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
