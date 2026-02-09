#!/usr/bin/env python3
"""P1D Runtime Validation: Contract-Centric Pre-Flight Grouping
Verifies grouped rendering, view routing, sheet filters, and no regressions.
"""
import asyncio, subprocess, json, sys

CHROMIUM_PATH = subprocess.check_output(['which', 'chromium']).decode().strip()
URL = 'http://127.0.0.1:5000/ui/viewer/index.html'
RESULTS = []

def report(name, passed, detail=''):
    tag = 'PASS' if passed else 'FAIL'
    RESULTS.append({'name': name, 'passed': passed, 'detail': detail})
    d = '  ' + detail if detail else ''
    print(f'  [{tag}] {name}{d}')

# Test data: 3 contracts, multiple sheets, various blocker types
SEED_SCRIPT = """(function() {
    var sheets = {
        'Accounts': {
            headers: ['contract_key', 'file_name', 'file_url', 'status', 'amount', 'name'],
            rows: [
                { contract_key: 'CK-001', file_name: 'contract_alpha.pdf', file_url: 'https://docs.example.com/contract_alpha.pdf', status: 'blocked', amount: '1000', name: 'Alpha Corp' },
                { contract_key: 'CK-001', file_name: 'contract_alpha.pdf', file_url: 'https://docs.example.com/contract_alpha.pdf', status: 'ready', amount: '2000', name: 'Alpha Corp' },
                { contract_key: 'CK-002', file_name: 'contract_beta.pdf', file_url: 'https://storage.example.com/contract_beta.pdf', status: 'needs_review', amount: '3000', name: 'Beta LLC' },
                { contract_key: 'CK-003', file_name: 'contract_gamma.pdf', file_url: '', status: 'ready', amount: '4000', name: 'Gamma Inc' }
            ]
        },
        'Opportunities': {
            headers: ['contract_key', 'file_name', 'file_url', 'status', 'opp_name'],
            rows: [
                { contract_key: 'CK-001', file_name: 'contract_alpha.pdf', file_url: 'https://docs.example.com/contract_alpha.pdf', status: 'blocked', opp_name: 'Deal A' },
                { contract_key: 'CK-002', file_name: 'contract_beta.pdf', file_url: 'https://storage.example.com/contract_beta.pdf', status: 'ready', opp_name: 'Deal B' },
                { contract_key: 'CK-002', file_name: 'contract_beta.pdf', file_url: 'https://storage.example.com/contract_beta.pdf', status: 'needs_review', opp_name: 'Deal C' }
            ]
        },
        'Financials': {
            headers: ['contract_key', 'file_name', 'file_url', 'status', 'revenue'],
            rows: [
                { contract_key: 'CK-001', file_name: 'contract_alpha.pdf', file_url: 'https://docs.example.com/contract_alpha.pdf', status: 'ready', revenue: '50000' },
                { contract_key: 'CK-003', file_name: 'contract_gamma.pdf', file_url: '', status: 'blocked', revenue: '60000' }
            ]
        }
    };
    workbook.sheets = sheets;
    workbook.order = ['Accounts', 'Opportunities', 'Financials'];
    workbook.activeSheet = 'Accounts';
    dataLoaded = true;
    if (typeof ContractIndex !== 'undefined' && typeof ContractIndex.rebuild === 'function') ContractIndex.rebuild();

    var testItems = [
        { request_id: 'pf_1', type: 'preflight_blocker', signal_type: 'UNKNOWN_COLUMN', record_id: 'CK-001', contract_id: 'CK-001', contract_key: 'CK-001', field_name: 'unknown_col_1', field_key: 'unknown_col_1', sheet_name: 'Accounts', severity: 'blocker', message: 'Unknown column', status: 'open', status_label: 'Open', status_color: '#f57c00', updated_at: new Date().toISOString(), source: 'preflight', blocker_type: 'UNKNOWN_COLUMN', can_create_patch: true, file_name: 'contract_alpha.pdf', file_url: 'https://docs.example.com/contract_alpha.pdf' },
        { request_id: 'pf_2', type: 'preflight_blocker', signal_type: 'MISSING_REQUIRED', record_id: 'CK-001', contract_id: 'CK-001', contract_key: 'CK-001', field_name: 'revenue', field_key: 'revenue', sheet_name: 'Financials', severity: 'blocker', message: 'Missing required', status: 'open', status_label: 'Open', status_color: '#f57c00', updated_at: new Date().toISOString(), source: 'preflight', blocker_type: 'MISSING_REQUIRED', can_create_patch: true, file_name: 'contract_alpha.pdf', file_url: 'https://docs.example.com/contract_alpha.pdf' },
        { request_id: 'pf_3', type: 'preflight_blocker', signal_type: 'UNKNOWN_COLUMN', record_id: 'CK-001', contract_id: 'CK-001', contract_key: 'CK-001', field_name: 'unknown_col_2', field_key: 'unknown_col_2', sheet_name: 'Accounts', severity: 'warning', message: 'Unknown column 2', status: 'open', status_label: 'Open', status_color: '#f57c00', updated_at: new Date().toISOString(), source: 'preflight', blocker_type: 'UNKNOWN_COLUMN', can_create_patch: true, file_name: 'contract_alpha.pdf', file_url: 'https://docs.example.com/contract_alpha.pdf' },
        { request_id: 'pf_4', type: 'preflight_blocker', signal_type: 'PICKLIST_INVALID', record_id: 'CK-002', contract_id: 'CK-002', contract_key: 'CK-002', field_name: 'status_field', field_key: 'status_field', sheet_name: 'Opportunities', severity: 'warning', message: 'Invalid picklist', status: 'open', status_label: 'Open', status_color: '#f57c00', updated_at: new Date().toISOString(), source: 'preflight', blocker_type: 'PICKLIST_INVALID', can_create_patch: false, file_name: 'contract_beta.pdf', file_url: 'https://storage.example.com/contract_beta.pdf' },
        { request_id: 'pf_5', type: 'preflight_blocker', signal_type: 'UNKNOWN_COLUMN', record_id: 'CK-002', contract_id: 'CK-002', contract_key: 'CK-002', field_name: 'extra_col', field_key: 'extra_col', sheet_name: 'Accounts', severity: 'blocker', message: 'Unknown column', status: 'open', status_label: 'Open', status_color: '#f57c00', updated_at: new Date().toISOString(), source: 'preflight', blocker_type: 'UNKNOWN_COLUMN', can_create_patch: true, file_name: 'contract_beta.pdf', file_url: 'https://storage.example.com/contract_beta.pdf' },
        { request_id: 'pf_6', type: 'preflight_blocker', signal_type: 'DOCUMENT_TYPE_MISSING', record_id: 'CK-003', contract_id: 'CK-003', contract_key: 'CK-003', field_name: '_document_type', field_key: '_document_type', sheet_name: 'Accounts', severity: 'blocker', message: 'Doc type missing', status: 'open', status_label: 'Open', status_color: '#f57c00', updated_at: new Date().toISOString(), source: 'preflight', blocker_type: 'DOCUMENT_TYPE_MISSING', can_create_patch: false, file_name: 'contract_gamma.pdf' },
        { request_id: 'pf_7', type: 'preflight_blocker', signal_type: 'MISSING_REQUIRED', record_id: 'CK-003', contract_id: 'CK-003', contract_key: 'CK-003', field_name: 'name', field_key: 'name', sheet_name: 'Financials', severity: 'blocker', message: 'Missing required', status: 'open', status_label: 'Open', status_color: '#f57c00', updated_at: new Date().toISOString(), source: 'preflight', blocker_type: 'MISSING_REQUIRED', can_create_patch: true, file_name: 'contract_gamma.pdf' },
        { request_id: 'pf_8', type: 'preflight_blocker', signal_type: 'UNKNOWN_COLUMN', record_id: 'CK-001', contract_id: 'CK-001', contract_key: 'CK-001', field_name: 'unknown_col_3', field_key: 'unknown_col_3', sheet_name: 'Opportunities', severity: 'warning', message: 'Unknown column 3', status: 'open', status_label: 'Open', status_color: '#f57c00', updated_at: new Date().toISOString(), source: 'preflight', blocker_type: 'UNKNOWN_COLUMN', can_create_patch: true, file_name: 'contract_alpha.pdf', file_url: 'https://docs.example.com/contract_alpha.pdf' }
    ];

    // Seed items into manualItems, then call renderAnalystTriage.
    // loadAnalystTriageFromStore will overwrite manualItems from store, then append
    // ContractIndex preflight items. We need to inject AFTER that reload.
    // So: call renderAnalystTriage first (initializes store), then append + re-render P1D.
    renderAnalystTriage();
    analystTriageState.manualItems = analystTriageState.manualItems.concat(testItems);
    _p1aBuildSheetTabs(analystTriageState.manualItems);
    var filtered = _p1aFilterBySheet(analystTriageState.manualItems);
    _p1dRenderGrouped(filtered, 'p1d-preflight-container');
})()"""

