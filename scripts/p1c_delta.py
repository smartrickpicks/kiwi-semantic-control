#!/usr/bin/env python3
"""P1C Delta: Contract Composite Grid (Nested Sheets, No Tabs)
Applies 4 edits to ui/viewer/index.html:
  E1: CSS for composite sections
  E2: Expand All / Collapse All controls (HTML)
  E3: Composite mode detection + section renderer in renderGrid()
  E4: Helper functions for composite mode
"""
import re, sys, os

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read_html():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def write_html(content):
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

# ─── E1: CSS for composite grid sections ───────────────────────────────
P1C_CSS = """
    /* ── P1C: Contract Composite Grid ── */
    .p1c-composite-controls { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
    .p1c-composite-controls button { padding: 4px 12px; font-size: 0.8em; border: 1px solid #ccc; border-radius: 4px; background: #f5f5f5; cursor: pointer; }
    .p1c-composite-controls button:hover { background: #e8e8e8; }
    .p1c-section { margin-bottom: 16px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
    .p1c-section-header { display: flex; align-items: center; gap: 10px; padding: 10px 16px; background: #f5f5f5; cursor: pointer; user-select: none; border-bottom: 1px solid #e0e0e0; }
    .p1c-section-header:hover { background: #eef2f7; }
    .p1c-section-caret { font-size: 0.8em; transition: transform 0.15s; display: inline-block; }
    .p1c-section-caret.collapsed { transform: rotate(-90deg); }
    .p1c-section-title { font-weight: 600; font-size: 0.95em; color: #333; }
    .p1c-section-count { font-size: 0.8em; color: #666; background: #e8e8e8; padding: 2px 8px; border-radius: 10px; }
    .p1c-section-chips { display: flex; gap: 6px; margin-left: auto; }
    .p1c-section-chip { font-size: 0.7em; padding: 1px 8px; border-radius: 10px; font-weight: 600; }
    .p1c-chip-ready { background: #e8f5e9; color: #2e7d32; }
    .p1c-chip-review { background: #fff3e0; color: #f57c00; }
    .p1c-chip-blocked { background: #ffebee; color: #c62828; }
    .p1c-section-body { overflow-x: auto; max-height: 600px; overflow-y: auto; }
    .p1c-section-body.collapsed { display: none; }
    .p1c-section-body table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
    .p1c-section-body table th { padding: 8px 12px; text-align: left; font-weight: 600; color: #333; background: #fafafa; border-bottom: 2px solid #ddd; white-space: nowrap; position: sticky; top: 0; z-index: 5; }
    .p1c-section-body table td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
    .p1c-section-body table tr:hover { background: #f8f9fa; }
    .p1c-section-body table tr.clickable { cursor: pointer; }
    .p1c-section-body table td.truncated { max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
    .p1c-section-body table td.status-ready { color: #2e7d32; }
    .p1c-section-body table td.status-needs_review { color: #f57c00; }
    .p1c-section-body table td.status-blocked { color: #c62828; }
    .p1c-section-body table td.status-finalized { color: #1565c0; }
    .p1c-section-body table td.status-flagged { color: #7b1fa2; }
    .p1c-empty-state { text-align: center; padding: 40px; color: #666; }
"""

# ─── E2: Expand All / Collapse All controls HTML ───────────────────────
P1C_CONTROLS_HTML = """
          <!-- P1C: Composite Grid Controls -->
          <div id="p1c-composite-controls" class="p1c-composite-controls" style="display: none;">
            <span style="font-size: 0.8em; color: #1565c0; font-weight: 600;">Composite View</span>
            <button onclick="_p1cExpandAll()">Expand All</button>
            <button onclick="_p1cCollapseAll()">Collapse All</button>
          </div>
"""

