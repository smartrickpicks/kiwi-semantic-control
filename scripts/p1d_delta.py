#!/usr/bin/env python3
"""P1D Delta: Contract-Centric Pre-Flight Grouping
Applies 3 edits to ui/viewer/index.html:
  E1: CSS for P1D grouped sections
  E2: P1D grouped rendering functions + integration hook
  E3: Replace flat preflight call in renderAnalystTriage with grouped call
"""
import re, sys, os

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read_html():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def write_html(content):
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

# ─── E1: CSS for P1D grouped preflight sections ──────────────────────
P1D_CSS = """
    /* ── P1D: Contract-Centric Pre-Flight Grouping ── */
    .p1d-group { margin-bottom: 10px; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; }
    .p1d-group-header { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #fafafa; cursor: pointer; user-select: none; border-bottom: 1px solid #eee; flex-wrap: wrap; }
    .p1d-group-header:hover { background: #f0f4f8; }
    .p1d-group-caret { font-size: 0.75em; transition: transform 0.15s; display: inline-block; color: #666; }
    .p1d-group-caret.collapsed { transform: rotate(-90deg); }
    .p1d-group-name { font-weight: 600; font-size: 0.9em; color: #333; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .p1d-group-id { font-size: 0.75em; color: #888; font-family: monospace; }
    .p1d-group-count { font-size: 0.78em; color: #555; background: #e8e8e8; padding: 1px 8px; border-radius: 10px; font-weight: 600; }
    .p1d-group-sheets { display: flex; gap: 4px; margin-left: auto; flex-wrap: wrap; }
    .p1d-sheet-chip { font-size: 0.7em; padding: 1px 7px; border-radius: 10px; font-weight: 500; background: #e3f2fd; color: #1565c0; }
    .p1d-group-body { overflow: hidden; }
    .p1d-group-body.collapsed { display: none; }
    .p1d-group-body table { width: 100%; border-collapse: collapse; font-size: 0.84em; }
    .p1d-group-body table th { padding: 6px 10px; text-align: left; font-weight: 600; color: #555; background: #f9f9f9; border-bottom: 1px solid #e0e0e0; font-size: 0.9em; }
    .p1d-group-body table td { padding: 7px 10px; border-bottom: 1px solid #f0f0f0; }
    .p1d-group-body table tr:hover { background: #fafafa; }
    .p1d-group-body table tr { cursor: pointer; }
    .p1d-domain-hint { font-size: 0.72em; color: #999; margin-left: 4px; }
    .p1d-empty-state { text-align: center; padding: 30px; color: #999; font-size: 0.9em; }
"""

