// Stage F (docs/18 §6 / docs/19 §6): THE ALGEDONIC LINE — pain that goes unacknowledged
// escalates, instead of scrolling quietly out of an event stream nobody was watching. Beer's
// term is deliberate: an algedonic signal bypasses the normal reporting hierarchy. Here that
// means: any `stalled` / `failed` / `held` fact (from Python's events.jsonl, or the ThinkPad
// exporter's receipts) that no human has acknowledged within M minutes surfaces as a banner on
// every widget surface until someone clicks ⚑.
//
// PROVISIONAL CONTRACT (flagged for Rab per docs/19 §6 — "M and the ack mechanism = Rab's
// call"): M lives in `algedonic-minutes.txt` (default 30, a lever like audit-mode.txt), and an
// acknowledgement is one appended line in `algedonic-acks.jsonl` — widget-owned, dot-free so
// Rab can read it, never touched by Python. Both are trivially replaceable if he signs a
// different mechanism; nothing else depends on their shape.
//
// Projection discipline: this module READS pipeline truth and derives; the only thing it ever
// writes is the ack ledger and the M lever — the widget's own files, never Python's.

use crate::receipts;
use serde_json::{json, Value};
use std::fs;
use std::path::Path;

const ACKS_NAME: &str = "algedonic-acks.jsonl";
const MINUTES_NAME: &str = "algedonic-minutes.txt";
const DEFAULT_MINUTES: u64 = 30; // PROVISIONAL default — Rab signs the real number
const WINDOW_S: u64 = 7 * 86_400; // older pain is archaeology, not an alarm
const MAX_ALERTS: usize = 12;

pub fn minutes(gpu_pipeline_dir: &str) -> u64 {
    fs::read_to_string(Path::new(gpu_pipeline_dir).join(MINUTES_NAME))
        .ok()
        .and_then(|s| s.trim().parse::<u64>().ok())
        .filter(|m| (1..=720).contains(m))
        .unwrap_or(DEFAULT_MINUTES)
}

pub fn set_minutes(gpu_pipeline_dir: &str, m: u64) -> Result<u64, String> {
    if !(1..=720).contains(&m) {
        return Err(format!("invalid algedonic minutes: {m} (1..720)"));
    }
    fs::write(
        Path::new(gpu_pipeline_dir).join(MINUTES_NAME),
        format!("{m}\n"),
    )
    .map_err(|e| format!("failed to write algedonic minutes: {e}"))?;
    Ok(m)
}

/// Acknowledge one alert by its stable id. Append-only: the ledger doubles as a record of who
/// silenced what, when — the same flight-recorder instinct as the cookie tally.
pub fn ack(gpu_pipeline_dir: &str, id: &str) -> Result<(), String> {
    if id.is_empty() {
        return Err("empty alert id".into());
    }
    let line = serde_json::to_string(&json!({ "id": id, "ts": now_iso() }))
        .map_err(|e| e.to_string())?
        + "\n";
    let path = Path::new(gpu_pipeline_dir).join(ACKS_NAME);
    use std::io::Write;
    fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .and_then(|mut f| f.write_all(line.as_bytes()))
        .map_err(|e| format!("failed to write ack: {e}"))
}

