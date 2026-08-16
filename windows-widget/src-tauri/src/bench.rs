// S63: THE BENCH SURFACE — the Repair Bench graduates into the widget as the fourth surface
// (docs/19 §7's graduation step, commissioned by Rab: "I want the widget running with the
// repair bench, along with the dock, room, wall"). The widget SPAWNS the quarantined prototype
// server (`prototypes/repair-bench/bench.py`) on a REAL held bundle and opens a dedicated
// window on it. The quarantine survives graduation: nothing here imports the prototype — the
// coupling is exactly one child process the widget owns, supervises, and kills.
//
// Safety inheritance, each from a paid-for lesson:
//   * spawned detached with null stdin/stdout + a last-words stderr file (S31 dead-handle
//     crash + the 0x67 "died unheard" class);
//   * adopted into the watcher's kill-on-close Job Object (S37 — no orphaned bench servers,
//     by ANY widget exit);
//   * the slow work (spawn + readiness wait) runs off the UI thread (the vault_check freeze);
//   * the window itself is created on the MAIN thread via run_on_main_thread (a Windows/Tauri
//     requirement for window creation).

use crate::vault::CREATE_NO_WINDOW;
use crate::watcher::adopt_into_job;
use serde_json::Value;
use std::fs;
use std::net::{TcpListener, TcpStream};
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;

/// One live bench at a time; opening a different held bundle replaces it. Arc so the async
/// command can move a handle into spawn_blocking (the assay_bless idiom).
#[derive(Clone, Default)]
pub struct BenchState(pub Arc<Mutex<Option<BenchRun>>>);

pub struct BenchRun {
    pub dir: PathBuf,
    pub port: u16,
    pub child: Child,
}

/// Which held bundle goes on the bench. `source` is the manifest's `source` filename — the
/// SAME per-row `data-src` contract bless/⟲/⟳ already use (assay.rs `held_list` sets
/// `bundle: m["source"]`). Empty = the newest held bundle.
pub fn resolve_held(gpu_pipeline_dir: &str, source: &str) -> Result<PathBuf, String> {
    let held = Path::new(gpu_pipeline_dir).join("held");
    let entries = fs::read_dir(&held).map_err(|_| "held/ is empty or missing".to_string())?;
    let mut newest: Option<(std::time::SystemTime, PathBuf)> = None;
    for e in entries.flatten() {
        let dir = e.path();
        if !dir.is_dir() {
            continue;
        }
        let Ok(text) = fs::read_to_string(dir.join("manifest.json")) else {
            continue;
        };
        let Ok(m) = serde_json::from_str::<Value>(&text) else {
            continue;
        };
        if !source.is_empty() && m["source"].as_str() != Some(source) {
            continue;
        }
        let t = e
            .metadata()
            .and_then(|md| md.modified())
            .unwrap_or(std::time::UNIX_EPOCH);
        if newest.as_ref().is_none_or(|(bt, _)| t > *bt) {
            newest = Some((t, dir));
        }
    }
    newest.map(|(_, d)| d).ok_or_else(|| {
        if source.is_empty() {
            "nothing in held/ to repair".into()
        } else {
            format!("no held bundle matches '{source}'")
        }
    })
}

/// First free port in the bench range, proven by binding. The tiny window between our probe
/// and the child's own bind is acceptable on a single-user desktop; a lost race surfaces as
/// "did not come up" with the last-words log, never silence.
pub fn free_port() -> Result<u16, String> {
    (7077..7097)
        .find(|p| TcpListener::bind(("127.0.0.1", *p)).is_ok())
        .ok_or_else(|| "no free port in 7077..7097".into())
}

/// prototypes/repair-bench/bench.py, derived from the converter dir — both live in the same
/// repo checkout, so no new config key is needed (and a moved repo moves both together).
pub fn bench_script(gpu_converter_dir: &str) -> Result<PathBuf, String> {
    let repo = Path::new(gpu_converter_dir)
        .parent()
        .ok_or("converter dir has no parent")?;
    let script = repo
        .join("prototypes")
        .join("repair-bench")
        .join("bench.py");
    if script.is_file() {
        Ok(script)
    } else {
        Err(format!("bench script not found: {}", script.display()))
    }
}

/// Spawn (or reuse) the bench server for `source` and open its window. Blocking — call from
/// spawn_blocking. Returns the port it serves on.
pub fn open(
    app: tauri::AppHandle,
    state: &BenchState,
    gpu_pipeline_dir: &str,
    gpu_python_exe: &str,
    gpu_converter_dir: &str,
    source: &str,
) -> Result<u16, String> {
    if gpu_python_exe.is_empty() || gpu_converter_dir.is_empty() {
        return Err("gpu_python_exe / gpu_converter_dir not configured".into());
    }
    let dir = resolve_held(gpu_pipeline_dir, source)?;
    let mut guard = state
        .0
        .lock()
        .map_err(|_| "bench lock poisoned".to_string())?;
    if let Some(run) = guard.as_mut() {
        let alive = matches!(run.child.try_wait(), Ok(None));
        if alive && run.dir == dir {
            let port = run.port;
            drop(guard);
            show_window(app, port, &dir);
            return Ok(port);
        }
        // A different patient (or a dead server): replace it. wait() reaps — no zombie row.
        let _ = run.child.kill();
        let _ = run.child.wait();
        *guard = None;
    }
    let script = bench_script(gpu_converter_dir)?;
    let port = free_port()?;
    // Last words to a file (the watcher-stderr idiom): a silent death must leave a note.
    let stderr = fs::File::create(Path::new(gpu_pipeline_dir).join("bench-stderr.log"))
        .map(Stdio::from)
        .unwrap_or_else(|_| Stdio::null());
    let child = Command::new(gpu_python_exe)
        .arg(&script)
        .arg(&dir)
        .args(["--port", &port.to_string()])
        .env("PYTHONIOENCODING", "utf-8")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(stderr)
        .creation_flags(CREATE_NO_WINDOW)
        .spawn()
        .map_err(|e| format!("failed to spawn bench: {e}"))?;
    adopt_into_job(&child); // no orphaned bench servers, by any widget exit (S37)
    let mut up = false;
    for _ in 0..30 {
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
        return Err("bench server did not come up — see bench-stderr.log".into());
    }
    *guard = Some(BenchRun {
        dir: dir.clone(),
        port,
        child,
    });
    drop(guard);
    show_window(app, port, &dir);
    Ok(port)
}

