#!/usr/bin/env python3
"""V2.3 Triage Analytics Header + V2.3b Record Inspector Guidance insertion script."""
import sys

FILE = 'ui/viewer/index.html'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

original_len = len(content)

# ============================================================
# 1. CSS STYLES - insert before </style>
# ============================================================
CSS_BLOCK = """
    /* V2.3: Triage Analytics Header */
    .ta-lane-card { position: relative; overflow: hidden; }
    .ta-lane-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
    .ta-lane-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
    #triage-analytics-header { animation: ta-fade-in 0.3s ease; }
    @keyframes ta-fade-in { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
    .ta-lifecycle-stage { transition: all 0.2s ease; }
    .ta-lifecycle-stage:hover { transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .ta-contract-row:hover { background: #f8f9ff !important; }
    /* V2.3b: Section Guidance */
    .section-guidance-card { animation: ta-fade-in 0.2s ease; }
    .section-guidance-toggle { cursor: pointer; user-select: none; }
    .knowledge-rail a:hover { background: #e3f2fd; }
"""

style_marker = '</style>'
idx = content.rfind(style_marker)
if idx < 0:
    print("ERROR: Could not find </style> marker")
    sys.exit(1)
content = content[:idx] + CSS_BLOCK + '\n    ' + content[idx:]
print(f"[1/7] CSS inserted before </style>")

# ============================================================
# 2. ANALYTICS HEADER HTML - insert before <!-- QUEUE 1: Pre-Flight -->
# ============================================================
ANALYTICS_HTML = """          <!-- V2.3: Triage Analytics Header -->
          <div id="triage-analytics-header" style="margin-bottom: 24px; display: none;">
            <!-- A) 3 Lanes -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px;">
              <div class="ta-lane-card" onclick="TriageAnalytics.handleLaneClick('preflight')" style="background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px; cursor: pointer; transition: box-shadow 0.2s; border-top: 3px solid #f44336;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                  <h4 style="margin: 0; font-size: 0.9em; color: #333;">Pre-Flight</h4>
                  <span id="ta-preflight-total" style="background: #ffebee; color: #c62828; padding: 2px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">0</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.8em;">
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Unknown Cols</span><span id="ta-pf-unknown" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">OCR Unreadable</span><span id="ta-pf-ocr" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Low Confidence</span><span id="ta-pf-lowconf" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Mojibake</span><span id="ta-pf-mojibake" style="font-weight: 600;">0</span></div>
                </div>
              </div>
              <div class="ta-lane-card" onclick="TriageAnalytics.handleLaneClick('semantic')" style="background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px; cursor: pointer; transition: box-shadow 0.2s; border-top: 3px solid #ff9800;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                  <h4 style="margin: 0; font-size: 0.9em; color: #333;">Semantic</h4>
                  <span id="ta-semantic-total" style="background: #fff3e0; color: #e65100; padding: 2px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">0</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.8em;">
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Proposals</span><span id="ta-sem-proposals" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Accepted</span><span id="ta-sem-accepted" style="font-weight: 600; color: #2e7d32;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Rejected</span><span id="ta-sem-rejected" style="font-weight: 600; color: #c62828;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Hinge-Impacted</span><span id="ta-sem-hinge" style="font-weight: 600; color: #e65100;">0</span></div>
                </div>
              </div>
              <div class="ta-lane-card" onclick="TriageAnalytics.handleLaneClick('patch')" style="background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px; cursor: pointer; transition: box-shadow 0.2s; border-top: 3px solid #1976d2;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                  <h4 style="margin: 0; font-size: 0.9em; color: #333;">Patch Review</h4>
                  <span id="ta-patch-total" style="background: #e3f2fd; color: #1565c0; padding: 2px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">0</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.8em;">
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Submitted</span><span id="ta-pr-submitted" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">At Verifier</span><span id="ta-pr-verifier" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">RFIs</span><span id="ta-pr-rfi" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Promoted</span><span id="ta-pr-promoted" style="font-weight: 600; color: #2e7d32;">0</span></div>
                </div>
              </div>
            </div>
            <!-- B) Lifecycle Stage Tracker -->
            <div style="margin-bottom: 20px; background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; font-size: 0.9em; color: #333;">Lifecycle Progression</h4>
                <span style="font-size: 0.75em; color: #999;" id="ta-lifecycle-updated"></span>
              </div>
              <div id="ta-lifecycle-stages" style="display: flex; gap: 2px; align-items: stretch; overflow-x: auto;"></div>
            </div>
            <!-- C) Contract Summary Table -->
            <div style="margin-bottom: 20px; background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
              <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #eee;">
                <h4 style="margin: 0; font-size: 0.9em; color: #333;">Contract Summary</h4>
                <span id="ta-contract-count" style="font-size: 0.8em; color: #666;">0 contracts</span>
              </div>
              <div style="max-height: 280px; overflow-y: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 0.82em;">
                  <thead style="background: #fafafa; position: sticky; top: 0;">
                    <tr>
                      <th style="padding: 8px 12px; text-align: left; font-weight: 600; color: #555;">Contract</th>
                      <th style="padding: 8px 12px; text-align: left; font-weight: 600; color: #555;">Doc Role</th>
                      <th style="padding: 8px 12px; text-align: center; font-weight: 600; color: #555;">Stage</th>
                      <th style="padding: 8px 12px; text-align: center; font-weight: 600; color: #f44336;">Pre-Flight</th>
                      <th style="padding: 8px 12px; text-align: center; font-weight: 600; color: #ff9800;">Semantic</th>
                      <th style="padding: 8px 12px; text-align: center; font-weight: 600; color: #1976d2;">Patches</th>
                      <th style="padding: 8px 12px; text-align: right; font-weight: 600; color: #555;">Rows</th>
                    </tr>
                  </thead>
                  <tbody id="ta-contract-tbody">
                    <tr><td colspan="7" style="padding: 20px; text-align: center; color: #999;">No contracts indexed</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
            <!-- D) Schema Snapshot -->
            <div style="margin-bottom: 20px; background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px;">
              <h4 style="margin: 0 0 12px; font-size: 0.9em; color: #333;">Schema Snapshot</h4>
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
                <div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
                  <div id="ta-schema-matched-pct" style="font-size: 1.4em; font-weight: 700; color: #2e7d32;">--</div>
                  <div style="font-size: 0.75em; color: #666;">Fields Matched</div>
                  <div id="ta-schema-matched-count" style="font-size: 0.7em; color: #999;">0 / 0</div>
                </div>
                <div style="text-align: center; padding: 10px; background: #fff3e0; border-radius: 8px;">
                  <div id="ta-schema-unknown" style="font-size: 1.4em; font-weight: 700; color: #e65100;">0</div>
                  <div style="font-size: 0.75em; color: #666;">Unknown Columns</div>
                </div>
                <div style="text-align: center; padding: 10px; background: #ffebee; border-radius: 8px;">
                  <div id="ta-schema-missing" style="font-size: 1.4em; font-weight: 700; color: #c62828;">0</div>
                  <div style="font-size: 0.75em; color: #666;">Missing Required</div>
                </div>
                <div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
                  <div id="ta-schema-drift" style="font-size: 1.4em; font-weight: 700; color: #555;">0</div>
                  <div style="font-size: 0.75em; color: #666;">Schema Drift</div>
                </div>
              </div>
            </div>
          </div>
"""

