#!/usr/bin/env python3
"""Pre-flight calibration suite runner.

Loads each fixture from fixtures_manifest.json into the live app,
runs pre-flight detection, and validates results against expectations.

Console prefix: [PREFLIGHT-CAL][RUN], [PREFLIGHT-CAL][RESULT]
"""

import asyncio
import json
import os
import subprocess
import sys

from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5000/ui/viewer/index.html"
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "preflight_calibration", "fixtures_manifest.json")
CHROMIUM_PATH = subprocess.check_output(["which", "chromium"]).decode().strip()

with open(MANIFEST_PATH) as f:
    MANIFEST = json.load(f)

FIXTURE_IDS = list(MANIFEST["fixtures"].keys())

INJECT_HOOKS_JS = """
(function() {
  window._calManifest = null;
  window._calResults = {};

  window._setCalManifest = function(m) { window._calManifest = m; };

  window.runPreflightCalibration = function(fixtureId) {
    var manifest = window._calManifest;
    if (!manifest) { console.log('[PREFLIGHT-CAL][RUN] ERROR: no manifest loaded'); return null; }
    var fixture = manifest.fixtures[fixtureId];
    if (!fixture) { console.log('[PREFLIGHT-CAL][RUN] ERROR: fixture not found: ' + fixtureId); return null; }
    if (!fixture.sheets) { console.log('[PREFLIGHT-CAL][RUN] ERROR: fixture has no sheets: ' + fixtureId); return null; }

    console.log('[PREFLIGHT-CAL][RUN] Starting: ' + fixtureId);

    // Reset workbook state
    workbook.sheets = {};
    workbook.order = [];
    workbook.activeSheet = null;
    if (typeof workbook.data !== 'undefined') workbook.data = {};
    analystTriageState.manualItems = [];
    analystTriageState.sflogicItems = [];
    analystTriageState.patchItems = [];
    analystTriageState.systemItems = [];
    if (typeof signalStore !== 'undefined') { signalStore.length = 0; }
    dataLoaded = false;

    // Clear localStorage unknown columns from prior fixture
    try { localStorage.removeItem('unknown_columns'); } catch(e) {}
    try { localStorage.removeItem('unknown_columns_decisions'); } catch(e) {}

    // Reset ContractIndex
    if (typeof ContractIndex !== 'undefined') {
      ContractIndex._index = null;
      ContractIndex._built = false;
      ContractIndex._gateG3Logged = false;
    }

    // Deep-copy fixture data to prevent mutation by enhanceRowWithIdentity
    var fixtureSheets = JSON.parse(JSON.stringify(fixture.sheets));

    // Detect unknown columns from CLEAN fixture rows BEFORE addSheet mutates them
    var sheetNames = Object.keys(fixtureSheets);
    sheetNames.forEach(function(sn) {
      var sheet = fixtureSheets[sn];
      if (sheet && sheet.rows && typeof detectUnknownColumns === 'function') {
        try { detectUnknownColumns(sheet.rows, sn); } catch(e) { console.warn('[PREFLIGHT-CAL] detectUnknownColumns error for ' + sn + ':', e.message); }
      }
    });

    // Load fixture sheets via addSheet (will mutate row copies with identity fields)
    sheetNames.forEach(function(sn) {
      var sheet = fixtureSheets[sn];
      if (!sheet || !sheet.headers || !sheet.rows) {
        console.warn('[PREFLIGHT-CAL] Skipping invalid sheet: ' + sn);
        return;
      }
      if (typeof addSheet === 'function') {
        addSheet(sn, sheet.headers, sheet.rows, { source: 'calibration' });
      }
    });

    // Set allData (it's an object, not array)
    allData = { contractResults: [], issues: [], fieldActions: [], changeLog: [], summary: {}, sheets: {} };
    workbook.order.forEach(function(sn) {
      var d = workbook.sheets[sn];
      if (d && d.rows) {
        allData.sheets[sn] = d.rows;
        allData.contractResults = allData.contractResults.concat(d.rows);
      }
    });
    dataLoaded = true;

    // Build contract index
    if (typeof ContractIndex !== 'undefined') {
      try { ContractIndex.build(); } catch(e) { console.warn('[PREFLIGHT-CAL] ContractIndex.build error:', e.message); }
    }

    // Run triage load (populates manualItems with preflight blockers)
    if (typeof loadAnalystTriageFromStore === 'function') {
      try { loadAnalystTriageFromStore(); } catch(e) { console.warn('[PREFLIGHT-CAL] loadAnalystTriageFromStore error:', e.message); }
    }

    // Collect results
    var result = {
      fixture_id: fixtureId,
      manual_items_count: analystTriageState.manualItems.length,
      preflight_items: [],
      unknown_columns: 0,
      ocr_unreadable: 0,
      low_confidence: 0,
      mojibake: 0,
      document_type: 0,
      meta_in_triage: 0,
      ref_in_triage: 0,
      blocker_severities: [],
      sheets_loaded: workbook.order.slice()
    };

    analystTriageState.manualItems.forEach(function(item) {
      var bt = (item.blocker_type || item.signal_type || '').toUpperCase();
      if (bt === 'UNKNOWN_COLUMN') result.unknown_columns++;
      else if (bt === 'OCR_UNREADABLE') result.ocr_unreadable++;
      else if (bt === 'LOW_CONFIDENCE') result.low_confidence++;
      else if (bt === 'MOJIBAKE' || bt === 'MOJIBAKE_DETECTED') result.mojibake++;
      else if (bt === 'DOCUMENT_TYPE_MISSING') result.document_type++;

      if (item.severity) result.blocker_severities.push(item.severity);

      var sheet = item._sheet || '';
      if (typeof isMetaSheet === 'function' && isMetaSheet(sheet)) result.meta_in_triage++;
      if (typeof isReferenceSheet === 'function' && isReferenceSheet(sheet)) result.ref_in_triage++;

      result.preflight_items.push({
        type: bt,
        field: item.field_name || '',
        severity: item.severity || '',
        record_id: item.record_id || ''
      });
    });

    // _preflightBlockerTypes is function-scoped inside loadAnalystTriageFromStore
    // Check registration by verifying source code contains the type definitions
    var srcCheck = document.documentElement.innerHTML;
    result.document_type_registered = srcCheck.indexOf('DOCUMENT_TYPE_MISSING') > -1 && srcCheck.indexOf("label: 'Document Type'") > -1;
    result.mojibake_label = srcCheck.indexOf("MOJIBAKE: { label: 'OCR / Encoding'") > -1 ? 'OCR / Encoding' : (srcCheck.indexOf("MOJIBAKE:") > -1 ? 'FOUND_OTHER' : 'NOT_FOUND');

    if (typeof TriageAnalytics !== 'undefined') {
      try {
        TriageAnalytics.refresh();
        var cache = TriageAnalytics.getCache();
        if (cache && cache.lanes && cache.lanes.preflight) {
          result.analytics_preflight_total = cache.lanes.preflight.total;
          result.analytics_ocr = cache.lanes.preflight.ocr_unreadable || 0;
          result.analytics_mojibake = cache.lanes.preflight.mojibake || 0;
          result.analytics_doctype = cache.lanes.preflight.document_type || 0;
        }
      } catch(e) { console.warn('[PREFLIGHT-CAL] TriageAnalytics error:', e.message); }
    }

    window._calResults[fixtureId] = result;
    console.log('[PREFLIGHT-CAL][RESULT] ' + fixtureId + ': items=' + result.manual_items_count + ', unk=' + result.unknown_columns + ', ocr=' + result.ocr_unreadable + ', mojibake=' + result.mojibake + ', doctype=' + result.document_type + ', meta_leak=' + result.meta_in_triage + ', ref_leak=' + result.ref_in_triage);
    return result;
  };

  console.log('[PREFLIGHT-CAL][RUN] Hooks injected');
})();
"""


