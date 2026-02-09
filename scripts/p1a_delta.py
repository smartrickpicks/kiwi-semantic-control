#!/usr/bin/env python3
"""
P1A Delta — Triage Clarity + Sheet-Scoped Pre-Flight
Applies targeted edits to ui/viewer/index.html on top of GREEN P0.9.

Changes:
  1. Pre-Flight table label cleanup (human-readable Type, tooltip for internal code)
  2. Pre-Flight sheet tabs (All + per-sheet with counts)
  3. Record column clarity (Contract + Sheet:Row or Batch-level)
  4. Schema snapshot deep-link inline explanation
  5. Hover explanations on reason chips
  6. sheet_name propagation on preflight blocker items
"""

import re, sys, os

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read_html():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def write_html(content):
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def apply_edit(html, label, old, new):
    if old not in html:
        print(f'  [FAIL] Edit {label}: old string not found')
        sys.exit(1)
    count = html.count(old)
    if count > 1:
        print(f'  [WARN] Edit {label}: {count} matches, replacing first only')
        idx = html.index(old)
        html = html[:idx] + new + html[idx + len(old):]
    else:
        html = html.replace(old, new)
    print(f'  [OK] Edit {label}')
    return html

def apply_edit_all(html, label, old, new):
    if old not in html:
        print(f'  [FAIL] Edit {label}: old string not found')
        sys.exit(1)
    count = html.count(old)
    html = html.replace(old, new)
    print(f'  [OK] Edit {label} ({count} replacements)')
    return html