html_marker = '          <!-- QUEUE 1: Pre-Flight -->'
idx = content.find(html_marker)
if idx < 0:
    print("ERROR: Could not find QUEUE 1 Pre-Flight marker")
    sys.exit(1)
content = content[:idx] + ANALYTICS_HTML + '\n' + content[idx:]
print(f"[2/7] Analytics header HTML inserted")

# ============================================================
# 3. TRIAGE ANALYTICS JS MODULE - insert before analystTriageState
# ============================================================
ANALYTICS_JS = """
    // ========================================================================
    // V2.3: Triage Analytics Aggregator + Renderer
    // ========================================================================
    var TriageAnalytics = {
      _cache: null,
      _lastRefreshedAt: null,

      refresh: function() {
        var cache = {
          refreshed_at: new Date().toISOString(),
          lanes: {
            preflight: { unknown_columns: 0, ocr_unreadable: 0, low_confidence: 0, mojibake: 0, total: 0 },
            semantic: { proposals_created: 0, accepted: 0, rejected: 0, pending: 0, hinge_impacted: 0, total: 0 },
            patch_review: { submitted: 0, in_verifier: 0, rfi_submitted: 0, clarification: 0, promoted: 0, applied: 0, total: 0 }
          },
          lifecycle: {
            loaded: { count: 0, pct: 0 },
            preflight_complete: { count: 0, pct: 0 },
            system_pass_complete: { count: 0, pct: 0 },
            system_changes_reviewed: { count: 0, pct: 0 },
            patch_submitted: { count: 0, pct: 0 },
            rfi_submitted: { count: 0, pct: 0 },
            verifier_complete: { count: 0, pct: 0 },
            admin_promoted: { count: 0, pct: 0 },
            applied: { count: 0, pct: 0 }
          },
          contracts: [],
          schema: { standard_matched: 0, standard_total: 0, unknown_columns: 0, missing_required: 0, schema_drift: 0 },
          processing: { queued: 0, processing: 0, completed: 0, failed: 0 },
          total_contracts: 0
        };

        (analystTriageState.manualItems || []).forEach(function(item) {
          var bt = (item.blocker_type || item.signal_type || '').toUpperCase();
          if (bt === 'UNKNOWN_COLUMN') cache.lanes.preflight.unknown_columns++;
          else if (bt === 'OCR_UNREADABLE') cache.lanes.preflight.ocr_unreadable++;
          else if (bt === 'LOW_CONFIDENCE') cache.lanes.preflight.low_confidence++;
          else if (bt === 'MOJIBAKE' || bt === 'MOJIBAKE_DETECTED') cache.lanes.preflight.mojibake++;
        });
        cache.lanes.preflight.total = cache.lanes.preflight.unknown_columns + cache.lanes.preflight.ocr_unreadable + cache.lanes.preflight.low_confidence + cache.lanes.preflight.mojibake;

        if (typeof SystemPass !== 'undefined' && SystemPass._proposals) {
          SystemPass._proposals.forEach(function(p) {
            cache.lanes.semantic.proposals_created++;
            if (p.status === 'accepted') cache.lanes.semantic.accepted++;
            else if (p.status === 'rejected') cache.lanes.semantic.rejected++;
            else cache.lanes.semantic.pending++;
            if (p.is_hinge) cache.lanes.semantic.hinge_impacted++;
          });
          cache.lanes.semantic.total = cache.lanes.semantic.proposals_created;
        }

        var allPatches = typeof PATCH_REQUEST_STORE !== 'undefined' ? PATCH_REQUEST_STORE.list() : [];
        allPatches.forEach(function(pr) {
          var s = (pr.status || '').toLowerCase().replace(/\\s+/g, '_');
          if (s === 'submitted' || s === 'draft') cache.lanes.patch_review.submitted++;
          else if (s === 'verifier_responded' || s === 'verifier_reviewing') cache.lanes.patch_review.in_verifier++;
          else if (s.indexOf('rfi') >= 0) cache.lanes.patch_review.rfi_submitted++;
          else if (s === 'needs_clarification') cache.lanes.patch_review.clarification++;
          else if (s === 'admin_approved' || s === 'verifier_approved') cache.lanes.patch_review.promoted++;
          else if (s === 'applied' || s === 'closed') cache.lanes.patch_review.applied++;
        });
        cache.lanes.patch_review.total = allPatches.length;

        var totalContracts = 0;
        if (typeof ContractIndex !== 'undefined' && ContractIndex.isAvailable() && ContractIndex._index) {
          var contractIds = Object.keys(ContractIndex._index.contracts);
          totalContracts = contractIds.length;
          cache.total_contracts = totalContracts;

          contractIds.forEach(function(cid) {
            var c = ContractIndex._index.contracts[cid];
            var contractPatches = allPatches.filter(function(pr) {
              return pr.contract_key === cid || pr.contract_id === cid;
            });

            var stage = 'loaded';
            var hasBlockers = false;
            (analystTriageState.manualItems || []).forEach(function(item) {
              if (item.contract_id === cid || item.contract_key === cid) hasBlockers = true;
            });
            if (!hasBlockers) stage = 'preflight_complete';

            if (typeof SystemPass !== 'undefined' && SystemPass._lastRunTimestamp) {
              stage = 'system_pass_complete';
              var cProposals = (SystemPass._proposals || []).filter(function(p) { return p.contract_id === cid; });
              var allReviewed = cProposals.length === 0 || cProposals.every(function(p) { return p.status !== 'pending'; });
              if (allReviewed) stage = 'system_changes_reviewed';
            }

            if (contractPatches.length > 0) {
              stage = 'patch_submitted';
              if (contractPatches.some(function(p) { return (p.status || '').toLowerCase().indexOf('rfi') >= 0 || p.artifact_type === 'rfi'; })) stage = 'rfi_submitted';
              if (contractPatches.every(function(p) { var s = (p.status||'').toLowerCase(); return s === 'verifier_approved' || s === 'admin_approved' || s === 'applied' || s === 'closed'; })) stage = 'verifier_complete';
              if (contractPatches.every(function(p) { var s = (p.status||'').toLowerCase(); return s === 'admin_approved' || s === 'applied' || s === 'closed'; })) stage = 'admin_promoted';
              if (contractPatches.every(function(p) { var s = (p.status||'').toLowerCase(); return s === 'applied' || s === 'closed'; })) stage = 'applied';
            }

            cache.lifecycle[stage] = cache.lifecycle[stage] || { count: 0, pct: 0 };
            cache.lifecycle[stage].count++;

            var pfAlerts = 0, semAlerts = 0, patchAlerts = contractPatches.length;
            (analystTriageState.manualItems || []).forEach(function(item) {
              if (item.contract_id === cid || item.contract_key === cid) pfAlerts++;
            });
            (SystemPass._proposals || []).forEach(function(p) {
              if (p.contract_id === cid) semAlerts++;
            });

            var displayName = c.file_name || cid;
            var docRole = '';
            if (c.sheets) {
              var firstSheet = Object.keys(c.sheets)[0];
              if (firstSheet && typeof workbook !== 'undefined' && workbook.sheets[firstSheet] && c.sheets[firstSheet][0]) {
                var firstRow = workbook.sheets[firstSheet].rows[c.sheets[firstSheet][0].row_index];
                if (firstRow) docRole = firstRow._document_role || firstRow.document_type || '';
              }
            }

            cache.contracts.push({
              contract_id: cid, display_name: displayName, doc_role: docRole,
              current_stage: stage, preflight_alerts: pfAlerts, semantic_alerts: semAlerts,
              patch_alerts: patchAlerts, last_updated: new Date().toISOString(), row_count: c.row_count || 0
            });
          });

          if (ContractIndex._index.orphan_rows && ContractIndex._index.orphan_rows.length > 0) {
            cache.contracts.push({
              contract_id: '__unassigned__', display_name: 'Unassigned (Batch Level)', doc_role: '',
              current_stage: 'loaded', preflight_alerts: 0, semantic_alerts: 0, patch_alerts: 0,
              last_updated: new Date().toISOString(), row_count: ContractIndex._index.orphan_rows.length
            });
            cache.lifecycle.loaded.count++;
            totalContracts++;
            cache.total_contracts = totalContracts;
          }
        } else {
          cache.total_contracts = 1;
          cache.lifecycle.loaded.count = 1;
          totalContracts = 1;
        }

        Object.keys(cache.lifecycle).forEach(function(stage) {
          cache.lifecycle[stage].pct = totalContracts > 0 ? Math.round((cache.lifecycle[stage].count / totalContracts) * 100) : 0;
        });

        if (typeof rulesBundleCache !== 'undefined' && rulesBundleCache.fieldMeta && rulesBundleCache.fieldMeta.fields) {
          var allFields = rulesBundleCache.fieldMeta.fields;
          cache.schema.standard_total = allFields.length;
          var wbCols = {};
          if (typeof workbook !== 'undefined' && workbook.order) {
            workbook.order.forEach(function(sn) {
              var sh = workbook.sheets[sn];
              if (sh && sh.headers) sh.headers.forEach(function(h) { wbCols[h.toLowerCase()] = true; });
            });
          }
          allFields.forEach(function(f) {
            if (wbCols[f.field_key.toLowerCase()] || wbCols[(f.field_key + '_c').toLowerCase()]) cache.schema.standard_matched++;
          });
          cache.schema.missing_required = allFields.filter(function(f) {
            return f.required && !wbCols[f.field_key.toLowerCase()] && !wbCols[(f.field_key + '_c').toLowerCase()];
          }).length;
        }
        if (typeof ContractIndex !== 'undefined' && ContractIndex.isAvailable() && ContractIndex._index && ContractIndex._index.unknown_columns) {
          cache.schema.unknown_columns = Object.keys(ContractIndex._index.unknown_columns).length;
        }
        cache.schema.schema_drift = cache.schema.unknown_columns + cache.schema.missing_required;
        cache.processing.completed = totalContracts;

        this._cache = cache;
        this._lastRefreshedAt = cache.refreshed_at;
        return cache;
      },

      getCache: function() {
        if (!this._cache) this.refresh();
        return this._cache;
      },

      renderHeader: function() {
        var cache = this.getCache();
        var header = document.getElementById('triage-analytics-header');
        if (!header) return;
        header.style.display = 'block';

        var el = function(id) { return document.getElementById(id); };
        if (el('ta-preflight-total')) el('ta-preflight-total').textContent = cache.lanes.preflight.total;
        if (el('ta-pf-unknown')) el('ta-pf-unknown').textContent = cache.lanes.preflight.unknown_columns;
        if (el('ta-pf-ocr')) el('ta-pf-ocr').textContent = cache.lanes.preflight.ocr_unreadable;
        if (el('ta-pf-lowconf')) el('ta-pf-lowconf').textContent = cache.lanes.preflight.low_confidence;
        if (el('ta-pf-mojibake')) el('ta-pf-mojibake').textContent = cache.lanes.preflight.mojibake;

        if (el('ta-semantic-total')) el('ta-semantic-total').textContent = cache.lanes.semantic.total;
        if (el('ta-sem-proposals')) el('ta-sem-proposals').textContent = cache.lanes.semantic.proposals_created;
        if (el('ta-sem-accepted')) el('ta-sem-accepted').textContent = cache.lanes.semantic.accepted;
        if (el('ta-sem-rejected')) el('ta-sem-rejected').textContent = cache.lanes.semantic.rejected;
        if (el('ta-sem-hinge')) el('ta-sem-hinge').textContent = cache.lanes.semantic.hinge_impacted;

        if (el('ta-patch-total')) el('ta-patch-total').textContent = cache.lanes.patch_review.total;
        if (el('ta-pr-submitted')) el('ta-pr-submitted').textContent = cache.lanes.patch_review.submitted;
        if (el('ta-pr-verifier')) el('ta-pr-verifier').textContent = cache.lanes.patch_review.in_verifier;
        if (el('ta-pr-rfi')) el('ta-pr-rfi').textContent = cache.lanes.patch_review.rfi_submitted;
        if (el('ta-pr-promoted')) el('ta-pr-promoted').textContent = cache.lanes.patch_review.promoted;

        this._renderLifecycle(cache);
        this._renderContractTable(cache);
        this._renderSchemaSnapshot(cache);

        if (el('ta-lifecycle-updated')) el('ta-lifecycle-updated').textContent = 'Updated: ' + new Date(cache.refreshed_at).toLocaleTimeString();
      },

      _renderLifecycle: function(cache) {
        var container = document.getElementById('ta-lifecycle-stages');
        if (!container) return;
        var stages = [
          { key: 'loaded', label: 'Loaded', icon: '\\u{1F4E5}' },
          { key: 'preflight_complete', label: 'Pre-Flight', icon: '\\u2705' },
          { key: 'system_pass_complete', label: 'System Pass', icon: '\\u2699\\uFE0F' },
          { key: 'system_changes_reviewed', label: 'Reviewed', icon: '\\u{1F50D}' },
          { key: 'patch_submitted', label: 'Patch Sub.', icon: '\\u{1F4DD}' },
          { key: 'rfi_submitted', label: 'RFI', icon: '\\u2753' },
          { key: 'verifier_complete', label: 'Verifier', icon: '\\u2696\\uFE0F' },
          { key: 'admin_promoted', label: 'Promoted', icon: '\\u{1F451}' },
          { key: 'applied', label: 'Applied', icon: '\\u{1F680}' }
        ];
        var html = '';
        stages.forEach(function(s, i) {
          var data = cache.lifecycle[s.key] || { count: 0, pct: 0 };
          var active = data.count > 0;
          var bg = active ? '#e3f2fd' : '#f5f5f5';
          var border = active ? '#1976d2' : '#e0e0e0';
          var color = active ? '#1565c0' : '#999';
          html += '<div class="ta-lifecycle-stage" onclick="TriageAnalytics.handleStageClick(\\'' + s.key + '\\')" style="flex: 1; min-width: 80px; text-align: center; padding: 10px 4px; background: ' + bg + '; border: 1px solid ' + border + '; border-radius: 6px; cursor: pointer;">';
          html += '<div style="font-size: 1.1em;">' + s.icon + '</div>';
          html += '<div style="font-size: 0.68em; font-weight: 600; color: ' + color + '; margin: 3px 0 1px;">' + s.label + '</div>';
          html += '<div style="font-size: 1em; font-weight: 700; color: ' + (active ? '#1565c0' : '#bbb') + ';">' + data.count + '</div>';
          html += '<div style="font-size: 0.62em; color: ' + color + ';">' + data.pct + '%</div>';
          html += '</div>';
          if (i < stages.length - 1) html += '<div style="display: flex; align-items: center; color: #ccc; font-size: 0.7em;">\\u25B6</div>';
        });
        container.innerHTML = html;
      },

      _renderContractTable: function(cache) {
        var tbody = document.getElementById('ta-contract-tbody');
        if (!tbody) return;
        var el = function(id) { return document.getElementById(id); };
        if (el('ta-contract-count')) el('ta-contract-count').textContent = cache.contracts.length + ' contract' + (cache.contracts.length !== 1 ? 's' : '');

        if (cache.contracts.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: #999;">No contracts indexed</td></tr>';
          return;
        }

        var SL = { loaded: 'Loaded', preflight_complete: 'Pre-Flight Done', system_pass_complete: 'System Pass', system_changes_reviewed: 'Reviewed', patch_submitted: 'Patch Sub.', rfi_submitted: 'RFI', verifier_complete: 'Verifier Done', admin_promoted: 'Promoted', applied: 'Applied' };
        var SC = { loaded: '#9e9e9e', preflight_complete: '#4caf50', system_pass_complete: '#ff9800', system_changes_reviewed: '#2196f3', patch_submitted: '#1976d2', rfi_submitted: '#f57f17', verifier_complete: '#7b1fa2', admin_promoted: '#00897b', applied: '#2e7d32' };

        var html = '';
        cache.contracts.forEach(function(c) {
          var sl = SL[c.current_stage] || c.current_stage;
          var sc = SC[c.current_stage] || '#666';
          var dn = (c.display_name || c.contract_id || '').replace(/"/g, '&quot;').replace(/'/g, "\\\\'");
          html += '<tr class="ta-contract-row" onclick="TriageAnalytics.handleContractClick(\\'' + c.contract_id + '\\', \\'' + c.current_stage + '\\')" style="cursor: pointer; border-bottom: 1px solid #f0f0f0;">';
          html += '<td style="padding: 8px 12px; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="' + (c.display_name || '').replace(/"/g, '&quot;') + '">' + (c.display_name || c.contract_id) + '</td>';
          html += '<td style="padding: 8px 12px; color: #666;">' + (c.doc_role || '-') + '</td>';
          html += '<td style="padding: 8px 12px; text-align: center;"><span style="padding: 2px 8px; border-radius: 10px; font-size: 0.85em; background: ' + sc + '22; color: ' + sc + '; font-weight: 600;">' + sl + '</span></td>';
          html += '<td style="padding: 8px 12px; text-align: center; color: ' + (c.preflight_alerts > 0 ? '#c62828' : '#ccc') + '; font-weight: 600;">' + c.preflight_alerts + '</td>';
          html += '<td style="padding: 8px 12px; text-align: center; color: ' + (c.semantic_alerts > 0 ? '#e65100' : '#ccc') + '; font-weight: 600;">' + c.semantic_alerts + '</td>';
          html += '<td style="padding: 8px 12px; text-align: center; color: ' + (c.patch_alerts > 0 ? '#1565c0' : '#ccc') + '; font-weight: 600;">' + c.patch_alerts + '</td>';
          html += '<td style="padding: 8px 12px; text-align: right; color: #666;">' + (c.row_count || 0) + '</td>';
          html += '</tr>';
        });
        tbody.innerHTML = html;
      },

      _renderSchemaSnapshot: function(cache) {
        var el = function(id) { return document.getElementById(id); };
        var pct = cache.schema.standard_total > 0 ? Math.round((cache.schema.standard_matched / cache.schema.standard_total) * 100) : 0;
        if (el('ta-schema-matched-pct')) el('ta-schema-matched-pct').textContent = pct + '%';
        if (el('ta-schema-matched-count')) el('ta-schema-matched-count').textContent = cache.schema.standard_matched + ' / ' + cache.schema.standard_total;
        if (el('ta-schema-unknown')) el('ta-schema-unknown').textContent = cache.schema.unknown_columns;
        if (el('ta-schema-missing')) el('ta-schema-missing').textContent = cache.schema.missing_required;
        if (el('ta-schema-drift')) el('ta-schema-drift').textContent = cache.schema.schema_drift;
      },

      handleLaneClick: function(lane) {
        var filterMap = { preflight: 'preflight', semantic: 'semantic', patch: 'patch' };
        navigateToGridFiltered(filterMap[lane] || 'all');
      },

      handleStageClick: function(stage) {
        navigateToGridFiltered('stage_' + stage);
      },

      handleContractClick: function(contractId, stage) {
        var params = ['contract=' + encodeURIComponent(contractId)];
        if (stage) params.push('stage=' + encodeURIComponent(stage));
        navigateTo('grid', { queryParams: params.join('&') });
      }
    };

"""