async def run():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, executable_path=CHROMIUM_PATH,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        page = await browser.new_page()
        errors = []
        logs = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda msg: logs.append(msg.text))

        await page.goto(URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        # A1: No JS errors
        js_errs = [e for e in errors if any(k in e for k in ['SyntaxError', 'ReferenceError'])]
        report('A1-no-js-errors', len(js_errs) == 0, f'errors={len(js_errs)}')

        # A2: P1D functions exist
        fns_ok = await page.evaluate("""(function() {
            return typeof _p1dRenderGrouped === 'function' &&
                   typeof _p1dToggleGroup === 'function' &&
                   typeof _p1dGetGroupKey === 'function' &&
                   typeof _p1dGetDisplayName === 'function' &&
                   typeof _p1dGetDomainHint === 'function';
        })()""")
        report('A2-p1d-functions', fns_ok)

        # A3: Container exists
        container = await page.evaluate("!!document.getElementById('p1d-preflight-container')")
        report('A3-container-exists', container)

        # Seed test data
        await page.evaluate(SEED_SCRIPT)
        await page.wait_for_timeout(1000)

        # A4: Groups rendered
        group_info = await page.evaluate("""(function() {
            var groups = document.querySelectorAll('.p1d-group');
            var result = [];
            for (var i = 0; i < groups.length; i++) {
                var g = groups[i];
                var name = g.querySelector('.p1d-group-name');
                var count = g.querySelector('.p1d-group-count');
                var chips = g.querySelectorAll('.p1d-sheet-chip');
                var rows = g.querySelectorAll('tbody tr');
                var key = g.getAttribute('data-group-key');
                result.push({
                    key: key,
                    name: name ? name.textContent : '',
                    count: count ? count.textContent : '',
                    chipCount: chips.length,
                    rowCount: rows.length
                });
            }
            return result;
        })()""")
        report('A4-groups-rendered', len(group_info) == 3, f'groups={len(group_info)}')

        # A5: Group 1 (CK-001) has most issues (4)
        ck001 = next((g for g in group_info if g['key'] == 'CK-001'), None)
        report('A5-ck001-group', ck001 is not None and ck001['rowCount'] == 4,
               f"rows={ck001['rowCount'] if ck001 else 0} chips={ck001['chipCount'] if ck001 else 0}")

        # A6: Group has per-sheet chips
        has_chips = all(g['chipCount'] >= 1 for g in group_info)
        report('A6-sheet-chips', has_chips, json.dumps([{'key': g['key'], 'chips': g['chipCount']} for g in group_info]))

        # A7: Group headers show display name (not raw ID as primary)
        names_ok = all(g['name'] for g in group_info)
        report('A7-display-names', names_ok, json.dumps([{'key': g['key'], 'name': g['name']} for g in group_info]))

        # A8: Domain hint shown for groups with URLs
        domain_hints = await page.evaluate("""(function() {
            var hints = document.querySelectorAll('.p1d-domain-hint');
            var result = [];
            for (var i = 0; i < hints.length; i++) {
                result.push(hints[i].textContent);
            }
            return result;
        })()""")
        report('A8-domain-hints', len(domain_hints) >= 1, f'hints={domain_hints}')

        # A9: Issue rows have correct columns (Sheet, Field, Reason, Severity, Status, Actions)
        cols = await page.evaluate("""(function() {
            var g = document.querySelector('.p1d-group');
            if (!g) return [];
            var ths = g.querySelectorAll('thead th');
            var result = [];
            for (var i = 0; i < ths.length; i++) result.push(ths[i].textContent);
            return result;
        })()""")
        expected_cols = ['Sheet', 'Field', 'Reason', 'Severity', 'Status', 'Actions']
        report('A9-issue-columns', cols == expected_cols, str(cols))

        # A10: View buttons exist and route correctly
        view_btns = await page.evaluate("""(function() {
            var btns = document.querySelectorAll('.p1d-group-body button');
            var viewBtns = [];
            for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.trim() === 'View') {
                    var onclick = btns[i].getAttribute('onclick') || btns[i].onclick;
                    viewBtns.push({ text: btns[i].textContent.trim(), hasHandler: !!onclick });
                }
            }
            return viewBtns;
        })()""")
        report('A10-view-buttons', len(view_btns) >= 5 and all(v['hasHandler'] for v in view_btns),
               f'count={len(view_btns)}')

        # A11: Collapse group
        await page.evaluate("_p1dToggleGroup('p1d-g-0')")
        await page.wait_for_timeout(200)
        collapsed = await page.evaluate("""(function() {
            var g = document.querySelector('.p1d-group[data-group-id=\"p1d-g-0\"]');
            if (!g) return false;
            var body = g.querySelector('.p1d-group-body');
            return body && body.classList.contains('collapsed');
        })()""")
        report('A11-collapse-group', collapsed)

        # A12: Expand group back
        await page.evaluate("_p1dToggleGroup('p1d-g-0')")
        await page.wait_for_timeout(200)
        expanded = await page.evaluate("""(function() {
            var g = document.querySelector('.p1d-group[data-group-id=\"p1d-g-0\"]');
            if (!g) return false;
            var body = g.querySelector('.p1d-group-body');
            return body && !body.classList.contains('collapsed');
        })()""")
        report('A12-expand-group', expanded)

        # A13: Sheet tab filter - Accounts only (use direct filter + render to avoid store reload)
        acct_groups = await page.evaluate("""(function() {
            _p1aActiveSheet = 'Accounts';
            var filtered = _p1aFilterBySheet(analystTriageState.manualItems);
            _p1dRenderGrouped(filtered, 'p1d-preflight-container');
            var groups = document.querySelectorAll('.p1d-group');
            var totalRows = 0;
            for (var i = 0; i < groups.length; i++) {
                totalRows += groups[i].querySelectorAll('tbody tr').length;
            }
            return { groupCount: groups.length, totalRows: totalRows };
        })()""")
        report('A13-sheet-filter-accounts', acct_groups['totalRows'] == 4,
               f"groups={acct_groups['groupCount']} rows={acct_groups['totalRows']}")

        # A14: Sheet tab filter - Financials only
        fin_groups = await page.evaluate("""(function() {
            _p1aActiveSheet = 'Financials';
            var filtered = _p1aFilterBySheet(analystTriageState.manualItems);
            _p1dRenderGrouped(filtered, 'p1d-preflight-container');
            var groups = document.querySelectorAll('.p1d-group');
            var totalRows = 0;
            for (var i = 0; i < groups.length; i++) {
                totalRows += groups[i].querySelectorAll('tbody tr').length;
            }
            return { groupCount: groups.length, totalRows: totalRows };
        })()""")
        report('A14-sheet-filter-financials', fin_groups['totalRows'] == 2,
               f"groups={fin_groups['groupCount']} rows={fin_groups['totalRows']}")

        # A15: Sheet tab filter - All restores all items
        all_groups = await page.evaluate("""(function() {
            _p1aActiveSheet = 'All';
            var filtered = _p1aFilterBySheet(analystTriageState.manualItems);
            _p1dRenderGrouped(filtered, 'p1d-preflight-container');
            var groups = document.querySelectorAll('.p1d-group');
            var totalRows = 0;
            for (var i = 0; i < groups.length; i++) {
                totalRows += groups[i].querySelectorAll('tbody tr').length;
            }
            return { groupCount: groups.length, totalRows: totalRows };
        })()""")
        report('A15-sheet-filter-all', all_groups['totalRows'] == 8,
               f"groups={all_groups['groupCount']} rows={all_groups['totalRows']}")

        # A16: Console logs (P1D uses [P1D-PREFLIGHT], sheet tabs use [P1A])
        p1d_logs = [l for l in logs if '[P1D-PREFLIGHT]' in l]
        p1a_logs = [l for l in logs if '[P1A]' in l]
        has_group_rendered = any('group_rendered' in l for l in p1d_logs)
        has_group_toggled = any('group_toggled' in l for l in p1d_logs)
        has_sheet_tabs = any('sheet_tabs_built' in l for l in p1a_logs) or any('total_groups' in l for l in p1d_logs)
        report('A16-console-logs', has_group_rendered and has_group_toggled and has_sheet_tabs,
               f"p1d={len(p1d_logs)} rendered={has_group_rendered} toggled={has_group_toggled} tabs={has_sheet_tabs}")

        # A17: Reason column shows human labels (not raw IDs)
        # Re-render all items first since sheet filter changed state
        await page.evaluate("""(function() {
            _p1aActiveSheet = 'All';
            var filtered = _p1aFilterBySheet(analystTriageState.manualItems);
            _p1dRenderGrouped(filtered, 'p1d-preflight-container');
        })()""")
        await page.wait_for_timeout(200)
        reason_labels = await page.evaluate("""(function() {
            var tds = document.querySelectorAll('.p1d-group-body td');
            var result = [];
            for (var i = 0; i < tds.length; i++) {
                var span = tds[i].querySelector('span[title]');
                if (span && span.getAttribute('style') && span.getAttribute('style').indexOf('fff3e0') >= 0) {
                    result.push(span.textContent.trim());
                }
            }
            return result;
        })()""")
        all_human = len(reason_labels) > 0 and all(r and r != 'UNKNOWN_COLUMN' and r != 'MISSING_REQUIRED' for r in reason_labels)
        report('A17-human-reason-labels', all_human,
               str(reason_labels[:5]))

        # A18: Severity column present with color coding
        sev_spans = await page.evaluate("""(function() {
            var tds = document.querySelectorAll('.p1d-group-body td');
            var result = [];
            for (var i = 0; i < tds.length; i++) {
                var span = tds[i].querySelector('span[style*="font-weight"]');
                if (span && span.textContent.trim().match(/^(Blocker|Warning|Info)$/)) {
                    result.push(span.textContent.trim());
                }
            }
            return result;
        })()""")
        report('A18-severity-column', len(sev_spans) >= 3, str(sev_spans[:5]))

        # A19: Default collapse for groups after 5th
        # We have only 3 groups, so all should be expanded
        all_expanded_check = await page.evaluate("""(function() {
            var groups = document.querySelectorAll('.p1d-group');
            for (var i = 0; i < groups.length; i++) {
                var body = groups[i].querySelector('.p1d-group-body');
                if (body && body.classList.contains('collapsed') && i < 5) return false;
            }
            return true;
        })()""")
        report('A19-default-expand-first-5', all_expanded_check)

        # ── A20-A27: Regression suites ──
        page2 = await browser.new_page()
        await page2.goto(URL, wait_until='networkidle', timeout=30000)
        await page2.wait_for_timeout(3000)
        await page2.evaluate("""(function() {
            var sheets = {
                'Schedule A': { headers: ['contract_key','file_name','file_url','status','amount'],
                    rows: [{ contract_key:'CK-001', file_name:'doc1.pdf', file_url:'', status:'ready', amount:'100' }] },
                'Schedule B': { headers: ['contract_key','file_name','file_url','status','amount'],
                    rows: [{ contract_key:'CK-001', file_name:'doc1.pdf', file_url:'', status:'ready', amount:'200' }] }
            };
            workbook.sheets = sheets; workbook.order = ['Schedule A','Schedule B'];
            workbook.activeSheet = 'Schedule A'; dataLoaded = true;
            if (typeof ContractIndex !== 'undefined' && typeof ContractIndex.rebuild === 'function') ContractIndex.rebuild();
        })()""")
        await page2.wait_for_timeout(500)

        suite_fns = {
            'p022': '_runP022', 'p1': '_runP1', 'calibration': '_runCalibration',
            'p08': '_runP08', 'p09': '_runP09', 'p1a': '_runP1A'
        }
        suites = ['p022', 'p1', 'calibration', 'p08', 'p09', 'p1a']
        for idx, suite in enumerate(suites):
            fn = suite_fns[suite]
            try:
                s = await page2.evaluate("""(function() {
                    var checks = QARunner.""" + fn + """();
                    var pass_count = 0, fail_count = 0;
                    for (var i = 0; i < checks.length; i++) {
                        if (checks[i].pass) pass_count++; else fail_count++;
                    }
                    return { result: fail_count === 0 ? 'PASS' : 'FAIL', pass_count: pass_count, fail_count: fail_count };
                })()""")
                passed = s.get('result') == 'PASS'
                detail = f"{s.get('pass_count',0)}/{s.get('pass_count',0)+s.get('fail_count',0)}"
                report(f'A{20+idx}-regression-{suite}', passed, detail)
            except Exception as e:
                report(f'A{20+idx}-regression-{suite}', False, f'error: {str(e)[:100]}')

        # A26: P1C regression (composite grid functions)
        p1c_ok = await page2.evaluate("typeof _p1cIsCompositeMode === 'function' && typeof _p1cRenderComposite === 'function'")
        report('A26-regression-p1c', p1c_ok)

        # A27: P1B regression (QA Runner)
        p1b_ok = await page2.evaluate("typeof QARunner !== 'undefined' && typeof QARunner.runAll === 'function'")
        report('A27-regression-p1b', p1b_ok)

        await page2.close()
        await page.close()
        await browser.close()

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r['passed'])
    failed = total - passed
    print('=' * 70)
    print(f'[P1D] FINAL: {"GREEN" if failed == 0 else "RED"} ({passed}/{total} passed)')
    if failed > 0:
        print('FAILURES:')
        for r in RESULTS:
            if not r['passed']:
                print(f'  - {r["name"]}: {r["detail"]}')
    print('=' * 70)
    return failed == 0

if __name__ == '__main__':
    print('=' * 70)
    print('[P1D] RUNTIME VALIDATION RESULTS')
    print('=' * 70)
    ok = asyncio.get_event_loop().run_until_complete(run())
    sys.exit(0 if ok else 1)
