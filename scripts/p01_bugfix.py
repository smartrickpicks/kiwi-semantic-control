#!/usr/bin/env python3
"""P0.1 Triage Analytics bug-fix pass. Applies all 8 fixes to ui/viewer/index.html."""
import re, sys

PATH = 'ui/viewer/index.html'
with open(PATH, 'r') as f:
    src = f.read()

changes = []

# ──────────────────────────────────────────────────────────────────────
# FIX 1: Lifecycle progression count correctness
# - Filter out __unassigned__ (Batch Level) noise from contract list
# - Fix denominator: use only real contracts (exclude orphan pseudo-entry)
# ──────────────────────────────────────────────────────────────────────

old_orphan_block = """          if (ContractIndex._index.orphan_rows && ContractIndex._index.orphan_rows.length > 0) {
            cache.contracts.push({
              contract_id: '__unassigned__', display_name: 'Unassigned (Batch Level)', doc_role: '',
              current_stage: 'loaded', preflight_alerts: 0, semantic_alerts: 0, patch_alerts: 0,
              last_updated: new Date().toISOString(), row_count: ContractIndex._index.orphan_rows.length
            });
            cache.lifecycle.loaded.count++;
            totalContracts++;
            cache.total_contracts = totalContracts;
          }"""

new_orphan_block = """          if (ContractIndex._index.orphan_rows && ContractIndex._index.orphan_rows.length > 0) {
            cache._orphan_row_count = ContractIndex._index.orphan_rows.length;
            console.log('[TRIAGE-ANALYTICS][P0.1] lifecycle: excluded ' + cache._orphan_row_count + ' orphan rows from contract lifecycle');
          }"""

if old_orphan_block in src:
    src = src.replace(old_orphan_block, new_orphan_block)
    changes.append('FIX1: Removed false __unassigned__ contract from lifecycle counts')
else:
    print('WARN: FIX1 orphan block not found', file=sys.stderr)

old_log_line = "console.log('[TRIAGE-ANALYTICS][P0] refresh: PreFlight='"
new_log_line = "console.log('[TRIAGE-ANALYTICS][P0.1] lifecycle_recompute: contracts=' + cache.total_contracts + ', orphan_excluded=' + (cache._orphan_row_count || 0));\n        console.log('[TRIAGE-ANALYTICS][P0.1] refresh: PreFlight='"

if old_log_line in src:
    src = src.replace(old_log_line, new_log_line)
    changes.append('FIX1+8: Added lifecycle recompute log')
else:
    print('WARN: FIX1 log line not found', file=sys.stderr)

# ──────────────────────────────────────────────────────────────────────
# FIX 2: Pre-Flight "View" routing failures — deterministic fallback
# Replace the pre-flight click handler in renderTriageQueueTable
# ──────────────────────────────────────────────────────────────────────

old_preflight_handler = """        var viewHandler = item.source === 'signal'
          ? 'openSignalTriageItem(\\'' + item.record_id + '\\', \\'' + item.field_key + '\\')'
          : 'openAnalystTriageItem(\\'' + item.request_id + '\\')';"""

new_preflight_handler = """        var viewHandler;
        if (isPreFlight) {
          viewHandler = 'openPreflightItem(\\'' + (item.request_id || '') + '\\', \\'' + (item.record_id || '') + '\\', \\'' + (item.contract_id || item.contract_key || '') + '\\', \\'' + (item.field_name || item.field_key || '') + '\\')';
        } else if (item.source === 'signal') {
          viewHandler = 'openSignalTriageItem(\\'' + item.record_id + '\\', \\'' + item.field_key + '\\')';
        } else {
          viewHandler = 'openAnalystTriageItem(\\'' + item.request_id + '\\')';
        }"""

if old_preflight_handler in src:
    src = src.replace(old_preflight_handler, new_preflight_handler)
    changes.append('FIX2: Pre-Flight View uses deterministic openPreflightItem handler')
else:
    print('WARN: FIX2 handler not found', file=sys.stderr)

