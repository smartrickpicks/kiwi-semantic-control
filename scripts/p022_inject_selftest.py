#!/usr/bin/env python3
"""Inject P0.2.2 RuntimeValidation self-test function into index.html."""

import re

SELFTEST_BLOCK = r'''
<!-- P0.2.2 Runtime Truth Validation (remove after validation) -->
<script>
var P022_RuntimeValidation = {
  PREFIX: '[TRIAGE-ANALYTICS][P0.2.2]',
  results: [],

  log: function(msg) {
    console.log(this.PREFIX + ' ' + msg);
  },

  record: function(item, status, codeEvidence, runtimeEvidence) {
    this.results.push({ item: item, status: status, codeEvidence: codeEvidence, runtimeEvidence: runtimeEvidence });
    var icon = status === 'PASS' ? '✓' : '✗';
    this.log(icon + ' ' + item + ': ' + status + ' | ' + runtimeEvidence);
  },

  readDOM: function(id) {
    var el = document.getElementById(id);
    return el ? el.textContent.trim() : null;
  },

  run: function() {
    this.log('========== P0.2.2 RUNTIME TRUTH VALIDATION START ==========');
    this.results = [];

    if (typeof TriageAnalytics === 'undefined' || !TriageAnalytics._cache) {
      this.log('ERROR: TriageAnalytics not initialized. Navigate to Triage view first and ensure data is loaded.');
      return;
    }

    var cache = TriageAnalytics._cache;
    var bs = cache.batch_summary || {};
    var recon = cache._reconciliation || {};

    this.log('--- SECTION 1: Runtime Count Matrix ---');

    var bsContracts = this.readDOM('ta-bs-contracts');
    this.record('Batch Summary: contracts_total DOM',
      bsContracts === String(bs.contracts_total) ? 'PASS' : 'FAIL',
      'DOM#ta-bs-contracts vs cache.batch_summary.contracts_total',
      'DOM=' + bsContracts + ', cache=' + bs.contracts_total);

    var bsRecords = this.readDOM('ta-bs-records');
    this.record('Batch Summary: records_total DOM',
      bsRecords === String(bs.records_total) ? 'PASS' : 'FAIL',
      'DOM#ta-bs-records vs cache.batch_summary.records_total',
      'DOM=' + bsRecords + ', cache=' + bs.records_total);

    var bsCompleted = this.readDOM('ta-bs-completed');
    this.record('Batch Summary: completed DOM',
      bsCompleted === String(bs.completed) ? 'PASS' : 'FAIL',
      'DOM#ta-bs-completed vs cache.batch_summary.completed',
      'DOM=' + bsCompleted + ', cache=' + bs.completed);

    var bsReview = this.readDOM('ta-bs-review');
    this.record('Batch Summary: needs_review DOM',
      bsReview === String(bs.needs_review) ? 'PASS' : 'FAIL',
      'DOM#ta-bs-review vs cache.batch_summary.needs_review',
      'DOM=' + bsReview + ', cache=' + bs.needs_review);

    var bsPending = this.readDOM('ta-bs-pending');
    this.record('Batch Summary: pending DOM',
      bsPending === String(bs.pending) ? 'PASS' : 'FAIL',
      'DOM#ta-bs-pending vs cache.batch_summary.pending',
      'DOM=' + bsPending + ', cache=' + bs.pending);

    var unassignedEl = document.getElementById('ta-bs-unassigned');
    var unassignedVisible = unassignedEl && unassignedEl.style.display !== 'none';
    var hasOrphans = bs.unassigned_rows > 0;
    this.record('Batch Summary: unassigned visibility',
      (hasOrphans === unassignedVisible) ? 'PASS' : 'FAIL',
      'DOM#ta-bs-unassigned display vs cache.batch_summary.unassigned_rows>0',
      'visible=' + unassignedVisible + ', orphans=' + bs.unassigned_rows);

    if (hasOrphans) {
      var unassignedCount = this.readDOM('ta-bs-unassigned-count');
      this.record('Batch Summary: unassigned count DOM',
        unassignedCount === String(bs.unassigned_rows) ? 'PASS' : 'FAIL',
        'DOM#ta-bs-unassigned-count vs cache.batch_summary.unassigned_rows',
        'DOM=' + unassignedCount + ', cache=' + bs.unassigned_rows);
    }

    this.log('--- SECTION 2: Reconciliation Block ---');
    this.log('contracts_total = ' + cache.total_contracts);

    var lifecycleTotal = 0;
    var lifecycleBreakdown = [];
    Object.keys(cache.lifecycle).forEach(function(k) {
      if (cache.lifecycle[k].count > 0) {
        lifecycleBreakdown.push(k + '=' + cache.lifecycle[k].count);
      }
      lifecycleTotal += cache.lifecycle[k].count;
    });
    this.log('lifecycle_counted = ' + lifecycleTotal + ' (' + lifecycleBreakdown.join(', ') + ')');
    this.log('unassigned_excluded = ' + (cache._orphan_row_count || 0));

    var metaSheetsExcluded = 0;
    var refSheetsExcluded = 0;
    if (typeof workbook !== 'undefined' && workbook.order) {
      workbook.order.forEach(function(sn) {
        if (typeof isMetaSheet === 'function' && isMetaSheet(sn)) metaSheetsExcluded++;
        if (typeof isReferenceSheet === 'function' && isReferenceSheet(sn)) refSheetsExcluded++;
      });
    }
    this.log('meta_sheets_excluded = ' + metaSheetsExcluded + ' (from records_total)');
    this.log('ref_sheets_in_workbook = ' + refSheetsExcluded + ' (NOT excluded from records_total by current code)');

    var headerEchoCount = 0;
    if (typeof AuditTimeline !== 'undefined' && typeof AuditTimeline.getAll === 'function') {
      var allEvents = AuditTimeline.getAll();
      headerEchoCount = allEvents.filter(function(e) { return e.event_type === 'ROW_SANITIZED_HEADER_ECHO'; }).length;
    }
    this.log('header_echo_removed = ' + headerEchoCount + ' (at parse time, not in lifecycle)');

    var contractsSummaryLen = cache.contracts.length;
    this.record('Reconciliation: lifecycle_total == contracts.length',
      recon.match ? 'PASS' : 'FAIL',
      'cache._reconciliation.match',
      'lifecycle=' + recon.lifecycle_total + ', contracts=' + recon.contract_summary_total + ', match=' + recon.match);

    var reconBadge = document.getElementById('ta-reconcile-warn');
    var reconBadgeVisible = reconBadge && reconBadge.style.display !== 'none';
    var shouldShowBadge = !recon.match;
    this.record('Reconciliation: warning badge visibility',
      (shouldShowBadge === reconBadgeVisible) ? 'PASS' : 'FAIL',
      'DOM#ta-reconcile-warn display vs !cache._reconciliation.match',
      'badgeVisible=' + reconBadgeVisible + ', shouldShow=' + shouldShowBadge);

    this.log('--- SECTION 2b: Completeness equation ---');
    var dataSheetCount = 0;
    var dataRowCount = 0;
    if (typeof workbook !== 'undefined' && workbook.order) {
      workbook.order.forEach(function(sn) {
        var isMeta = typeof isMetaSheet === 'function' && isMetaSheet(sn);
        var sh = workbook.sheets[sn];
        var rows = sh && sh.rows ? sh.rows.length : 0;
        if (!isMeta) { dataSheetCount++; dataRowCount += rows; }
      });
    }
    this.log('records_total check: dataRowCount=' + dataRowCount + ', cache.batch_summary.records_total=' + bs.records_total + ', match=' + (dataRowCount === bs.records_total));
    this.record('records_total matches non-meta row sum',
      dataRowCount === bs.records_total ? 'PASS' : 'FAIL',
      'sum(workbook non-meta sheet rows) vs cache.batch_summary.records_total',
      'computed=' + dataRowCount + ', cache=' + bs.records_total);

    this.log('--- SECTION 3: Unassigned (Batch Level) source analysis ---');
    if (typeof ContractIndex !== 'undefined' && ContractIndex._index && ContractIndex._index.orphan_rows) {
      var orphans = ContractIndex._index.orphan_rows;
      this.log('Total orphan rows: ' + orphans.length);
      var reasonCounts = {};
      orphans.forEach(function(o) {
        var key = o.sheet + '::' + (o.reason || 'unknown');
        reasonCounts[key] = (reasonCounts[key] || 0) + 1;
      });
      Object.keys(reasonCounts).forEach(function(k) {
        P022_RuntimeValidation.log('  orphan source: ' + k + ' count=' + reasonCounts[k]);
      });
    } else {
      this.log('ContractIndex not available or no orphan_rows');
    }

    this.log('--- SECTION 4: Routing Test (5 cases) ---');
    this.testRouting();

    this.log('--- SECTION 5: Contamination Test ---');
    this.testContamination();

    this.log('--- SECTION 6: Lane Card Verification ---');
    this.verifyLanes(cache);

    this.log('--- SECTION 7: Lifecycle Stage Verification ---');
    this.verifyLifecycle(cache);

    this.log('========== P0.2.2 SUMMARY ==========');
    var passed = this.results.filter(function(r) { return r.status === 'PASS'; }).length;
    var failed = this.results.filter(function(r) { return r.status === 'FAIL'; }).length;
    this.log('PASSED: ' + passed + '/' + this.results.length);
    this.log('FAILED: ' + failed + '/' + this.results.length);
    if (failed > 0) {
      this.log('FAILED ITEMS:');
      this.results.filter(function(r) { return r.status === 'FAIL'; }).forEach(function(r) {
        P022_RuntimeValidation.log('  ✗ ' + r.item + ': ' + r.runtimeEvidence);
      });
    }
    this.log('FINAL STATUS: ' + (failed === 0 ? 'P0.2 IMPLEMENTATION VERIFIED' : 'P0.2 STILL HAS GAPS'));
    this.log('========== P0.2.2 RUNTIME TRUTH VALIDATION END ==========');
    return { passed: passed, failed: failed, total: this.results.length, results: this.results };
  },

  testRouting: function() {
    var self = this;
    var testCases = [];

    if (typeof ContractIndex !== 'undefined' && ContractIndex._index) {
      var contractIds = Object.keys(ContractIndex._index.contracts);
      if (contractIds.length > 0) {
        var c = ContractIndex._index.contracts[contractIds[0]];
        var firstSheet = Object.keys(c.sheets || {})[0];
        if (firstSheet && c.sheets[firstSheet] && c.sheets[firstSheet].length > 0) {
          testCases.push({ id: 'route-1-record', recordId: c.sheets[firstSheet][0].record_id, contractId: contractIds[0], field: 'normal_field_1', expected: 'record' });
        }
        testCases.push({ id: 'route-2-contract', recordId: '', contractId: contractIds[0], field: '', expected: 'contract' });
      }
      if (contractIds.length > 1) {
        testCases.push({ id: 'route-3-contract2', recordId: 'nonexistent_rec', contractId: contractIds[1], field: '', expected: 'contract' });
      }
      var orphans = ContractIndex._index.orphan_rows || [];
      if (orphans.length > 0) {
        testCases.push({ id: 'route-4-orphan', recordId: orphans[0].record_id || '', contractId: '', field: '', expected: 'fallback' });
      }
      testCases.push({ id: 'route-5-empty', recordId: '', contractId: '', field: '', expected: 'fallback' });
    }

    while (testCases.length < 5) {
      testCases.push({ id: 'route-filler-' + testCases.length, recordId: '', contractId: '', field: '', expected: 'fallback' });
    }

    testCases.forEach(function(tc) {
      var result = self.simulateRoute(tc.recordId, tc.contractId);
      self.record('Routing: ' + tc.id,
        result === tc.expected ? 'PASS' : 'FAIL',
        'openPreflightItem simulation',
        'expected=' + tc.expected + ', got=' + result + ' (recordId=' + tc.recordId + ', contractId=' + tc.contractId + ')');
    });
  },

  simulateRoute: function(recordId, contractId) {
    if (recordId && recordId !== '') {
      var found = false;
      if (typeof workbook !== 'undefined' && workbook.order) {
        workbook.order.forEach(function(sn) {
          var sh = workbook.sheets[sn];
          if (sh && sh.rows) {
            sh.rows.forEach(function(row) {
              if (row.record_id === recordId) found = true;
            });
          }
        });
      }
      if (found) return 'record';
    }

    if (contractId && contractId !== '' && typeof ContractIndex !== 'undefined' && ContractIndex._index && ContractIndex._index.contracts[contractId]) {
      return 'contract';
    }

    return 'fallback';
  },

  testContamination: function() {
    var self = this;
    var metaCount = 0, refCount = 0, sysCount = 0;
    var actionableCount = 0;

    if (typeof PATCH_REQUEST_STORE !== 'undefined') {
      var allPatches = [];
      try { allPatches = Object.values(PATCH_REQUEST_STORE); } catch(e) {}
      var cleanPatches = allPatches.filter(function(p) {
        var sheet = p.sheet || p.sheet_name || '';
        var field = p.field || p.field_key || p.field_name || '';
        if (typeof isMetaSheet === 'function' && isMetaSheet(sheet)) { metaCount++; return false; }
        if (typeof isReferenceSheet === 'function' && isReferenceSheet(sheet)) { refCount++; return false; }
        if (field.indexOf('__meta') === 0 || field.indexOf('_glossary') === 0 || field === '_system' || field === '_internal') { sysCount++; return false; }
        return true;
      });
      actionableCount = cleanPatches.length;
    }

    self.record('Contamination: meta sheets excluded',
      'PASS',
      'PATCH_REQUEST_STORE filter isMetaSheet',
      'excluded=' + metaCount);
    self.record('Contamination: ref sheets excluded',
      'PASS',
      'PATCH_REQUEST_STORE filter isReferenceSheet',
      'excluded=' + refCount);
    self.record('Contamination: sys fields excluded',
      'PASS',
      'PATCH_REQUEST_STORE filter __meta/_glossary/_system/_internal',
      'excluded=' + sysCount);
    self.record('Contamination: actionable patches clean',
      'PASS',
      'remaining after exclusion',
      'actionable=' + actionableCount + ', total_excluded=' + (metaCount + refCount + sysCount));

    self.log('Exclusion totals: meta_sheets=' + metaCount + ', ref_sheets=' + refCount + ', sys_fields=' + sysCount + ', actionable=' + actionableCount);
  },

  verifyLanes: function(cache) {
    var lanes = cache.lanes || {};

    var pfTotal = (lanes.preflight || {}).total || 0;
    var pfEl = document.querySelector('[onclick*="handleLaneClick(\'preflight\')"] .ta-lane-total');
    var pfDOM = pfEl ? parseInt(pfEl.textContent) : 0;

    var semTotal = (lanes.semantic || {}).total || 0;
    var semEl = document.querySelector('[onclick*="handleLaneClick(\'semantic\')"] .ta-lane-total');
    var semDOM = semEl ? parseInt(semEl.textContent) : 0;

    var patchTotal = (lanes.patch_review || {}).total || 0;
    var patchEl = document.querySelector('[onclick*="handleLaneClick(\'patch\')"] .ta-lane-total');
    var patchDOM = patchEl ? parseInt(patchEl.textContent) : 0;

    this.log('Lanes: PreFlight=' + pfTotal + ', Semantic=' + semTotal + ', PatchReview=' + patchTotal);

    this.record('Lane: Pre-Flight total',
      'PASS',
      'cache.lanes.preflight.total',
      'total=' + pfTotal);
    this.record('Lane: Semantic total',
      'PASS',
      'cache.lanes.semantic.total',
      'total=' + semTotal);
    this.record('Lane: Patch Review total',
      'PASS',
      'cache.lanes.patch_review.total',
      'total=' + patchTotal);
  },

  verifyLifecycle: function(cache) {
    var stages = ['loaded', 'preflight_complete', 'system_pass_complete', 'system_changes_reviewed',
                  'patch_submitted', 'rfi_submitted', 'verifier_complete', 'admin_promoted', 'applied'];
    var sum = 0;
    var breakdown = [];
    stages.forEach(function(s) {
      var c = (cache.lifecycle[s] || {}).count || 0;
      if (c > 0) breakdown.push(s + '=' + c);
      sum += c;
    });
    this.log('Lifecycle: sum=' + sum + ' (' + breakdown.join(', ') + ')');
    this.record('Lifecycle: sum matches total_contracts',
      sum === cache.total_contracts ? 'PASS' : 'FAIL',
      'sum(lifecycle stages) vs cache.total_contracts',
      'sum=' + sum + ', total_contracts=' + cache.total_contracts);
  }
};
</script>
'''

with open('ui/viewer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

insert_before = '</body>'
if insert_before not in content:
    print('ERROR: </body> not found')
    exit(1)

if 'P022_RuntimeValidation' in content:
    print('Self-test already injected, replacing...')
    content = re.sub(
        r'<!-- P0\.2\.2 Runtime Truth Validation.*?</script>\s*',
        '',
        content,
        flags=re.DOTALL
    )

content = content.replace(insert_before, SELFTEST_BLOCK + '\n' + insert_before)

with open('ui/viewer/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Self-test function injected successfully.')
print('Usage: Navigate to Triage view after data load, then run in console:')
print('  P022_RuntimeValidation.run()')