/// Open (or refocus/renavigate) the dedicated bench window. Window creation MUST happen on the
/// main thread; errors land in widget-boot.log via the debug channel rather than being lost.
fn show_window(app: tauri::AppHandle, port: u16, dir: &Path) {
    let title = format!(
        "Repair Bench — {}",
        dir.file_name()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_default()
    );
    let url = format!("http://127.0.0.1:{port}/");
    let _ = app.clone().run_on_main_thread(move || {
        use tauri::Manager;
        if let Some(w) = app.get_webview_window("repair-bench") {
            // Reuse the existing window: navigate it in-page (no label-collision race) + front.
            let _ = w.eval(format!("window.location.replace('{url}')"));
            let _ = w.set_title(&title);
            let _ = w.set_focus();
            return;
        }
        match url.parse() {
            Ok(parsed) => {
                if let Err(e) = tauri::WebviewWindowBuilder::new(
                    &app,
                    "repair-bench",
                    tauri::WebviewUrl::External(parsed),
                )
                .title(title)
                .inner_size(1280.0, 860.0)
                .build()
                {
                    log_boot(&app, &format!("bench window failed: {e}"));
                }
            }
            Err(e) => log_boot(&app, &format!("bench url parse failed: {e}")),
        }
    });
}

pub(crate) fn log_boot(app: &tauri::AppHandle, msg: &str) {
    // pub(crate) since S85: chat.rs's window path reports through the same channel.
    use tauri::Manager;
    let state: tauri::State<crate::AppState> = app.state();
    // Clone the path out and release the lock immediately — a guard held across the write
    // (or an if-let scrutinee temporary) borrows `state` longer than it lives (E0597).
    let dir = state
        .config
        .lock()
        .map(|cfg| cfg.gpu_pipeline_dir.clone())
        .unwrap_or_default();
    if dir.is_empty() {
        return;
    }
    let line = format!(
        "{} bench: {}\n",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0),
        msg
    );
    let _ = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(Path::new(&dir).join("widget-boot.log"))
        .and_then(|mut f| std::io::Write::write_all(&mut f, line.as_bytes()));
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn tmp(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(name);
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn write_held(base: &Path, sha: &str, source: &str) {
        let d = base.join("held").join(sha);
        fs::create_dir_all(&d).unwrap();
        fs::write(
            d.join("manifest.json"),
            serde_json::to_string(&json!({ "source": source })).unwrap(),
        )
        .unwrap();
    }

    #[test]
    fn resolves_by_the_rows_own_source_contract() {
        let base = tmp("fp-bench-resolve");
        write_held(&base, "aaaa000000000001", "Book A.pdf");
        write_held(&base, "bbbb000000000002", "Book B.pdf");
        let p = resolve_held(base.to_str().unwrap(), "Book B.pdf").unwrap();
        assert!(p.ends_with("bbbb000000000002"));
        // Empty source = newest held bundle; an unknown source is a plain refusal, not a guess.
        assert!(resolve_held(base.to_str().unwrap(), "").is_ok());
        let err = resolve_held(base.to_str().unwrap(), "Nope.pdf").unwrap_err();
        assert!(err.contains("Nope.pdf"));
        let _ = fs::remove_dir_all(&base);
    }

    #[test]
    fn an_empty_held_dir_refuses_calmly() {
        let base = tmp("fp-bench-empty");
        fs::create_dir_all(base.join("held")).unwrap();
        assert!(resolve_held(base.to_str().unwrap(), "").is_err());
        let _ = fs::remove_dir_all(&base);
    }

    #[test]
    fn free_port_skips_a_bound_one() {
        // Bind the range's first port; the scanner must return a DIFFERENT free one.
        let held = TcpListener::bind(("127.0.0.1", 7077)).ok(); // may already be busy — fine
        let p = free_port().unwrap();
        if held.is_some() {
            assert_ne!(p, 7077);
        }
        assert!((7077..7097).contains(&p));
    }

    #[test]
    fn bench_script_derives_from_the_repo_layout() {
        let repo = tmp("fp-bench-repo");
        let conv = repo.join("windows-converter");
        fs::create_dir_all(&conv).unwrap();
        let rb = repo.join("prototypes").join("repair-bench");
        fs::create_dir_all(&rb).unwrap();
        fs::write(rb.join("bench.py"), "# stub").unwrap();
        let s = bench_script(conv.to_str().unwrap()).unwrap();
        assert!(s.ends_with("bench.py"));
        // A checkout without the prototype refuses with the path it looked at.
        let bare = tmp("fp-bench-bare");
        let conv2 = bare.join("windows-converter");
        fs::create_dir_all(&conv2).unwrap();
        assert!(bench_script(conv2.to_str().unwrap()).is_err());
        let _ = fs::remove_dir_all(&repo);
        let _ = fs::remove_dir_all(&bare);
    }
}