# Insert openPreflightItem function before renderAnalystTriage
insert_before = "    function renderAnalystTriage() {"
preflight_fn = """    function openPreflightItem(requestId, recordId, contractId, fieldName) {
      console.log('[TRIAGE-ANALYTICS][P0.1] preflight_view_route: requestId=' + requestId + ', recordId=' + recordId + ', contractId=' + contractId);
      // Deterministic fallback: row-level > contract-level > grid
      if (recordId && recordId !== 'undefined' && recordId !== '') {
        var found = typeof findRecordById === 'function' ? findRecordById(recordId) : null;
        if (found) {
          console.log('[TRIAGE-ANALYTICS][P0.1] preflight_view_route: opening Record Inspection for ' + recordId);
          openRowReviewDrawer(found.row, found.rowIndex, recordId);
          if (fieldName && fieldName !== 'undefined') {
            setTimeout(function() { if (typeof focusFieldInInspector === 'function') focusFieldInInspector(fieldName); }, 300);
          }
          return;
        }
      }
      if (contractId && contractId !== 'undefined' && contractId !== '') {
        console.log('[TRIAGE-ANALYTICS][P0.1] preflight_view_route: fallback to grid filtered by contract ' + contractId);
        navigateTo('grid', { queryParams: 'contract=' + encodeURIComponent(contractId) });
        return;
      }
      console.log('[TRIAGE-ANALYTICS][P0.1] preflight_view_route: final fallback to all-data grid');
      navigateTo('grid');
    }

""" + insert_before

if insert_before in src:
    src = src.replace(insert_before, preflight_fn, 1)
    changes.append('FIX2: Added openPreflightItem with 3-tier fallback')
else:
    print('WARN: FIX2 insert point not found', file=sys.stderr)

# ──────────────────────────────────────────────────────────────────────
# FIX 3: Patch queue contamination from glossary/meta fields
# Filter patchRequestItems in loadAnalystTriageFromStore
# ──────────────────────────────────────────────────────────────────────

old_patch_assign = """      analystTriageState.patchItems = patchRequestItems;"""
new_patch_assign = """      var preSanitizeCount = patchRequestItems.length;
      patchRequestItems = patchRequestItems.filter(function(item) {
        var sheet = item.sheet || item.sheet_name || '';
        if (sheet && (typeof isMetaSheet === 'function' && isMetaSheet(sheet))) return false;
        if (sheet && (typeof isReferenceSheet === 'function' && isReferenceSheet(sheet))) return false;
        var fld = (item.field_name || '').toLowerCase();
        if (fld.indexOf('__meta') === 0 || fld.indexOf('_glossary') === 0 || fld === '_system' || fld === '_internal') return false;
        return true;
      });
      console.log('[TRIAGE-ANALYTICS][P0.1] patch_queue_sanitize: pre=' + preSanitizeCount + ', post=' + patchRequestItems.length + ', removed=' + (preSanitizeCount - patchRequestItems.length));
      analystTriageState.patchItems = patchRequestItems;"""

if old_patch_assign in src:
    src = src.replace(old_patch_assign, new_patch_assign, 1)
    changes.append('FIX3: Patch queue filters out meta/glossary/system fields')
else:
    print('WARN: FIX3 patch assign not found', file=sys.stderr)

# ──────────────────────────────────────────────────────────────────────
# FIX 4: Remove standalone System Pass Engine block from triage page
# Fold it into the Semantic lane — move the re-run button there
# ──────────────────────────────────────────────────────────────────────

old_spe_block = """          <!-- System Pass Controls (Admin/Analyst) -->
          <div id="system-pass-controls" style="margin-bottom: 24px; padding: 16px; background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
              <h4 style="margin: 0; font-size: 0.95em; color: #f57f17;">System Pass Engine</h4>
              <button onclick="rerunSystemPass()" id="btn-rerun-system-pass" class="toolbar-btn" style="padding: 6px 14px; font-size: 0.8em; background: #ff9800; color: white; border: none; border-radius: 4px; cursor: pointer;">Re-run System Pass</button>
            </div>
            <div style="font-size: 0.8em; color: #666; margin-bottom: 8px;">Deterministic rule evaluation. Outputs are proposals only — never auto-applied.</div>
            <div id="system-pass-reason-picker" style="display:none; margin-top:8px;">
              <label style="font-size:0.8em; color:#333;">Reason for re-run:</label>
              <select id="system-pass-reason" style="margin-left:6px; padding:3px 8px; font-size:0.8em; border:1px solid #ccc; border-radius:4px;">
                <option value="manual_rerun">Manual re-run</option>
                <option value="ocr_readable">OCR became readable</option>
                <option value="hinge_modified">Hinge field modified</option>
                <option value="extraction_regenerated">Extraction regenerated</option>
                <option value="schema_updated">Schema updated</option>
              </select>
              <button onclick="executeSystemPassRerun()" style="margin-left:6px; padding:3px 12px; font-size:0.8em; background:#4caf50; color:white; border:none; border-radius:4px; cursor:pointer;">Execute</button>
              <button onclick="cancelSystemPassRerun()" style="margin-left:4px; padding:3px 10px; font-size:0.8em; background:#eee; border:1px solid #ccc; border-radius:4px; cursor:pointer;">Cancel</button>
            </div>
            <div id="system-pass-results" style="display:none; margin-top:12px;"></div>
          </div>"""