/// The projection: every unresolved pain signal in the window, newest first, each carrying its
/// age and ack state. `escalated` = unacked AND older than M — the banner's population.
pub fn state(gpu_pipeline_dir: &str) -> Result<Value, String> {
    if gpu_pipeline_dir.is_empty() {
        return Ok(json!({ "available": false }));
    }
    let base = Path::new(gpu_pipeline_dir);
    let now = now_epoch();
    let m = minutes(gpu_pipeline_dir);

    let events: Vec<Value> = fs::read_to_string(base.join("events.jsonl"))
        .unwrap_or_default()
        .lines()
        .filter_map(|l| serde_json::from_str(l).ok())
        .collect();
    let receipt_rows: Vec<Value> = receipts::read_cached(gpu_pipeline_dir)["rows"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let acks: Vec<String> = fs::read_to_string(base.join(ACKS_NAME))
        .unwrap_or_default()
        .lines()
        .filter_map(|l| serde_json::from_str::<Value>(l).ok())
        .filter_map(|v| v["id"].as_str().map(String::from))
        .collect();

    let sfield = |ev: &Value, keys: &[&str]| -> String {
        keys.iter()
            .find_map(|k| ev[*k].as_str().map(String::from))
            .unwrap_or_default()
    };

    // ---- gather candidates from the desktop event stream --------------------------------
    let mut candidates: Vec<(String, String, String, String, String)> = vec![]; // (ts, kind, stage, bundle, detail)
    for ev in &events {
        let (stage, event) = (
            ev["stage"].as_str().unwrap_or(""),
            ev["event"].as_str().unwrap_or(""),
        );
        let ts = ev["ts"].as_str().unwrap_or("").to_string();
        let bundle = sfield(ev, &["bundle", "source", "id"]);
        let detail = sfield(ev, &["error", "verdict", "reason"]);
        let kind = match (stage, event) {
            ("convert", "stalled") => "stalled",
            ("audit", "held") => "held",
            ("intake", "failed") | ("gate", "failed") | ("ship", "failed") => "failed",
            _ => continue,
        };
        // Resolution suppression: a LATER success/park over the same subject retires the alarm
        // (the algedonic line reports standing pain, not history).
        let resolved = events.iter().any(|later| {
            let lts = later["ts"].as_str().unwrap_or("");
            if lts <= ts.as_str() {
                return false;
            }
            let lb = sfield(later, &["bundle", "source", "id"]);
            if lb != bundle {
                return false;
            }
            matches!(
                (later["stage"].as_str(), later["event"].as_str()),
                (Some("convert"), Some("converted"))
                    | (Some("ship"), Some("shipped"))
                    | (Some("gate"), Some("resolved"))
                    | (Some("audit"), Some("held")) // a park is the RESOLUTION of a ship failure
            ) && !(stage == "audit") // ...but nothing auto-resolves a park except a human
        });
        if !resolved {
            candidates.push((ts, kind.into(), stage.into(), bundle, detail));
        }
    }

    // ---- gather from the vault's receipts (the ThinkPad's own refusals) -----------------
    for r in &receipt_rows {
        let outcome = r["outcome"].as_str().unwrap_or("");
        let kind = match outcome {
            "supersede-held" => "vault-held",
            "bless-invalid" => "bless-invalid",
            "failed" => "failed",
            _ => continue,
        };
        let ts = r["ts"].as_str().unwrap_or("").to_string();
        let bundle = r["bundle"].as_str().unwrap_or("").to_string();
        let detail = sfield(r, &["verdict", "why", "error"]);
        let resolved = receipt_rows.iter().any(|later| {
            later["ts"].as_str().unwrap_or("") > ts.as_str()
                && later["bundle"].as_str() == Some(bundle.as_str())
                && matches!(
                    later["outcome"].as_str(),
                    Some("exported") | Some("exported-supersede") | Some("blessed")
                )
        });
        if !resolved {
            candidates.push((ts, kind.into(), "export".into(), bundle, detail));
        }
    }

    // ---- window, dedupe (kind+bundle keeps the NEWEST occurrence), sort, cap ------------
    candidates.retain(|(ts, ..)| {
        parse_iso_utc(ts).is_some_and(|t| now.saturating_sub(t) <= WINDOW_S)
    });
    candidates.sort_by(|a, b| b.0.cmp(&a.0)); // newest first
    let mut seen = std::collections::HashSet::new();
    candidates.retain(|(_, kind, _, bundle, _)| seen.insert(format!("{kind}|{bundle}")));
    candidates.truncate(MAX_ALERTS);

    let alerts: Vec<Value> = candidates
        .into_iter()
        .map(|(ts, kind, stage, bundle, detail)| {
            let id = format!("{ts}|{kind}|{bundle}");
            let age_min = parse_iso_utc(&ts)
                .map(|t| now.saturating_sub(t) / 60)
                .unwrap_or(0);
            let acked = acks.contains(&id);
            json!({
                "id": id, "ts": ts, "kind": kind, "stage": stage, "bundle": bundle,
                "detail": detail, "age_min": age_min, "acked": acked,
                "escalated": !acked && age_min >= m,
            })
        })
        .collect();
    let unacked = alerts.iter().filter(|a| a["acked"] == false).count();
    let escalated = alerts.iter().filter(|a| a["escalated"] == true).count();
    Ok(json!({
        "available": true,
        "m_minutes": m,
        "m_provisional": true, // Rab has not signed M or the ack mechanism yet (docs/19 §6)
        "alerts": alerts,
        "unacked": unacked,
        "escalated": escalated,
    }))
}

// ---- time, without a date crate (the events.rs idiom, both directions) ----------------------

fn now_epoch() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// "2026-08-03T07:13:03+00:00" (or any ISO-8601 UTC prefix) → unix seconds. Every writer in
/// this pipeline stamps UTC to the second, so the zone suffix is checked only for absence of
/// an actual offset. Returns None rather than guessing on anything malformed.
fn parse_iso_utc(ts: &str) -> Option<u64> {
    let b = ts.as_bytes();
    if b.len() < 19 || !b[..19].is_ascii() {
        return None; // non-ASCII would also make the byte-offset slices below panic
    }
    if b[4] != b'-' || b[7] != b'-' || b[10] != b'T' || b[13] != b':' || b[16] != b':' {
        return None;
    }
    let num = |s: &str| s.parse::<i64>().ok();
    let (y, m, d) = (num(&ts[0..4])?, num(&ts[5..7])?, num(&ts[8..10])?);
    let (hh, mm, ss) = (num(&ts[11..13])?, num(&ts[14..16])?, num(&ts[17..19])?);
    if !(1..=12).contains(&m) || !(1..=31).contains(&d) || hh > 23 || mm > 59 || ss > 60 {
        return None;
    }
    // days_from_civil (Howard Hinnant) — the inverse of events.rs's civil_from_days.
    let y2 = if m <= 2 { y - 1 } else { y };
    let era = y2.div_euclid(400);
    let yoe = y2 - era * 400;
    let mp = if m > 2 { m - 3 } else { m + 9 };
    let doy = (153 * mp + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    let days = era * 146_097 + doe - 719_468;
    u64::try_from(days * 86_400 + hh * 3_600 + mm * 60 + ss).ok()
}

/// Unix seconds → the same ISO shape the pipeline writes (for the ack ledger's own stamps).
fn now_iso() -> String {
    iso_of(now_epoch())
}

fn iso_of(secs: u64) -> String {
    let days = secs / 86_400;
    let (h, mi, s) = ((secs % 86_400) / 3_600, (secs % 3_600) / 60, secs % 60);
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
    format!("{y:04}-{m:02}-{d:02}T{h:02}:{mi:02}:{s:02}+00:00")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn iso_round_trip_agrees_with_itself() {
        // The parser must invert the formatter exactly — the two halves of the same algorithm.
        let now = now_epoch();
        assert_eq!(parse_iso_utc(&now_iso()), Some(now));
        // And a pipeline-authored stamp parses (this exact string is from the real events.jsonl).
        let t = parse_iso_utc("2026-08-03T07:13:03+00:00").unwrap();
        assert_eq!(t % 60, 3);
        assert!(parse_iso_utc("garbage").is_none());
        assert!(parse_iso_utc("2026-13-40T99:99:99").is_none());
    }

    fn tmp(name: &str) -> String {
        let dir = std::env::temp_dir().join(name);
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir.to_string_lossy().into_owned()
    }

    #[test]
    fn held_alerts_survive_and_resolved_failures_retire() {
        let dir = tmp("fp-alg-basic");
        let recent = now_iso();
        fs::write(
            Path::new(&dir).join("events.jsonl"),
            format!(
                "{{\"ts\": \"{recent}\", \"stage\": \"audit\", \"event\": \"held\", \"bundle\": \"BookA\", \"verdict\": \"fail\"}}\n\
                 {{\"ts\": \"2026-08-01T00:00:00+00:00\", \"stage\": \"ship\", \"event\": \"failed\", \"bundle\": \"BookB\", \"error\": \"502\"}}\n\
                 {{\"ts\": \"2026-08-02T00:00:00+00:00\", \"stage\": \"ship\", \"event\": \"shipped\", \"bundle\": \"BookB\"}}\n"
            ),
        )
        .unwrap();
        let st = state(&dir).unwrap();
        let alerts = st["alerts"].as_array().unwrap();
        assert_eq!(alerts.len(), 1, "BookB's failure was resolved by its later ship");
        assert_eq!(alerts[0]["kind"], "held");
        assert_eq!(alerts[0]["bundle"], "BookA");
        assert_eq!(alerts[0]["acked"], false);
        let _ = fs::remove_dir_all(std::env::temp_dir().join("fp-alg-basic"));
    }

    #[test]
    fn a_park_resolves_the_ship_failure_but_nothing_auto_resolves_a_park() {
        // The Damodaran shape: ship failed (ThinkPad down), then the retry enforce-parked it.
        // The failure retires; the park stands until a human acks it.
        let dir = tmp("fp-alg-park");
        let recent = now_iso();
        fs::write(
            Path::new(&dir).join("events.jsonl"),
            format!(
                "{{\"ts\": \"2026-08-03T04:37:46+00:00\", \"stage\": \"ship\", \"event\": \"failed\", \"bundle\": \"Dam\", \"error\": \"502\"}}\n\
                 {{\"ts\": \"{recent}\", \"stage\": \"audit\", \"event\": \"held\", \"bundle\": \"Dam\", \"verdict\": \"fail\"}}\n"
            ),
        )
        .unwrap();
        let st = state(&dir).unwrap();
        let alerts = st["alerts"].as_array().unwrap();
        assert_eq!(alerts.len(), 1);
        assert_eq!(alerts[0]["kind"], "held", "the park is the standing fact");
        let _ = fs::remove_dir_all(std::env::temp_dir().join("fp-alg-park"));
    }

    #[test]
    fn acking_silences_and_a_new_occurrence_realarms() {
        let dir = tmp("fp-alg-ack");
        let older = iso_of(now_epoch() - 120);
        fs::write(
            Path::new(&dir).join("events.jsonl"),
            format!("{{\"ts\": \"{older}\", \"stage\": \"audit\", \"event\": \"held\", \"bundle\": \"BookA\"}}\n"),
        )
        .unwrap();
        let st = state(&dir).unwrap();
        let id = st["alerts"][0]["id"].as_str().unwrap().to_string();
        ack(&dir, &id).unwrap();
        let st2 = state(&dir).unwrap();
        assert_eq!(st2["alerts"][0]["acked"], true);
        assert_eq!(st2["unacked"], 0);
        // A NEWER held event for the same bundle carries a new ts → a new id → un-acked again:
        // an acknowledgement silences an occurrence, never the class.
        let mut text = fs::read_to_string(Path::new(&dir).join("events.jsonl")).unwrap();
        text.push_str(&format!(
            "{{\"ts\": \"{}\", \"stage\": \"audit\", \"event\": \"held\", \"bundle\": \"BookA\"}}\n",
            iso_of(now_epoch() - 30)
        ));
        fs::write(Path::new(&dir).join("events.jsonl"), text).unwrap();
        let st3 = state(&dir).unwrap();
        assert_eq!(st3["alerts"].as_array().unwrap().len(), 1, "deduped by kind+bundle");
        assert_eq!(st3["alerts"][0]["acked"], false, "the newer occurrence re-alarms");
        assert_eq!(st3["unacked"], 1);
        let _ = fs::remove_dir_all(std::env::temp_dir().join("fp-alg-ack"));
    }

    #[test]
    fn receipts_join_the_stream_and_the_lever_validates() {
        let dir = tmp("fp-alg-rcpt");
        let recent = now_iso();
        fs::write(
            Path::new(&dir).join(".receipts-cache.jsonl"),
            format!(
                "{{\"ts\": \"{recent}\", \"outcome\": \"supersede-held\", \"bundle\": \"CC\", \"verdict\": \"fail\"}}\n"
            ),
        )
        .unwrap();
        let st = state(&dir).unwrap();
        assert_eq!(st["alerts"][0]["kind"], "vault-held");
        assert_eq!(st["alerts"][0]["stage"], "export");
        assert_eq!(minutes(&dir), DEFAULT_MINUTES);
        assert!(set_minutes(&dir, 0).is_err());
        assert!(set_minutes(&dir, 999).is_err());
        assert_eq!(set_minutes(&dir, 60).unwrap(), 60);
        assert_eq!(minutes(&dir), 60);
        let _ = fs::remove_dir_all(std::env::temp_dir().join("fp-alg-rcpt"));
    }
}