# ─── E3: Composite mode detection block (inserted at start of renderGrid body rendering) ───
P1C_COMPOSITE_BLOCK = """
      // ── P1C: Contract Composite Grid ──
      if (_p1cIsCompositeMode()) {
        _p1cRenderComposite(filtered, records);
        perfLog('renderGrid(composite)', perfT);
        if (typeof hideUploadLoading === 'function') hideUploadLoading();
        return;
      }
      // P1C cleanup: remove composite view when not in composite mode
      var _p1cOldRoot = document.getElementById('p1c-composite-root');
      if (_p1cOldRoot) { _p1cOldRoot.parentNode.removeChild(_p1cOldRoot); console.log('[GRID-COMPOSITE][P1C] mode_disabled'); }
      var _p1cCtrl = document.getElementById('p1c-composite-controls');
      if (_p1cCtrl) _p1cCtrl.style.display = 'none';
      var _p1cOrigTable = document.getElementById('grid-table');
      if (_p1cOrigTable) _p1cOrigTable.style.display = '';
"""

# ─── E4: Helper functions for composite mode ───────────────────────────
P1C_HELPERS = """
    // ═══ P1C: Contract Composite Grid — Helpers ═══
    var _p1cSectionState = {};

    function _p1cIsCompositeMode() {
      return _activeContractFilter && _activeContractFilter !== '' &&
             (!gridState.sheet || gridState.sheet === '' || gridState.sheet === 'all');
    }

    function _p1cExpandAll() {
      console.log('[GRID-COMPOSITE][P1C] expand_all');
      var sections = document.querySelectorAll('.p1c-section');
      for (var i = 0; i < sections.length; i++) {
        var sid = sections[i].getAttribute('data-section-id');
        _p1cSectionState[sid] = false;
        var body = sections[i].querySelector('.p1c-section-body');
        if (body) body.classList.remove('collapsed');
        var caret = sections[i].querySelector('.p1c-section-caret');
        if (caret) caret.classList.remove('collapsed');
      }
    }

    function _p1cCollapseAll() {
      console.log('[GRID-COMPOSITE][P1C] collapse_all');
      var sections = document.querySelectorAll('.p1c-section');
      for (var i = 0; i < sections.length; i++) {
        var sid = sections[i].getAttribute('data-section-id');
        _p1cSectionState[sid] = true;
        var body = sections[i].querySelector('.p1c-section-body');
        if (body) body.classList.add('collapsed');
        var caret = sections[i].querySelector('.p1c-section-caret');
        if (caret) caret.classList.add('collapsed');
      }
    }

    function _p1cToggleSection(sectionId) {
      console.log('[GRID-COMPOSITE][P1C] section_toggled: ' + sectionId);
      var sec = document.querySelector('.p1c-section[data-section-id="' + sectionId + '"]');
      if (!sec) return;
      var body = sec.querySelector('.p1c-section-body');
      var caret = sec.querySelector('.p1c-section-caret');
      var isCollapsed = body.classList.contains('collapsed');
      if (isCollapsed) {
        body.classList.remove('collapsed');
        if (caret) caret.classList.remove('collapsed');
        _p1cSectionState[sectionId] = false;
      } else {
        body.classList.add('collapsed');
        if (caret) caret.classList.add('collapsed');
        _p1cSectionState[sectionId] = true;
      }
    }

    function _p1cRenderComposite(filtered, allRecords) {
      console.log('[GRID-COMPOSITE][P1C] mode_enabled');
      var STATUS_KEYS = ['status', 'Status', 'sf_contract_status', 'review_state', 'Review_State'];

      // Show controls
      var ctrl = document.getElementById('p1c-composite-controls');
      if (ctrl) ctrl.style.display = 'flex';

      // Group rows by sheet
      var sheetMap = {};
      var sheetOrder = [];
      for (var i = 0; i < filtered.length; i++) {
        var sn = filtered[i].sheet || 'Unknown';
        if (!sheetMap[sn]) {
          sheetMap[sn] = [];
          sheetOrder.push(sn);
        }
        sheetMap[sn].push(filtered[i]);
      }
      sheetOrder.sort();

      // Hide original table, use container for composite
      var origTable = document.getElementById('grid-table');
      if (origTable) origTable.style.display = 'none';

      var container = document.querySelector('.grid-table-container');
      if (!container) return;

      // Remove previous composite content
      var old = document.getElementById('p1c-composite-root');
      if (old) old.parentNode.removeChild(old);

      if (sheetOrder.length === 0) {
        var emptyDiv = document.createElement('div');
        emptyDiv.id = 'p1c-composite-root';
        emptyDiv.className = 'p1c-empty-state';
        emptyDiv.innerHTML = '<div style="font-weight: 600; margin-bottom: 5px;">No records match filters</div>' +
          '<div style="font-size: 0.85em; color: #888;">Try adjusting the search or status filters.</div>';
        container.appendChild(emptyDiv);
        console.log('[GRID-COMPOSITE][P1C] mode_disabled reason=no_matching_rows');
        document.getElementById('grid-row-count').textContent = '0 of ' + allRecords.length + ' records';
        return;
      }

      var root = document.createElement('div');
      root.id = 'p1c-composite-root';

      for (var si = 0; si < sheetOrder.length; si++) {
        var sheetName = sheetOrder[si];
        var rows = sheetMap[sheetName];
        var sectionId = 'p1c-sheet-' + si;
        var isCollapsed = _p1cSectionState[sectionId] === true;

        // Status counts
        var ready = 0, review = 0, blocked = 0;
        for (var ri = 0; ri < rows.length; ri++) {
          var st = '';
          for (var sk = 0; sk < STATUS_KEYS.length; sk++) {
            if (rows[ri][STATUS_KEYS[sk]]) { st = rows[ri][STATUS_KEYS[sk]]; break; }
          }
          st = (st || '').toLowerCase().replace(/\\s+/g, '_');
          if (st === 'ready') ready++;
          else if (st === 'needs_review') review++;
          else if (st === 'blocked') blocked++;
        }

        // Build section
        var section = document.createElement('div');
        section.className = 'p1c-section';
        section.setAttribute('data-section-id', sectionId);
        section.setAttribute('data-sheet-name', sheetName);

        // Header
        var header = document.createElement('div');
        header.className = 'p1c-section-header';
        header.setAttribute('onclick', '_p1cToggleSection("' + sectionId + '")');
        var caretClass = 'p1c-section-caret' + (isCollapsed ? ' collapsed' : '');
        var chipsHtml = '';
        if (ready > 0) chipsHtml += '<span class="p1c-section-chip p1c-chip-ready">' + ready + ' Ready</span>';
        if (review > 0) chipsHtml += '<span class="p1c-section-chip p1c-chip-review">' + review + ' Review</span>';
        if (blocked > 0) chipsHtml += '<span class="p1c-section-chip p1c-chip-blocked">' + blocked + ' Blocked</span>';
        header.innerHTML = '<span class="' + caretClass + '">&#9660;</span>' +
          '<span class="p1c-section-title">' + escapeHtml(sheetName) + '</span>' +
          '<span class="p1c-section-count">' + rows.length + ' row' + (rows.length !== 1 ? 's' : '') + '</span>' +
          '<div class="p1c-section-chips">' + chipsHtml + '</div>';

        section.appendChild(header);

        // Body
        var bodyDiv = document.createElement('div');
        bodyDiv.className = 'p1c-section-body' + (isCollapsed ? ' collapsed' : '');

        // Determine columns for this sheet
        var columns = [];
        if (workbook.sheets[sheetName] && workbook.sheets[sheetName].headers) {
          columns = workbook.sheets[sheetName].headers.filter(function(h) {
            return h && h !== '_row_index';
          });
        } else if (rows.length > 0) {
          columns = Object.keys(rows[0]).filter(function(k) {
            return k !== '_row_index' && k !== '_originalIdx' && k !== 'sheet' && k !== '_sheetRowIndex';
          });
        }
        columns = getPreferredColumnOrder(columns);
        if (gridState.visibleColumns && gridState.allColumns) {
          columns = columns.filter(function(c) {
            return gridState.visibleColumns.indexOf(c) >= 0;
          });
        }

        // Table
        var tbl = document.createElement('table');
        tbl.className = 'grid-table';

        // Thead
        var thead = document.createElement('thead');
        var headTr = document.createElement('tr');
        headTr.innerHTML = '<th style="background: #fafafa; font-weight: 600;">#</th>';
        for (var ci = 0; ci < columns.length; ci++) {
          var col = columns[ci];
          var colLetter = getColumnLetter(ci);
          var displayName = col.replace(/_c$/i, '').replace(/_/g, ' ').replace(/\\b\\w/g, function(l) { return l.toUpperCase(); });
          if (displayName.length > 20) displayName = displayName.substring(0, 18) + '...';
          headTr.innerHTML += '<th style="min-width: 80px;">' +
            '<div style="font-size: 0.7em; color: #888; margin-bottom: 2px; font-weight: 600;">' + colLetter + '</div>' +
            '<div title="' + col + '" style="font-size: 0.85em;">' + displayName + '</div></th>';
        }
        thead.appendChild(headTr);
        tbl.appendChild(thead);

        // Tbody
        var tbody = document.createElement('tbody');
        for (var ri2 = 0; ri2 < rows.length; ri2++) {
          var r = rows[ri2];
          var statusVal = '';
          for (var sk2 = 0; sk2 < STATUS_KEYS.length; sk2++) {
            if (r[STATUS_KEYS[sk2]]) { statusVal = r[STATUS_KEYS[sk2]]; break; }
          }
          var statusClass = 'status-' + (statusVal || '').toLowerCase().replace(/\\s+/g, '_');
          var rSheetName = escapeHtml(r.sheet || sheetName);
          var sheetRowIdx = r._sheetRowIndex !== undefined ? r._sheetRowIndex : ri2;
          var recordId = r.record_id || (r._identity && r._identity.record_id) || r.contract_key || '';
          if (!recordId) recordId = rSheetName + ':' + sheetRowIdx;

          var changeSummary = getRecordChangeSummary(recordId);
          var rowClasses = ['clickable'];
          if (changeSummary && changeSummary.total > 0) {
            if (changeSummary.by_type.added) rowClasses.push('row-added');
            else if (changeSummary.by_type.blacklist || changeSummary.by_type.removed) rowClasses.push('row-removed');
            else rowClasses.push('row-changed');
          }

          var cellStyle = getGridCellStyle ? '' : '';
          var rowBadgesHtml = typeof renderRowBadges === 'function' ? renderRowBadges(recordId) : '';

          var tr = document.createElement('tr');
          tr.className = rowClasses.join(' ');
          tr.setAttribute('data-sheet-name', rSheetName);
          tr.setAttribute('data-record-index', '' + sheetRowIdx);
          tr.setAttribute('data-record-id', escapeHtml(recordId));
          tr.onclick = (function(sn, sri) { return function() { openRowReviewDrawer(sn, sri); }; })(r.sheet || sheetName, sheetRowIdx);

          var rowHtml = '<td class="row-index">' + (ri2 + 1) + rowBadgesHtml + '</td>';
          for (var ci2 = 0; ci2 < columns.length; ci2++) {
            var col2 = columns[ci2];
            var val = r[col2];
            if (val === null || val === undefined) val = '';
            if (typeof val === 'object') val = JSON.stringify(val);
            var isFileNameCol = col2.toLowerCase().indexOf('file_name') >= 0;
            var cellContent = String(val);
            if (isFileNameCol && val) {
              var fileUrl = r.file_url || r.File_URL_c || '';
              if (fileUrl) {
                var shortName = val.length > 40 ? val.substring(0, 38) + '...' : val;
                cellContent = '<a href="' + fileUrl + '" target="_blank" onclick="event.stopPropagation();" style="color: #1976d2; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;"><span style="font-size: 0.9em;">&#128279;</span>' + shortName + '</a>';
              }
            }
            var isStatusCol = STATUS_KEYS.indexOf(col2) >= 0 || col2.toLowerCase() === 'status';
            var cellCls = isStatusCol ? statusClass : '';
            var cStyle = typeof getGridCellStyle === 'function' ? getGridCellStyle(recordId, col2, r) : '';
            var changeInfo = typeof getCellChangeInfo === 'function' ? getCellChangeInfo(recordId, col2, r) : null;
            var titlePfx = changeInfo && typeof CHANGE_TYPE_STYLES !== 'undefined' && CHANGE_TYPE_STYLES[changeInfo.type] ? '[' + CHANGE_TYPE_STYLES[changeInfo.type].label + '] ' : '';
            rowHtml += '<td class="' + cellCls + ' truncated" style="' + cStyle + '" title="' + titlePfx + String(val).replace(/"/g, '&quot;') + '">' + cellContent + '</td>';
          }
          tr.innerHTML = rowHtml;
          tbody.appendChild(tr);
        }
        tbl.appendChild(tbody);
        bodyDiv.appendChild(tbl);
        section.appendChild(bodyDiv);
        root.appendChild(section);
        console.log('[GRID-COMPOSITE][P1C] section_rendered: ' + sheetName + ' rows=' + rows.length);
      }

      container.appendChild(root);

      // Update footer
      document.getElementById('grid-row-count').textContent = filtered.length + ' of ' + allRecords.length + ' records (composite: ' + sheetOrder.length + ' sheets)';
      gridState.filteredData = filtered;

      var filterInfo = [];
      if (gridState.filter !== 'all') filterInfo.push('Status: ' + gridState.filter);
      if (gridState.search) filterInfo.push('Search: "' + gridState.search + '"');
      filterInfo.push('Contract: ' + _activeContractFilter.substring(0, 20));
      document.getElementById('grid-filter-info').textContent = filterInfo.join(' | ');
      updateGridSheetStats(allRecords, filtered);
    }
"""