# ─── E2: P1D helper functions ────────────────────────────────────────
P1D_HELPERS = """
    // ═══ P1D: Contract-Centric Pre-Flight Grouping ═══
    var _p1dGroupState = {};

    function _p1dToggleGroup(groupId) {
      console.log('[P1D-PREFLIGHT] group_toggled: ' + groupId);
      var sec = document.querySelector('.p1d-group[data-group-id="' + groupId + '"]');
      if (!sec) return;
      var body = sec.querySelector('.p1d-group-body');
      var caret = sec.querySelector('.p1d-group-caret');
      var isCollapsed = body.classList.contains('collapsed');
      if (isCollapsed) {
        body.classList.remove('collapsed');
        if (caret) caret.classList.remove('collapsed');
        _p1dGroupState[groupId] = false;
      } else {
        body.classList.add('collapsed');
        if (caret) caret.classList.add('collapsed');
        _p1dGroupState[groupId] = true;
      }
    }

    function _p1dGetGroupKey(item) {
      if (item.contract_id || item.contract_key) return item.contract_id || item.contract_key;
      var fu = item.file_url || '';
      var fn = item.file_name || '';
      if (fu) return 'file:' + fu;
      if (fn) return 'file:' + fn;
      return '_batch_level';
    }

    function _p1dGetDisplayName(groupKey, items) {
      if (groupKey === '_batch_level') return 'Batch-level Issues';
      if (groupKey.indexOf('file:') === 0) {
        var raw = groupKey.substring(5);
        return raw.length > 50 ? raw.substring(0, 48) + '...' : raw;
      }
      var sample = items[0];
      var fn = sample.file_name || '';
      if (fn) return fn.length > 50 ? fn.substring(0, 48) + '...' : fn;
      return groupKey.length > 40 ? groupKey.substring(0, 38) + '...' : groupKey;
    }

    function _p1dGetDomainHint(items) {
      for (var i = 0; i < items.length; i++) {
        var u = items[i].file_url || '';
        if (u) {
          try {
            var m = u.match(/^https?:\\/\\/([^\\/]+)/);
            if (m) return m[1];
          } catch(e) {}
        }
      }
      return '';
    }

    function _p1dRenderGrouped(items, containerId) {
      var container = document.getElementById(containerId);
      if (!container) return;

      if (items.length === 0) {
        container.innerHTML = '<div class="p1d-empty-state">No pre-flight items</div>';
        return;
      }

      var groups = {};
      var groupOrder = [];
      for (var i = 0; i < items.length; i++) {
        var key = _p1dGetGroupKey(items[i]);
        if (!groups[key]) {
          groups[key] = [];
          groupOrder.push(key);
        }
        groups[key].push(items[i]);
      }

      groupOrder.sort(function(a, b) {
        if (a === '_batch_level') return 1;
        if (b === '_batch_level') return -1;
        return groups[b].length - groups[a].length;
      });

      var html = '';
      for (var gi = 0; gi < groupOrder.length; gi++) {
        var gk = groupOrder[gi];
        var gItems = groups[gk];
        var groupId = 'p1d-g-' + gi;
        var defaultCollapsed = gi >= 5;
        var isCollapsed = _p1dGroupState[groupId] !== undefined ? _p1dGroupState[groupId] : defaultCollapsed;

        var displayName = _p1dGetDisplayName(gk, gItems);
        var compactId = gk === '_batch_level' ? '' : (gk.length > 20 ? gk.substring(0, 18) + '...' : gk);
        var domainHint = _p1dGetDomainHint(gItems);

        var sheetCounts = {};
        for (var si = 0; si < gItems.length; si++) {
          var sn = gItems[si].sheet_name || 'Unknown';
          sheetCounts[sn] = (sheetCounts[sn] || 0) + 1;
        }
        var sheetChips = '';
        var sheetNames = Object.keys(sheetCounts).sort();
        for (var sc = 0; sc < sheetNames.length; sc++) {
          sheetChips += '<span class="p1d-sheet-chip">' + escapeHtml(sheetNames[sc]) + ' (' + sheetCounts[sheetNames[sc]] + ')</span>';
        }

        var caretClass = 'p1d-group-caret' + (isCollapsed ? ' collapsed' : '');
        var bodyClass = 'p1d-group-body' + (isCollapsed ? ' collapsed' : '');

        html += '<div class="p1d-group" data-group-id="' + groupId + '" data-group-key="' + escapeHtml(gk) + '">';
        html += '<div class="p1d-group-header" onclick="_p1dToggleGroup(' + String.fromCharCode(39) + groupId + String.fromCharCode(39) + ')">';
        html += '<span class="' + caretClass + '">&#9660;</span>';
        html += '<span class="p1d-group-name" title="' + escapeHtml(gk) + '">' + escapeHtml(displayName) + '</span>';
        if (compactId && compactId !== displayName) {
          html += '<span class="p1d-group-id" title="' + escapeHtml(gk) + '">' + escapeHtml(compactId) + '</span>';
        }
        if (domainHint) {
          html += '<span class="p1d-domain-hint">' + escapeHtml(domainHint) + '</span>';
        }
        html += '<span class="p1d-group-count">' + gItems.length + ' issue' + (gItems.length !== 1 ? 's' : '') + '</span>';
        html += '<div class="p1d-group-sheets">' + sheetChips + '</div>';
        html += '</div>';

        html += '<div class="' + bodyClass + '">';
        html += '<table><thead><tr>';
        html += '<th>Sheet</th><th>Field</th><th>Reason</th><th>Severity</th><th>Status</th><th>Actions</th>';
        html += '</tr></thead><tbody>';

        for (var ri = 0; ri < gItems.length; ri++) {
          var item = gItems[ri];
          var sName = escapeHtml(item.sheet_name || 'Unknown');
          var fName = escapeHtml(item.field_name || item.field_key || '-');

          var reasonHtml = '-';
          if (item.blocker_type && typeof _preflightBlockerTypes !== 'undefined') {
            var bt = _preflightBlockerTypes[item.blocker_type] || {};
            var rLabel = bt.label || (item.blocker_type || '').replace(/_/g, ' ');
            var rTip = (bt.desc || item.message || '').replace(/"/g, '&quot;');
            reasonHtml = '<span style="display:inline-block; padding: 2px 7px; border-radius: 3px; background: #fff3e0; color: #e65100; font-size: 0.85em; font-weight: 500; cursor: help;" title="' + rTip + '">' + escapeHtml(rLabel) + '</span>';
          } else if (item.reason_summary || item.signal_type) {
            reasonHtml = escapeHtml(item.reason_summary || item.signal_type || '-');
          }

          var sevColor = item.severity === 'blocker' ? '#c62828' : (item.severity === 'warning' ? '#f57c00' : '#666');
          var sevLabel = item.severity ? item.severity.charAt(0).toUpperCase() + item.severity.slice(1) : '-';
          var sevHtml = '<span style="color:' + sevColor + '; font-weight: 500; font-size: 0.85em;">' + sevLabel + '</span>';

          var stBadge = '<span style="display:inline-block; padding:2px 7px; border-radius:4px; font-size:0.75em; font-weight:600; background:' + (item.status_color || '#9e9e9e') + '15; color:' + (item.status_color || '#9e9e9e') + ';">' + (item.status_label || item.status || 'open') + '</span>';

          var viewHandler = 'openPreflightItem(\\'' + (item.request_id || '') + '\\', \\'' + (item.record_id || '') + '\\', \\'' + (item.contract_id || item.contract_key || '') + '\\', \\'' + (item.field_name || item.field_key || '') + '\\')';
          var patchBtn = '';
          if (item.can_create_patch && item.status === 'open') {
            patchBtn = ' <button class="btn-secondary" style="padding:2px 6px; font-size:0.72em; background:#e3f2fd; border:1px solid #bbdefb;" onclick="event.stopPropagation(); createPatchFromBlocker(\\'' + (item.request_id || '') + '\\', \\'' + (item.record_id || '') + '\\', \\'' + (item.field_name || '') + '\\', \\'' + (item.blocker_type || '') + '\\')">Patch</button>';
          }

          html += '<tr onclick="event.stopPropagation(); ' + viewHandler + '">';
          html += '<td>' + sName + '</td>';
          html += '<td>' + fName + '</td>';
          html += '<td>' + reasonHtml + '</td>';
          html += '<td>' + sevHtml + '</td>';
          html += '<td>' + stBadge + '</td>';
          html += '<td><button class="btn-secondary" style="padding:3px 8px; font-size:0.75em;" onclick="event.stopPropagation(); ' + viewHandler + '">View</button>' + patchBtn + '</td>';
          html += '</tr>';
        }

        html += '</tbody></table></div></div>';
        console.log('[P1D-PREFLIGHT] group_rendered: ' + gk + ' issues=' + gItems.length + ' sheets=' + sheetNames.length);
      }

      container.innerHTML = html;
      console.log('[P1D-PREFLIGHT] total_groups=' + groupOrder.length + ' total_items=' + items.length);
    }
"""