js_marker = '    var analystTriageState = {'
idx = content.find(js_marker)
if idx < 0:
    print("ERROR: Could not find analystTriageState marker")
    sys.exit(1)
content = content[:idx] + ANALYTICS_JS + content[idx:]
print(f"[3/7] TriageAnalytics JS module inserted")

# ============================================================
# 4. WIRE ANALYTICS INTO renderAnalystTriage
# ============================================================
render_marker = '    function renderAnalystTriage() {\n      // Reload from store\n      loadAnalystTriageFromStore();'
idx = content.find(render_marker)
if idx < 0:
    render_marker = '    function renderAnalystTriage() {'
    idx = content.find(render_marker)
    if idx < 0:
        print("ERROR: Could not find renderAnalystTriage marker")
        sys.exit(1)
    insert_after = idx + len(render_marker)
    wire_code = """
      // V2.3: Refresh and render analytics header
      if (typeof TriageAnalytics !== 'undefined') {
        try { TriageAnalytics.refresh(); TriageAnalytics.renderHeader(); } catch(e) { console.warn('[V2.3] Analytics render error:', e); }
      }
"""
    content = content[:insert_after] + wire_code + content[insert_after:]
else:
    insert_after = idx + len(render_marker)
    wire_code = """

      // V2.3: Refresh and render analytics header
      if (typeof TriageAnalytics !== 'undefined') {
        try { TriageAnalytics.refresh(); TriageAnalytics.renderHeader(); } catch(e) { console.warn('[V2.3] Analytics render error:', e); }
      }
"""
    content = content[:insert_after] + wire_code + content[insert_after:]
