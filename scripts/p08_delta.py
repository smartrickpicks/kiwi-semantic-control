#!/usr/bin/env python3
"""P0.8 Triage Record-Link Integrity Delta Script.

Applies targeted edits to ui/viewer/index.html:
  1. Unresolved-record diagnostics modal HTML
  2. resolveRecordForTriageItem() unified resolver
  3. Rewire openSignalTriageItem / openAnalystTriageItem / openPreflightItem
  4. Dataset mismatch purge on load
  5. [P0.8-LINK] deterministic logging
"""
import re, sys, os

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read_file():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(content):
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

# ── EDIT 1: Inject diagnostics modal HTML after elevate-to-patch-modal ──
MODAL_HTML = '''
        <!-- P0.8: Unresolved Record Diagnostics Modal -->
        <div id="p08-unresolved-modal" class="modal-overlay" style="display: none;">
          <div class="modal-content" style="max-width: 580px;">
            <div class="modal-header" style="display:flex; justify-content:space-between; align-items:center;">
              <h3 style="margin:0; color:#c62828;">Unresolved Record</h3>
              <button class="modal-close" onclick="closeUnresolvedModal()">&times;</button>
            </div>
            <div class="modal-body" style="max-height:400px; overflow-y:auto;">
              <p style="font-size:0.9em; color:#666; margin-bottom:12px;">The triage item could not be matched to a record in the active dataset.</p>
              <div id="p08-unresolved-summary" style="background:#fff3e0; padding:12px; border-radius:6px; margin-bottom:12px; font-size:0.88em;"></div>
              <details style="margin-bottom:12px;">
                <summary style="cursor:pointer; font-size:0.85em; font-weight:600; color:#555;">Debug JSON</summary>
                <pre id="p08-unresolved-json" style="background:#263238; color:#eee; padding:12px; border-radius:6px; font-size:0.78em; max-height:200px; overflow:auto; white-space:pre-wrap;"></pre>
              </details>
            </div>
            <div class="modal-footer" style="display:flex; gap:8px; justify-content:flex-end; margin-top:12px; flex-wrap:wrap;">
              <button id="p08-btn-open-contract" class="toolbar-btn" style="background:#1565c0; color:#fff; display:none;" onclick="p08ActionOpenContract()">Open Contract in Grid</button>
              <button id="p08-btn-open-sheet" class="toolbar-btn" style="background:#2e7d32; color:#fff; display:none;" onclick="p08ActionOpenSheet()">Open Sheet Row</button>
              <button class="toolbar-btn" onclick="p08CopyDebugJSON()" style="background:#546e7a; color:#fff;">Copy Debug JSON</button>
              <button class="toolbar-btn" onclick="closeUnresolvedModal()">Dismiss</button>
            </div>
          </div>
        </div>'''