def apply_edits():
    html = read_html()
    edits_applied = []

    # ── E1: Insert CSS before closing </style> ──
    marker_css = '    /* ── P1C: Contract Composite Grid ── */'
    if marker_css not in html:
        # Find last </style> in <head>
        style_close = html.rfind('</style>')
        if style_close < 0:
            print('[E1] FAIL: </style> not found'); sys.exit(1)
        html = html[:style_close] + P1C_CSS + '\n' + html[style_close:]
        edits_applied.append('E1-css')
    else:
        edits_applied.append('E1-css(skip)')

    # ── E2: Insert Expand/Collapse controls before the grid-table-container ──
    marker_controls = 'id="p1c-composite-controls"'
    if marker_controls not in html:
        anchor = '<div class="grid-table-container"'
        pos = html.find(anchor)
        if pos < 0:
            print('[E2] FAIL: grid-table-container not found'); sys.exit(1)
        html = html[:pos] + P1C_CONTROLS_HTML + '\n        ' + html[pos:]
        edits_applied.append('E2-controls')
    else:
        edits_applied.append('E2-controls(skip)')

    # ── E3: Insert composite mode detection in renderGrid ──
    marker_composite = '_p1cIsCompositeMode()'
    if marker_composite not in html:
        anchor3 = '      // Determine columns from workbook sheet or fallback to defaults (v1.4.3 GRID-01)'
        pos3 = html.find(anchor3)
        if pos3 < 0:
            print('[E3] FAIL: could not find column extraction anchor'); sys.exit(1)
        html = html[:pos3] + P1C_COMPOSITE_BLOCK + '\n' + html[pos3:]
        edits_applied.append('E3-composite-detect')
    else:
        edits_applied.append('E3-composite-detect(skip)')

    # ── E4: Insert helper functions before the SRR state block ──
    marker_helpers = '_p1cIsCompositeMode'
    # Already checked in E3, but for functions we look for the function block
    marker_fn = 'function _p1cRenderComposite'
    if marker_fn not in html:
        anchor4 = '    // Single Row Review state'
        pos4 = html.find(anchor4)
        if pos4 < 0:
            print('[E4] FAIL: SRR state anchor not found'); sys.exit(1)
        html = html[:pos4] + P1C_HELPERS + '\n\n' + html[pos4:]
        edits_applied.append('E4-helpers')
    else:
        edits_applied.append('E4-helpers(skip)')

    write_html(html)
    print('[P1C] Delta applied:', ', '.join(edits_applied))
    return edits_applied

if __name__ == '__main__':
    edits = apply_edits()
    print('[P1C] Done. Edits:', len(edits))