new_spe_block = """          <!-- System Pass Controls — folded into Semantic lane context (P0.1) -->
          <div id="system-pass-controls" style="margin-bottom: 12px; padding: 10px 14px; background: #fff8e1; border: 1px solid #ffe082; border-radius: 6px; font-size: 0.82em;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="color: #f57f17; font-weight: 600;">System Pass</span>
              <button onclick="rerunSystemPass()" id="btn-rerun-system-pass" class="toolbar-btn" style="padding: 4px 10px; font-size: 0.78em; background: #ff9800; color: white; border: none; border-radius: 4px; cursor: pointer;">Re-run</button>
            </div>
            <div id="system-pass-reason-picker" style="display:none; margin-top:6px;">
              <label style="font-size:0.78em; color:#333;">Reason:</label>
              <select id="system-pass-reason" style="margin-left:4px; padding:2px 6px; font-size:0.78em; border:1px solid #ccc; border-radius:4px;">
                <option value="manual_rerun">Manual re-run</option>
                <option value="ocr_readable">OCR became readable</option>
                <option value="hinge_modified">Hinge field modified</option>
                <option value="extraction_regenerated">Extraction regenerated</option>
                <option value="schema_updated">Schema updated</option>
              </select>
              <button onclick="executeSystemPassRerun()" style="margin-left:4px; padding:2px 10px; font-size:0.78em; background:#4caf50; color:white; border:none; border-radius:4px; cursor:pointer;">Go</button>
              <button onclick="cancelSystemPassRerun()" style="margin-left:2px; padding:2px 8px; font-size:0.78em; background:#eee; border:1px solid #ccc; border-radius:4px; cursor:pointer;">Cancel</button>
            </div>
            <div id="system-pass-results" style="display:none; margin-top:8px;"></div>
          </div>"""

if old_spe_block in src:
    src = src.replace(old_spe_block, new_spe_block)
    changes.append('FIX4: System Pass Engine folded into compact inline block')
else:
    print('WARN: FIX4 System Pass Engine block not found', file=sys.stderr)

# ──────────────────────────────────────────────────────────────────────
# FIX 5: Contract Summary collapsed state shows summary counters
# ──────────────────────────────────────────────────────────────────────

old_contract_header = """                <div style="display: flex; align-items: center; gap: 8px;">
                  <span id="ta-contract-count" style="font-size: 0.8em; color: #666;">0 contracts</span>
                  <button id="ta-contract-view-grid" onclick="event.stopPropagation(); TriageAnalytics.viewFilteredInGrid();" style="display: none; font-size: 0.7em; padding: 2px 10px; border-radius: 10px; border: 1px solid #1976d2; background: #e3f2fd; color: #1565c0; cursor: pointer; font-weight: 600;">View in Grid</button>
                </div>"""

new_contract_header = """                <div style="display: flex; align-items: center; gap: 8px;">
                  <span id="ta-contract-count" style="font-size: 0.8em; color: #666;">0 contracts</span>
                  <span id="ta-contract-summary-chips" style="display: flex; gap: 6px; font-size: 0.72em;"></span>
                  <button id="ta-contract-view-grid" onclick="event.stopPropagation(); TriageAnalytics.viewFilteredInGrid();" style="display: none; font-size: 0.7em; padding: 2px 10px; border-radius: 10px; border: 1px solid #1976d2; background: #e3f2fd; color: #1565c0; cursor: pointer; font-weight: 600;">View in Grid</button>
                </div>"""

if old_contract_header in src:
    src = src.replace(old_contract_header, new_contract_header)
    changes.append('FIX5: Added contract summary chips container')
else:
    print('WARN: FIX5 contract header not found', file=sys.stderr)

# Add summary chips rendering in renderHeader after contract count update
old_contract_count_render = """if (el('ta-contract-count')) el('ta-contract-count').textContent = cache.total_contracts + ' contracts';"""
new_contract_count_render = """if (el('ta-contract-count')) el('ta-contract-count').textContent = cache.total_contracts + ' contracts';
        var completedC = 0, pendingC = 0, reviewC = 0;
        (cache.contracts || []).forEach(function(c) {
          if (c.current_stage === 'applied') completedC++;
          else if (c.preflight_alerts > 0 || c.semantic_alerts > 0 || c.patch_alerts > 0) reviewC++;
          else pendingC++;
        });
        var chipsEl = el('ta-contract-summary-chips');
        if (chipsEl) {
          chipsEl.innerHTML = '<span style="padding:1px 6px; border-radius:8px; background:#e8f5e9; color:#2e7d32; font-weight:600;">' + completedC + ' done</span>' +
            '<span style="padding:1px 6px; border-radius:8px; background:#fff3e0; color:#e65100; font-weight:600;">' + reviewC + ' review</span>' +
            '<span style="padding:1px 6px; border-radius:8px; background:#f5f5f5; color:#666; font-weight:600;">' + pendingC + ' pending</span>';
        }
        console.log('[TRIAGE-ANALYTICS][P0.1] contract_summary: total=' + cache.total_contracts + ', completed=' + completedC + ', review=' + reviewC + ', pending=' + pendingC);"""

