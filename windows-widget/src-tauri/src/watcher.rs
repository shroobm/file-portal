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

/// Spawn `cmd` and immediately adopt the child into the kill-on-close Job Object — one call,
/// so a spawn site cannot carry the launch half and forget the supervision half. S108: the
/// census found 3 of 10 spawn sites adopting, and the two that did NOT were both full GPU
/// conversions (`--resume` in preflight.rs, `--reanalyze` in assay.rs) — the SYM-047 orphan
/// class: a force-killed widget left a conversion running on the card. Those two now come
/// through here. Best-effort like the adoption itself: a failed job assignment never blocks
/// the launch. The tripwire test below holds the census; amend its allowlist ONLY with a
/// comment naming why a site is exempt.
pub(crate) fn spawn_supervised(cmd: &mut Command) -> std::io::Result<Child> {
    let child = cmd.spawn()?;
    adopt_into_job(&child);
    Ok(child)
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

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::Path;

    /// THE SPAWN-SUPERVISION TRIPWIRE (S108). Every process spawn site in this crate is named
    /// here with its supervision census: how many raw spawn calls, how many supervised ones,
    /// how many explicit adoptions. A new spawn site, a deleted one, or — the case this exists
    /// for — an adoption quietly REMOVED (the SYM-047 orphan class coming back) changes a count
    /// and fails this test. Exemptions are rows, each with a reason:
    ///   * line.rs — four launches of the USER'S apps (reader/editor/uri/Explorer); killing
    ///     those with the widget would be wrong, so they must never be adopted;
    ///   * transfer.rs — a piped tailscale-ssh the code waits on inline; short-lived by
    ///     construction.
    ///
    /// The needles are assembled at runtime so this file's own strings never match them.
    #[test]
    fn every_spawn_site_is_named_on_the_supervision_allowlist() {
        let raw_needle = format!(".{}{}", "spawn", "()");
        let sup_needle = format!("{}{}", "spawn_supervised", "(&");
        let adopt_needle = format!("{}{}", "adopt_into_job", "(&");
        // (file, raw spawn calls, supervised calls, explicit adoptions)
        let allow: &[(&str, usize, usize, usize)] = &[
            ("assay.rs", 0, 1, 0),     // --reanalyze GPU conversion: supervised (S108)
            ("bench.rs", 1, 0, 1),     // bench server: spawn + adopt (S63)
            ("chat.rs", 1, 0, 1),      // chat server: spawn + adopt (S85)
            ("line.rs", 4, 0, 0),      // EXEMPT: user's own apps — must outlive the widget
            ("preflight.rs", 0, 1, 0), // --resume GPU conversion: supervised (S108)
            ("transfer.rs", 1, 0, 0),  // EXEMPT: inline-waited ssh, short-lived
            ("watcher.rs", 2, 0, 2),   // helper's own spawn + the watcher start, both adopted
        ];
        let src = Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
        let mut seen: Vec<String> = vec![];
        for entry in fs::read_dir(&src).expect("src dir readable").flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("rs") {
                continue;
            }
            let name = path
                .file_name()
                .expect("file has a name")
                .to_string_lossy()
                .to_string();
            let text = fs::read_to_string(&path).expect("source file readable");
            let counts = (
                text.matches(&raw_needle).count(),
                text.matches(&sup_needle).count(),
                text.matches(&adopt_needle).count(),
            );
            match allow.iter().find(|(f, ..)| *f == name.as_str()) {
                Some((_, raw, sup, adopt)) => {
                    assert_eq!(
                        counts,
                        (*raw, *sup, *adopt),
                        "{name}: spawn census (raw, supervised, adopted) = {counts:?},                          allowlist says ({raw}, {sup}, {adopt}) — a spawn site was added,                          removed, or LOST ITS ADOPTION (SYM-047 class). Supervise it via                          watcher::spawn_supervised, or amend the allowlist row WITH a                          comment naming why the site is exempt."
                    );
                    seen.push(name);
                }
                None => {
                    assert_eq!(
                        counts,
                        (0, 0, 0),
                        "{name}: has spawn/supervision call sites but no allowlist row —                          add one, with its supervision story."
                    );
                }
            }
        }
        for (f, ..) in allow {
            assert!(
                seen.iter().any(|s| s == f),
                "allowlisted file {f} not found in src/ — stale allowlist row"
            );
        }
    }
}