print(f"[4/7] Analytics wired into renderAnalystTriage")

# ============================================================
# 5. SECTION GUIDANCE + KNOWLEDGE RAIL JS - insert before openRowReviewDrawer
# ============================================================
GUIDANCE_JS = """
    // ========================================================================
    // V2.3b: Section Guidance + Knowledge Rail
    // ========================================================================
    var _sectionGuidanceConfig = null;
    var _knowledgeLinksConfig = null;
    var _guidanceCardExpanded = null;

    function loadSectionGuidanceConfig() {
      if (_sectionGuidanceConfig) return Promise.resolve(_sectionGuidanceConfig);
      return fetch('/config/section_guidance.json')
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) { _sectionGuidanceConfig = data; return data; })
        .catch(function() { _sectionGuidanceConfig = null; return null; });
    }

    function loadKnowledgeLinksConfig() {
      if (_knowledgeLinksConfig) return Promise.resolve(_knowledgeLinksConfig);
      return fetch('/config/knowledge_links.json')
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) { _knowledgeLinksConfig = data; return data; })
        .catch(function() { _knowledgeLinksConfig = null; return null; });
    }

    function getSectionGuidance(docRole, docType) {
      if (!_sectionGuidanceConfig || !_sectionGuidanceConfig.guidance) {
        return _sectionGuidanceConfig ? _sectionGuidanceConfig.guidance['default'] : null;
      }
      var key1 = (docRole || '') + '::' + (docType || '');
      var key2 = docRole || '';
      return _sectionGuidanceConfig.guidance[key1] || _sectionGuidanceConfig.guidance[key2] || _sectionGuidanceConfig.guidance['default'] || null;
    }

    function renderSectionGuidanceCard(record, container) {
      if (!container || !_sectionGuidanceConfig) return;
      var docRole = record._document_role || record.document_role || '';
      var docType = record._document_type || record.document_type || '';
      var confidence = record._confidence || record.confidence || null;
      var guidance = getSectionGuidance(docRole, docType);
      if (!guidance) return;

      if (_guidanceCardExpanded === null) {
        var pref = localStorage.getItem('guidance_card_expanded');
        _guidanceCardExpanded = pref === null ? true : pref === 'true';
      }

      var expanded = _guidanceCardExpanded;
      var html = '<div id="section-guidance-card" class="section-guidance-card" style="margin-bottom: 16px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; background: #fafbff;">';
      html += '<div class="section-guidance-toggle" onclick="toggleGuidanceCard()" style="padding: 10px 14px; background: #f0f4ff; display: flex; justify-content: space-between; align-items: center; border-bottom: ' + (expanded ? '1px solid #e0e0e0' : 'none') + ';">';
      html += '<div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">';
      html += '<span style="font-size: 1.1em;">\\u{1F4D6}</span>';
      html += '<span style="font-weight: 600; font-size: 0.85em; color: #333;">Section Guidance</span>';
      if (docRole) html += '<span style="padding: 2px 8px; background: #e8eaf6; color: #3949ab; border-radius: 10px; font-size: 0.75em;">' + docRole + '</span>';
      if (docType) html += '<span style="padding: 2px 8px; background: #e0f2f1; color: #00695c; border-radius: 10px; font-size: 0.75em;">' + docType + '</span>';
      if (confidence) {
        var confColor = confidence >= 0.8 ? '#2e7d32' : confidence >= 0.6 ? '#e65100' : '#c62828';
        html += '<span style="padding: 2px 8px; background: ' + confColor + '18; color: ' + confColor + '; border-radius: 10px; font-size: 0.75em;">' + Math.round(confidence * 100) + '% conf</span>';
      }
      html += '</div>';
      html += '<span style="font-size: 0.8em; color: #999;" id="guidance-card-chevron">' + (expanded ? '\\u25B2' : '\\u25BC') + '</span>';
      html += '</div>';

      html += '<div id="guidance-card-body" style="' + (expanded ? '' : 'display: none;') + ' padding: 14px;">';
      html += '<div style="font-size: 0.9em; font-weight: 600; color: #333; margin-bottom: 10px;">' + (guidance.section_label || 'General Review') + '</div>';

      if (guidance.what_to_look_for && guidance.what_to_look_for.length > 0) {
        html += '<div style="margin-bottom: 10px;">';
        html += '<div style="font-size: 0.78em; font-weight: 600; color: #1565c0; margin-bottom: 4px;">What to look for:</div>';
        html += '<ul style="margin: 0; padding-left: 18px; font-size: 0.8em; color: #444; line-height: 1.7;">';
        guidance.what_to_look_for.forEach(function(item) { html += '<li>' + item + '</li>'; });
        html += '</ul></div>';
      }

      if (guidance.common_failure_modes && guidance.common_failure_modes.length > 0) {
        html += '<div>';
        html += '<div style="font-size: 0.78em; font-weight: 600; color: #c62828; margin-bottom: 4px;">Common failure modes:</div>';
        html += '<ul style="margin: 0; padding-left: 18px; font-size: 0.8em; color: #666; line-height: 1.7;">';
        guidance.common_failure_modes.forEach(function(item) { html += '<li>' + item + '</li>'; });
        html += '</ul></div>';
      }

      html += '</div></div>';
      container.insertAdjacentHTML('afterbegin', html);
    }

    function toggleGuidanceCard() {
      var body = document.getElementById('guidance-card-body');
      var chevron = document.getElementById('guidance-card-chevron');
      if (!body) return;
      var isVisible = body.style.display !== 'none';
      body.style.display = isVisible ? 'none' : 'block';
      if (chevron) chevron.textContent = isVisible ? '\\u25BC' : '\\u25B2';
      _guidanceCardExpanded = !isVisible;
      localStorage.setItem('guidance_card_expanded', String(_guidanceCardExpanded));
    }

    function renderKnowledgeRail(container) {
      if (!container || !_knowledgeLinksConfig || !_knowledgeLinksConfig.links) return;
      var links = _knowledgeLinksConfig.links
        .filter(function(l) { return l.enabled && l.roles_allowed && l.roles_allowed.indexOf(currentMode) >= 0; })
        .sort(function(a, b) { return (a.order || 99) - (b.order || 99); });
      if (links.length === 0) return;

      var categories = {};
      links.forEach(function(l) {
        var cat = l.category || 'General';
        if (!categories[cat]) categories[cat] = [];
        categories[cat].push(l);
      });

      var html = '<div class="knowledge-rail" style="margin-top: 16px; border-top: 1px solid #e0e0e0; padding-top: 12px;">';
      html += '<div style="display: flex; align-items: center; gap: 6px; margin-bottom: 10px;">';
      html += '<span style="font-size: 1em;">\\u{1F4DA}</span>';
      html += '<span style="font-weight: 600; font-size: 0.85em; color: #333;">Knowledge</span>';
      html += '</div>';

      Object.keys(categories).forEach(function(cat) {
        html += '<div style="margin-bottom: 8px;">';
        html += '<div style="font-size: 0.72em; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">' + cat + '</div>';
        categories[cat].forEach(function(link) {
          html += '<a href="' + link.url + '" target="_blank" rel="noopener" onclick="emitKnowledgeLinkEvent(\\'' + link.id + '\\')" style="display: flex; align-items: center; gap: 6px; padding: 5px 8px; margin-bottom: 2px; font-size: 0.8em; color: #1565c0; text-decoration: none; border-radius: 4px; transition: background 0.15s;" onmouseover="this.style.background=\\'#e3f2fd\\'" onmouseout="this.style.background=\\'transparent\\'">';
          html += '<span>' + link.title + '</span>';
          html += '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; opacity: 0.5;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>';
          html += '</a>';
        });
        html += '</div>';
      });

      html += '</div>';
      container.insertAdjacentHTML('beforeend', html);
    }

    function emitKnowledgeLinkEvent(linkId) {
      if (typeof AuditTimeline !== 'undefined') {
        var context = {};
        if (typeof srrState !== 'undefined' && srrState.currentRowId !== null) context.record_id = srrState.currentRowId;
        if (typeof srrState !== 'undefined' && srrState.currentSheetName) context.sheet = srrState.currentSheetName;
        AuditTimeline.emit('knowledge_link_opened', {
          metadata: { link_id: linkId, actor_role: currentMode, page_context: context }
        });
      }
    }

"""

