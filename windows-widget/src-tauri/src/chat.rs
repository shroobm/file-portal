// S85: THE ASSISTANT GRADUATES — the llama app embedded into File Portal (Rab, the overnight
// commission: "make sure that the llama app is essentially embedded into the file portal app,
// and so I can talk to models that I have downloaded on my device, that are directly connected
// to a schema regarding the file portal knowledge corpus"). The widget SPAWNS the graduated
// server (`windows-converter/room_chat.py`) and opens a dedicated window on it — bench.rs's
// proven chassis (S63), with the S85 differences deliberate:
//
//   * `llama_server_exe` config key, EMPTY HIDES THE FEATURE (docs/33 §2 requirement; the
//     reader_config idiom — the button does not exist on a machine that has not set it up);
//   * a `chat_stop` command exists (the bench has no stop — recon hazard: a resident 8B model
//     with no visible off-switch is VRAM held by nothing the operator can see);
//   * the death-certificate second mutex (the watcher's idiom) — a dead chat server files its
//     exit code instead of vanishing;
//   * the model LOAD is not waited on here. The UI server is stdlib and comes up in well under
//     bench.rs's 6 s; the slow 20–90 s llama load happens inside the page's own Load button
//     (docs/33 §2.4 — the 6 s ceiling was the copy-paste defect, and it is not copied).
//
// The hold file discipline: killing this child skips room_chat.py's cleanup, and the stale
// chat-hold is then reaped by pid-liveness — by the watcher's gate, and by the next chat server
// at startup. Proven by deferral_gate_selftest.py (12/12) before this module existed.

use crate::vault::CREATE_NO_WINDOW;
use crate::watcher::adopt_into_job;
use std::fs;
use std::net::{TcpListener, TcpStream};
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;

/// One chat server at a time. Arc for the spawn_blocking move (the bench idiom); the second
/// mutex is the death certificate (the watcher idiom — recon: bench lacks it and a bench death
/// is invisible).
#[derive(Clone, Default)]
pub struct ChatState(pub Arc<Mutex<Option<ChatRun>>>, pub Arc<Mutex<Option<i32>>>);

pub struct ChatRun {
    pub port: u16,
    pub child: Child,
    /// Per-launch loopback token (S108; threat model at bench::launch_token). None when the
    /// server predates the token contract - the reuse path re-sends the birth token only.
    pub token: Option<String>,
}

/// First free port in the chat UI range, proven by binding. room_chat.py's own llama child uses
/// 7110–7119; the bench owns 7077–7096. Distinct on purpose (docs/33 §2.5), and 7100–7109 keeps
/// this server clear of BOTH (the parity harness's 7117 borrow was S83 §10.4's lesson).
fn free_port() -> Result<u16, String> {
    (7100..7110)
        .find(|p| TcpListener::bind(("127.0.0.1", *p)).is_ok())
        .ok_or_else(|| "no free port in 7100..7110".into())
}

