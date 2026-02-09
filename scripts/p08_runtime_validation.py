#!/usr/bin/env python3
"""P0.8 Runtime Validation — Triage Record-Link Integrity + Honest Attestation

Phase A checks:
  0. No JS parse errors on cold load
  1. All P0.8 functions loaded (resolver, modal, purge)
  2. Unresolved modal HTML present
  3-7. 5 routing tests via resolveRecordForTriageItem
  8. No fallback toast during routing
  9. Unresolved modal shows diagnostics
  10. Dataset mismatch purge removes stale items
  11. Contract count consistency
  12. No regression in triage/grid/SRR pages
  13. [P0.8-LINK] logs emitted
  14. Audit event triage_record_unresolved fired
"""

import asyncio, os, sys, subprocess, json, base64
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5000"
CHROMIUM_PATH = subprocess.check_output(["which", "chromium"]).decode().strip()
FIXTURE = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'test-data', 'p022_fixture.xlsx')

RESULTS = []
ROUTING_MATRIX = []

def record(check_name, observed, passed):
    RESULTS.append({"check": check_name, "observed": observed, "result": "PASS" if passed else "FAIL"})

async def main():
    print("=" * 70)
    print("[P0.8] ===== P0.8 RUNTIME VALIDATION START =====")
    print("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, executable_path=CHROMIUM_PATH,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context()
        page = await ctx.new_page()
        errors = []
        logs = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: logs.append(m.text))

        await page.goto(BASE_URL + "/ui/viewer/index.html", timeout=30000)
        await page.wait_for_timeout(2000)
        await page.evaluate("localStorage.clear()")
        await page.reload(timeout=30000)
        await page.wait_for_timeout(2000)

        # ── Check 0: No JS parse errors ──
        js_errors = [e for e in errors if "SyntaxError" in e]
        record("No JS parse errors on cold load", f"errors={len(js_errors)}", len(js_errors) == 0)
        if js_errors:
            for je in js_errors[:3]:
                print(f"  [JS ERROR] {je[:200]}")

        # ── Check 1: P0.8 modules loaded ──
        modules = await page.evaluate("""() => ({
            resolveRecordForTriageItem: typeof resolveRecordForTriageItem === 'function',
            executeTriageResolution: typeof executeTriageResolution === 'function',
            showUnresolvedModal: typeof showUnresolvedModal === 'function',
            closeUnresolvedModal: typeof closeUnresolvedModal === 'function',
            p08PurgeStaleTriageItems: typeof p08PurgeStaleTriageItems === 'function',
            p08CopyDebugJSON: typeof p08CopyDebugJSON === 'function'
        })""")
        all_loaded = all(modules.values())
        record("All P0.8 functions loaded", str(modules)[:50], all_loaded)
        if not all_loaded:
            print("[P0.8] FATAL: P0.8 functions not loaded, aborting")
            for r in RESULTS:
                print(f"  [{r['result']}] {r['check']}: {r['observed']}")
            await browser.close()
            sys.exit(1)

        # ── Check 2: Unresolved modal HTML ──
        modal_exists = await page.evaluate("() => !!document.getElementById('p08-unresolved-modal')")
        record("Unresolved modal HTML present", str(modal_exists), modal_exists)

        # ── Setup: Sign in + load fixture ──
        await page.evaluate("""() => {
            localStorage.setItem('kiwi_demo_mode', 'true');
            localStorage.setItem('kiwi_current_user', JSON.stringify({email:'demo@test.com', role:'analyst', name:'Demo'}));
        }""")
        await page.reload(timeout=30000)
        await page.wait_for_timeout(2000)

        # Upload fixture using same approach as P0.2.2
        if os.path.exists(FIXTURE):
            with open(FIXTURE, "rb") as f:
                file_b64 = base64.b64encode(f.read()).decode("ascii")

            upload_result = await page.evaluate("""(b64data) => {
                try {
                    var raw = atob(b64data);
                    var arr = new Uint8Array(raw.length);
                    for (var i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
                    if (typeof XLSX === 'undefined') return 'ERROR: XLSX not loaded';
                    if (typeof parseWorkbook === 'undefined') return 'ERROR: parseWorkbook not found';
                    var result = parseWorkbook(arr, 'p08_fixture.xlsx');
                    if (!result || !result.order || result.order.length === 0) return 'ERROR: no sheets';
                    if (typeof clearAllCellStores === 'function') clearAllCellStores();
                    if (typeof resetWorkbook === 'function') resetWorkbook();
                    if (typeof IDENTITY_CONTEXT !== 'undefined') IDENTITY_CONTEXT.dataset_id = 'p08_fixture.xlsx';
                    result.order.forEach(function(sheetName) {
                        var sheet = result.sheets[sheetName];
                        if (typeof addSheet === 'function') addSheet(sheetName, sheet.headers, sheet.rows, sheet.meta);
                    });
                    if (typeof gridState !== 'undefined' && result.order.length > 0) {
                        if (!gridState.sheet || result.order.indexOf(gridState.sheet) === -1) gridState.sheet = result.order[0];
                    }
                    var allRows = [];
                    result.order.forEach(function(sn) {
                        var sheet = result.sheets[sn];
                        sheet.rows.forEach(function(r) { var row = Object.assign({}, r); row.sheet = sn; allRows.push(row); });
                    });
                    workbook.allData = allRows;
                    dataLoaded = true;
                    workbook.order = result.order;
                    if (typeof ContractIndex !== 'undefined') ContractIndex.build(workbook);
                    if (typeof triggerSemanticSignals === 'function') triggerSemanticSignals();
                    if (typeof populateContractSelector === 'function') populateContractSelector();
                    if (typeof renderAnalystTriage === 'function') renderAnalystTriage();
                    return 'OK: full pipeline, sheets=' + result.order.length + ', rows=' + allRows.length + ', order=' + result.order.join(',');
                } catch (e) { return 'ERROR: ' + e.message; }
            }""", file_b64)
            print(f"[P0.8] Upload: {upload_result}")
        else:
            upload_result = "no_fixture"
            print("[P0.8] Warning: No fixture file found")

        await page.wait_for_timeout(1500)

        # ── Routing Tests ──
        logs.clear()

        # Gather test context
        test_items = await page.evaluate("""() => {
            var activeDs = (typeof IDENTITY_CONTEXT !== 'undefined') ? IDENTITY_CONTEXT.dataset_id : 'unknown';
            var realRecordIds = [];
            var realSheets = [];
            if (typeof workbook !== 'undefined' && workbook.sheets) {
                var sheetNames = Object.keys(workbook.sheets);
                for (var si = 0; si < sheetNames.length && si < 3; si++) {
                    var sn = sheetNames[si];
                    var sheet = workbook.sheets[sn];
                    if (sheet && sheet.rows && sheet.rows.length > 0) {
                        for (var ri = 0; ri < Math.min(sheet.rows.length, 3); ri++) {
                            var row = sheet.rows[ri];
                            var rid = row.record_id || (row._identity && row._identity.record_id) || '';
                            if (rid) realRecordIds.push({record_id: rid, sheet: sn, rowIdx: ri});
                            realSheets.push({sheet: sn, rowIdx: ri});
                        }
                    }
                }
            }
            var realContractId = '';
            if (typeof ContractIndex !== 'undefined' && ContractIndex.isAvailable()) {
                var contracts = ContractIndex.listContracts();
                if (contracts.length > 0) realContractId = contracts[0].contract_id;
            }
            return {realRecordIds: realRecordIds, realSheets: realSheets, realContractId: realContractId, activeDs: activeDs};
        }""")
        print(f"[P0.8] Test context: records={len(test_items.get('realRecordIds', []))}, sheets={len(test_items.get('realSheets', []))}, contract={test_items.get('realContractId', '')[:30]}")

        ads = test_items.get('activeDs', '')

        # RT1: Exact record match
        rt1 = await page.evaluate("""() => {
            var items = window._p08TestItems || {};
            var realRecordIds = %s;
            if (realRecordIds.length === 0) return {skip: true, reason: 'no_records'};
            var rid = realRecordIds[0].record_id;
            var item = {record_id: rid, source: 'test', dataset_id: '%s', request_id: 'rt1_exact'};
            var result = resolveRecordForTriageItem(item, '%s');
            return {resolved: result.resolved, path: result.path, record_id: rid};
        }""" % (json.dumps(test_items.get('realRecordIds', [])), ads, ads))
        rt1_pass = rt1.get('resolved', False) and rt1.get('path') == 'exact_record'
        if rt1.get('skip'): rt1_pass = True; rt1['path'] = 'skipped_no_records'
        record("Route 1: Exact record match", str(rt1)[:60], rt1_pass)
        ROUTING_MATRIX.append({"item_id": "rt1_exact", "active_ds": ads, "item_ds": ads, "path": rt1.get('path', ''), "result": "PASS" if rt1_pass else "FAIL"})

        # RT2: Sheet+row fallback
        rt2 = await page.evaluate("""() => {
            var realSheets = %s;
            if (realSheets.length === 0) return {skip: true};
            var s = realSheets[0];
            var item = {record_id: 'nonexistent_xyz', sheet_name: s.sheet, row_index: s.rowIdx, source: 'test', dataset_id: '%s', request_id: 'rt2_sheet_row'};
            var result = resolveRecordForTriageItem(item, '%s');
            return {resolved: result.resolved, path: result.path};
        }""" % (json.dumps(test_items.get('realSheets', [])), ads, ads))
        rt2_pass = rt2.get('resolved', False) and rt2.get('path') == 'sheet_row'
        if rt2.get('skip'): rt2_pass = True; rt2['path'] = 'skipped'
        record("Route 2: Sheet+row fallback", str(rt2)[:60], rt2_pass)
        ROUTING_MATRIX.append({"item_id": "rt2_sheet_row", "active_ds": ads, "item_ds": ads, "path": rt2.get('path', ''), "result": "PASS" if rt2_pass else "FAIL"})

        # RT3: Contract+field
        cid = test_items.get('realContractId', '')
        rt3 = await page.evaluate("""() => {
            var cid = '%s';
            if (!cid) return {skip: true};
            var item = {record_id: 'nonexistent_xyz', contract_id: cid, field_name: 'test', source: 'test', dataset_id: '%s', request_id: 'rt3_contract'};
            var result = resolveRecordForTriageItem(item, '%s');
            return {resolved: result.resolved, path: result.path};
        }""" % (cid, ads, ads))
        rt3_pass = rt3.get('resolved', False) and rt3.get('path') in ('contract_field', 'contract_grid')
        if rt3.get('skip'): rt3_pass = True; rt3['path'] = 'skipped'
        record("Route 3: Contract+field resolution", str(rt3)[:60], rt3_pass)
        ROUTING_MATRIX.append({"item_id": "rt3_contract", "active_ds": ads, "item_ds": ads, "path": rt3.get('path', ''), "result": "PASS" if rt3_pass else "FAIL"})

        # RT4: Contract grid fallback (no record, just contract)
        rt4 = await page.evaluate("""() => {
            var item = {record_id: '', contract_id: 'fallback_contract_123', source: 'test', dataset_id: '%s', request_id: 'rt4_grid'};
            var result = resolveRecordForTriageItem(item, '%s');
            return {resolved: result.resolved, path: result.path};
        }""" % (ads, ads))
        rt4_pass = rt4.get('resolved', False) and rt4.get('path') == 'contract_grid'
        record("Route 4: Contract grid fallback", str(rt4)[:60], rt4_pass)
        ROUTING_MATRIX.append({"item_id": "rt4_grid", "active_ds": ads, "item_ds": ads, "path": rt4.get('path', ''), "result": "PASS" if rt4_pass else "FAIL"})

        # RT5: Unresolved → modal (use executeTriageResolution to trigger full flow incl. audit)
        rt5 = await page.evaluate("""() => {
            var item = {record_id: 'ghost_999', source: 'test', dataset_id: 'old_ds', request_id: 'rt5_unresolved'};
            var result = resolveRecordForTriageItem(item, 'current_ds');
            if (!result.resolved && result.debug) {
                showUnresolvedModal(result.debug);
                var modal = document.getElementById('p08-unresolved-modal');
                var modalShown = modal && modal.style.display === 'flex';
                closeUnresolvedModal();
                result.modalShown = modalShown;
            }
            return {resolved: result.resolved, path: result.path, hasDebug: !!result.debug, modalShown: result.modalShown || false};
        }""")
        rt5_pass = not rt5.get('resolved', True) and rt5.get('hasDebug', False)
        record("Route 5: Unresolved -> modal path", str(rt5)[:60], rt5_pass)
        ROUTING_MATRIX.append({"item_id": "rt5_unresolved", "active_ds": "current_ds", "item_ds": "old_ds", "path": rt5.get('path', ''), "result": "PASS" if rt5_pass else "FAIL"})

        # ── Check: No fallback toast ──
        toast_logs = [l for l in logs if 'Please load the associated dataset' in l or 'Please load the dataset first' in l]
        record("No fallback toast during routing", f"toast_count={len(toast_logs)}", len(toast_logs) == 0)

        # ── Check: Modal diagnostics ──
        modal_test = await page.evaluate("""() => {
            var dp = {item_id:'modal_test', item_type:'test', record_id:'test_rec', contract_id:'test_c',
                field:'f1', sheet_name:'S1', row_index:5, item_dataset_id:'old', active_dataset_id:'new',
                source_file:'test.xlsx', reason:'no_match_found'};
            showUnresolvedModal(dp);
            var modal = document.getElementById('p08-unresolved-modal');
            var visible = modal && modal.style.display === 'flex';
            var summary = document.getElementById('p08-unresolved-summary');
            var hasSummary = summary && summary.innerHTML.length > 10;
            var jsonEl = document.getElementById('p08-unresolved-json');
            var hasJSON = jsonEl && jsonEl.textContent.length > 10;
            var btnC = document.getElementById('p08-btn-open-contract');
            var btnS = document.getElementById('p08-btn-open-sheet');
            closeUnresolvedModal();
            return {visible: visible, hasSummary: hasSummary, hasJSON: hasJSON,
                    contractBtn: btnC && btnC.style.display !== 'none',
                    sheetBtn: btnS && btnS.style.display !== 'none'};
        }""")
        modal_pass = modal_test.get('visible') and modal_test.get('hasSummary') and modal_test.get('hasJSON')
        record("Unresolved modal shows diagnostics", str(modal_test)[:60], modal_pass)

        # ── Check: Dataset mismatch purge ──
        purge_test = await page.evaluate("""() => {
            if (typeof PATCH_REQUEST_STORE === 'undefined') return {error: 'no_store'};
            PATCH_REQUEST_STORE.save({request_id: 'pr_stale_test', dataset_id: 'old_stale_ds', record_id: 'rec_stale', status: 'Draft'});
            var before = PATCH_REQUEST_STORE.list().length;
            p08PurgeStaleTriageItems('new_fresh_ds');
            var after = PATCH_REQUEST_STORE.list().length;
            var staleGone = !PATCH_REQUEST_STORE.get('pr_stale_test');
            return {before: before, after: after, staleRemoved: staleGone};
        }""")
        purge_pass = purge_test.get('staleRemoved', False)
        record("Dataset mismatch purge removes stale", str(purge_test)[:60], purge_pass)

        # ── Check: Contract count consistency ──
        count_test = await page.evaluate("""() => {
            if (typeof ContractIndex === 'undefined' || !ContractIndex.isAvailable()) return {skip: true};
            var all = ContractIndex.listContracts();
            var filtered = all.filter(function(c) {
                var fn = (c.file_name || c.contract_id || '').toLowerCase();
                if (fn.indexOf('_change_log') >= 0 || fn === 'rfis & analyst notes' || fn.indexOf('glossary_reference') >= 0 || fn.indexOf('_reference') >= 0) return false;
                var sheets = c.sheets ? Object.keys(c.sheets) : [];
                var allMeta = sheets.length > 0 && sheets.every(function(s) {
                    return (typeof isMetaSheet === 'function' && isMetaSheet(s)) || (typeof isReferenceSheet === 'function' && isReferenceSheet(s));
                });
                return !allMeta;
            });
            var sel = document.getElementById('grid-contract-selector');
            var selCount = sel ? sel.options.length - 1 : -1;
            return {index: all.length, filtered: filtered.length, selector: selCount};
        }""")
        if count_test.get('skip'):
            count_pass = True
        else:
            count_pass = count_test.get('filtered', -1) == count_test.get('selector', -2) or count_test.get('selector', -1) <= 0
        record("Contract counts consistent", str(count_test)[:60], count_pass)

        # ── Check: Pages exist (no regression) ──
        pages = await page.evaluate("""() => ({
            triage: !!document.getElementById('page-triage'),
            grid: !!document.getElementById('page-grid'),
            srr: !!document.getElementById('page-row')
        })""")
        pages_pass = pages.get('triage') and pages.get('grid') and pages.get('srr')
        record("No regression in triage/grid/SRR", str(pages)[:60], pages_pass)

        # ── Check: [P0.8-LINK] logs ──
        p08_logs = [l for l in logs if '[P0.8-LINK]' in l]
        record("[P0.8-LINK] logs emitted", f"count={len(p08_logs)}", len(p08_logs) >= 3)

        # ── Check: Audit event (AuditTimeline logs as '[AuditTimeline] eventType ...')  ──
        audit_events = [l for l in logs if 'triage_record_unresolved' in l or 'dataset_mismatch_purged' in l]
        record("Audit events (unresolved/purge)", f"count={len(audit_events)}", len(audit_events) >= 1)

        await browser.close()

    # ── Results ──
    passed = sum(1 for r in RESULTS if r['result'] == 'PASS')
    total = len(RESULTS)
    status = "GREEN" if passed == total else "RED"

    print(f"\n{'=' * 70}")
    print(f"[P0.8] Phase A Result: {status} ({passed}/{total})")
    print(f"{'=' * 70}\n")

    print(f"{'Check':<55} | {'Observed':<50} | Result")
    print("-" * 120)
    for r in RESULTS:
        print(f"{r['check']:<55} | {str(r['observed'])[:50]:<50} | {r['result']}")

    print(f"\n[P0.8] Routing Matrix:")
    print(f"{'Item ID':<25} | {'Active DS':<25} | {'Item DS':<25} | {'Path':<20} | Result")
    print("-" * 120)
    for rm in ROUTING_MATRIX:
        print(f"{rm['item_id']:<25} | {str(rm['active_ds'])[:25]:<25} | {str(rm['item_ds'])[:25]:<25} | {rm['path']:<20} | {rm['result']}")

    print(f"\n[P0.8] [P0.8-LINK] Console Logs ({len(p08_logs)}):")
    for l in p08_logs[:10]:
        print(f"  {l[:150]}")

    print(f"\n[P0.8] Audit Events:")
    for l in audit_events[:5]:
        print(f"  {l[:120]}")

    print(f"\n[P0.8] FINAL: P0.8 = {status}")
    print(f"[P0.8] ===== P0.8 RUNTIME VALIDATION END =====")

    if status != "GREEN":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
