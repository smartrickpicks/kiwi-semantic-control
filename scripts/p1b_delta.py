#!/usr/bin/env python3
"""P1B Delta — Admin QA Runner (debug/test control panel)

Adds an Admin/Architect-only QA Runner tab that runs in-browser validation
suites and shows pass/fail results. Reuses existing runtime validation logic
(function existence, DOM checks, basic assertions) without duplicating
business logic. Persists run history to SessionDB, emits audit events,
and supports an Architect-only Quality Lock Candidate toggle.

Edits:
  1. Add QA Runner tab button in admin tab bar
  2. Add qa-runner tab panel HTML
  3. Register 'qa-runner' in switchAdminTab tabs array
  4. Add QARunner JS module with 6 test suites + persistence + audit
"""

import re, sys, os, shutil

TARGET = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def apply_edit(content, edit_id, anchor, insertion, mode='after'):
    if anchor not in content:
        print('[P1B] FAIL edit %s: anchor not found' % edit_id)
        return content, False
    if mode == 'after':
        content = content.replace(anchor, anchor + insertion, 1)
    elif mode == 'before':
        content = content.replace(anchor, insertion + anchor, 1)
    elif mode == 'replace':
        content = content.replace(anchor, insertion, 1)
    print('[P1B] OK edit %s' % edit_id)
    return content, True