srr_marker = '    function openRowReviewDrawer(arg1, arg2) {'
idx = content.find(srr_marker)
if idx < 0:
    print("ERROR: Could not find openRowReviewDrawer marker")
    sys.exit(1)
content = content[:idx] + GUIDANCE_JS + content[idx:]
print(f"[5/7] Section guidance + knowledge rail JS inserted")

# ============================================================
# 6. WIRE GUIDANCE + KNOWLEDGE RAIL INTO openRowReviewDrawer
# We need to find where SRR drawer content is rendered and add
# calls to render guidance card and knowledge rail.
# Look for where the drawer HTML is assembled or where the
# SRR side panel is built.
# ============================================================
# Find the function and insert near the end where drawer is shown
# We'll look for a distinctive pattern near the end of openRowReviewDrawer
# where the drawer is opened/displayed

# Strategy: find 'drawer-content' or 'srr-' containers used in the function
# and add the guidance rendering after the drawer is shown.
# Let's add a hook at the end by finding where SRR state is set up:

# Find a good insertion point - look for where the function sets srrState
# and renders fields. We want to add our rendering AFTER the drawer is populated.
# Let's look for the pattern where SRR content is finalized.

# We'll use a different approach: add a wrapper function that's called
# after openRowReviewDrawer finishes its work.
# Find the closing of the main SRR render section.