# ── EDIT 2: The unified resolver + modal JS + purge logic + logging ──
RESOLVER_JS = '''
    // ═══════════════════════════════════════════════════════════════
    // P0.8: Unified Triage Record-Link Resolver
    // ═══════════════════════════════════════════════════════════════
    var _p08UnresolvedPayload = null;

    function resolveRecordForTriageItem(item, activeDatasetId) {
      var result = { resolved: false, path: 'unresolved', target: null, debug: null };
      var itemDatasetId = item.dataset_id || '';
      var itemRecordId = item.record_id || '';
      var itemContractId = item.contract_id || item.contract_key || '';
      var itemSheetName = item.sheet_name || '';
      var itemRowIndex = (item.row_index !== undefined && item.row_index !== null) ? item.row_index : -1;
      var itemFieldKey = item.field_key || item.field_name || '';

      console.log('[P0.8-LINK] route_attempt: item_id=' + (item.request_id || item.id || 'unknown') +
        ', active_dataset=' + (activeDatasetId || 'null') +
        ', item_dataset=' + itemDatasetId +
        ', record_id=' + itemRecordId +
        ', contract_id=' + itemContractId +
        ', sheet=' + itemSheetName +
        ', row=' + itemRowIndex);

      // Step 1: Exact match by record_id
      if (itemRecordId) {
        var found = typeof findRecordById === 'function' ? findRecordById(itemRecordId) : null;
        if (found) {
          console.log('[P0.8-LINK] route_resolved_record: record_id=' + itemRecordId + ' found in workbook sheet=' + found.sheetName);
          result.resolved = true;
          result.path = 'exact_record';
          result.target = found;
          result.fieldKey = itemFieldKey;
          return result;
        }
        // Also try canonical store
        var tid = (typeof IDENTITY_CONTEXT !== 'undefined') ? IDENTITY_CONTEXT.tenant_id : '';
        var did = activeDatasetId || '';
        if (tid && did) {
          var storeKey = 'kiwi/v1/' + tid + '/records/' + did + '/' + itemRecordId + '.json';
          var stored = localStorage.getItem(storeKey);
          if (stored) {
            try {
              var rec = JSON.parse(stored);
              console.log('[P0.8-LINK] route_resolved_record: record_id=' + itemRecordId + ' found in canonical store');
              result.resolved = true;
              result.path = 'canonical_store';
              result.target = { row: rec, rowIndex: 0, sheetName: 'canonical', fromStore: true };
              result.fieldKey = itemFieldKey;
              return result;
            } catch (e) { /* ignore parse errors */ }
          }
        }
      }

      // Step 2: sheet_name + row_index lookup
      if (itemSheetName && itemRowIndex >= 0 && workbook && workbook.sheets) {
        var sheet = workbook.sheets[itemSheetName];
        if (sheet && sheet.rows && itemRowIndex < sheet.rows.length) {
          console.log('[P0.8-LINK] route_resolved_record: sheet=' + itemSheetName + ' row=' + itemRowIndex);
          result.resolved = true;
          result.path = 'sheet_row';
          result.target = { row: sheet.rows[itemRowIndex], rowIndex: itemRowIndex, sheetName: itemSheetName };
          result.fieldKey = itemFieldKey;
          return result;
        }
      }

      // Step 3: contract_id + field_key - find any record in active dataset matching contract
      if (itemContractId && workbook && workbook.sheets && typeof ContractIndex !== 'undefined' && ContractIndex.isAvailable()) {
        var contractInfo = ContractIndex._index && ContractIndex._index.contracts ? ContractIndex._index.contracts[itemContractId] : null;
        if (contractInfo && contractInfo.sheets) {
          var sheetKeys = Object.keys(contractInfo.sheets);
          for (var si = 0; si < sheetKeys.length; si++) {
            var sn = sheetKeys[si];
            var rowIndices = contractInfo.sheets[sn];
            if (rowIndices && rowIndices.length > 0 && workbook.sheets[sn] && workbook.sheets[sn].rows) {
              var ri = rowIndices[0];
              if (ri < workbook.sheets[sn].rows.length) {
                console.log('[P0.8-LINK] route_resolved_contract: contract=' + itemContractId + ' sheet=' + sn + ' row=' + ri);
                result.resolved = true;
                result.path = 'contract_field';
                result.target = { row: workbook.sheets[sn].rows[ri], rowIndex: ri, sheetName: sn };
                result.fieldKey = itemFieldKey;
                return result;
              }
            }
          }
        }
      }

      // Step 4: Contract-level fallback - open grid filtered by contract
      if (itemContractId) {
        console.log('[P0.8-LINK] route_resolved_contract: fallback grid filter contract=' + itemContractId);
        result.resolved = true;
        result.path = 'contract_grid';
        result.contractId = itemContractId;
        return result;
      }

      // Step 5: Unresolved - show diagnostics modal
      var debugPayload = {
        item_id: item.request_id || item.id || 'unknown',
        item_type: item.type || item.source || 'unknown',
        record_id: itemRecordId,
        contract_id: itemContractId,
        field: itemFieldKey,
        sheet_name: itemSheetName,
        row_index: itemRowIndex,
        item_dataset_id: itemDatasetId,
        active_dataset_id: activeDatasetId || 'null',
        source_file: item.file_url || item.file_name || '',
        reason: 'no_match_found'
      };
      console.log('[P0.8-LINK] route_unresolved_modal: item_id=' + debugPayload.item_id + ' reason=' + debugPayload.reason);
      result.debug = debugPayload;
      return result;
    }

    function executeTriageResolution(item) {
      var activeDatasetId = (typeof IDENTITY_CONTEXT !== 'undefined') ? IDENTITY_CONTEXT.dataset_id : null;
      var resolution = resolveRecordForTriageItem(item, activeDatasetId);

      if (resolution.resolved) {
        if (resolution.path === 'contract_grid') {
          _activeContractFilter = resolution.contractId;
          navigateTo('grid');
          setTimeout(function() { if (typeof renderGrid === 'function') renderGrid(); }, 100);
        } else if (resolution.target) {
          if (resolution.target.sheetName && resolution.target.sheetName !== 'canonical') {
            openRowReviewDrawer(resolution.target.sheetName, resolution.target.rowIndex);
          } else {
            openRowReviewDrawer(resolution.target.row, resolution.target.rowIndex, item.record_id);
          }
          if (resolution.fieldKey) {
            setTimeout(function() {
              if (typeof focusFieldInInspector === 'function') focusFieldInInspector(resolution.fieldKey);
            }, 300);
          }
        }
      } else {
        showUnresolvedModal(resolution.debug);
      }
    }

    function showUnresolvedModal(debugPayload) {
      _p08UnresolvedPayload = debugPayload;
      var modal = document.getElementById('p08-unresolved-modal');
      if (!modal) return;
      var summaryEl = document.getElementById('p08-unresolved-summary');
      var jsonEl = document.getElementById('p08-unresolved-json');
      var btnContract = document.getElementById('p08-btn-open-contract');
      var btnSheet = document.getElementById('p08-btn-open-sheet');

      if (summaryEl) {
        summaryEl.innerHTML =
          '<div><strong>Item Type:</strong> ' + (debugPayload.item_type || '-') + '</div>' +
          '<div><strong>Record ID:</strong> ' + (debugPayload.record_id || '-') + '</div>' +
          '<div><strong>Contract ID:</strong> ' + (debugPayload.contract_id || '-') + '</div>' +
          '<div><strong>Field:</strong> ' + (debugPayload.field || '-') + '</div>' +
          '<div style="margin-top:8px; padding-top:8px; border-top:1px solid #ffe0b2;">' +
          '<strong>Item Dataset:</strong> ' + (debugPayload.item_dataset_id || '-') +
          ' &nbsp;|&nbsp; <strong>Active Dataset:</strong> ' + (debugPayload.active_dataset_id || '-') + '</div>' +
          '<div><strong>Sheet:</strong> ' + (debugPayload.sheet_name || '-') + ' &nbsp;|&nbsp; <strong>Row:</strong> ' + (debugPayload.row_index >= 0 ? debugPayload.row_index : '-') + '</div>' +
          '<div><strong>Source:</strong> ' + (debugPayload.source_file || '-') + '</div>';
      }
      if (jsonEl) {
        jsonEl.textContent = JSON.stringify(debugPayload, null, 2);
      }
      if (btnContract) {
        btnContract.style.display = debugPayload.contract_id ? 'inline-block' : 'none';
      }
      if (btnSheet) {
        btnSheet.style.display = (debugPayload.sheet_name && debugPayload.row_index >= 0) ? 'inline-block' : 'none';
      }

      modal.style.display = 'flex';

      if (typeof AuditTimeline !== 'undefined' && AuditTimeline.record) {
        AuditTimeline.record({
          action: 'triage_record_unresolved',
          active_dataset_id: debugPayload.active_dataset_id,
          item_dataset_id: debugPayload.item_dataset_id,
          item_id: debugPayload.item_id,
          reason: debugPayload.reason
        });
      }
    }

    function closeUnresolvedModal() {
      var modal = document.getElementById('p08-unresolved-modal');
      if (modal) modal.style.display = 'none';
      _p08UnresolvedPayload = null;
    }

    function p08ActionOpenContract() {
      if (!_p08UnresolvedPayload || !_p08UnresolvedPayload.contract_id) return;
      _activeContractFilter = _p08UnresolvedPayload.contract_id;
      closeUnresolvedModal();
      navigateTo('grid');
      setTimeout(function() { if (typeof renderGrid === 'function') renderGrid(); }, 100);
    }

    function p08ActionOpenSheet() {
      if (!_p08UnresolvedPayload) return;
      var sn = _p08UnresolvedPayload.sheet_name;
      var ri = _p08UnresolvedPayload.row_index;
      if (sn && ri >= 0) {
        closeUnresolvedModal();
        openRowReviewDrawer(sn, ri);
      }
    }

    function p08CopyDebugJSON() {
      if (!_p08UnresolvedPayload) return;
      var text = JSON.stringify(_p08UnresolvedPayload, null, 2);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function() {
          showToast('Debug JSON copied to clipboard', 'success');
        });
      } else {
        window.prompt('Copy this debug JSON:', text);
      }
    }

    function p08PurgeStaleTriageItems(newDatasetId) {
      if (!newDatasetId) return;
      var purgedCount = 0;

      var allPRs = PATCH_REQUEST_STORE.list();
      for (var i = 0; i < allPRs.length; i++) {
        var pr = allPRs[i];
        var prDataset = pr.dataset_id || '';
        if (prDataset && prDataset !== newDatasetId && !pr.cross_dataset) {
          PATCH_REQUEST_STORE.remove(pr.request_id);
          purgedCount++;
        }
      }

      if (purgedCount > 0) {
        console.log('[P0.8-LINK] dataset_mismatch_purged: count=' + purgedCount + ', new_dataset=' + newDatasetId);
        if (typeof AuditTimeline !== 'undefined' && AuditTimeline.record) {
          AuditTimeline.record({
            action: 'dataset_mismatch_purged',
            purged_count: purgedCount,
            new_dataset_id: newDatasetId
          });
        }
      }
    }
'''

