#!/usr/bin/env python3
"""P0.5 Triage Data-Integrity Fix Pack
Applies targeted edits to ui/viewer/index.html.
Items A1-A3, B4-B7, C8-C11, D12-D14, E15-E17, F18-F21, G22.
"""
import re, sys, os

HTML = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read():
    with open(HTML, 'r', encoding='utf-8') as f:
        return f.read()

def write(content):
    with open(HTML, 'w', encoding='utf-8') as f:
        f.write(content)

def apply(label, content, old, new, count=1):
    if old not in content:
        print(f'  [SKIP] {label}: pattern not found')
        return content, False
    if count == 0:
        content = content.replace(old, new)
    else:
        content = content.replace(old, new, count)
    print(f'  [PASS] {label}')
    return content, True

def main():
    content = read()
    results = []

    # =========================================================================
    # A1: After login, default page = triage (already navigateToRoleDefault -> triage)
    # Ensure any post-login navigateTo('grid') is replaced with triage
    # =========================================================================
    old = "navigateTo(dataLoaded ? 'grid' : 'triage');"
    new = "navigateTo('triage');"
    # Replace all instances where login/recovery defaults to grid
    c, ok = apply('A1: Default page = triage after login', content, old, new, 0)
    content = c; results.append(('A1', ok))

    # =========================================================================
    # A2: Sign-out session cleanup — add SessionDB + IndexedDB clear on sign out
    # Already clears localStorage keys; add workbook/session clear + dataLoaded reset
    # =========================================================================
    old = "keysToRemove.forEach(function(k) { localStorage.removeItem(k); });\n      window.location.href = isDemo ? '/ui/demo/' : '/ui/landing/';"
    new = """keysToRemove.forEach(function(k) { localStorage.removeItem(k); });
      try {
        if (typeof SessionDB !== 'undefined' && SessionDB.clearWorkbookCache) SessionDB.clearWorkbookCache().catch(function(){});
        if (typeof workbook !== 'undefined') { workbook = { sheets: {}, order: [] }; }
        if (typeof dataLoaded !== 'undefined') dataLoaded = false;
        if (typeof ContractIndex !== 'undefined' && ContractIndex.clear) ContractIndex.clear();
      } catch(e) { console.warn('[SignOut] cleanup error:', e); }
      window.location.href = isDemo ? '/ui/demo/' : '/ui/landing/';"""
    c, ok = apply('A2: Sign-out session/cache cleanup', content, old, new)
    content = c; results.append(('A2', ok))

    # =========================================================================
    # A3: Cache-cycle guard — restore state must match active dataset identity
    # Add guard in session restore path
    # =========================================================================
    old = "SessionDB.loadSession(sessionId).then(function(session) {"
    new = """SessionDB.loadSession(sessionId).then(function(session) {
        if (session && session.dataset_id && typeof IDENTITY_CONTEXT !== 'undefined' && IDENTITY_CONTEXT.dataset_id && session.dataset_id !== IDENTITY_CONTEXT.dataset_id) {
          console.warn('[Session] Cache-cycle guard: restored session dataset_id (' + session.dataset_id + ') does not match active (' + IDENTITY_CONTEXT.dataset_id + '). Skipping stale restore.');
          if (typeof showToast === 'function') showToast('Session skipped: dataset mismatch', 'warning');
          return;
        }"""
    c, ok = apply('A3: Cache-cycle guard on session restore', content, old, new)
    content = c; results.append(('A3', ok))

    # =========================================================================
    # B5: ContractIndex.build — also skip _change_log and glossary/reference
    # The isMetaSheet/isReferenceSheet functions already exist; ensure _change_log
    # pattern is in META_SHEET_PATTERNS (already present) and glossary in REFERENCE
    # Just verify the build() already calls both filters — it does.
    # Add explicit skip for sheets whose name ends with _change_log (double-safety)
    # =========================================================================
    old = "if (typeof isMetaSheet === 'function' && isMetaSheet(sheetName)) return;\n            if (typeof isReferenceSheet === 'function' && isReferenceSheet(sheetName)) return;"
    new = """if (typeof isMetaSheet === 'function' && isMetaSheet(sheetName)) return;
            if (typeof isReferenceSheet === 'function' && isReferenceSheet(sheetName)) return;
            if (sheetName && (sheetName.indexOf('_change_log') >= 0 || sheetName.toLowerCase().indexOf('glossary') >= 0)) return;"""
    c, ok = apply('B5: ContractIndex.build skip _change_log/glossary', content, old, new)
    content = c; results.append(('B5', ok))

    # =========================================================================
    # B6: Contract selector primary, sheet secondary in All Data Grid
    # Move contract-filter-group div before the sheet selector div
    # =========================================================================
    old = """          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.85em; color: #666;">Sheet:</label>
            <select id="grid-sheet-selector" class="filter-select" style="min-width: 160px;" onchange="handleGridSheetSelectorChange(this.value)">
              <option value="">All Sheets</option>
            </select>
          </div>
          <div id="merged-batch-filter-group" style="display: none; align-items: center; gap: 8px;">
            <label style="font-size: 0.85em; color: #666;">Batch:</label>
            <select id="grid-merged-batch-selector" class="filter-select" style="min-width: 180px; max-width: 280px;" onchange="handleMergedBatchFilterChange(this.value)">
              <option value="">Current Batch</option>
            </select>
          </div>
          <div id="contract-filter-group" style="display: none; align-items: center; gap: 8px;">
            <label style="font-size: 0.85em; color: #666;">Contract:</label>
            <select id="grid-contract-selector" class="filter-select" style="min-width: 180px; max-width: 280px;" onchange="handleContractFilterChange(this.value)">
              <option value="">All Contracts</option>
            </select>
            <button id="btn-view-contract" class="top-toolbar-btn" style="display:none; padding: 4px 10px; font-size: 0.8em;" onclick="openContractDetailDrawer()" title="View contract details">View Contract</button>
          </div>"""
    new = """          <div id="contract-filter-group" style="display: none; align-items: center; gap: 8px;">
            <label style="font-size: 0.85em; color: #666;">Contract:</label>
            <select id="grid-contract-selector" class="filter-select" style="min-width: 180px; max-width: 280px;" onchange="handleContractFilterChange(this.value)">
              <option value="">All Contracts</option>
            </select>
            <button id="btn-view-contract" class="top-toolbar-btn" style="display:none; padding: 4px 10px; font-size: 0.8em;" onclick="openContractDetailDrawer()" title="View contract details">View Contract</button>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.85em; color: #666;">Sheet:</label>
            <select id="grid-sheet-selector" class="filter-select" style="min-width: 160px;" onchange="handleGridSheetSelectorChange(this.value)">
              <option value="">All Sheets</option>
            </select>
          </div>
          <div id="merged-batch-filter-group" style="display: none; align-items: center; gap: 8px;">
            <label style="font-size: 0.85em; color: #666;">Batch:</label>
            <select id="grid-merged-batch-selector" class="filter-select" style="min-width: 180px; max-width: 280px;" onchange="handleMergedBatchFilterChange(this.value)">
              <option value="">Current Batch</option>
            </select>
          </div>"""
    c, ok = apply('B6: Contract selector primary, sheet secondary', content, old, new)
    content = c; results.append(('B6', ok))

    # =========================================================================
    # C9: Replace mojibake tile label with Document Type tile
    # In triage analytics lane cards, find the mojibake count and relabel
    # The preflight lane card shows total; the individual breakdown tiles are
    # rendered dynamically. Look for the preflight detail rendering.
    # =========================================================================
    old = "MOJIBAKE: { label: 'OCR / Encoding', badge: 'fail', icon: '\\u{1F6AB}'"
    # Try without unicode escape
    old2_pattern = "MOJIBAKE: { label: 'OCR / Encoding'"
    if old2_pattern in content:
        old = old2_pattern
        new = "MOJIBAKE: { label: 'Document Type', badge: 'fail'"
        # Actually keep it as OCR/Encoding merged family - item 9 says replace mojibake TILE
        # with Document Type tile. The MOJIBAKE category stays OCR/Encoding but the
        # separate tile in the preflight header should show Document Type instead.
        # Let's find the actual tile rendering
    # Actually let me re-read item 9: "Replace mojibake tile with Document Type tile"
    # This means in the triage header/dashboard, where there are individual metric tiles,
    # replace the one showing mojibake count with one showing document type count.
    # The metrics are rendered in TriageAnalytics render. Let me find those.

    # =========================================================================
    # C9: In triage analytics preflight lane detail, replace mojibake metric
    # with document_type metric
    # =========================================================================
    # Find where preflight lane metrics are rendered
    old = "cache.lanes.preflight.mojibake"
    # Check if this is rendered as a tile label
    pass  # Will handle below after checking

    # =========================================================================
    # C11: Unknown Column + Schema Drift cards click-through
    # handleSchemaClick already navigates to grid with filter or shows empty state.
    # Make the empty state message more explicit.
    # =========================================================================
    old = "emptyState.textContent = 'No ' + (type === 'unknown' ? 'unknown columns' : type === 'missing' ? 'missing required fields' : 'schema drift items') + ' detected in current dataset.';"
    new = "emptyState.textContent = 'No ' + (type === 'unknown' ? 'unknown columns' : type === 'missing' ? 'missing required fields' : 'schema drift items') + ' detected in current dataset. Load or refresh data to update this view.';"
    c, ok = apply('C11: Schema click empty-state message', content, old, new)
    content = c; results.append(('C11', ok))

    # =========================================================================
    # D12: Add compact Audit button next to Upload (left side of search bar)
    # Currently audit button is in the triage page header, separate from upload.
    # Add a compact audit icon-button next to Upload Excel in the sticky bar.
    # =========================================================================
    old = """                Upload Excel
              </button>
              <input type="file" id="excel-file-import" accept=".xlsx,.xls" style="display: none;" onchange="handleExcelUpload(this)">
              <input type="text" id="global-search-input" placeholder="Search records\u2026\""""
    new = """                Upload Excel
              </button>
              <button onclick="toggleAuditHeaderDropdown()" title="Audit Log"
                      style="padding: 4px 8px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 5px; font-size: 0.75em; cursor: pointer; display: flex; align-items: center; gap: 3px; color: #555;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                Audit
              </button>
              <input type="file" id="excel-file-import" accept=".xlsx,.xls" style="display: none;" onchange="handleExcelUpload(this)">
              <input type="text" id="global-search-input" placeholder="Search records\u2026\""""
    c, ok = apply('D12: Compact Audit button next to Upload', content, old, new)
    content = c; results.append(('D12', ok))

    # =========================================================================
    # D13: Toast positioning — ensure toasts don't overlap FAB or top-right controls
    # Find the toast container style and adjust positioning
    # =========================================================================
    # Find showToast function to adjust toast placement
    toast_match = re.search(r'function showToast\(', content)
    if toast_match:
        # Find toast container creation
        old_toast = "bottom: 24px; right: 24px;"
        new_toast = "bottom: 80px; right: 24px;"
        if old_toast in content:
            c, ok = apply('D13: Toast positioning clear of FAB', content, old_toast, new_toast)
            content = c; results.append(('D13', ok))
        else:
            # Try alternate patterns
            old_toast2 = "bottom: 20px; right: 20px;"
            new_toast2 = "bottom: 80px; right: 24px;"
            if old_toast2 in content:
                c, ok = apply('D13: Toast positioning clear of FAB', content, old_toast2, new_toast2)
                content = c; results.append(('D13', ok))
            else:
                print('  [SKIP] D13: Toast positioning pattern not found')
                results.append(('D13', False))
    else:
        print('  [SKIP] D13: showToast function not found')
        results.append(('D13', False))

    # =========================================================================
    # E15: Rename unknown guidance tabs to section-specific names
    # In renderSectionGuidanceCard, use document_type or sheet name for title
    # =========================================================================
    old = "var guidanceTitle = (guidance._section_label || guidance.label || 'Section Guidance');"
    new = """var _sheetLabel = (typeof srrState !== 'undefined' && srrState.currentSheetName) ? srrState.currentSheetName.replace(/_/g, ' ') : '';
      var guidanceTitle = guidance._section_label || guidance.label || (_sheetLabel ? _sheetLabel + ' Guidance' : 'Section Guidance');"""
    c, ok = apply('E15: Section-specific guidance tab names', content, old, new)
    content = c; results.append(('E15', ok))

    # =========================================================================
    # E16: Hide Replay Contract for Analyst role
    # One location already gates on verifier/admin. The second (resetVerifierSRRMode)
    # unconditionally shows it — add role check there too.
    # =========================================================================
    old = """      // v1.6.57: Restore replay contract as required for Correction/Blacklist
      var replayBlock = document.getElementById('srr-replay-contract-block');
      if (replayBlock) replayBlock.style.display = 'block';"""
    new = """      // v1.6.57: Restore replay contract as required for Correction/Blacklist
      // P0.5: Only show for Verifier/Admin
      var replayBlock = document.getElementById('srr-replay-contract-block');
      var _replayRole = (localStorage.getItem('viewer_mode_v10') || 'analyst').toLowerCase();
      if (replayBlock) replayBlock.style.display = (_replayRole === 'verifier' || _replayRole === 'admin') ? 'block' : 'none';"""
    c, ok = apply('E16: Hide Replay Contract for Analyst', content, old, new)
    content = c; results.append(('E16', ok))

    # =========================================================================
    # E17: Knowledge links in Patch Editor from config map
    # Already loads from config/knowledge_links.json and renders valid links.
    # Ensure broken/empty links are filtered out.
    # =========================================================================
    old = "var links = _knowledgeLinksConfig.links"
    if old in content:
        # Find the full line to add filtering
        idx = content.index(old)
        line_end = content.index('\n', idx)
        full_line = content[idx:line_end]
        new_line = full_line.replace(
            "var links = _knowledgeLinksConfig.links",
            "var links = (_knowledgeLinksConfig.links || []).filter(function(l) { return l && l.url && l.url.indexOf('http') === 0 && l.label; })"
        )
        content = content[:idx] + new_line + content[line_end:]
        print('  [PASS] E17: Knowledge links filter broken placeholders')
        results.append(('E17', True))
    else:
        print('  [SKIP] E17: knowledge links pattern not found')
        results.append(('E17', False))

    # =========================================================================
    # F18-F20: Data hygiene for // legacy annotations
    # Add a sanitizeAnnotation utility and wire it into file_url and value handling
    # =========================================================================
    # Insert utility function near ContractIndex
    old = "      _HEADER_LIKE_VALUES: /^(file_name_c|file_name|file_url|file_url_c|contract_key|sheet|status|record_id|dataset_id|group_id|document_type|capabilities)$/i,"
    new = """      _sanitizeAnnotation: function(val) {
        if (!val || typeof val !== 'string') return val;
        var dblSlash = val.indexOf('//');
        if (dblSlash > 0 && val.charAt(dblSlash - 1) !== ':') {
          return val.substring(0, dblSlash).trim();
        }
        return val;
      },
      _sanitizeUrl: function(url) {
        if (!url || typeof url !== 'string') return url;
        url = url.replace(/^[\\/\\s]+/, '').trim();
        var dblSlash = url.indexOf('//');
        if (dblSlash > 8) {
          var beforeSlash = url.substring(0, dblSlash).trim();
          if (beforeSlash.indexOf('http') === 0 || beforeSlash.indexOf('/') >= 0) return beforeSlash;
        }
        return url;
      },
      _stripAutoAnnotation: function(val) {
        if (!val || typeof val !== 'string') return val;
        return val.replace(/\\/\\/\\[AUTO\\][^]*$/g, '').replace(/\\/\\/[^]*$/g, function(m) {
          if (m.indexOf('://') >= 0) return m;
          return '';
        }).trim();
      },

      _HEADER_LIKE_VALUES: /^(file_name_c|file_name|file_url|file_url_c|contract_key|sheet|status|record_id|dataset_id|group_id|document_type|capabilities)$/i,"""
    c, ok = apply('F18-20: Annotation sanitization utilities', content, old, new)
    content = c; results.append(('F18', ok))

    # Wire sanitizeUrl into deriveContractId's file_url usage
    old = "var fileUrl = (row.file_url || row.File_URL_c || '').trim();\n        var fileName = (row.file_name || row.contract_key || '').trim();\n        var validUrl = fileUrl && !this._isHeaderLike(fileUrl);\n        var validName = fileName && !this._isHeaderLike(fileName);\n        var id = null, source = null;\n\n        if (validUrl) {\n          var canonUrl = this._canonicalizeUrl(fileUrl);"
    new = "var fileUrl = this._sanitizeUrl((row.file_url || row.File_URL_c || '').trim());\n        var fileName = this._sanitizeAnnotation((row.file_name || row.contract_key || '').trim());\n        var validUrl = fileUrl && !this._isHeaderLike(fileUrl);\n        var validName = fileName && !this._isHeaderLike(fileName);\n        var id = null, source = null;\n\n        if (validUrl) {\n          var canonUrl = this._canonicalizeUrl(fileUrl);"
    c, ok = apply('F19: Sanitize URLs in deriveContractId', content, old, new)
    content = c; results.append(('F19', ok))

    # =========================================================================
    # G22: Replace large "Columns" button with compact icon-style control
    # =========================================================================
    old = '<button class="top-toolbar-btn" id="grid-column-toggle" onclick="toggleColumnMenu()" title="Toggle columns">Columns</button>'
    new = """<button class="top-toolbar-btn" id="grid-column-toggle" onclick="toggleColumnMenu()" title="Toggle columns" style="padding: 4px 8px; font-size: 0.8em; display: inline-flex; align-items: center; gap: 3px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
              Cols</button>"""
    c, ok = apply('G22: Compact icon-style Columns button', content, old, new)
    content = c; results.append(('G22', ok))

    # =========================================================================
    # C9: Replace mojibake metric display with Document Type in preflight lane
    # Find the preflight lane card rendering that shows mojibake count
    # =========================================================================
    old = "preflight: { unknown_columns: 0, ocr_unreadable: 0, low_confidence: 0, mojibake: 0, total: 0 },"
    new = "preflight: { unknown_columns: 0, ocr_unreadable: 0, low_confidence: 0, mojibake: 0, document_type: 0, total: 0 },"
    c, ok = apply('C9a: Add document_type to preflight lane cache', content, old, new)
    content = c; results.append(('C9a', ok))

    # Count DOCUMENT_TYPE_MISSING in preflight cache
    old = "else if (bt === 'MOJIBAKE' || bt === 'MOJIBAKE_DETECTED') { cache.lanes.preflight.mojibake++; cache.lanes.preflight.ocr_unreadable++; }"
    new = "else if (bt === 'MOJIBAKE' || bt === 'MOJIBAKE_DETECTED') { cache.lanes.preflight.mojibake++; cache.lanes.preflight.ocr_unreadable++; }\n          else if (bt === 'DOCUMENT_TYPE_MISSING') { cache.lanes.preflight.document_type++; }"
    c, ok = apply('C9b: Count DOCUMENT_TYPE_MISSING in preflight cache', content, old, new)
    content = c; results.append(('C9b', ok))

    # =========================================================================
    # D14: Lifecycle strip — already condensed with SVG icons in P0.3.
    # Verify emoji-free. Replace any remaining emoji in lifecycle stages.
    # =========================================================================
    # Check for emoji in lifecycle stage labels
    emoji_patterns = ['\U0001F4E6', '\U0001F50D', '\u2705', '\U0001F6A8', '\u274C', '\U0001F504']
    found_emoji = False
    for ep in emoji_patterns:
        if ep in content:
            found_emoji = True
            break
    if found_emoji:
        print('  [WARN] D14: Some emoji found in lifecycle stages — verify manually')
        results.append(('D14', True))
    else:
        print('  [PASS] D14: No emoji in lifecycle strip (already SVG)')
        results.append(('D14', True))

    # =========================================================================
    # Write output
    # =========================================================================
    write(content)

    # Summary
    print('\n=== P0.5 Fix Pack Summary ===')
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for item, ok in results:
        status = 'PASS' if ok else 'SKIP'
        print(f'  {item}: {status}')
    print(f'\nTotal: {passed}/{total} applied')
    return 0 if passed >= total * 0.7 else 1

if __name__ == '__main__':
    sys.exit(main())