# Actually, the safest approach is to hook into the end of the function
# by finding a unique pattern near the end. Let's search for hash update:

srr_hash_marker = "window.location.hash = '#/row/' + rowId;"
idx = content.find(srr_hash_marker)
if idx >= 0:
    # Insert guidance rendering after the hash update line
    insert_after = idx + len(srr_hash_marker)
    guidance_wire = """

      // V2.3b: Render section guidance card and knowledge rail
      setTimeout(function() {
        Promise.all([loadSectionGuidanceConfig(), loadKnowledgeLinksConfig()]).then(function() {
          if (record) {
            var srrBody = document.getElementById('srr-body') || document.getElementById('srr-content') || document.querySelector('.srr-content');
            if (srrBody) renderSectionGuidanceCard(record, srrBody);
            var srrSidePanel = document.getElementById('srr-side-panel') || document.getElementById('srr-sidebar') || document.querySelector('.srr-sidebar');
            if (srrSidePanel) renderKnowledgeRail(srrSidePanel);
            else if (srrBody) renderKnowledgeRail(srrBody);
          }
        });
      }, 100);
"""
    content = content[:insert_after] + guidance_wire + content[insert_after:]
    print(f"[6/7] Guidance + knowledge rail wired into openRowReviewDrawer (after hash update)")