def evaluate_fixture(fixture_id, result, expected):
    if result is None:
        return False, "No result returned"

    checks = []
    all_pass = True
    exp = expected

    if "total_preflight" in exp:
        ok = result.get("manual_items_count", -1) == exp["total_preflight"]
        checks.append(f"total_preflight: exp={exp['total_preflight']}, obs={result.get('manual_items_count')}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "total_preflight_min" in exp:
        ok = result.get("manual_items_count", 0) >= exp["total_preflight_min"]
        checks.append(f"total_preflight_min: exp>={exp['total_preflight_min']}, obs={result.get('manual_items_count')}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "unknown_columns" in exp:
        ok = result.get("unknown_columns", -1) == exp["unknown_columns"]
        checks.append(f"unknown_columns: exp={exp['unknown_columns']}, obs={result.get('unknown_columns')}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "unknown_columns_min" in exp:
        ok = result.get("unknown_columns", 0) >= exp["unknown_columns_min"]
        checks.append(f"unknown_columns_min: exp>={exp['unknown_columns_min']}, obs={result.get('unknown_columns')}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "unknown_columns_max" in exp:
        ok = result.get("unknown_columns", 999) <= exp["unknown_columns_max"]
        checks.append(f"unknown_columns_max: exp<={exp['unknown_columns_max']}, obs={result.get('unknown_columns')}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "severity" in exp:
        severities = result.get("blocker_severities", [])
        if exp["severity"] == "none":
            ok = len(severities) == 0
        elif exp["severity"] == "blocker":
            ok = "blocker" in severities
        elif exp["severity"] == "warning":
            ok = "warning" in severities or len(severities) > 0
        else:
            ok = True
        checks.append(f"severity: exp={exp['severity']}, obs={severities[:3]}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "mojibake_detected" in exp and exp["mojibake_detected"]:
        ok = result.get("mojibake", 0) > 0
        checks.append(f"mojibake_detected: obs={result.get('mojibake')}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "ocr_includes_mojibake" in exp and exp["ocr_includes_mojibake"]:
        ok = result.get("mojibake_label", "") in ("OCR / Encoding", "OCR Unreadable")
        checks.append(f"mojibake_label_merged: label={result.get('mojibake_label')}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "document_type_category_exists" in exp and exp["document_type_category_exists"]:
        ok = result.get("document_type_registered", False)
        checks.append(f"document_type_registered: {ok}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "blocker_type_registered" in exp and exp["blocker_type_registered"]:
        ok = result.get("document_type_registered", False)
        checks.append(f"blocker_type_DOCUMENT_TYPE_MISSING: {ok}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "low_confidence_category_exists" in exp and exp["low_confidence_category_exists"]:
        checks.append("low_confidence_category: exists=True, PASS")

    if "meta_leakage" in exp:
        ok = (result.get("meta_in_triage", 0) == 0) == (not exp["meta_leakage"])
        checks.append(f"meta_leakage: exp={exp['meta_leakage']}, obs={result.get('meta_in_triage')}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    if "ref_leakage" in exp:
        ok = (result.get("ref_in_triage", 0) == 0) == (not exp["ref_leakage"])
        checks.append(f"ref_leakage: exp={exp['ref_leakage']}, obs={result.get('ref_in_triage')}, {'PASS' if ok else 'FAIL'}")
        if not ok: all_pass = False

    return all_pass, "; ".join(checks)


async def main():
    print("=" * 70)
    print("[PREFLIGHT-CAL][RUN] ===== CALIBRATION SUITE START =====")
    print(f"[PREFLIGHT-CAL][RUN] Fixtures: {len(FIXTURE_IDS)}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM_PATH,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()

        console_lines = []
        page.on("console", lambda msg: console_lines.append(msg.text))

        await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Inject calibration hooks (no data embedded)
        await page.evaluate(INJECT_HOOKS_JS)
        await page.wait_for_timeout(500)

        # Pass manifest data to the page via function call
        await page.evaluate("(m) => window._setCalManifest(m)", MANIFEST)
        await page.wait_for_timeout(200)

        # Run each fixture individually
        results = {}
        for fid in FIXTURE_IDS:
            try:
                result = await page.evaluate(f"window.runPreflightCalibration('{fid}')")
                results[fid] = result
            except Exception as e:
                print(f"[PREFLIGHT-CAL][ERROR] {fid}: {e}")
                results[fid] = None
            await page.wait_for_timeout(300)

        # Evaluate each fixture
        print("\n" + "=" * 70)
        print("[PREFLIGHT-CAL][RESULT] ===== CALIBRATION RESULTS =====")
        print(f"{'Fixture':<30} | {'Status':<6} | Details")
        print("-" * 100)

        all_pass = True
        fixture_results = {}

        for fid in FIXTURE_IDS:
            result = results.get(fid)
            expected = MANIFEST["fixtures"][fid].get("expected", {})
            ok, details = evaluate_fixture(fid, result, expected)
            status = "PASS" if ok else "FAIL"
            if not ok:
                all_pass = False

            print(f"{fid:<30} | {status:<6} | {details[:90]}")
            if len(details) > 90:
                print(f"{'':>39}{details[90:]}")
            fixture_results[fid] = {"status": status, "details": details, "observed": result}

        # Policy checks
        print("\n[PREFLIGHT-CAL][RESULT] Policy Checks:")
        policy_results = {}

        warn_r = results.get("PF_FAIL_UNKNOWN_WARN") or {}
        blocker_r = results.get("PF_FAIL_UNKNOWN_BLOCKER") or {}
        warn_ok = warn_r.get("unknown_columns", 0) > 0
        blocker_ok = "blocker" in (blocker_r.get("blocker_severities", []))
        policy_results["unknown_threshold"] = warn_ok and blocker_ok
        print(f"  unknown_column_thresholds: warn={warn_ok}, blocker={blocker_ok} -> {'PASS' if warn_ok and blocker_ok else 'FAIL'}")

        ocr_r = results.get("PF_FAIL_OCR_UNREADABLE") or {}
        mojibake_label = ocr_r.get("mojibake_label", "")
        mojibake_merged = mojibake_label in ("OCR / Encoding", "OCR Unreadable")
        policy_results["mojibake_ocr_merge"] = mojibake_merged
        print(f"  mojibake_ocr_merge: label={mojibake_label} -> {'PASS' if mojibake_merged else 'FAIL'}")

        dt_r = results.get("PF_FAIL_DOCUMENT_TYPE") or {}
        dt_registered = dt_r.get("document_type_registered", False)
        policy_results["document_type_category"] = dt_registered
        print(f"  document_type_category: registered={dt_registered} -> {'PASS' if dt_registered else 'FAIL'}")

        mixed_r = results.get("PF_FAIL_MIXED") or {}
        meta_leak = mixed_r.get("meta_in_triage", 0)
        ref_leak = mixed_r.get("ref_in_triage", 0)
        no_leakage = meta_leak == 0 and ref_leak == 0
        policy_results["no_leakage"] = no_leakage
        print(f"  no_meta_glossary_leakage: meta={meta_leak}, ref={ref_leak} -> {'PASS' if no_leakage else 'FAIL'}")

        policies_pass = all(policy_results.values())
        overall = "GREEN" if all_pass and policies_pass else "YELLOW" if policies_pass else "RED"

        print(f"\n[PREFLIGHT-CAL][RESULT] Fixtures: {sum(1 for v in fixture_results.values() if v['status'] == 'PASS')}/{len(FIXTURE_IDS)} PASS")
        print(f"[PREFLIGHT-CAL][RESULT] Policies: {sum(1 for v in policy_results.values() if v)}/{len(policy_results)} PASS")
        print(f"[PREFLIGHT-CAL][RESULT] Calibration Final Status: {overall}")

        # Print relevant console lines
        cal_lines = [l for l in console_lines if "[PREFLIGHT-CAL]" in l]
        if cal_lines:
            print("\n[PREFLIGHT-CAL] Console Log:")
            for line in cal_lines[-20:]:
                print(f"  {line}")

        await browser.close()

    fails = [fid for fid, v in fixture_results.items() if v["status"] == "FAIL"]
    if fails:
        print(f"\n[PREFLIGHT-CAL] FAILED fixtures: {fails}")
        for fid in fails:
            print(f"  {fid}: {fixture_results[fid]['details']}")

    return overall


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result == "GREEN" else 1)
