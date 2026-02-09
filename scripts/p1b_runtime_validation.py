#!/usr/bin/env python3
"""
P1B Runtime Validation — Admin QA Runner
Phase A: 15 targeted checks for P1B features
Phase B: Run All suites, verify results table, persistence, regressions
"""

import asyncio, subprocess, sys, json

CHROMIUM_PATH = subprocess.check_output(['which', 'chromium']).decode().strip()
BASE_URL = 'http://127.0.0.1:5000/ui/viewer/index.html'

async def run():
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

        # ─── A2: QARunner module loaded ───
        qa_exists = await page.evaluate('typeof QARunner !== "undefined"')
        results.append(('A2-qarunner-exists', qa_exists, ''))

        # ─── A3: Tab button present ───
        tab_btn = await page.evaluate('!!document.querySelector("[data-admin-tab=qa-runner]")')
        results.append(('A3-tab-button', tab_btn, ''))

        # ─── A4: Tab panel present ───
        tab_panel = await page.evaluate('!!document.getElementById("admin-tab-qa-runner")')
        results.append(('A4-tab-panel', tab_panel, ''))

        # ─── A5: All 6 suite runners exist ───
        suites_check = await page.evaluate('''(function() {
            var fns = ['_runP022','_runP1','_runCalibration','_runP08','_runP09','_runP1A'];
            var missing = [];
            for (var i = 0; i < fns.length; i++) {
                if (typeof QARunner[fns[i]] !== 'function') missing.push(fns[i]);
            }
            return { ok: missing.length === 0, missing: missing };
        })()''')
        results.append(('A5-all-suites', suites_check['ok'], json.dumps(suites_check.get('missing', []))))

        # ─── A6: Set admin mode and switch to QA Runner tab ───
        await page.evaluate('''(function() {
            localStorage.setItem('viewer_mode_v10', 'architect');
            currentMode = 'architect';
        })()''')
        await page.wait_for_timeout(200)
        await page.evaluate('''(function() {
            if (typeof navigateTo === 'function') navigateTo('admin');
        })()''')
        await page.wait_for_timeout(300)
        await page.evaluate('''(function() {
            if (typeof switchAdminTab === 'function') switchAdminTab('qa-runner');
        })()''')
        await page.wait_for_timeout(500)

        tab_visible = await page.evaluate('''(function() {
            var el = document.getElementById('admin-tab-qa-runner');
            return el && el.style.display !== 'none';
        })()''')
        results.append(('A6-tab-visible', tab_visible, ''))

        # ─── A7: Quality lock visible for architect ───
        lock_visible = await page.evaluate('''(function() {
            var el = document.getElementById('p1b-quality-lock');
            return el && el.style.display !== 'none';
        })()''')
        results.append(('A7-quality-lock-visible', lock_visible, ''))

        # ─── A8: Run All suites ───
        run_result = await page.evaluate('''(function() {
            QARunner.runAll();
            var run = QARunner._currentRun;
            if (!run) return { ok: false, reason: 'no current run' };
            return {
                ok: true,
                run_id: run.run_id,
                suite_count: run.suites.length,
                overall: run.overall,
                suites: run.suites.map(function(s) {
                    return { suite: s.suite, pass: s.pass, passed: s.passed, total: s.total };
                })
            };
        })()''')
        results.append(('A8-run-all', run_result['ok'] and run_result.get('suite_count', 0) == 6,
                        'suites=' + str(run_result.get('suite_count', 0))))

        # ─── A9: Results table populated ───
        await page.wait_for_timeout(300)
        result_rows = await page.evaluate('''(function() {
            var tbody = document.getElementById('p1b-results-tbody');
            if (!tbody) return 0;
            return tbody.querySelectorAll('tr').length;
        })()''')
        results.append(('A9-results-table', result_rows >= 6, 'rows=' + str(result_rows)))

        # ─── A10: Individual suite results ───
        suite_details = run_result.get('suites', [])
        all_pass = True
        detail_str = ''
        for s in suite_details:
            detail_str += s['suite'] + ':' + ('PASS' if s['pass'] else 'FAIL') + '(' + str(s['passed']) + '/' + str(s['total']) + ') '
            if not s['pass']:
                all_pass = False
        results.append(('A10-all-suites-pass', all_pass, detail_str))

        # ─── A11: History persisted ───
        await page.wait_for_timeout(500)
        history_check = await page.evaluate('''(function() {
            return QARunner._history.length;
        })()''')
        results.append(('A11-history-saved', history_check >= 1, 'runs=' + str(history_check)))

        # ─── A12: History table rendered ───
        history_rows = await page.evaluate('''(function() {
            var tbody = document.getElementById('p1b-history-tbody');
            if (!tbody) return 0;
            return tbody.querySelectorAll('tr').length;
        })()''')
        results.append(('A12-history-table', history_rows >= 1, 'rows=' + str(history_rows)))

        # ─── A13: Audit events emitted ───
        audit_events = [l for l in logs if 'qa_run_started' in l or 'qa_run_finished' in l]
        results.append(('A13-audit-events', len(audit_events) >= 2, 'events=' + str(len(audit_events))))

        # ─── A14: Quality lock toggle works ───
        lock_result = await page.evaluate('''(function() {
            QARunner.toggleQualityLock(true);
            var locked = QARunner._currentRun ? QARunner._currentRun.locked : false;
            return locked;
        })()''')
        results.append(('A14-quality-lock', lock_result, ''))

        # ─── A15: Persistence survives reload ───
        await page.wait_for_timeout(500)
        await page.reload(wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        await page.evaluate('''(function() {
            localStorage.setItem('viewer_mode_v10', 'architect');
            currentMode = 'architect';
        })()''')
        await page.wait_for_timeout(200)
        await page.evaluate('''(function() {
            if (typeof navigateTo === 'function') navigateTo('admin');
        })()''')
        await page.wait_for_timeout(300)
        await page.evaluate('''(function() {
            if (typeof switchAdminTab === 'function') switchAdminTab('qa-runner');
        })()''')
        await page.wait_for_timeout(1500)

        persist_check = await page.evaluate('''(function() {
            return QARunner._history.length;
        })()''')
        results.append(('A15-persistence', persist_check >= 1, 'runs_after_reload=' + str(persist_check)))

        await browser.close()

    # ── Report ──
    print('=' * 70)
    print('[P1B] RUNTIME VALIDATION RESULTS')
    print('=' * 70)
    passed = 0
    failed = 0
    for name, ok, detail in results:
        status = 'PASS' if ok else 'FAIL'
        if ok:
            passed += 1
        else:
            failed += 1
        print('  [%s] %s  %s' % (status, name, detail))

    print('-' * 70)
    overall = 'GREEN' if failed == 0 else 'RED'
    print('[P1B] FINAL: %s (%d/%d passed)' % (overall, passed, len(results)))
    print('=' * 70)

    return failed == 0

if __name__ == '__main__':
    ok = asyncio.get_event_loop().run_until_complete(run())
    sys.exit(0 if ok else 1)
