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
use std::fs::File;
use std::os::windows::io::AsRawHandle;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::{Mutex, OnceLock};
use windows_sys::Win32::Foundation::HANDLE;
use windows_sys::Win32::System::JobObjects::{
    AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
    SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
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

/// Put a spawned child into the kill-on-close job so it dies with the widget. Best-effort: if
/// the job or assignment fails, the child still runs — we just lose the force-kill guarantee
/// for that launch, never correctness. `pub(crate)` since S63: the Bench surface's spawned
/// server gets the same no-orphans guarantee the watcher earned at S37.
pub(crate) fn adopt_into_job(child: &Child) {
    let job = kill_on_close_job();
    if !job.is_null() {
        unsafe { AssignProcessToJobObject(job, child.as_raw_handle() as HANDLE) };
    }
}

// Stage A (docs/18 §4A): the second mutex REMEMBERS the last death's exit code after the
// child is reaped — a status flag alone is a claim; the certificate is the evidence. Cleared
// on a fresh start and on a deliberate stop (a stop is not a death).
pub struct WatcherState(pub Mutex<Option<Child>>, pub Mutex<Option<i32>>);

#[derive(Serialize)]
pub struct WatcherStatus {
    /// "running" | "stopped" | "unconfigured"
    pub state: String,
    pub pid: Option<u32>,
    /// Stage A death certificate: Some(code) iff the last run DIED (vs was stopped/never ran).
    pub exit_code: Option<i32>,
}

pub fn status(state: &WatcherState, configured: bool) -> WatcherStatus {
    if !configured {
        return WatcherStatus {
            state: "unconfigured".into(),
            pid: None,
            exit_code: None,
        };
    }
    let mut guard = state.0.lock().unwrap();
    if let Some(child) = guard.as_mut() {
        match child.try_wait() {
            Ok(None) => {
                return WatcherStatus {
                    state: "running".into(),
                    pid: Some(child.id()),
                    exit_code: None,
                }
            }
            Ok(Some(st)) => {
                // Died: file the certificate BEFORE reaping (blind spot #2 — never discard
                // an exit code again; 0x67 had to be recovered via a Security-log audit).
                *state.1.lock().unwrap() = st.code();
                *guard = None;
            }
            Err(_) => *guard = None, // unknowable — reflect reality, no certificate to file
        }
    }
    WatcherStatus {
        state: "stopped".into(),
        pid: None,
        exit_code: *state.1.lock().unwrap(),
    }
}

pub fn start(
    state: &WatcherState,
    gpu_python_exe: &str,
    gpu_converter_dir: &str,
    gpu_pipeline_dir: &str,
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
                exit_code: None,
            });
        }
    }
    // A Start-menu (GUI) launch has NO console, so a spawned console child inherits
    // invalid std handles and the Python watcher dies on startup before it can even log
    // ("auto-start runs but nothing converts", S31). stdin/stdout stay explicitly null —
    // but stderr now goes to a LAST-WORDS FILE (Stage A, blind spot #3): a file handle is
    // just as valid as the null device, and the 0x67 launcher error ("No Python at …")
    // died unheard into NUL for five days. Truncated per spawn: the file is always the
    // most recent run's stderr. Falls back to null if the pipeline dir is unset.
    let stderr: Stdio = if gpu_pipeline_dir.is_empty() {
        Stdio::null()
    } else {
        match File::create(Path::new(gpu_pipeline_dir).join("watcher-stderr.log")) {
            Ok(f) => Stdio::from(f),
            Err(_) => Stdio::null(), // last words are a courtesy, never a spawn blocker
        }
    };
    let child = Command::new(gpu_python_exe)
        .arg(&script)
        .env("PYTHONIOENCODING", "utf-8")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(stderr)
        .creation_flags(CREATE_NO_WINDOW)
        .spawn()
        .map_err(|e| format!("failed to spawn watcher: {e}"))?;
    let pid = child.id();
    adopt_into_job(&child); // dies with the widget even on a force-kill / crash (S37)
    *guard = Some(child);
    *state.1.lock().unwrap() = None; // fresh run — no standing death certificate
    Ok(WatcherStatus {
        state: "running".into(),
        pid: Some(pid),
        exit_code: None,
    })
}

pub fn stop(state: &WatcherState) -> WatcherStatus {
    let mut guard = state.0.lock().unwrap();
    if let Some(mut child) = guard.take() {
        let _ = child.kill();
        let _ = child.wait();
    }
    *state.1.lock().unwrap() = None; // a deliberate stop is not a death — no certificate
    WatcherStatus {
        state: "stopped".into(),
        pid: None,
        exit_code: None,
    }
}