def main():
    html = read_html()
    print('P1A Delta: Triage Clarity + Sheet-Scoped Pre-Flight')
    print('=' * 60)

    # ─── EDIT 1: Human-readable type labels ───
    html = apply_edit(html, '1-type-labels',
        """    function getTriageTypeLabel(type) {
      switch (type) {
        case 'rfi': return 'RFI';
        case 'blacklist': return 'Blacklist';
        case 'qa': return 'QA';
        case 'required': return 'Required';
        case 'picklist': return 'Picklist';
        case 'encoding': return 'Encoding';
        case 'correction': return 'Correction';
        case 'extraction': return 'Extraction';
        case 'logic': return 'Logic';
        case 'preflight_blocker': return 'Pre-Flight';
        default: return type ? type.charAt(0).toUpperCase() + type.slice(1) : 'Signal';
      }
    }""",
        """    var _p1aLabelMap = {
      'rfi': { label: 'RFI', tip: 'Request for Information — analyst needs clarification' },
      'blacklist': { label: 'Blacklisted', tip: 'Field or value is on the exclusion list' },
      'qa': { label: 'QA Flag', tip: 'Quality assurance flag from qa_flags.json rules' },
      'required': { label: 'Missing Required', tip: 'Required field is missing or empty (field_meta.json)' },
      'picklist': { label: 'Invalid Picklist', tip: 'Value not in allowed picklist options' },
      'encoding': { label: 'Encoding Issue', tip: 'Character encoding problem detected' },
      'correction': { label: 'Correction', tip: 'Value correction suggested by system rules' },
      'extraction': { label: 'Extraction Error', tip: 'Data extraction from source document failed or is suspect' },
      'logic': { label: 'Logic Flag', tip: 'Business logic rule triggered a warning' },
      'preflight_blocker': { label: 'Pre-Flight', tip: 'Pre-flight blocker — must resolve before proceeding' }
    };
    function getTriageTypeLabel(type) {
      var entry = _p1aLabelMap[type];
      if (entry) return entry.label;
      return type ? type.charAt(0).toUpperCase() + type.slice(1) : 'Signal';
    }
    function getTriageTypeTip(type) {
      var entry = _p1aLabelMap[type];
      return entry ? entry.tip : '';
    }""")

    # ─── EDIT 2: Type badge in table row — add tooltip ───
    html = apply_edit(html, '2-type-badge-tooltip',
        """'<td style="padding: 10px 12px;"><span style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: 600; background: ' + typeBadgeColor + '15; color: ' + typeBadgeColor + ';">' + typeLabel + '</span>' + preflightBadge + '</td>'""",
        """'<td style="padding: 10px 12px;"><span style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: 600; background: ' + typeBadgeColor + '15; color: ' + typeBadgeColor + ';" title="' + getTriageTypeTip(item.type) + '">' + typeLabel + '</span>' + preflightBadge + '</td>'""")

    # ─── EDIT 3: Record column — Contract + Sheet:Row or Batch-level ───
    html = apply_edit(html, '3-record-clarity',
        """        var recordDisplay = item.contract_key || item.record_id || 'Unknown';
        if (recordDisplay.length > 20) recordDisplay = recordDisplay.substring(0, 18) + '...';""",
        """        var recordDisplay = '';
        if (isPreFlight) {
          var _ck = item.contract_key || item.contract_id || '';
          var _sn = item.sheet_name || '';
          var _ri = (item.row_index !== undefined && item.row_index !== null && item.row_index >= 0) ? item.row_index : -1;
          if (_ck && _sn && _ri >= 0) {
            recordDisplay = _ck.substring(0, 12) + ' ' + _sn + ':' + _ri;
          } else if (_ck && _sn) {
            recordDisplay = _ck.substring(0, 12) + ' ' + _sn;
          } else if (_ck) {
            recordDisplay = _ck.substring(0, 18);
          } else {
            recordDisplay = 'Batch-level';
          }
        } else {
          recordDisplay = item.contract_key || item.record_id || 'Unknown';
        }
        if (recordDisplay.length > 28) recordDisplay = recordDisplay.substring(0, 26) + '...';""")

    # ─── EDIT 4: Reason column — human-readable blocker label + hover ───
    html = apply_edit(html, '4-reason-hover',
        """'<td style="padding: 10px 12px; font-size: 0.82em;">' + (isPreFlight && item.blocker_type ? '<span style="display:inline-block; padding: 2px 7px; border-radius: 3px; background: #fff3e0; color: #e65100; font-size: 0.85em; font-weight: 500;">' + (item.blocker_type || '').replace(/_/g, ' ') + '</span>' : (item.reason_summary || item.signal_type || '-')) + '</td>'""",
        """'<td style="padding: 10px 12px; font-size: 0.82em;">' + (isPreFlight && item.blocker_type ? (function() { var _bt = _preflightBlockerTypes[item.blocker_type] || {}; var _reasonLabel = _bt.label || (item.blocker_type || '').replace(/_/g, ' '); var _reasonTip = _bt.desc || item.message || ''; return '<span style="display:inline-block; padding: 2px 7px; border-radius: 3px; background: #fff3e0; color: #e65100; font-size: 0.85em; font-weight: 500; cursor: help;" title="' + _reasonTip.replace(/"/g, '&quot;') + '">' + _reasonLabel + '</span>'; })() : (item.reason_summary || item.signal_type || '-')) + '</td>'""")

    # ─── EDIT 5: Add sheet_name to UNKNOWN_COLUMN blocker items ───
    html = apply_edit(html, '5a-sheet-name-unknown-col',
        """              analystTriageState.manualItems.push({
                request_id: 'preflight_unk_' + c.contract_id + '_' + uc.column,
                type: 'preflight_blocker',
                signal_type: 'UNKNOWN_COLUMN',
                record_id: c.contract_id,
                field_name: uc.column,
                severity: ucSeverity,
                message: 'Unknown column: ' + uc.column + ' (sheet: ' + uc.sheet + ', non-empty: ' + uc.non_empty + ', severity: ' + ucSeverity + ')',
                status: 'open',
                updated_at: new Date().toISOString(),
                source: 'preflight',
                note_type: 'Pre-Flight Blocker',
                blocker_type: 'UNKNOWN_COLUMN',
                can_create_patch: true
              });""",
        """              analystTriageState.manualItems.push({
                request_id: 'preflight_unk_' + c.contract_id + '_' + uc.column,
                type: 'preflight_blocker',
                signal_type: 'UNKNOWN_COLUMN',
                record_id: c.contract_id,
                contract_id: c.contract_id,
                contract_key: c.contract_id,
                field_name: uc.column,
                sheet_name: uc.sheet || '',
                severity: ucSeverity,
                message: 'Unknown column: ' + uc.column + ' (sheet: ' + uc.sheet + ', non-empty: ' + uc.non_empty + ', severity: ' + ucSeverity + ')',
                status: 'open',
                updated_at: new Date().toISOString(),
                source: 'preflight',
                note_type: 'Pre-Flight Blocker',
                blocker_type: 'UNKNOWN_COLUMN',
                can_create_patch: true
              });""")

    # ─── EDIT 5b: Add sheet_name to OCR/extraction blocker items ───
    html = apply_edit(html, '5b-sheet-name-extraction',
        """                analystTriageState.manualItems.push({
                  request_id: 'preflight_' + bt.toLowerCase() + '_' + c.contract_id + '_' + (sig.field || sig.sheet || ''),
                  type: 'preflight_blocker',
                  signal_type: bt,
                  record_id: c.contract_id,
                  field_name: sig.field || '',
                  severity: bt === 'LOW_CONFIDENCE' ? 'warning' : 'blocker',""",
        """                analystTriageState.manualItems.push({
                  request_id: 'preflight_' + bt.toLowerCase() + '_' + c.contract_id + '_' + (sig.field || sig.sheet || ''),
                  type: 'preflight_blocker',
                  signal_type: bt,
                  record_id: c.contract_id,
                  contract_id: c.contract_id,
                  contract_key: c.contract_id,
                  field_name: sig.field || '',
                  sheet_name: sig.sheet || '',
                  severity: bt === 'LOW_CONFIDENCE' ? 'warning' : 'blocker',""")

    # ─── EDIT 6: Pre-Flight queue HTML — add sheet tab bar ───
    html = apply_edit(html, '6-sheet-tabs-html',
        """          <!-- QUEUE 1: Pre-Flight -->
          <div class="triage-queue-section" style="margin-bottom: 24px;">
            <div class="queue-header" style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
              <h3 style="margin: 0; font-size: 1.05em; color: #333;">Pre-Flight <span id="manual-queue-count" style="font-weight: 400; color: #666;">(0)</span></h3>
            </div>""",
        """          <!-- QUEUE 1: Pre-Flight -->
          <div class="triage-queue-section" style="margin-bottom: 24px;">
            <div class="queue-header" style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
              <h3 style="margin: 0; font-size: 1.05em; color: #333;">Pre-Flight <span id="manual-queue-count" style="font-weight: 400; color: #666;">(0)</span></h3>
            </div>
            <div id="p1a-preflight-sheet-tabs" style="display: flex; gap: 4px; margin-bottom: 10px; flex-wrap: wrap; font-size: 0.82em;"></div>""")

    # ─── EDIT 7: renderAnalystTriage — build sheet tabs + filter ───
    html = apply_edit(html, '7-sheet-tab-logic',
        """      renderTriageQueueTable(analystTriageState.manualItems, 'manual-queue-list', 'No pre-flight items', true);""",
        """      _p1aBuildSheetTabs(analystTriageState.manualItems);
      var _p1aFiltered = _p1aFilterBySheet(analystTriageState.manualItems);
      renderTriageQueueTable(_p1aFiltered, 'manual-queue-list', 'No pre-flight items', true);""")

    # ─── EDIT 8: Insert P1A sheet tab functions (before renderAnalystTriage) ───
    html = apply_edit(html, '8-sheet-tab-functions',
        """    function renderAnalystTriage() {""",
        """    var _p1aActiveSheet = 'All';

    function _p1aBuildSheetTabs(items) {
      var container = document.getElementById('p1a-preflight-sheet-tabs');
      if (!container) return;
      var sheetCounts = {};
      var totalCount = items.length;
      for (var i = 0; i < items.length; i++) {
        var sn = items[i].sheet_name || 'Unknown';
        sheetCounts[sn] = (sheetCounts[sn] || 0) + 1;
      }
      var sheets = Object.keys(sheetCounts).sort();
      var tabsHtml = '<button class="p1a-sheet-tab' + (_p1aActiveSheet === 'All' ? ' active' : '') + '" onclick="_p1aSelectSheet(\'All\')" style="padding: 4px 10px; border: 1px solid ' + (_p1aActiveSheet === 'All' ? '#1565c0' : '#ccc') + '; background: ' + (_p1aActiveSheet === 'All' ? '#e3f2fd' : '#f5f5f5') + '; color: ' + (_p1aActiveSheet === 'All' ? '#1565c0' : '#666') + '; border-radius: 14px; cursor: pointer; font-weight: 600; font-size: 0.9em;">All <span style="font-weight: 400;">(' + totalCount + ')</span></button>';
      for (var s = 0; s < sheets.length; s++) {
        var sName = sheets[s];
        var isActive = _p1aActiveSheet === sName;
        tabsHtml += '<button class="p1a-sheet-tab' + (isActive ? ' active' : '') + '" onclick="_p1aSelectSheet(\'' + sName.replace(/'/g, "\\'") + '\')" style="padding: 4px 10px; border: 1px solid ' + (isActive ? '#1565c0' : '#ccc') + '; background: ' + (isActive ? '#e3f2fd' : '#f5f5f5') + '; color: ' + (isActive ? '#1565c0' : '#666') + '; border-radius: 14px; cursor: pointer; font-weight: 500; font-size: 0.9em;">' + sName + ' <span style="font-weight: 400;">(' + sheetCounts[sName] + ')</span></button>';
      }
      container.innerHTML = tabsHtml;
      console.log('[P1A] preflight_sheet_tabs_built: total=' + totalCount + ', sheets=' + sheets.length + ', active=' + _p1aActiveSheet);
    }

    function _p1aFilterBySheet(items) {
      if (_p1aActiveSheet === 'All') return items;
      var filtered = [];
      for (var i = 0; i < items.length; i++) {
        var sn = items[i].sheet_name || 'Unknown';
        if (sn === _p1aActiveSheet) filtered.push(items[i]);
      }
      return filtered;
    }

    function _p1aSelectSheet(sheetName) {
      _p1aActiveSheet = sheetName;
      console.log('[P1A] preflight_sheet_filter: sheet=' + sheetName);
      renderAnalystTriage();
    }

    function renderAnalystTriage() {""")

    # ─── EDIT 9: Schema deep-link — batch-level explanation ───
    html = apply_edit(html, '9-schema-deeplink',
        """      handleSchemaClick: function(type) {
        console.log('[TRIAGE-ANALYTICS][P0.2] snapshot_filter_applied: type=' + type);
        var emptyState = document.getElementById('ta-schema-empty-state');
        if (emptyState) emptyState.style.display = 'none';
        var targetFilter = type === 'unknown' ? 'preflight' : (type === 'missing' ? 'blocked' : 'needs_review');
        var count = 0;
        var cache = this.getCache();
        if (type === 'unknown') count = cache.schema.unknown_columns;
        else if (type === 'missing') count = cache.schema.missing_required;
        else if (type === 'drift') count = cache.schema.schema_drift;
        if (count === 0 && emptyState) {
          emptyState.style.display = '';
          var _emptyReasons = {
            unknown: 'No unknown columns detected. All imported columns match the canonical schema.',
            missing: 'No missing required fields. All required fields from field_meta.json are present in the active dataset.',
            drift: 'No schema drift detected. This may indicate batch-level drift only — check Admin > Schema Tree for cross-batch comparison.'
          };
          emptyState.textContent = _emptyReasons[type] || 'No items found for this filter.';
          return;
        }
        navigateToGridFiltered(targetFilter);
      },""",
        """      handleSchemaClick: function(type) {
        console.log('[TRIAGE-ANALYTICS][P0.2] snapshot_filter_applied: type=' + type);
        var emptyState = document.getElementById('ta-schema-empty-state');
        if (emptyState) emptyState.style.display = 'none';
        var targetFilter = type === 'unknown' ? 'preflight' : (type === 'missing' ? 'blocked' : 'needs_review');
        var count = 0;
        var cache = this.getCache();
        if (type === 'unknown') count = cache.schema.unknown_columns;
        else if (type === 'missing') count = cache.schema.missing_required;
        else if (type === 'drift') count = cache.schema.schema_drift;
        if (count === 0 && emptyState) {
          emptyState.style.display = '';
          var _emptyReasons = {
            unknown: 'No unknown columns detected. All imported columns match the canonical schema.',
            missing: 'No missing required fields. All required fields from field_meta.json are present in the active dataset.',
            drift: 'No schema drift detected. This is batch-level drift; no record row available. Check Admin > Schema Tree for cross-batch comparison.'
          };
          emptyState.textContent = _emptyReasons[type] || 'No items found for this filter.';
          console.log('[P1A] schema_deeplink_empty: type=' + type + ', reason=batch_level_no_rows');
          return;
        }
        var _hasRowTarget = false;
        if (type === 'unknown' || type === 'drift') {
          var _pfItems = analystTriageState.manualItems || [];
          for (var _si = 0; _si < _pfItems.length; _si++) {
            if (_pfItems[_si].blocker_type === 'UNKNOWN_COLUMN' && _pfItems[_si].row_index >= 0) {
              _hasRowTarget = true;
              break;
            }
          }
          if (!_hasRowTarget && emptyState) {
            emptyState.style.display = '';
            emptyState.textContent = count + ' ' + type + ' item(s) found. This is batch-level drift; no individual record row available. Items are listed in the Pre-Flight queue below.';
            console.log('[P1A] schema_deeplink_batch_level: type=' + type + ', count=' + count);
            return;
          }
        }
        console.log('[P1A] schema_deeplink_navigate: type=' + type + ', filter=' + targetFilter);
        navigateToGridFiltered(targetFilter);
      },""")

    # ─── EDIT 10: CSS for sheet tabs ───
    html = apply_edit(html, '10-sheet-tab-css',
        """    .preflight-checklist { margin-bottom: 15px; }""",
        """    .p1a-sheet-tab { transition: all 0.15s ease; }
    .p1a-sheet-tab:hover { border-color: #1565c0 !important; color: #1565c0 !important; }
    .preflight-checklist { margin-bottom: 15px; }""")

    # ─── EDIT 11: Update manual queue count to show filtered count ───
    html = apply_edit(html, '11-filtered-count',
        """      var manualCount = analystTriageState.manualItems.length;""",
        """      var _p1aFilteredItems = _p1aFilterBySheet(analystTriageState.manualItems);
      var manualCount = _p1aFilteredItems.length;""")

    # ─── EDIT 12: Add DOCUMENT_TYPE_MISSING + MISSING_REQUIRED to blocker types ───
    _e12_old = "DOCUMENT_TYPE_MISSING: { label: 'Document Type', badge: 'warn', icon: '\\ud83d\\udcc4', desc: 'Document type not assigned or not recognized. Assign a valid document type before proceeding.' }\n      };"
    _e12_new = "DOCUMENT_TYPE_MISSING: { label: 'Document Type Missing', badge: 'warn', icon: '\\ud83d\\udcc4', desc: 'Document type not assigned or not recognized. Assign a valid document type before proceeding.' },\n        MISSING_REQUIRED: { label: 'Missing Required', badge: 'fail', icon: '\\u2757', desc: 'A required field defined in field_meta.json is missing or empty in this record.' },\n        PICKLIST_INVALID: { label: 'Invalid Picklist', badge: 'warn', icon: '\\ud83d\\udcdd', desc: 'Field value does not match any allowed option in the picklist.' }\n      };"
    html = apply_edit(html, '12-blocker-type-missing-required', _e12_old, _e12_new)

    # ─── VERIFY ───
    print('=' * 60)
    print('P1A Delta: 12 edits applied successfully')
    write_html(html)
    print('Written to:', os.path.abspath(HTML_PATH))

if __name__ == '__main__':
    main()