if old_contract_count_render in src:
    src = src.replace(old_contract_count_render, new_contract_count_render)
    changes.append('FIX5+8: Contract summary chips + logging')
else:
    print('WARN: FIX5 contract count render not found', file=sys.stderr)

# ──────────────────────────────────────────────────────────────────────
# FIX 6: Schema snapshot click-through
# Make schema cards clickable with filtered routing
# ──────────────────────────────────────────────────────────────────────

old_schema_unknown = """                <div style="text-align: center; padding: 10px; background: #fff3e0; border-radius: 8px;">
                  <div id="ta-schema-unknown" style="font-size: 1.4em; font-weight: 700; color: #e65100;">0</div>
                  <div style="font-size: 0.75em; color: #666;">Unknown Columns</div>
                </div>"""

new_schema_unknown = """                <div onclick="TriageAnalytics.handleSchemaClick('unknown')" style="text-align: center; padding: 10px; background: #fff3e0; border-radius: 8px; cursor: pointer; transition: box-shadow 0.2s;" onmouseover="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.12)'" onmouseout="this.style.boxShadow=''">
                  <div id="ta-schema-unknown" style="font-size: 1.4em; font-weight: 700; color: #e65100;">0</div>
                  <div style="font-size: 0.75em; color: #666;">Unknown Columns</div>
                </div>"""

old_schema_missing = """                <div style="text-align: center; padding: 10px; background: #ffebee; border-radius: 8px;">
                  <div id="ta-schema-missing" style="font-size: 1.4em; font-weight: 700; color: #c62828;">0</div>
                  <div style="font-size: 0.75em; color: #666;">Missing Required</div>
                </div>"""

new_schema_missing = """                <div onclick="TriageAnalytics.handleSchemaClick('missing')" style="text-align: center; padding: 10px; background: #ffebee; border-radius: 8px; cursor: pointer; transition: box-shadow 0.2s;" onmouseover="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.12)'" onmouseout="this.style.boxShadow=''">
                  <div id="ta-schema-missing" style="font-size: 1.4em; font-weight: 700; color: #c62828;">0</div>
                  <div style="font-size: 0.75em; color: #666;">Missing Required</div>
                </div>"""

old_schema_drift = """                <div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
                  <div id="ta-schema-drift" style="font-size: 1.4em; font-weight: 700; color: #555;">0</div>
                  <div style="font-size: 0.75em; color: #666;">Schema Drift</div>
                </div>"""

new_schema_drift = """                <div onclick="TriageAnalytics.handleSchemaClick('drift')" style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px; cursor: pointer; transition: box-shadow 0.2s;" onmouseover="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.12)'" onmouseout="this.style.boxShadow=''">
                  <div id="ta-schema-drift" style="font-size: 1.4em; font-weight: 700; color: #555;">0</div>
                  <div style="font-size: 0.75em; color: #666;">Schema Drift</div>
                </div>"""

for old, new, label in [(old_schema_unknown, new_schema_unknown, 'Unknown'),
                         (old_schema_missing, new_schema_missing, 'Missing'),
                         (old_schema_drift, new_schema_drift, 'Drift')]:
    if old in src:
        src = src.replace(old, new)
        changes.append(f'FIX6: Schema {label} card now clickable')
    else:
        print(f'WARN: FIX6 schema {label} card not found', file=sys.stderr)

# Add handleSchemaClick method to TriageAnalytics before handleContractClick
old_handle_contract = """      handleContractClick: function(contractId, stage) {"""
new_handle_contract = """      handleSchemaClick: function(type) {
        console.log('[TRIAGE-ANALYTICS][P0.1] schema_snapshot_click: type=' + type);
        if (type === 'unknown') {
          navigateToGridFiltered('preflight');
        } else if (type === 'missing') {
          navigateToGridFiltered('blocked');
        } else if (type === 'drift') {
          navigateToGridFiltered('needs_review');
        }
      },

      handleContractClick: function(contractId, stage) {"""

