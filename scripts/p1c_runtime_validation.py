#!/usr/bin/env python3
"""P1C Runtime Validation: Contract Composite Grid
Verifies composite mode triggers, section rendering, SRR routing,
filter/search behavior, and no regressions to prior suites.
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

        # ── A1: No JS errors ──
        js_errs = [e for e in errors if any(k in e for k in ['SyntaxError', 'ReferenceError'])]
        report('A1-no-js-errors', len(js_errs) == 0, f'errors={len(js_errs)}')

        # ── A2: P1C functions exist ──
        fns_ok = await page.evaluate("""(function() {
            return typeof _p1cIsCompositeMode === 'function' &&
                   typeof _p1cRenderComposite === 'function' &&
                   typeof _p1cToggleSection === 'function' &&
                   typeof _p1cExpandAll === 'function' &&
                   typeof _p1cCollapseAll === 'function';
        })()""")
        report('A2-p1c-functions', fns_ok)

        # ── A3: Composite controls in DOM, hidden by default ──
        ctrl_hidden = await page.evaluate("""(function() {
            var el = document.getElementById('p1c-composite-controls');
            return el && el.style.display === 'none';
        })()""")
        report('A3-controls-hidden', ctrl_hidden)

        # ── Load test data via workbook ──
        await page.evaluate("""(function() {
            var sheets = {
                'Schedule A': {
                    headers: ['contract_key', 'file_name', 'file_url', 'status', 'amount'],
                    rows: [
                        { contract_key: 'CK-001', file_name: 'doc1.pdf', file_url: 'http://example.com/doc1.pdf', status: 'ready', amount: '100' },
                        { contract_key: 'CK-001', file_name: 'doc1.pdf', file_url: 'http://example.com/doc1.pdf', status: 'needs_review', amount: '200' },
                        { contract_key: 'CK-002', file_name: 'doc2.pdf', file_url: '', status: 'blocked', amount: '300' }
                    ]
                },
                'Schedule B': {
                    headers: ['contract_key', 'file_name', 'file_url', 'status', 'amount'],
                    rows: [
                        { contract_key: 'CK-001', file_name: 'doc1.pdf', file_url: 'http://example.com/doc1.pdf', status: 'ready', amount: '400' },
                        { contract_key: 'CK-001', file_name: 'doc1.pdf', file_url: 'http://example.com/doc1.pdf', status: 'ready', amount: '500' }
                    ]
                },
                'Schedule C': {
                    headers: ['contract_key', 'file_name', 'file_url', 'status', 'amount'],
                    rows: [
                        { contract_key: 'CK-002', file_name: 'doc2.pdf', file_url: '', status: 'needs_review', amount: '600' }
                    ]
                }
            };
            workbook.sheets = sheets;
            workbook.order = ['Schedule A', 'Schedule B', 'Schedule C'];
            workbook.activeSheet = 'Schedule A';
            dataLoaded = true;

            if (typeof ContractIndex !== 'undefined' && typeof ContractIndex.rebuild === 'function') {
                ContractIndex.rebuild();
            }
        })()""")
        await page.wait_for_timeout(500)

        # Navigate to grid page
        await page.evaluate("navigateTo('grid')")
        await page.wait_for_timeout(1000)

        # ── A4: Composite mode NOT active when sheet is selected ──
        not_composite = await page.evaluate("""(function() {
            return !_p1cIsCompositeMode();
        })()""")
        report('A4-not-composite-with-sheet', not_composite)

        # ── Set contract filter and All Sheets ──
        await page.evaluate("""(function() {
            // Get first contract ID
            var contracts = ContractIndex.isAvailable() ? ContractIndex.listContracts() : [];
            if (contracts.length > 0) {
                _activeContractFilter = contracts[0].contract_id;
            } else {
                // Fallback: derive from data
                var ds = getGridDataset();
                if (ds && ds.sf_contract_results && ds.sf_contract_results.length > 0) {
                    var r = ds.sf_contract_results[0];
                    _activeContractFilter = ContractIndex.isAvailable() ? ContractIndex.deriveContractId(r) : 'CK-001';
                }
            }
            // Set sheet to All Sheets
            gridState.sheet = null;
            var sel = document.getElementById('grid-sheet-selector');
            if (sel) sel.value = '';
            renderGrid();
        })()""")
        await page.wait_for_timeout(1000)

        # ── A5: Composite mode IS active ──
        is_composite = await page.evaluate("_p1cIsCompositeMode()")
        report('A5-composite-mode-active', is_composite)

        # ── A6: Composite controls visible ──
        ctrl_visible = await page.evaluate("""(function() {
            var el = document.getElementById('p1c-composite-controls');
            return el && el.style.display !== 'none';
        })()""")
        report('A6-controls-visible', ctrl_visible)

        # ── A7: Multiple sections rendered ──
        section_info = await page.evaluate("""(function() {
            var sections = document.querySelectorAll('.p1c-section');
            var names = [];
            for (var i = 0; i < sections.length; i++) {
                names.push(sections[i].getAttribute('data-sheet-name'));
            }
            return { count: sections.length, names: names };
        })()""")
        report('A7-sections-rendered', section_info['count'] >= 2,
               f"sections={section_info['count']} sheets={section_info['names']}")

        # ── A8: Each section has header with row count and status chips ──
        section_details = await page.evaluate("""(function() {
            var sections = document.querySelectorAll('.p1c-section');
            var results = [];
            for (var i = 0; i < sections.length; i++) {
                var header = sections[i].querySelector('.p1c-section-header');
                var title = sections[i].querySelector('.p1c-section-title');
                var count = sections[i].querySelector('.p1c-section-count');
                var chips = sections[i].querySelectorAll('.p1c-section-chip');
                var rows = sections[i].querySelectorAll('tbody tr');
                results.push({
                    sheet: title ? title.textContent : '',
                    countLabel: count ? count.textContent : '',
                    chipCount: chips.length,
                    rowCount: rows.length
                });
            }
            return results;
        })()""")
        all_have_headers = all(s['sheet'] and s['countLabel'] and s['rowCount'] > 0 for s in section_details)
        report('A8-section-headers', all_have_headers,
               json.dumps(section_details))

        # ── A9: Original table hidden in composite mode ──
        orig_hidden = await page.evaluate("""(function() {
            var t = document.getElementById('grid-table');
            return t && t.style.display === 'none';
        })()""")
        report('A9-orig-table-hidden', orig_hidden)

        # ── A10: Row click -> SRR routing ──
        srr_results = await page.evaluate("""(function() {
            var sections = document.querySelectorAll('.p1c-section');
            var results = [];
            for (var i = 0; i < sections.length; i++) {
                var firstRow = sections[i].querySelector('tbody tr.clickable');
                if (firstRow) {
                    var sheet = firstRow.getAttribute('data-sheet-name');
                    var idx = firstRow.getAttribute('data-record-index');
                    results.push({ sheet: sheet, index: idx, hasOnclick: typeof firstRow.onclick === 'function' });
                }
            }
            return results;
        })()""")
        all_clickable = len(srr_results) >= 2 and all(r['hasOnclick'] for r in srr_results)
        report('A10-row-click-srr', all_clickable,
               f"clickable_rows={len(srr_results)}")

        # ── A11: Collapse All ──
        await page.evaluate("_p1cCollapseAll()")
        await page.wait_for_timeout(300)
        all_collapsed = await page.evaluate("""(function() {
            var bodies = document.querySelectorAll('.p1c-section-body');
            for (var i = 0; i < bodies.length; i++) {
                if (!bodies[i].classList.contains('collapsed')) return false;
            }
            return bodies.length > 0;
        })()""")
        report('A11-collapse-all', all_collapsed)

        # ── A12: Expand All ──
        await page.evaluate("_p1cExpandAll()")
        await page.wait_for_timeout(300)
        all_expanded = await page.evaluate("""(function() {
            var bodies = document.querySelectorAll('.p1c-section-body');
            for (var i = 0; i < bodies.length; i++) {
                if (bodies[i].classList.contains('collapsed')) return false;
            }
            return bodies.length > 0;
        })()""")
        report('A12-expand-all', all_expanded)

        # ── A13: Toggle individual section ──
        await page.evaluate("_p1cToggleSection('p1c-sheet-0')")
        await page.wait_for_timeout(200)
        toggled = await page.evaluate("""(function() {
            var sec = document.querySelector('.p1c-section[data-section-id=\"p1c-sheet-0\"]');
            if (!sec) return false;
            var body = sec.querySelector('.p1c-section-body');
            return body && body.classList.contains('collapsed');
        })()""")
        report('A13-toggle-section', toggled)
        # Expand back
        await page.evaluate("_p1cToggleSection('p1c-sheet-0')")

        # ── A14: Status filter in composite mode ──
        await page.evaluate("""(function() {
            gridState.filter = 'ready';
            renderGrid();
        })()""")
        await page.wait_for_timeout(500)
        filter_result = await page.evaluate("""(function() {
            var sections = document.querySelectorAll('.p1c-section');
            var totalRows = 0;
            for (var i = 0; i < sections.length; i++) {
                totalRows += sections[i].querySelectorAll('tbody tr').length;
            }
            return { sections: sections.length, rows: totalRows };
        })()""")
        # CK-001 has ready rows in Schedule A (1) and Schedule B (2) = 3 ready
        report('A14-status-filter', filter_result['rows'] > 0 and filter_result['rows'] <= 5,
               f"sections={filter_result['sections']} rows={filter_result['rows']}")

        # Reset filter
        await page.evaluate("""(function() {
            gridState.filter = 'all';
            renderGrid();
        })()""")
        await page.wait_for_timeout(300)

        # ── A15: Search filter in composite mode ──
        await page.evaluate("""(function() {
            gridState.search = '400';
            renderGrid();
        })()""")
        await page.wait_for_timeout(500)
        search_result = await page.evaluate("""(function() {
            var sections = document.querySelectorAll('.p1c-section');
            var totalRows = 0;
            for (var i = 0; i < sections.length; i++) {
                totalRows += sections[i].querySelectorAll('tbody tr').length;
            }
            return { sections: sections.length, rows: totalRows };
        })()""")
        report('A15-search-filter', search_result['rows'] >= 1,
               f"sections={search_result['sections']} rows={search_result['rows']}")

        # Reset search
        await page.evaluate("""(function() {
            gridState.search = '';
            renderGrid();
        })()""")
        await page.wait_for_timeout(300)

        # ── A16: Exiting composite mode (set specific sheet) ──
        await page.evaluate("""(function() {
            gridState.sheet = 'Schedule A';
            renderGrid();
        })()""")
        await page.wait_for_timeout(500)
        exit_composite = await page.evaluate("""(function() {
            var composite = document.getElementById('p1c-composite-root');
            var origTable = document.getElementById('grid-table');
            var ctrl = document.getElementById('p1c-composite-controls');
            return {
                compositeGone: !composite,
                tableVisible: origTable && origTable.style.display !== 'none',
                controlsHidden: ctrl && ctrl.style.display === 'none'
            };
        })()""")
        mode_disabled = exit_composite.get('tableVisible', False) and exit_composite.get('controlsHidden', False)
        report('A16-mode-disabled', mode_disabled, json.dumps(exit_composite))

        # ── A17: Console logs ──
        p1c_logs = [l for l in logs if '[GRID-COMPOSITE][P1C]' in l]
        has_mode_enabled = any('mode_enabled' in l for l in p1c_logs)
        has_section_rendered = any('section_rendered' in l for l in p1c_logs)
        has_section_toggled = any('section_toggled' in l for l in p1c_logs)
        has_mode_disabled = any('mode_disabled' in l for l in p1c_logs)
        report('A17-console-logs', has_mode_enabled and has_section_rendered and has_section_toggled,
               f"total={len(p1c_logs)} enabled={has_mode_enabled} rendered={has_section_rendered} toggled={has_section_toggled}")

        # ── A18: Empty state when no rows match ──
        await page.evaluate("""(function() {
            gridState.sheet = null;
            gridState.search = 'XYZNONEXISTENT';
            renderGrid();
        })()""")
        await page.wait_for_timeout(300)
        empty_state = await page.evaluate("""(function() {
            var root = document.getElementById('p1c-composite-root');
            if (!root) return false;
            return root.textContent.indexOf('No records match') >= 0;
        })()""")
        report('A18-empty-state', empty_state)

        # Reset
        await page.evaluate("""(function() {
            gridState.search = '';
            _activeContractFilter = '';
            gridState.sheet = 'Schedule A';
            renderGrid();
        })()""")
        await page.wait_for_timeout(300)

        # ── A19: Footer shows composite count ──
        await page.evaluate("""(function() {
            _activeContractFilter = ContractIndex.isAvailable() ? ContractIndex.listContracts()[0].contract_id : 'CK-001';
            gridState.sheet = null;
            renderGrid();
        })()""")
        await page.wait_for_timeout(300)
        footer = await page.evaluate("document.getElementById('grid-row-count').textContent")
        report('A19-footer-composite', 'composite' in footer and 'sheets' in footer, footer)

        # Reset for regression tests
        await page.evaluate("""(function() {
            _activeContractFilter = '';
            gridState.sheet = 'Schedule A';
            gridState.filter = 'all';
            gridState.search = '';
            renderGrid();
        })()""")
        await page.wait_for_timeout(300)

        # ── A20-A25: Regression suite (QA Runner) ──
        # Run check functions directly (bypasses role gate, no hash navigation)
        page2 = await browser.new_page()
        await page2.goto(URL, wait_until='networkidle', timeout=30000)
        await page2.wait_for_timeout(3000)
        await page2.evaluate("""(function() {
            var sheets = {
                'Schedule A': { headers: ['contract_key','file_name','file_url','status','amount'],
                    rows: [{ contract_key:'CK-001', file_name:'doc1.pdf', file_url:'', status:'ready', amount:'100' },
                           { contract_key:'CK-001', file_name:'doc1.pdf', file_url:'', status:'needs_review', amount:'200' }] },
                'Schedule B': { headers: ['contract_key','file_name','file_url','status','amount'],
                    rows: [{ contract_key:'CK-001', file_name:'doc1.pdf', file_url:'', status:'ready', amount:'300' }] }
            };
            workbook.sheets = sheets; workbook.order = ['Schedule A','Schedule B'];
            workbook.activeSheet = 'Schedule A'; dataLoaded = true;
            if (typeof ContractIndex !== 'undefined' && typeof ContractIndex.rebuild === 'function') ContractIndex.rebuild();
        })()""")
        await page2.wait_for_timeout(500)

        suite_fns = {
            'p022': '_runP022',
            'p1': '_runP1',
            'calibration': '_runCalibration',
            'p08': '_runP08',
            'p09': '_runP09',
            'p1a': '_runP1A'
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

        await page2.close()
        await page.close()
        await browser.close()

    # Print summary
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r['passed'])
    failed = total - passed
    print('=' * 70)
    print(f'[P1C] FINAL: {"GREEN" if failed == 0 else "RED"} ({passed}/{total} passed)')
    if failed > 0:
        print('FAILURES:')
        for r in RESULTS:
            if not r['passed']:
                print(f'  - {r["name"]}: {r["detail"]}')
    print('=' * 70)
    return failed == 0

if __name__ == '__main__':
    print('=' * 70)
    print('[P1C] RUNTIME VALIDATION RESULTS')
    print('=' * 70)
    ok = asyncio.get_event_loop().run_until_complete(run())
    sys.exit(0 if ok else 1)