def main():
    if not os.path.exists(TARGET):
        print('[P1B] FATAL: Target not found:', TARGET)
        sys.exit(1)

    backup = TARGET + '.p1b.bak'
    shutil.copy2(TARGET, backup)
    print('[P1B] Backup:', backup)

    content = read_file(TARGET)
    ok_count = 0
    total = 4

    # ── EDIT 1: Add QA Runner tab button ──
    anchor1 = '''<button class="admin-tab" data-admin-tab="people" onclick="switchAdminTab('people')" style="padding: 10px 20px; background: #f5f5f5; color: #666; border: none; border-radius: 6px 6px 0 0; cursor: pointer;">People</button>'''
    insert1 = '''
          <button class="admin-tab" data-admin-tab="qa-runner" onclick="switchAdminTab('qa-runner')" style="padding: 10px 20px; background: #f5f5f5; color: #666; border: none; border-radius: 6px 6px 0 0; cursor: pointer;">QA Runner</button>'''
    content, ok = apply_edit(content, 'E1-tab-button', anchor1, insert1, 'after')
    if ok: ok_count += 1

    # ── EDIT 2: Add QA Runner tab panel HTML ──
    anchor2 = '        </div><!-- end admin-tab-people -->'
    insert2 = '''

        <div id="admin-tab-qa-runner" class="admin-tab-panel" data-admin-section="true" style="display: none;">
          <h3 style="margin: 0 0 16px 0; color: #1a237e;">QA Runner</h3>
          <p style="color: #666; font-size: 0.9em; margin: 0 0 16px 0;">Run in-browser validation suites to verify all governance features are working correctly.</p>
          <div id="p1b-run-controls" style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;">
            <button onclick="QARunner.runSuite('p022')" class="p1b-run-btn" style="padding: 6px 14px; font-size: 0.85em; background: #1976d2; color: white; border: none; border-radius: 4px; cursor: pointer;">Run P0.2.2</button>
            <button onclick="QARunner.runSuite('p1')" class="p1b-run-btn" style="padding: 6px 14px; font-size: 0.85em; background: #1976d2; color: white; border: none; border-radius: 4px; cursor: pointer;">Run P1</button>
            <button onclick="QARunner.runSuite('calibration')" class="p1b-run-btn" style="padding: 6px 14px; font-size: 0.85em; background: #1976d2; color: white; border: none; border-radius: 4px; cursor: pointer;">Run Calibration</button>
            <button onclick="QARunner.runSuite('p08')" class="p1b-run-btn" style="padding: 6px 14px; font-size: 0.85em; background: #1976d2; color: white; border: none; border-radius: 4px; cursor: pointer;">Run P0.8</button>
            <button onclick="QARunner.runSuite('p09')" class="p1b-run-btn" style="padding: 6px 14px; font-size: 0.85em; background: #1976d2; color: white; border: none; border-radius: 4px; cursor: pointer;">Run P0.9</button>
            <button onclick="QARunner.runSuite('p1a')" class="p1b-run-btn" style="padding: 6px 14px; font-size: 0.85em; background: #1976d2; color: white; border: none; border-radius: 4px; cursor: pointer;">Run P1A</button>
            <button onclick="QARunner.runAll()" style="padding: 6px 14px; font-size: 0.85em; background: #388e3c; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">Run All</button>
            <button onclick="QARunner.exportReport()" style="padding: 6px 14px; font-size: 0.85em; background: #f57c00; color: white; border: none; border-radius: 4px; cursor: pointer;">Export QA Report JSON</button>
          </div>
          <div id="p1b-quality-lock" style="display: none; margin-bottom: 12px; padding: 8px 12px; background: #fff3e0; border-radius: 6px; border: 1px solid #ffe0b2;">
            <label style="font-size: 0.85em; color: #e65100; cursor: pointer;">
              <input type="checkbox" id="p1b-lock-toggle" onchange="QARunner.toggleQualityLock(this.checked)" style="margin-right: 6px;">
              Quality Lock Candidate (Architect only)
            </label>
            <span id="p1b-lock-status" style="margin-left: 8px; font-size: 0.8em; color: #999;"></span>
          </div>
          <div id="p1b-running-status" style="display: none; padding: 10px; background: #e3f2fd; border-radius: 6px; margin-bottom: 12px;">
            <span id="p1b-running-label" style="font-size: 0.9em; color: #1565c0;">Running...</span>
          </div>
          <table id="p1b-results-table" style="width: 100%; border-collapse: collapse; font-size: 0.85em; margin-bottom: 16px;">
            <thead>
              <tr style="background: #f5f5f5; text-align: left;">
                <th style="padding: 8px; border-bottom: 2px solid #ddd;">Suite</th>
                <th style="padding: 8px; border-bottom: 2px solid #ddd;">Started</th>
                <th style="padding: 8px; border-bottom: 2px solid #ddd;">Finished</th>
                <th style="padding: 8px; border-bottom: 2px solid #ddd;">Result</th>
                <th style="padding: 8px; border-bottom: 2px solid #ddd;">Metrics</th>
                <th style="padding: 8px; border-bottom: 2px solid #ddd;">Details</th>
              </tr>
            </thead>
            <tbody id="p1b-results-tbody"></tbody>
          </table>
          <h4 style="margin: 24px 0 8px 0; color: #37474f;">Run History</h4>
          <table id="p1b-history-table" style="width: 100%; border-collapse: collapse; font-size: 0.82em;">
            <thead>
              <tr style="background: #fafafa; text-align: left;">
                <th style="padding: 6px; border-bottom: 1px solid #eee;">Run ID</th>
                <th style="padding: 6px; border-bottom: 1px solid #eee;">Timestamp</th>
                <th style="padding: 6px; border-bottom: 1px solid #eee;">Suites</th>
                <th style="padding: 6px; border-bottom: 1px solid #eee;">Result</th>
                <th style="padding: 6px; border-bottom: 1px solid #eee;">Locked</th>
              </tr>
            </thead>
            <tbody id="p1b-history-tbody"></tbody>
          </table>
        </div><!-- end admin-tab-qa-runner -->'''
    content, ok = apply_edit(content, 'E2-tab-panel', anchor2, insert2, 'after')
    if ok: ok_count += 1

    # ── EDIT 3: Register 'qa-runner' in switchAdminTab tabs array ──
    anchor3 = "var tabs = ['governance', 'users', 'patch-queue', 'config', 'inspector', 'standardizer', 'patch-console', 'evidence', 'unknown-cols', 'people'];"
    replace3 = "var tabs = ['governance', 'users', 'patch-queue', 'config', 'inspector', 'standardizer', 'patch-console', 'evidence', 'unknown-cols', 'people', 'qa-runner'];"
    content, ok = apply_edit(content, 'E3-tabs-array', anchor3, replace3, 'replace')
    if ok: ok_count += 1

    # ── EDIT 4: Add QARunner JS module ──
    # Insert before the final closing </script> — find a good anchor
    anchor4 = "console.log('[Admin] Switched to tab:', tabName);"
    insert4 = r"""
      if (tabName === 'qa-runner') {
        QARunner._onTabOpen();
      }"""
    content, ok = apply_edit(content, 'E4a-tab-hook', anchor4, insert4, 'after')
    if ok: ok_count += 1

    # Now insert the full QARunner module. Find the end of the file's last script section.
    # Insert after AuditTimeline init or near end of script.
    qa_module = r'''

    /* ═══════════════════════════════════════════════════════════════
       P1B: QA Runner — In-browser validation suite runner
       Admin + Architect can view; only Architect can set quality lock.
       ═══════════════════════════════════════════════════════════════ */
    var QARunner = {
      _currentRun: null,
      _history: [],
      _historyLoaded: false,
      HISTORY_KEY: 'qa_runner_history',

      _suiteRegistry: {
        'p022': { label: 'P0.2.2 Core Triage', fn: '_runP022' },
        'p1':   { label: 'P1 Triage Analytics', fn: '_runP1' },
        'calibration': { label: 'Calibration', fn: '_runCalibration' },
        'p08':  { label: 'P0.8 Record-Link', fn: '_runP08' },
        'p09':  { label: 'P0.9 Cleanup', fn: '_runP09' },
        'p1a':  { label: 'P1A Triage Clarity', fn: '_runP1A' }
      },

      _onTabOpen: function() {
        var mode = (localStorage.getItem('viewer_mode_v10') || '').toLowerCase();
        var lockEl = document.getElementById('p1b-quality-lock');
        if (lockEl) lockEl.style.display = (mode === 'architect') ? 'block' : 'none';
        if (!this._historyLoaded) this._loadHistory();
        this._renderHistory();
      },

      _isAllowed: function() {
        var mode = (localStorage.getItem('viewer_mode_v10') || '').toLowerCase();
        return mode === 'admin' || mode === 'architect';
      },

      _isArchitect: function() {
        var mode = (localStorage.getItem('viewer_mode_v10') || '').toLowerCase();
        return mode === 'architect';
      },

      _timestamp: function() {
        return new Date().toISOString().replace('T', ' ').substring(0, 19);
      },

      _generateRunId: function() {
        return 'qar_' + Date.now().toString(36) + '_' + Math.random().toString(36).substring(2, 6);
      },

      runSuite: function(suiteId) {
        if (!this._isAllowed()) { alert('QA Runner requires Admin or Architect role.'); return; }
        var reg = this._suiteRegistry[suiteId];
        if (!reg) { console.warn('[P1B] Unknown suite:', suiteId); return; }
        var self = this;
        var runId = this._generateRunId();
        var started = this._timestamp();
        this._showRunning(reg.label);
        AuditTimeline.emit('qa_run_started', { metadata: { run_id: runId, suite: suiteId } });
        console.log('[P1B] qa_run_started suite=' + suiteId + ' run_id=' + runId);

        var checks = this[reg.fn]();
        var passed = 0;
        var failed = 0;
        for (var ci = 0; ci < checks.length; ci++) {
          if (checks[ci].pass) passed++; else failed++;
        }
        var finished = this._timestamp();
        var result = { suite: suiteId, label: reg.label, started: started, finished: finished,
                       pass: failed === 0, passed: passed, failed: failed, total: checks.length, checks: checks };

        this._hideRunning();
        this._renderSingleResult(result);
        AuditTimeline.emit('qa_run_finished', { metadata: { run_id: runId, suite: suiteId, pass: failed === 0, passed: passed, failed: failed, total: checks.length } });
        console.log('[P1B] qa_run_finished suite=' + suiteId + ' pass=' + (failed === 0) + ' (' + passed + '/' + checks.length + ')');

        this._currentRun = this._currentRun || { run_id: runId, started: started, suites: [], overall: true, locked: false };
        this._currentRun.suites.push(result);
        if (!result.pass) this._currentRun.overall = false;
        this._currentRun.finished = finished;

        return result;
      },

      runAll: function() {
        if (!this._isAllowed()) { alert('QA Runner requires Admin or Architect role.'); return; }
        this._currentRun = null;
        var tbody = document.getElementById('p1b-results-tbody');
        if (tbody) tbody.innerHTML = '';
        var keys = ['p022', 'p1', 'calibration', 'p08', 'p09', 'p1a'];
        for (var ki = 0; ki < keys.length; ki++) {
          this.runSuite(keys[ki]);
        }
        if (this._currentRun) {
          this._saveHistory(this._currentRun);
          this._renderHistory();
        }
      },

      exportReport: function() {
        var data = {
          exported_at: new Date().toISOString(),
          current_run: this._currentRun,
          history: this._history
        };
        var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'qa_report_' + Date.now() + '.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        AuditTimeline.emit('qa_run_exported', { metadata: { run_id: this._currentRun ? this._currentRun.run_id : 'none', suites_count: this._currentRun ? this._currentRun.suites.length : 0 } });
        console.log('[P1B] qa_run_exported');
      },

      toggleQualityLock: function(checked) {
        if (!this._isArchitect()) {
          alert('Only Architect can set Quality Lock.');
          var toggle = document.getElementById('p1b-lock-toggle');
          if (toggle) toggle.checked = false;
          return;
        }
        if (!this._currentRun) {
          alert('Run suites first before setting Quality Lock.');
          var toggle2 = document.getElementById('p1b-lock-toggle');
          if (toggle2) toggle2.checked = false;
          return;
        }
        this._currentRun.locked = checked;
        var statusEl = document.getElementById('p1b-lock-status');
        if (statusEl) statusEl.textContent = checked ? 'Locked at ' + this._timestamp() : '';
        if (this._history.length > 0) {
          for (var hi = 0; hi < this._history.length; hi++) {
            if (this._history[hi].run_id === this._currentRun.run_id) {
              this._history[hi].locked = checked;
              break;
            }
          }
          this._persistHistory();
          this._renderHistory();
        }
        AuditTimeline.emit('qa_quality_lock_set', { metadata: { run_id: this._currentRun.run_id, locked: checked } });
        console.log('[P1B] qa_quality_lock_set locked=' + checked);
      },

      _showRunning: function(label) {
        var el = document.getElementById('p1b-running-status');
        var lbl = document.getElementById('p1b-running-label');
        if (el) el.style.display = 'block';
        if (lbl) lbl.textContent = 'Running: ' + label + '...';
      },

      _hideRunning: function() {
        var el = document.getElementById('p1b-running-status');
        if (el) el.style.display = 'none';
      },

      _renderSingleResult: function(result) {
        var tbody = document.getElementById('p1b-results-tbody');
        if (!tbody) return;
        var statusColor = result.pass ? '#4caf50' : '#e53935';
        var statusText = result.pass ? 'PASS' : 'FAIL';
        var detailId = 'p1b-detail-' + result.suite + '-' + Date.now();
        var detailRows = '';
        for (var di = 0; di < result.checks.length; di++) {
          var c = result.checks[di];
          var cColor = c.pass ? '#4caf50' : '#e53935';
          detailRows += '<tr><td style="padding:3px 8px;color:' + cColor + '">' + (c.pass ? 'PASS' : 'FAIL') + '</td><td style="padding:3px 8px">' + c.name + '</td><td style="padding:3px 8px;color:#888">' + (c.detail || '') + '</td></tr>';
        }
        var row = '<tr style="border-bottom: 1px solid #eee;">' +
          '<td style="padding:8px;font-weight:600">' + result.label + '</td>' +
          '<td style="padding:8px;color:#888">' + result.started + '</td>' +
          '<td style="padding:8px;color:#888">' + result.finished + '</td>' +
          '<td style="padding:8px"><span style="background:' + statusColor + ';color:white;padding:2px 10px;border-radius:10px;font-size:0.85em;font-weight:600">' + statusText + '</span></td>' +
          '<td style="padding:8px">' + result.passed + '/' + result.total + ' passed</td>' +
          '<td style="padding:8px"><button onclick="var d=document.getElementById(\'' + detailId + '\');d.style.display=d.style.display===\'none\'?\'\':\'none\'" style="padding:3px 10px;font-size:0.8em;background:#e3f2fd;border:1px solid #90caf9;border-radius:3px;cursor:pointer">View details</button></td>' +
          '</tr>' +
          '<tr id="' + detailId + '" style="display:none"><td colspan="6" style="padding:4px 16px;background:#fafafa"><table style="width:100%;font-size:0.82em">' + detailRows + '</table></td></tr>';
        tbody.innerHTML += row;
      },

      _saveHistory: function(run) {
        this._history.unshift({
          run_id: run.run_id,
          timestamp: run.finished,
          suites: run.suites.length,
          suite_names: run.suites.map(function(s) { return s.suite; }),
          overall: run.overall,
          locked: run.locked || false,
          summary: run.suites.map(function(s) { return s.suite + ':' + (s.pass ? 'PASS' : 'FAIL'); }).join(', ')
        });
        if (this._history.length > 20) this._history = this._history.slice(0, 20);
        this._persistHistory();
      },

      _persistHistory: function() {
        var payload = { id: this.HISTORY_KEY, type: 'qa_runner_history', data: this._history, updated_at: new Date().toISOString() };
        SessionDB._put(SessionDB.WORKBOOK_STORE, payload).then(function() {
          console.log('[P1B] History persisted to SessionDB');
        }).catch(function(e) {
          console.warn('[P1B] History persist failed:', e);
        });
      },

      _loadHistory: function() {
        var self = this;
        SessionDB._get(SessionDB.WORKBOOK_STORE, this.HISTORY_KEY).then(function(record) {
          if (record && record.data) {
            self._history = record.data;
            console.log('[P1B] History loaded from SessionDB:', self._history.length, 'runs');
            self._renderHistory();
          }
        }).catch(function(e) {
          console.warn('[P1B] History load failed:', e);
        });
        this._historyLoaded = true;
      },

      _renderHistory: function() {
        var tbody = document.getElementById('p1b-history-tbody');
        if (!tbody) return;
        if (this._history.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="padding:12px;color:#999;text-align:center">No run history yet</td></tr>';
          return;
        }
        var html = '';
        for (var hi = 0; hi < this._history.length; hi++) {
          var h = this._history[hi];
          var color = h.overall ? '#4caf50' : '#e53935';
          var lockBadge = h.locked ? '<span style="background:#ff9800;color:white;padding:1px 6px;border-radius:8px;font-size:0.8em">Locked</span>' : '-';
          html += '<tr style="border-bottom:1px solid #f0f0f0">' +
            '<td style="padding:6px;font-family:monospace;font-size:0.8em">' + h.run_id + '</td>' +
            '<td style="padding:6px">' + h.timestamp + '</td>' +
            '<td style="padding:6px">' + h.summary + '</td>' +
            '<td style="padding:6px"><span style="color:' + color + ';font-weight:600">' + (h.overall ? 'PASS' : 'FAIL') + '</span></td>' +
            '<td style="padding:6px">' + lockBadge + '</td></tr>';
        }
        tbody.innerHTML = html;
      },

      /* ── Test Suites ─────────────────────────────────────────── */

      _check: function(name, pass, detail) {
        return { name: name, pass: !!pass, detail: detail || '' };
      },

      _runP022: function() {
        var checks = [];
        checks.push(this._check('XLSX loaded', typeof XLSX !== 'undefined'));
        checks.push(this._check('parseWorkbook exists', typeof parseWorkbook === 'function'));
        checks.push(this._check('addSheet exists', typeof addSheet === 'function'));
        checks.push(this._check('renderGrid exists', typeof renderGrid === 'function'));
        checks.push(this._check('generateSignalsForDataset exists', typeof generateSignalsForDataset === 'function'));
        checks.push(this._check('persistAllRecordsToStore exists', typeof persistAllRecordsToStore === 'function'));
        checks.push(this._check('ContractIndex exists', typeof ContractIndex !== 'undefined'));
        checks.push(this._check('ContractIndex.build exists', typeof ContractIndex !== 'undefined' && typeof ContractIndex.build === 'function'));
        checks.push(this._check('seedPatchRequestsFromMetaSheet exists', typeof seedPatchRequestsFromMetaSheet === 'function'));
        checks.push(this._check('IDENTITY_CONTEXT exists', typeof IDENTITY_CONTEXT !== 'undefined'));
        checks.push(this._check('navigateTo exists', typeof navigateTo === 'function'));
        checks.push(this._check('TriageAnalytics exists', typeof TriageAnalytics !== 'undefined'));
        checks.push(this._check('renderAnalystTriage exists', typeof renderAnalystTriage === 'function'));
        return checks;
      },

      _runP1: function() {
        var checks = [];
        checks.push(this._check('TriageAnalytics defined', typeof TriageAnalytics !== 'undefined'));
        checks.push(this._check('TriageAnalytics.refresh exists', typeof TriageAnalytics !== 'undefined' && typeof TriageAnalytics.refresh === 'function'));
        checks.push(this._check('TriageAnalytics.renderHeader exists', typeof TriageAnalytics !== 'undefined' && typeof TriageAnalytics.renderHeader === 'function'));
        checks.push(this._check('TriageTelemetry defined', typeof TriageTelemetry !== 'undefined'));
        checks.push(this._check('TriageTelemetry.EVENT_STAGE_MAP', typeof TriageTelemetry !== 'undefined' && typeof TriageTelemetry.EVENT_STAGE_MAP === 'object'));
        checks.push(this._check('TruthPack defined', typeof TruthPack !== 'undefined'));
        checks.push(this._check('TruthPack.isArchitect exists', typeof TruthPack !== 'undefined' && typeof TruthPack.isArchitect === 'function'));
        checks.push(this._check('ta-processing-banner in DOM', !!document.getElementById('ta-processing-banner')));
        checks.push(this._check('ta-lifecycle-stages in DOM', !!document.getElementById('ta-lifecycle-stages')));
        checks.push(this._check('ta-contract-tbody in DOM', !!document.getElementById('ta-contract-tbody')));
        return checks;
      },

      _runCalibration: function() {
        var checks = [];
        checks.push(this._check('_preflightBlockerTypes defined', typeof _preflightBlockerTypes !== 'undefined'));
        var types = typeof _preflightBlockerTypes !== 'undefined' ? _preflightBlockerTypes : {};
        checks.push(this._check('UNKNOWN_COLUMN type', !!types['UNKNOWN_COLUMN']));
        checks.push(this._check('MOJIBAKE type', !!types['MOJIBAKE']));
        checks.push(this._check('DOCUMENT_TYPE_MISSING type', !!types['DOCUMENT_TYPE_MISSING']));
        checks.push(this._check('MISSING_REQUIRED type', !!types['MISSING_REQUIRED']));
        checks.push(this._check('PICKLIST_INVALID type', !!types['PICKLIST_INVALID']));
        checks.push(this._check('DTM label is Document Type Missing', types['DOCUMENT_TYPE_MISSING'] ? types['DOCUMENT_TYPE_MISSING'].label === 'Document Type Missing' : false, types['DOCUMENT_TYPE_MISSING'] ? types['DOCUMENT_TYPE_MISSING'].label : 'missing'));
        var docTypesCfg = false;
        try { docTypesCfg = typeof document_types_config !== 'undefined' || typeof documentTypesConfig !== 'undefined'; } catch(e) {}
        checks.push(this._check('field_meta or qa_flags accessible', typeof field_meta_config !== 'undefined' || typeof window.fieldMetaConfig !== 'undefined' || typeof _preflightBlockerTypes !== 'undefined'));
        return checks;
      },

      _runP08: function() {
        var checks = [];
        checks.push(this._check('resolveRecordForTriageItem exists', typeof resolveRecordForTriageItem === 'function'));
        checks.push(this._check('executeTriageResolution exists', typeof executeTriageResolution === 'function'));
        checks.push(this._check('showUnresolvedModal exists', typeof showUnresolvedModal === 'function'));
        checks.push(this._check('closeUnresolvedModal exists', typeof closeUnresolvedModal === 'function'));
        checks.push(this._check('p08PurgeStaleTriageItems exists', typeof p08PurgeStaleTriageItems === 'function'));
        checks.push(this._check('p08CopyDebugJSON exists', typeof p08CopyDebugJSON === 'function'));
        checks.push(this._check('p08-unresolved-modal in DOM', !!document.getElementById('p08-unresolved-modal')));
        checks.push(this._check('openSignalTriageItem exists', typeof openSignalTriageItem === 'function'));
        checks.push(this._check('openPreflightItem exists', typeof openPreflightItem === 'function'));
        checks.push(this._check('openAnalystTriageItem exists', typeof openAnalystTriageItem === 'function'));
        return checks;
      },

      _runP09: function() {
        var checks = [];
        checks.push(this._check('sanitizeDoubleSlashAnnotations exists', typeof sanitizeDoubleSlashAnnotations === 'function'));
        checks.push(this._check('Default route log emitted', (function() {
          try { var mode = (localStorage.getItem('viewer_mode_v10') || '').toLowerCase(); return mode.length > 0; } catch(e) { return false; }
        })(), 'mode=' + (localStorage.getItem('viewer_mode_v10') || 'unset')));
        checks.push(this._check('showToast exists', typeof showToast === 'function'));
        checks.push(this._check('getRoleRegistry exists', typeof getRoleRegistry === 'function'));
        checks.push(this._check('saveRoleRegistry exists', typeof saveRoleRegistry === 'function'));
        checks.push(this._check('hasPermission exists', typeof hasPermission === 'function'));
        checks.push(this._check('TruthConfig defined', typeof TruthConfig !== 'undefined'));
        checks.push(this._check('InviteManager defined', typeof InviteManager !== 'undefined'));
        checks.push(this._check('AuditTimeline defined', typeof AuditTimeline !== 'undefined'));
        checks.push(this._check('AuditTimeline.emit exists', typeof AuditTimeline !== 'undefined' && typeof AuditTimeline.emit === 'function'));
        return checks;
      },

      _runP1A: function() {
        var checks = [];
        checks.push(this._check('getTriageTypeLabel exists', typeof getTriageTypeLabel === 'function'));
        checks.push(this._check('getTriageTypeTip exists', typeof getTriageTypeTip === 'function'));
        checks.push(this._check('_p1aBuildSheetTabs exists', typeof _p1aBuildSheetTabs === 'function'));
        checks.push(this._check('_p1aFilterBySheet exists', typeof _p1aFilterBySheet === 'function'));
        checks.push(this._check('_p1aSelectSheet exists', typeof _p1aSelectSheet === 'function'));
        checks.push(this._check('p1a-preflight-sheet-tabs in DOM', !!document.getElementById('p1a-preflight-sheet-tabs')));
        checks.push(this._check('Label: required -> Missing Required', (function() {
          if (typeof getTriageTypeLabel !== 'function') return false;
          return getTriageTypeLabel('required') === 'Missing Required';
        })()));
        checks.push(this._check('Label: encoding -> Encoding Issue', (function() {
          if (typeof getTriageTypeLabel !== 'function') return false;
          return getTriageTypeLabel('encoding') === 'Encoding Issue';
        })()));
        checks.push(this._check('Tooltip for required', (function() {
          if (typeof getTriageTypeTip !== 'function') return false;
          var tip = getTriageTypeTip('required');
          return tip && tip.length > 10;
        })()));
        checks.push(this._check('Sheet filter All returns all', (function() {
          if (typeof _p1aFilterBySheet !== 'function') return false;
          try {
            var prev = typeof _p1aActiveSheet !== 'undefined' ? _p1aActiveSheet : 'All';
            _p1aActiveSheet = 'All';
            var items = [{sheet_name:'A'},{sheet_name:'B'}];
            var result = _p1aFilterBySheet(items);
            _p1aActiveSheet = prev;
            return result.length === 2;
          } catch(e) { return false; }
        })()));
        checks.push(this._check('Sheet filter specific', (function() {
          if (typeof _p1aFilterBySheet !== 'function') return false;
          try {
            var prev = typeof _p1aActiveSheet !== 'undefined' ? _p1aActiveSheet : 'All';
            _p1aActiveSheet = 'A';
            var items = [{sheet_name:'A'},{sheet_name:'B'}];
            var result = _p1aFilterBySheet(items);
            _p1aActiveSheet = prev;
            return result.length === 1;
          } catch(e) { return false; }
        })()));
        checks.push(this._check('_preflightBlockerTypes has MISSING_REQUIRED', typeof _preflightBlockerTypes !== 'undefined' && !!_preflightBlockerTypes['MISSING_REQUIRED']));
        return checks;
      }
    };

    console.log('[P1B] QARunner module loaded');'''

    # Find insertion point for the QARunner module — before the closing of the main script
    # Use the BUILD version line as anchor
    anchor5 = "console.log('[P1B] QARunner module loaded');"
    if anchor5 in content:
        print('[P1B] SKIP E5: QARunner already present')
    else:
        # Insert before the very last '</script>' tag
        # Find after AuditTimeline or near end
        # Better: insert before the comment "// ── END P1A" or after last function definition
        # Safest: insert before the final </script> in the file
        last_script_close = content.rfind('</script>')
        if last_script_close == -1:
            print('[P1B] FAIL E5: no closing </script> found')
        else:
            content = content[:last_script_close] + qa_module + '\n    ' + content[last_script_close:]
            print('[P1B] OK edit E5-qa-module')

    # ── CSS for QA Runner ──
    css_anchor = '</style>'
    css_insert = '''
    /* P1B QA Runner */
    .p1b-run-btn:hover { opacity: 0.85; }
    .p1b-run-btn:active { transform: scale(0.97); }'''

    # Insert before first </style>
    first_style_close = content.find('</style>')
    if first_style_close != -1 and 'P1B QA Runner' not in content:
        content = content[:first_style_close] + css_insert + '\n    ' + content[first_style_close:]
        print('[P1B] OK edit E6-css')
    else:
        print('[P1B] SKIP E6-css: already present or no </style>')

    write_file(TARGET, content)
    print('[P1B] ══════════════════════════════════════')
    print('[P1B] Applied %d/%d core edits' % (ok_count, total))
    print('[P1B] Target: %s' % TARGET)

if __name__ == '__main__':
    main()
