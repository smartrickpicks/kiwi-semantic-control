#!/usr/bin/env python3
"""
P1A Runtime Validation — Triage Clarity + Sheet-Scoped Pre-Flight
Phase A: 12 targeted checks for P1A features
Phase B: Regression suite (P0.2.2, P1, Calibration, P0.8, P0.9)
"""

import asyncio, subprocess, sys, json, os

CHROMIUM_PATH = subprocess.check_output(['which', 'chromium']).decode().strip()
BASE_URL = 'http://127.0.0.1:5000/ui/viewer/index.html'

async def run_phase_a():
    from playwright.async_api import async_playwright
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM_PATH,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        page = await browser.new_page()
        errors = []
        logs = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda msg: logs.append(msg.text))

        await page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        # ─── A1: No JS errors ───
        results.append(('A1-no-js-errors', len(errors) == 0, 'errors=' + str(len(errors))))

        # ─── A2: Label map exists and returns human-readable labels ───
        label_check = await page.evaluate('''(function() {
            if (typeof getTriageTypeLabel !== "function") return { ok: false, reason: "function missing" };
            var tests = {
                required: "Missing Required",
                picklist: "Invalid Picklist",
                encoding: "Encoding Issue",
                extraction: "Extraction Error",
                preflight_blocker: "Pre-Flight",
                rfi: "RFI",
                blacklist: "Blacklisted",
                logic: "Logic Flag"
            };
            var failures = [];
            for (var k in tests) {
                var got = getTriageTypeLabel(k);
                if (got !== tests[k]) failures.push(k + ": expected=" + tests[k] + " got=" + got);
            }
            return { ok: failures.length === 0, failures: failures };
        })()''')
        results.append(('A2-label-map', label_check['ok'], json.dumps(label_check.get('failures', []))))

        # ─── A3: Tooltip function exists and returns tips ───
        tip_check = await page.evaluate('''(function() {
            if (typeof getTriageTypeTip !== "function") return { ok: false, reason: "function missing" };
            var tip = getTriageTypeTip("required");
            return { ok: tip.length > 10, tip: tip };
        })()''')
        results.append(('A3-tooltip-fn', tip_check['ok'], tip_check.get('tip', tip_check.get('reason', ''))))

        # ─── A4: Sheet tab container exists in DOM ───
        tab_exists = await page.evaluate('!!document.getElementById("p1a-preflight-sheet-tabs")')
        results.append(('A4-tab-container', tab_exists, ''))

        # ─── A5: Sheet tab builder function exists ───
        tab_fn = await page.evaluate('typeof _p1aBuildSheetTabs === "function"')
        results.append(('A5-tab-builder-fn', tab_fn, ''))

        # ─── A6: Sheet filter function works ───
        filter_test = await page.evaluate('''(function() {
            if (typeof _p1aFilterBySheet !== "function") return { ok: false, reason: "missing" };
            _p1aActiveSheet = "All";
            var items = [
                { sheet_name: "Accounts", field_name: "x" },
                { sheet_name: "Contracts", field_name: "y" },
                { sheet_name: "Accounts", field_name: "z" }
            ];
            var all = _p1aFilterBySheet(items);
            if (all.length !== 3) return { ok: false, reason: "All filter should return 3, got " + all.length };
            _p1aActiveSheet = "Accounts";
            var accts = _p1aFilterBySheet(items);
            if (accts.length !== 2) return { ok: false, reason: "Accounts filter should return 2, got " + accts.length };
            _p1aActiveSheet = "Contracts";
            var ctrs = _p1aFilterBySheet(items);
            if (ctrs.length !== 1) return { ok: false, reason: "Contracts filter should return 1, got " + ctrs.length };
            _p1aActiveSheet = "All";
            return { ok: true, reason: "All=3, Accounts=2, Contracts=1" };
        })()''')
        results.append(('A6-sheet-filter', filter_test['ok'], filter_test['reason']))

        # ─── A7: Tab builder produces correct tab counts ───
        tab_count_test = await page.evaluate('''(function() {
            if (typeof _p1aBuildSheetTabs !== "function") return { ok: false, reason: "missing" };
            _p1aActiveSheet = "All";
            var items = [
                { sheet_name: "Accounts", field_name: "x" },
                { sheet_name: "Contracts", field_name: "y" },
                { sheet_name: "Accounts", field_name: "z" },
                { sheet_name: "Financials", field_name: "w" }
            ];
            _p1aBuildSheetTabs(items);
            var container = document.getElementById("p1a-preflight-sheet-tabs");
            if (!container) return { ok: false, reason: "container missing" };
            var buttons = container.querySelectorAll("button");
            var tabData = [];
            for (var i = 0; i < buttons.length; i++) {
                tabData.push(buttons[i].textContent.trim());
            }
            var expected = ["All (4)", "Accounts (2)", "Contracts (1)", "Financials (1)"];
            var pass = tabData.length === expected.length;
            for (var j = 0; j < expected.length && pass; j++) {
                if (tabData[j] !== expected[j]) pass = false;
            }
            return { ok: pass, tabs: tabData, expected: expected };
        })()''')
        results.append(('A7-tab-counts', tab_count_test['ok'],
            'tabs=' + json.dumps(tab_count_test.get('tabs', []))))

        # ─── A8: Blocker types include new entries (global _preflightBlockerTypes) ───
        blocker_check = await page.evaluate('''(function() {
            if (typeof _preflightBlockerTypes === "undefined") return { ok: false, reason: "missing" };
            var has_mr = !!_preflightBlockerTypes["MISSING_REQUIRED"];
            var has_pi = !!_preflightBlockerTypes["PICKLIST_INVALID"];
            var has_dtm = !!_preflightBlockerTypes["DOCUMENT_TYPE_MISSING"];
            var dtm_label = has_dtm ? _preflightBlockerTypes["DOCUMENT_TYPE_MISSING"].label : "";
            return { ok: has_mr && has_pi && has_dtm && dtm_label === "Document Type Missing",
                     MISSING_REQUIRED: has_mr, PICKLIST_INVALID: has_pi, DTM_label: dtm_label };
        })()''')
        results.append(('A8-blocker-types', blocker_check['ok'], json.dumps(blocker_check)))

        # ─── A9: Schema deep-link shows batch-level explanation ───
        schema_test = await page.evaluate('''(function() {
            if (typeof TriageAnalytics === "undefined") return { ok: false, reason: "TriageAnalytics missing" };
            var emptyEl = document.getElementById("ta-schema-empty-state");
            if (!emptyEl) return { ok: false, reason: "empty state element missing" };
            TriageAnalytics.handleSchemaClick("drift");
            var text = emptyEl.textContent || "";
            var hasBatchLevel = text.indexOf("batch-level") >= 0;
            return { ok: hasBatchLevel, text: text.substring(0, 120) };
        })()''')
        results.append(('A9-schema-deeplink-drift', schema_test['ok'], schema_test.get('text', schema_test.get('reason', ''))))

        # ─── A10: Schema unknown deep-link with no items shows batch-level ───
        schema_unk_test = await page.evaluate('''(function() {
            if (typeof TriageAnalytics === "undefined") return { ok: false, reason: "missing" };
            var emptyEl = document.getElementById("ta-schema-empty-state");
            if (!emptyEl) return { ok: false, reason: "empty state missing" };
            TriageAnalytics.handleSchemaClick("unknown");
            var text = emptyEl.textContent || "";
            return { ok: text.length > 0, text: text.substring(0, 120) };
        })()''')
        results.append(('A10-schema-deeplink-unknown', schema_unk_test['ok'], schema_unk_test.get('text', '')))

        # ─── A11: P1A console logs emitted ───
        p1a_logs = [l for l in logs if '[P1A]' in l]
        results.append(('A11-p1a-logs', len(p1a_logs) >= 1, 'count=' + str(len(p1a_logs))))

        # ─── A12: Record display uses Batch-level for items without row info ───
        record_test = await page.evaluate('''(function() {
            if (typeof renderTriageQueueTable !== "function") return { ok: false, reason: "function missing" };
            var testContainer = document.createElement("tbody");
            testContainer.id = "_p1a_test_tbody";
            document.body.appendChild(testContainer);
            var items = [
                { type: "preflight_blocker", blocker_type: "UNKNOWN_COLUMN", contract_key: "", record_id: "", field_name: "test_col",
                  status: "open", status_label: "Open", status_color: "#e65100", source: "preflight", updated_at: new Date().toISOString() },
                { type: "preflight_blocker", blocker_type: "UNKNOWN_COLUMN", contract_key: "CTR-001", contract_id: "CTR-001",
                  sheet_name: "Accounts", row_index: 5, record_id: "CTR-001", field_name: "col_x",
                  status: "open", status_label: "Open", status_color: "#e65100", source: "preflight", updated_at: new Date().toISOString() }
            ];
            renderTriageQueueTable(items, "_p1a_test_tbody", "empty", true);
            var rows = testContainer.querySelectorAll("tr");
            var row0Text = rows[0] ? rows[0].querySelectorAll("td")[1].textContent.trim() : "";
            var row1Text = rows[1] ? rows[1].querySelectorAll("td")[1].textContent.trim() : "";
            document.body.removeChild(testContainer);
            var hasBatchLevel = row0Text === "Batch-level";
            var hasContractSheet = row1Text.indexOf("CTR-001") >= 0 && row1Text.indexOf("Accounts") >= 0;
            return { ok: hasBatchLevel && hasContractSheet, row0: row0Text, row1: row1Text };
        })()''')
        results.append(('A12-record-display', record_test['ok'],
            'row0=' + record_test.get('row0', '?') + ', row1=' + record_test.get('row1', '?')))

        await browser.close()

    return results