def apply_edits(content):
    edits_applied = 0

    # ── EDIT 1: Modal HTML after elevate-to-patch-modal closing div ──
    marker1 = '</div><!-- end admin-tab-patch-console -->'
    if 'p08-unresolved-modal' not in content:
        idx = content.find(marker1)
        if idx == -1:
            print('[P0.8] ERROR: Could not find marker for modal insertion')
            sys.exit(1)
        content = content[:idx] + MODAL_HTML + '\n' + content[idx:]
        edits_applied += 1
        print('[P0.8] EDIT 1: Inserted unresolved-record diagnostics modal HTML')
    else:
        print('[P0.8] EDIT 1: Modal already present, skipping')

    # ── EDIT 2: Resolver JS before openSignalTriageItem ──
    marker2 = '    // v1.6.0: Open SRR at specific field from signal triage item\n    function openSignalTriageItem'
    if 'resolveRecordForTriageItem' not in content:
        idx = content.find(marker2)
        if idx == -1:
            print('[P0.8] ERROR: Could not find marker for resolver insertion')
            sys.exit(1)
        content = content[:idx] + RESOLVER_JS + '\n\n' + content[idx:]
        edits_applied += 1
        print('[P0.8] EDIT 2: Inserted resolveRecordForTriageItem + modal JS + purge logic')
    else:
        print('[P0.8] EDIT 2: Resolver already present, skipping')

    # ── EDIT 3: Rewire openSignalTriageItem to use resolver ──
    old_signal = '''    function openSignalTriageItem(recordId, fieldKey) {
      console.log('[AnalystTriage] Opening signal item:', recordId, fieldKey);
      
      // Find record in workbook or canonical store
      var found = findRecordById(recordId);
      
      if (found) {
        // Open SRR with the record
        openRowReviewDrawer(found.row, found.rowIndex, recordId);
        
        // After SRR opens, scroll to and focus the field
        setTimeout(function() {
          focusFieldInInspector(fieldKey);
        }, 300);
      } else {
        // Try loading from canonical store
        var storeKeys = Object.keys(localStorage).filter(function(k) {
          return k.includes('/records/') && k.endsWith('/' + recordId + '.json');
        });
        
        if (storeKeys.length > 0) {
          try {
            var record = JSON.parse(localStorage.getItem(storeKeys[0]));
            openRowReviewDrawer(record, 0, recordId);
            
            setTimeout(function() {
              focusFieldInInspector(fieldKey);
            }, 300);
          } catch (e) {
            console.error('[AnalystTriage] Error loading record from store:', e);
            showToast('Could not load record data', 'error');
          }
        } else {
          showToast('Record not found. Please load the dataset first.', 'warning');
        }
      }
    }'''

    new_signal = '''    function openSignalTriageItem(recordId, fieldKey) {
      console.log('[AnalystTriage] Opening signal item:', recordId, fieldKey);
      var item = {
        record_id: recordId,
        field_key: fieldKey,
        source: 'signal',
        dataset_id: (typeof IDENTITY_CONTEXT !== 'undefined' ? IDENTITY_CONTEXT.dataset_id : '') || ''
      };
      executeTriageResolution(item);
    }'''

    if old_signal in content:
        content = content.replace(old_signal, new_signal)
        edits_applied += 1
        print('[P0.8] EDIT 3: Rewired openSignalTriageItem to use resolver')
    else:
        print('[P0.8] EDIT 3: openSignalTriageItem already rewired or not found')

    # ── EDIT 4: Rewire openPreflightItem to use resolver ──
    old_preflight = '''    function openPreflightItem(requestId, recordId, contractId, fieldName) {
      console.log('[TRIAGE-ANALYTICS][P0.2] route_decision_start: requestId=' + requestId + ', recordId=' + recordId + ', contractId=' + contractId);
      // Deterministic fallback: row-level > contract-level > grid
      if (recordId && recordId !== 'undefined' && recordId !== '') {
        var found = typeof findRecordById === 'function' ? findRecordById(recordId) : null;
        if (found) {
          console.log('[TRIAGE-ANALYTICS][P0.2] route_decision_record: opening Record Inspection for ' + recordId);
          openRowReviewDrawer(found.row, found.rowIndex, recordId);
          if (fieldName && fieldName !== 'undefined') {
            setTimeout(function() { if (typeof focusFieldInInspector === 'function') focusFieldInInspector(fieldName); }, 300);
          }
          return;
        }
      }
      if (contractId && contractId !== 'undefined' && contractId !== '') {
        console.log('[TRIAGE-ANALYTICS][P0.2] route_decision_contract: fallback to grid filtered by contract ' + contractId);
        navigateTo('grid', { queryParams: 'contract=' + encodeURIComponent(contractId) });
        return;
      }
      console.log('[TRIAGE-ANALYTICS][P0.2] route_decision_fallback: final fallback to all-data grid with warning');
      navigateTo('grid'); if (typeof showToast === 'function') { showToast('No specific record or contract found. Showing all data.', 'warning'); }
    }'''

    new_preflight = '''    function openPreflightItem(requestId, recordId, contractId, fieldName) {
      console.log('[TRIAGE-ANALYTICS][P0.2] route_decision_start: requestId=' + requestId + ', recordId=' + recordId + ', contractId=' + contractId);
      var item = {
        request_id: requestId,
        record_id: (recordId && recordId !== 'undefined') ? recordId : '',
        contract_id: (contractId && contractId !== 'undefined') ? contractId : '',
        field_name: (fieldName && fieldName !== 'undefined') ? fieldName : '',
        source: 'preflight',
        dataset_id: (typeof IDENTITY_CONTEXT !== 'undefined' ? IDENTITY_CONTEXT.dataset_id : '') || ''
      };
      executeTriageResolution(item);
    }'''

    if old_preflight in content:
        content = content.replace(old_preflight, new_preflight)
        edits_applied += 1
        print('[P0.8] EDIT 4: Rewired openPreflightItem to use resolver')
    else:
        print('[P0.8] EDIT 4: openPreflightItem already rewired or not found')

    # ── EDIT 5: Rewire openAnalystTriageItem to use resolver ──
    # Find the old function body and replace
    old_analyst_start = '    function openAnalystTriageItem(requestId) {\n      console.log(\'[AnalystTriage] Opening item:\', requestId);\n      var pr = PATCH_REQUEST_STORE.get(requestId);'
    old_analyst_end = "          showToast('No specific record or contract found. Showing all data.', 'warning');\n        }\n      }\n    }"

    if old_analyst_start in content:
        start_idx = content.find(old_analyst_start)
        end_idx = content.find(old_analyst_end, start_idx)
        if end_idx != -1:
            end_idx += len(old_analyst_end)
            new_analyst = '''    function openAnalystTriageItem(requestId) {
      console.log('[AnalystTriage] Opening item:', requestId);
      var pr = PATCH_REQUEST_STORE.get(requestId);
      if (!pr) {
        console.error('[AnalystTriage] PatchRequest not found:', requestId);
        showToast('Could not find patch request', 'error');
        return;
      }
      var item = {
        request_id: requestId,
        record_id: pr.record_id || (pr.payload && pr.payload.record_id) || '',
        contract_id: pr.contract_id || ((pr.payload && pr.payload.contract_id) || '') || pr.contract_key || '',
        contract_key: pr.contract_key || '',
        field_name: pr.field_name || ((pr.payload && pr.payload.changes) ? Object.keys(pr.payload.changes)[0] : ''),
        dataset_id: pr.dataset_id || (typeof IDENTITY_CONTEXT !== 'undefined' ? IDENTITY_CONTEXT.dataset_id : '') || '',
        source: 'patch_request',
        type: pr.type || 'correction'
      };
      executeTriageResolution(item);

      if (pr.status === 'Needs_Clarification' && pr.clarification_notes) {
        setTimeout(function() {
          showToast('Verifier requested clarification: ' + pr.clarification_notes.substring(0, 100), 'warning');
        }, 500);
      }
    }'''
            content = content[:start_idx] + new_analyst + content[end_idx:]
            edits_applied += 1
            print('[P0.8] EDIT 5: Rewired openAnalystTriageItem to use resolver')
        else:
            print('[P0.8] EDIT 5: Could not find end of openAnalystTriageItem')
    else:
        print('[P0.8] EDIT 5: openAnalystTriageItem already rewired or not found')

    # ── EDIT 6: Hook dataset mismatch purge into workbook load path ──
    # Insert purge call right after IDENTITY_CONTEXT.dataset_id = file.name (line ~15951)
    purge_marker = "        IDENTITY_CONTEXT.dataset_id = file.name;"
    purge_call = "\n        if (typeof p08PurgeStaleTriageItems === 'function') p08PurgeStaleTriageItems(file.name);"
    if 'p08PurgeStaleTriageItems' not in content:
        content = content.replace(
            purge_marker,
            purge_marker + purge_call,
            2  # Replace both occurrences (there are 2 upload paths)
        )
        edits_applied += 1
        print('[P0.8] EDIT 6: Added dataset mismatch purge hook on workbook load')
    else:
        print('[P0.8] EDIT 6: Purge hook already present, skipping')

    print('[P0.8] Total edits applied: ' + str(edits_applied))
    return content

if __name__ == '__main__':
    content = read_file()
    content = apply_edits(content)
    write_file(content)
    print('[P0.8] Delta applied successfully.')