# ─── E3: Replace flat preflight call with grouped call ────────────────
# In renderAnalystTriage, replace:
#   renderTriageQueueTable(_p1aFiltered, 'manual-queue-list', 'No pre-flight items', true);
# with:
#   _p1dRenderGrouped(_p1aFiltered, 'p1d-preflight-container');
# Also need to swap the tbody container to a div for grouped rendering.

def apply_edits():
    html = read_html()
    edits_applied = []

    # ── E1: Insert CSS ──
    marker_css = '/* ── P1D: Contract-Centric Pre-Flight Grouping ── */'
    if marker_css not in html:
        style_close = html.rfind('</style>')
        if style_close < 0:
            print('[E1] FAIL: </style> not found'); sys.exit(1)
        html = html[:style_close] + P1D_CSS + '\n' + html[style_close:]
        edits_applied.append('E1-css')
    else:
        edits_applied.append('E1-css(skip)')

    # ── E2: Insert helper functions before P1C helpers or SRR state ──
    marker_fn = 'function _p1dRenderGrouped'
    if marker_fn not in html:
        anchor2 = '    // ═══ P1C: Contract Composite Grid'
        pos2 = html.find(anchor2)
        if pos2 < 0:
            anchor2 = '    // Single Row Review state'
            pos2 = html.find(anchor2)
        if pos2 < 0:
            print('[E2] FAIL: anchor not found'); sys.exit(1)
        html = html[:pos2] + P1D_HELPERS + '\n\n' + html[pos2:]
        edits_applied.append('E2-helpers')
    else:
        edits_applied.append('E2-helpers(skip)')

    # ── E3a: Replace tbody container with div for grouped rendering ──
    marker_container = 'id="p1d-preflight-container"'
    if marker_container not in html:
        old_tbody = '<tbody id="manual-queue-list" style="background: #fffef5;">'
        # We need to replace the entire table structure for preflight with a div
        # Find the preflight table and replace tbody with div
        old_table_block = """<div class="queue-table-container" style="border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden;">
              <table style="width: 100%; border-collapse: collapse; font-size: 0.85em; text-align: left;">
                <thead style="background: #f5f5f5; border-bottom: 1px solid #e0e0e0;">
                  <tr>
                    <th style="padding: 8px 12px;">Type</th>
                    <th style="padding: 8px 12px;">Record</th>
                    <th style="padding: 8px 12px;">Field</th>
                    <th style="padding: 8px 12px;">Reason</th>
                    <th style="padding: 8px 12px;">Status</th>
                    <th style="padding: 8px 12px;">Last Updated</th>
                    <th style="padding: 8px 12px;">Actions</th>
                  </tr>
                </thead>
                <tbody id="manual-queue-list" style="background: #fffef5;">
                  <tr><td colspan="7" style="padding: 20px; text-align: center; color: #999;">No pre-flight items</td></tr>
                </tbody>
              </table>
            </div>"""
        new_container = """<div id="p1d-preflight-container" class="p1d-preflight-container">
              <div class="p1d-empty-state">No pre-flight items</div>
            </div>"""
        if old_table_block in html:
            html = html.replace(old_table_block, new_container, 1)
            edits_applied.append('E3a-container')
        else:
            # Try line-insensitive match
            print('[E3a] WARN: exact table block not found, trying fuzzy')
            # At minimum, replace the tbody ID
            if old_tbody in html:
                html = html.replace(old_tbody, '<tbody id="manual-queue-list" data-p1d="true" style="background: #fffef5;">', 1)
                edits_applied.append('E3a-container(fallback)')
            else:
                print('[E3a] FAIL: manual-queue-list tbody not found')
                sys.exit(1)
    else:
        edits_applied.append('E3a-container(skip)')

    # ── E3b: Replace renderTriageQueueTable call with _p1dRenderGrouped ──
    old_call = "renderTriageQueueTable(_p1aFiltered, 'manual-queue-list', 'No pre-flight items', true);"
    new_call = "_p1dRenderGrouped(_p1aFiltered, 'p1d-preflight-container');"
    if old_call in html and new_call not in html:
        html = html.replace(old_call, new_call)
        edits_applied.append('E3b-render-call')
    elif new_call in html:
        edits_applied.append('E3b-render-call(skip)')
    else:
        print('[E3b] FAIL: old renderTriageQueueTable call not found')
        sys.exit(1)

    # ── E3c: Also add sheet filter log ──
    old_sheet_log = "console.log('[P1A] preflight_sheet_filter: sheet=' + sheetName);"
    new_sheet_log = "console.log('[P1A] preflight_sheet_filter: sheet=' + sheetName); console.log('[P1D-PREFLIGHT] sheet_filter_applied: ' + sheetName);"
    if '[P1D-PREFLIGHT] sheet_filter_applied' not in html:
        if old_sheet_log in html:
            html = html.replace(old_sheet_log, new_sheet_log)
            edits_applied.append('E3c-sheet-log')
        else:
            edits_applied.append('E3c-sheet-log(skip-no-anchor)')
    else:
        edits_applied.append('E3c-sheet-log(skip)')

    # ── E3d: Add view_routed log to openPreflightItem ──
    marker_view_log = '[P1D-PREFLIGHT] view_routed'
    if marker_view_log not in html:
        old_open = "function openPreflightItem(requestId, recordId, contractId, fieldName) {"
        new_open = "function openPreflightItem(requestId, recordId, contractId, fieldName) {\n      console.log('[P1D-PREFLIGHT] view_routed: contract=' + contractId + ' record=' + recordId + ' field=' + fieldName);"
        if old_open in html:
            html = html.replace(old_open, new_open)
            edits_applied.append('E3d-view-log')
        else:
            edits_applied.append('E3d-view-log(skip-no-anchor)')
    else:
        edits_applied.append('E3d-view-log(skip)')

    write_html(html)
    print('[P1D] Delta applied:', ', '.join(edits_applied))
    return edits_applied

if __name__ == '__main__':
    edits = apply_edits()
    print('[P1D] Done. Edits:', len(edits))