/// Spawn (or reuse) the chat server and open its window. Blocking — call from spawn_blocking.
pub fn open(
    app: tauri::AppHandle,
    state: &ChatState,
    gpu_pipeline_dir: &str,
    gpu_python_exe: &str,
    gpu_converter_dir: &str,
    llama_server_exe: &str,
) -> Result<u16, String> {
    if llama_server_exe.is_empty() {
        // Empty key = feature hidden. Reaching here means the UI showed a button it should
        // not have — refuse loudly rather than spawn a server that cannot load a model.
        return Err("llama_server_exe is not configured — the assistant is disabled".into());
    }
    if gpu_python_exe.is_empty() || gpu_converter_dir.is_empty() || gpu_pipeline_dir.is_empty() {
        return Err("gpu_python_exe / gpu_converter_dir / gpu_pipeline_dir not configured".into());
    }
    let script = Path::new(gpu_converter_dir).join("room_chat.py");
    if !script.is_file() {
        return Err(format!("chat server not found: {}", script.display()));
    }
    let mut guard = state
        .0
        .lock()
        .map_err(|_| "chat lock poisoned".to_string())?;
    if let Some(run) = guard.as_mut() {
        if matches!(run.child.try_wait(), Ok(None)) {
            let port = run.port;
            let token = run.token.clone();
            drop(guard);
            show_window(app, port, token.as_deref());
            return Ok(port);
        }
        // Died since last time: file the certificate, then replace. wait() reaps — no zombie.
        if let Ok(Some(status)) = run.child.try_wait() {
            if let Ok(mut cert) = state.1.lock() {
                *cert = status.code();
            }
        }
        let _ = run.child.kill();
        let _ = run.child.wait();
        *guard = None;
    }
    let port = free_port()?;
    // S108 loopback-CSRF fence, the bench's idiom: fresh token per launch, argv in, ?token=
    // on the window URL. Feature-detected until lane D's server half lands.
    let token = crate::bench::server_takes_token(&script).then(crate::bench::launch_token);
    // Last words to a file (the watcher-stderr idiom). room_chat.py's own llama child writes
    // chat-stderr.log; this is the UI server's, kept separate so one death cannot mask the other.
    let stderr = fs::File::create(Path::new(gpu_pipeline_dir).join("room-chat-stderr.log"))
        .map(Stdio::from)
        .unwrap_or_else(|_| Stdio::null());
    let mut cmd = Command::new(gpu_python_exe);
    cmd.arg(&script)
        .args(["--port", &port.to_string()])
        .args(["--llama", llama_server_exe])
        // The server derives its hold file, event stream and tree snapshot from FP_PIPELINE;
        // it MUST be the widget's own pipeline dir or the mutex splits across roots (recon
        // hazard: a hold in one root, a watcher reading another).
        .env("FP_PIPELINE", gpu_pipeline_dir)
        .env("PYTHONIOENCODING", "utf-8")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(stderr)
        .creation_flags(CREATE_NO_WINDOW);
    if let Some(tok) = token.as_deref() {
        cmd.args(["--token", tok]);
    }
    let child = cmd
        .spawn()
        .map_err(|e| format!("failed to spawn chat server: {e}"))?;
    adopt_into_job(&child); // dies with the widget, by ANY exit (S37)
    let mut up = false;
    for _ in 0..30 {
        // The UI server is stdlib-instant; 6 s is generous HERE (the model load is elsewhere).
        if TcpStream::connect_timeout(
            &std::net::SocketAddr::from(([127, 0, 0, 1], port)),
            Duration::from_millis(200),
        )
        .is_ok()
        {
            up = true;
            break;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    if !up {
        return Err("chat server did not come up — see room-chat-stderr.log".into());
    }
    *guard = Some(ChatRun {
        port,
        child,
        token: token.clone(),
    });
    drop(guard);
    show_window(app, port, token.as_deref());
    Ok(port)
}

/// Stop the chat server. The kill skips room_chat.py's unload cleanup by design (TerminateProcess
/// via kill), so the hold file may briefly survive — the watcher's pid-liveness reap clears it on
/// its next poll, and llama-server (the grandchild) dies with the Job Object when the widget
/// exits or is reaped as an orphaned child of a killed tree.
pub fn stop(state: &ChatState) -> Result<bool, String> {
    let mut guard = state
        .0
        .lock()
        .map_err(|_| "chat lock poisoned".to_string())?;
    if let Some(mut run) = guard.take() {
        let _ = run.child.kill();
        if let Ok(status) = run.child.wait() {
            if let Ok(mut cert) = state.1.lock() {
                *cert = status.code();
            }
        }
        return Ok(true);
    }
    Ok(false)
}

/// Liveness + death certificate, proven per call via try_wait (the watcher's status idiom).
pub fn status(state: &ChatState) -> Result<serde_json::Value, String> {
    let mut guard = state
        .0
        .lock()
        .map_err(|_| "chat lock poisoned".to_string())?;
    let (running, port) = match guard.as_mut() {
        Some(run) => match run.child.try_wait() {
            Ok(None) => (true, Some(run.port)),
            Ok(Some(status)) => {
                if let Ok(mut cert) = state.1.lock() {
                    *cert = status.code();
                }
                *guard = None;
                (false, None)
            }
            Err(_) => (false, None),
        },
        None => (false, None),
    };
    let died = state.1.lock().ok().and_then(|c| *c);
    Ok(serde_json::json!({ "running": running, "port": port, "last_exit": died }))
}

/// Open (or refocus) the assistant window — bench.rs's main-thread pattern verbatim.
fn show_window(app: tauri::AppHandle, port: u16, token: Option<&str>) {
    let url = match token {
        Some(tok) => format!("http://127.0.0.1:{port}/?token={tok}"),
        None => format!("http://127.0.0.1:{port}/"),
    };
    let _ = app.clone().run_on_main_thread(move || {
        use tauri::Manager;
        if let Some(w) = app.get_webview_window("room-chat") {
            let _ = w.eval(format!("window.location.replace('{url}')"));
            let _ = w.set_focus();
            return;
        }
        match url.parse() {
            Ok(parsed) => {
                if let Err(e) = tauri::WebviewWindowBuilder::new(
                    &app,
                    "room-chat",
                    tauri::WebviewUrl::External(parsed),
                )
                .title("Room · Assistant")
                .inner_size(880.0, 720.0)
                .build()
                {
                    crate::bench::log_boot(&app, &format!("chat window failed: {e}"));
                }
            }
            Err(e) => crate::bench::log_boot(&app, &format!("chat url parse failed: {e}")),
        }
    });
}