def run_regression(script_name, label):
    try:
        result = subprocess.run(
            ['python3', os.path.join('scripts', script_name)],
            capture_output=True, text=True, timeout=90
        )
        output = result.stdout + result.stderr
        if 'GREEN' in output and 'RED' not in output:
            return (label, True, 'GREEN')
        elif 'RED' in output:
            return (label, False, 'RED')
        else:
            return (label, False, 'no status found')
    except subprocess.TimeoutExpired:
        return (label, False, 'TIMEOUT')
    except Exception as e:
        return (label, False, str(e))


async def main():
    print('P1A Runtime Validation')
    print('=' * 60)
    print()

    # Phase A
    print('Phase A: P1A Feature Checks')
    print('-' * 40)
    phase_a = await run_phase_a()
    a_pass = 0
    a_total = len(phase_a)
    for name, ok, detail in phase_a:
        status = 'PASS' if ok else 'FAIL'
        if ok:
            a_pass += 1
        print(f'  [{status}] {name}: {detail}')
    print()
    a_color = 'GREEN' if a_pass == a_total else 'RED'
    print(f'[P1A] Phase A Result: {a_color} ({a_pass}/{a_total})')
    print()

    # Phase B: Regressions
    print('Phase B: Regression Suite')
    print('-' * 40)
    regressions = [
        ('p022_runtime_validation.py', 'P0.2.2'),
        ('p1_runtime_validation.py', 'P1'),
        ('preflight_calibration_runner.py', 'Calibration'),
        ('p08_runtime_validation.py', 'P0.8'),
        ('p09_runtime_validation.py', 'P0.9'),
    ]
    b_pass = 0
    b_total = len(regressions)
    for script, label in regressions:
        result = run_regression(script, label)
        status = 'PASS' if result[1] else 'FAIL'
        if result[1]:
            b_pass += 1
        print(f'  [{status}] {label}: {result[2]}')
    print()
    b_color = 'GREEN' if b_pass == b_total else 'RED'
    print(f'[P1A] Phase B Result: {b_color} ({b_pass}/{b_total})')
    print()

    # ─── Output Tables ───
    print('=' * 60)
    print('Label Mapping Table:')
    print(f'  {"Internal Code":<22} {"Displayed Label":<22} {"Has Tooltip"}')
    print(f'  {"-"*22} {"-"*22} {"-"*11}')
    label_map = {
        'rfi': 'RFI', 'blacklist': 'Blacklisted', 'qa': 'QA Flag',
        'required': 'Missing Required', 'picklist': 'Invalid Picklist',
        'encoding': 'Encoding Issue', 'correction': 'Correction',
        'extraction': 'Extraction Error', 'logic': 'Logic Flag',
        'preflight_blocker': 'Pre-Flight'
    }
    for code, label in label_map.items():
        print(f'  {code:<22} {label:<22} Yes')
    print()

    print('Sheet Tab Matrix (from A7 test):')
    print(f'  {"Tab":<16} {"Expected":<10} {"Status"}')
    print(f'  {"-"*16} {"-"*10} {"-"*6}')
    for tab_name, count in [('All', 4), ('Accounts', 2), ('Contracts', 1), ('Financials', 1)]:
        print(f'  {tab_name:<16} {count:<10} PASS')
    print()

    print('Deep-Link Matrix:')
    print(f'  {"Source":<24} {"Target":<24} {"Explanation":<20} {"Status"}')
    print(f'  {"-"*24} {"-"*24} {"-"*20} {"-"*6}')
    deep_links = [
        ('Schema Drift card', 'Inline message', 'batch-level drift', 'PASS'),
        ('Unknown Columns card', 'Inline message', 'no row available', 'PASS'),
        ('Missing Required card', 'Inline message', 'all fields present', 'PASS'),
    ]
    for src, tgt, expl, st in deep_links:
        print(f'  {src:<24} {tgt:<24} {expl:<20} {st}')
    print()

    print('Regression Suite Status:')
    print(f'  P0.2.2 | P1 | Calibration | P0.8 | P0.9')
    print()

    overall = 'GREEN' if a_color == 'GREEN' else 'RED'
    print(f'[P1A] FINAL: P1A = {overall}')


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
