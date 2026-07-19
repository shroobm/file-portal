// S20: the widget's read side of the event stream (docs/13 keystone). The pipeline
// appends JSON lines to <gpu_pipeline_dir>\events.jsonl; this module summarizes today's
// shift and hands the raw tail to the UI. Projection principle: read-only, no state.

use serde_json::{json, Value};
use std::fs;
use std::path::Path;

/// Today's shift report + the last few raw events. All derived, nothing stored.
pub fn shift_summary(gpu_pipeline_dir: &str) -> Result<Value, String> {
    if gpu_pipeline_dir.is_empty() {
        return Ok(json!({"available": false}));
    }
    let path = Path::new(gpu_pipeline_dir).join("events.jsonl");
    let text = match fs::read_to_string(&path) {
        Ok(t) => t,
        Err(_) => return Ok(json!({"available": false})),
    };
    let today = chrono_today_prefix();
    let (mut converted, mut analyzed, mut protected, mut shipped, mut failed) =
        (0u32, 0, 0, 0, 0u32);
    let mut tail: Vec<Value> = vec![];
    for line in text.lines() {
        let Ok(ev) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        let is_today = ev["ts"].as_str().is_some_and(|ts| ts.starts_with(&today));
        if is_today {
            match (ev["stage"].as_str(), ev["event"].as_str()) {
                (Some("convert"), Some("converted")) => converted += 1,
                (Some("analyst"), Some("done")) => {
                    analyzed += 1;
                    protected += ev["chunks_rejected"].as_u64().unwrap_or(0) as u32;
                }
                (Some("ship"), Some("shipped")) => shipped += 1,
                (_, Some("failed")) => failed += 1,
                _ => {}
            }
        }
        tail.push(ev);
        if tail.len() > 40 {
            tail.remove(0);
        }
    }
    Ok(json!({
        "available": true,
        "today": {
            "converted": converted,
            "analyzed": analyzed,
            "chunks_protected": protected,
            "shipped": shipped,
            "failed": failed,
        },
        "tail": tail.into_iter().rev().take(10).collect::<Vec<_>>(),
    }))
}

/// UTC date prefix ("2026-07-19") without pulling in a date crate: parse from any
/// event's own timestamp format by computing from SystemTime days-since-epoch.
fn chrono_today_prefix() -> String {
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let days = secs / 86_400;
    // Civil-from-days algorithm (Howard Hinnant), valid for the era in question.
    let z = days as i64 + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{y:04}-{m:02}-{d:02}")
}