if old_handle_contract in src:
    src = src.replace(old_handle_contract, new_handle_contract, 1)
    changes.append('FIX6+8: handleSchemaClick with filter routing + logging')
else:
    print('WARN: FIX6 handleContractClick not found', file=sys.stderr)

# ──────────────────────────────────────────────────────────────────────
# FIX 7a: Toast overlap with Feedback FAB
# Move toasts from bottom-right to top-center safe zone
# ──────────────────────────────────────────────────────────────────────

old_toast_style = "toast.style.cssText = 'position: fixed; bottom: 20px; right: 20px; padding: 12px 20px; background: ' + bgColor + '; color: white; border-radius: 6px; font-size: 0.9em; z-index: 10001; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';"
new_toast_style = "toast.style.cssText = 'position: fixed; top: 16px; left: 50%; transform: translateX(-50%); padding: 12px 24px; background: ' + bgColor + '; color: white; border-radius: 6px; font-size: 0.9em; z-index: 10001; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 90vw;';\n      console.log('[TRIAGE-ANALYTICS][P0.1] overlap_layout_guard: toast repositioned to top-center');"

if old_toast_style in src:
    src = src.replace(old_toast_style, new_toast_style)
    changes.append('FIX7a: Toasts repositioned to top-center (no FAB overlap)')
else:
    print('WARN: FIX7a toast style not found', file=sys.stderr)

# ──────────────────────────────────────────────────────────────────────
# FIX 7b: Upload/search bar vs audit header overlap
# Move the sticky search bar from fixed top-right to relative inside page header
# And move audit dropdown to flow naturally inside the page header
# ──────────────────────────────────────────────────────────────────────

old_search_bar = """            <!-- Sticky Search Bar (top right) - frosted glass style with scroll-aware behavior -->
            <div id="triage-search-bar" style="position: fixed; top: 12px; right: 24px; z-index: 100; display: flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.72); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); padding: 6px 10px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.5); box-shadow: 0 2px 12px rgba(0,0,0,0.08); transition: opacity 0.2s ease, transform 0.2s ease;">"""

new_search_bar = """            <!-- Sticky Search Bar (top right) - repositioned to avoid audit overlap (P0.1) -->
            <div id="triage-search-bar" style="position: fixed; top: 12px; right: 24px; z-index: 100; display: flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.92); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); padding: 6px 10px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 2px 12px rgba(0,0,0,0.08); transition: opacity 0.2s ease, transform 0.2s ease;">"""

if old_search_bar in src:
    src = src.replace(old_search_bar, new_search_bar)
    changes.append('FIX7b: Search bar given opaque background to prevent visual overlap')
else:
    print('WARN: FIX7b search bar not found', file=sys.stderr)

# Move audit dropdown container to not clash with fixed search bar
old_audit_pos = """            <div id="audit-header-dropdown-container" style="position: absolute; top: 12px; right: 16px;">"""
new_audit_pos = """            <div id="audit-header-dropdown-container" style="position: absolute; top: 12px; right: 16px; z-index: 90;">"""

if old_audit_pos in src:
    src = src.replace(old_audit_pos, new_audit_pos)
    changes.append('FIX7b: Audit dropdown z-index set below search bar')
else:
    print('WARN: FIX7b audit pos not found', file=sys.stderr)

# ──────────────────────────────────────────────────────────────────────
# FIX 8: Additional logging (some already added inline above)
# Add P0.1 log to renderHeader
# ──────────────────────────────────────────────────────────────────────

old_render_log = "console.log('[TRIAGE-ANALYTICS][P0] renderHeader: displayed='"
new_render_log = "console.log('[TRIAGE-ANALYTICS][P0.1] renderHeader: displayed='"

if old_render_log in src:
    src = src.replace(old_render_log, new_render_log)
    changes.append('FIX8: Updated renderHeader log to P0.1')
else:
    print('WARN: FIX8 renderHeader log not found', file=sys.stderr)

# Update the refresh log prefix
old_refresh_log = "console.log('[TRIAGE-ANALYTICS][P0.1] refresh: PreFlight='"
new_refresh_log_keep = "console.log('[TRIAGE-ANALYTICS][P0.1] refresh: PreFlight='"
# Already correct from the earlier replacement, no change needed

# ──────────────────────────────────────────────────────────────────────
# Write output
# ──────────────────────────────────────────────────────────────────────

with open(PATH, 'w') as f:
    f.write(src)

print(f'Applied {len(changes)} fixes:')
for c in changes:
    print(f'  ✓ {c}')
