#!/usr/bin/env python3
"""
Staging Rollout Monitor — Evidence Inspector v2.51
Checks 3 signals hourly + rollback trip-wires.
Run: python scripts/staging_monitor.py
"""
import os
import sys
import json
import datetime
import requests as req_lib

BASE = os.environ.get("BASE_URL", "http://localhost:5000")
WS = "ws_SEED0100000000000000000000"
DOC = "doc_SEED0100000000000000000000"
ANALYST = {"Authorization": "Bearer usr_SEED0100000000000000000000"}
VERIFIER = {"Authorization": "Bearer usr_SEED0200000000000000000000"}

def api(method, path, body=None, headers=None, auth_token=None):
    hdrs = dict(ANALYST)
    if auth_token:
        hdrs["Authorization"] = auth_token
    if headers:
        hdrs.update(headers)
    r = req_lib.request(method, BASE + path, json=body, headers=hdrs)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}

def api_noauth(method, path):
    r = req_lib.request(method, BASE + path)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}

def section(title):
    print("\n" + "=" * 60)
    print("  " + title)
    print("=" * 60)

def check_pass(label, ok, detail=""):
    tag = "OK" if ok else "ALERT"
    print("  [%s] %s%s" % (tag, label, (" — " + detail) if detail else ""))
    return ok

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    print("STAGING ROLLOUT MONITOR — %s UTC" % now.strftime("%Y-%m-%d %H:%M:%S"))
    print("Feature flag: EVIDENCE_INSPECTOR_V251")

    alerts = []

    # ── SIGNAL 1: 5xx rate ──
    section("SIGNAL 1: 5xx Error Rate")
    status, data = api("GET", "/api/v2.5/workspaces/%s/audit-events?limit=200" % WS)
    raw = data.get("data", [])
    events = raw if isinstance(raw, list) else raw.get("items", []) if isinstance(raw, dict) else []
    total_events = len(events)
    error_events = [e for e in events if "error" in str(e.get("event_type", "")).lower() or "5xx" in str(e.get("event_type", "")).lower()]
    error_rate = (len(error_events) / total_events * 100) if total_events > 0 else 0
    ok = check_pass("Error events in audit log", error_rate < 1, "%d/%d (%.2f%%)" % (len(error_events), total_events, error_rate))
    if not ok:
        alerts.append("TRIP-WIRE: Sustained API error rate >1%% (%d errors in %d events)" % (len(error_events), total_events))

    status_health, _ = api_noauth("GET", "/health")
    check_pass("Health endpoint", status_health == 200, "HTTP %d" % status_health)

    v25_endpoints = [
        ("GET", "/api/v2.5/workspaces"),
        ("GET", "/api/v2.5/workspaces/%s/patches" % WS),
        ("GET", "/api/v2.5/workspaces/%s/rfis" % WS),
        ("GET", "/api/v2.5/workspaces/%s/audit-events?limit=1" % WS),
    ]
    v25_ok = True
    for method, path in v25_endpoints:
        s, _ = api(method, path)
        if s != 200:
            v25_ok = False
            check_pass("v2.5 %s %s" % (method, path.split("?")[0]), False, "HTTP %d" % s)
    check_pass("v2.5 regression (4 endpoints)", v25_ok, "all 200")
    if not v25_ok:
        alerts.append("TRIP-WIRE: v2.5 regression failure")

    # ── SIGNAL 2: MOJIBAKE_ESCALATION_REQUESTED spikes ──
    section("SIGNAL 2: Mojibake Escalation Trend")
    mojibake_events = [e for e in events if e.get("event_type") == "MOJIBAKE_ESCALATION_REQUESTED"]
    mojibake_count = len(mojibake_events)
    check_pass("MOJIBAKE_ESCALATION_REQUESTED count", True, "%d in audit log" % mojibake_count)
    if mojibake_count > 20:
        alerts.append("WARNING: High mojibake escalation count (%d) — investigate OCR quality" % mojibake_count)
        check_pass("Mojibake spike threshold (<20)", False, "%d escalations" % mojibake_count)
    else:
        check_pass("Mojibake spike threshold (<20)", True, "%d escalations — within normal range" % mojibake_count)

    # ── SIGNAL 3: 403 trend by endpoint ──
    section("SIGNAL 3: Unauthorized 403 Trend by Endpoint")

    role_tests = [
        ("RFI analyst→return (should block)", "PATCH", None, {"custody_status": "returned_to_analyst"}, "analyst"),
        ("Correction analyst→approve (should block)", "PATCH", None, {"status": "approved"}, "analyst"),
    ]

    run_tag = now.strftime("%H%M%S")

    s1, d1 = api("POST", "/api/v2.5/workspaces/%s/rfis" % WS, {
        "patch_id": "pat_SEED0100000000000000000000",
        "field_id": "fld_monitor_%s" % run_tag,
        "target_record_id": "rec_monitor_%s" % run_tag,
        "question": "Monitor test RFI %s" % now.isoformat(),
    })

    if s1 == 201:
        rfi_id = d1.get("data", {}).get("id", "")
        rfi_v = d1.get("data", {}).get("version", 1)

        s_send, d_send = api("PATCH", "/api/v2.5/rfis/%s" % rfi_id,
            {"custody_status": "awaiting_verifier", "version": rfi_v})
        rfi_v = d_send.get("data", {}).get("version", rfi_v + 1) if s_send == 200 else rfi_v
        check_pass("RFI: analyst send OK", s_send == 200, "HTTP %d" % s_send)

        s_block, d_block = api("PATCH", "/api/v2.5/rfis/%s" % rfi_id,
            {"custody_status": "returned_to_analyst", "version": rfi_v})
        ok_403 = check_pass("RFI: analyst return blocked", s_block == 403,
            "HTTP %d, code=%s" % (s_block, d_block.get("error", {}).get("code", "?")))
        if not ok_403:
            alerts.append("TRIP-WIRE: Role enforcement failure on RFI return")

        s_ret, d_ret = api("PATCH", "/api/v2.5/rfis/%s" % rfi_id,
            {"custody_status": "returned_to_analyst", "version": rfi_v}, auth_token=VERIFIER["Authorization"])
        check_pass("RFI: verifier return OK", s_ret == 200, "HTTP %d" % s_ret)
    else:
        check_pass("RFI create for 403 test", s1 == 201, "HTTP %d" % s1)

    s_anc, d_anc = api("POST", "/api/v2.5/documents/%s/anchors" % DOC, {
        "node_id": "node_monitor_%s" % run_tag,
        "field_id": "fld_monitor_%s" % run_tag,
        "selected_text": "monitor anchor text %s" % run_tag,
        "char_start": 0, "char_end": 20,
    })
    anchor_id = d_anc.get("data", {}).get("id", "anc_fallback") if s_anc in (200, 201) else "anc_fallback"
    check_pass("Anchor create for correction test", s_anc in (200, 201), "HTTP %d" % s_anc)

    s2, d2 = api("POST", "/api/v2.5/documents/%s/corrections" % DOC, {
        "anchor_id": anchor_id,
        "field_id": "fld_test",
        "original_value": "short text A",
        "corrected_value": "This is a significantly different and much longer corrected value for monitor testing purposes",
    })

    if s2 == 201:
        cor_id = d2.get("data", {}).get("id", "")
        cor_v = d2.get("data", {}).get("version", 1)
        s_block2, d_block2 = api("PATCH", "/api/v2.5/corrections/%s" % cor_id,
            {"status": "approved", "version": cor_v})
        ok_403_2 = check_pass("Correction: analyst approve blocked", s_block2 == 403,
            "HTTP %d, code=%s" % (s_block2, d_block2.get("error", {}).get("code", "?")))
        if not ok_403_2:
            alerts.append("TRIP-WIRE: Role enforcement failure on correction approve")

        s_approve, _ = api("PATCH", "/api/v2.5/corrections/%s" % cor_id,
            {"status": "approved", "version": cor_v}, auth_token=VERIFIER["Authorization"])
        check_pass("Correction: verifier approve OK", s_approve == 200, "HTTP %d" % s_approve)
    else:
        check_pass("Correction create for 403 test", s2 == 201, "HTTP %d" % s2)

    # ── SIGNAL 4: Audit emission gaps ──
    section("AUDIT EMISSION COVERAGE")
    all_events = []
    cursor = None
    for _ in range(10):
        url = "/api/v2.5/workspaces/%s/audit-events?limit=200" % WS
        if cursor:
            url += "&cursor=%s" % cursor
        _, page_data = api("GET", url)
        page_raw = page_data.get("data", [])
        page_events = page_raw if isinstance(page_raw, list) else []
        if not page_events:
            break
        all_events.extend(page_events)
        next_cursor = page_data.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        cursor = next_cursor
    fresh_events = all_events

    v251_types = {
        "anchor.created", "correction.created", "correction.updated",
        "ocr_escalation.created", "reader_node_cache.upserted",
        "MOJIBAKE_ESCALATION_REQUESTED", "CORRECTION_PROPOSED",
        "CORRECTION_APPLIED_MINOR", "CORRECTION_APPROVED", "CORRECTION_REJECTED",
        "RFI_CREATED", "RFI_SENT", "RFI_RETURNED", "RFI_RESOLVED",
        "rfi.created", "rfi.updated",
    }
    found_types = set()
    type_counts = {}
    for e in fresh_events:
        et = e.get("event_type", "")
        if et in v251_types:
            found_types.add(et)
            type_counts[et] = type_counts.get(et, 0) + 1

    missing = v251_types - found_types
    for t in sorted(found_types):
        check_pass(t, True, "%d events" % type_counts[t])

    if missing:
        print("\n  Missing event types:")
        for m in sorted(missing):
            check_pass(m, False, "NOT FOUND in audit log")
        alerts.append("TRIP-WIRE: Audit emission gap — missing types: %s" % ", ".join(sorted(missing)))
    else:
        check_pass("All 16 v2.51 event types present", True, "full coverage")

    # ── SUMMARY ──
    section("ROLLOUT STATUS SUMMARY")
    print("  Timestamp: %s UTC" % now.strftime("%Y-%m-%d %H:%M:%S"))
    print("  Feature flag: EVIDENCE_INSPECTOR_V251 = ON")
    print("  Audit events total: %d" % len(fresh_events))
    print("  v2.51 event types: %d/16" % len(found_types))
    print("  Error rate: %.2f%%" % error_rate)
    print("  Mojibake escalations: %d" % mojibake_count)
    print("")

    if alerts:
        print("  >>> ALERTS (%d) <<<" % len(alerts))
        for a in alerts:
            print("    ! %s" % a)
        print("")
        print("  RECOMMENDATION: INVESTIGATE — rollback may be needed")
        print("  Rollback: unset EVIDENCE_INSPECTOR_V251 && restart (< 2 min)")
        return 1
    else:
        print("  >>> ALL CLEAR — No trip-wires triggered <<<")
        print("  RECOMMENDATION: Continue rollout")
        print("")
        print("  Rollback armed: unset EVIDENCE_INSPECTOR_V251 && restart (< 2 min)")
        return 0

if __name__ == "__main__":
    sys.exit(main())