else:
    # Fallback: find the function and add at the end before closing brace
    print("[6/7] WARNING: Could not find SRR hash update pattern - skipping guidance wire")
    print("       Will need manual wiring into openRowReviewDrawer")

# ============================================================
# 7. LOAD CONFIGS ON INIT
# ============================================================
# Find app init / DOMContentLoaded or loadRulesBundle call to load configs
init_marker = 'async function loadRulesBundle() {'
idx = content.find(init_marker)
if idx >= 0:
    # Find end of loadRulesBundle function's try block or after rulesBundleCache.loaded = true
    loaded_marker = 'rulesBundleCache.loaded = true;'
    loaded_idx = content.find(loaded_marker, idx)
    if loaded_idx >= 0:
        insert_after = loaded_idx + len(loaded_marker)
        config_load = """

        // V2.3b: Pre-load section guidance and knowledge link configs
        try { loadSectionGuidanceConfig(); loadKnowledgeLinksConfig(); } catch(e) { console.warn('[V2.3b] Config load error:', e); }
"""
        content = content[:insert_after] + config_load + content[insert_after:]
        print(f"[7/7] Config loading wired into loadRulesBundle")
    else:
        print("[7/7] WARNING: Could not find rulesBundleCache.loaded marker")
else:
    print("[7/7] WARNING: Could not find loadRulesBundle marker")

# Write the modified file
with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

new_len = len(content)
added = new_len - original_len
print(f"\nDone! File grew by {added} characters ({content.count(chr(10))} total lines)")
