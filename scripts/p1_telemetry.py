#!/usr/bin/env python3
"""P1 Triage Analytics: Telemetry + Stage Observability injection script.

Adds:
1) Live telemetry cache with processing_state
2) Lifecycle progression with deltas, percentages, throughput
3) Lane drill-down hardening with clear-filter
4) Contract state chips (derived)
5) Processing status banner
6) Event→stage mapping table with dedupe
7) Performance guardrails (debounce, partial rerender)
8) [TRIAGE-ANALYTICS][P1] logging
"""

import re, sys, os

HTML_FILE = 'ui/viewer/index.html'

with open(HTML_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

original_len = len(content)

# ============================================================
# PART A: Insert Processing Status Banner HTML (before Batch Summary)
# ============================================================
PROCESSING_BANNER_HTML = '''            <!-- P1: Processing Status Banner -->
            <div id="ta-processing-banner" style="display: none; padding: 8px 16px; background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 8px; margin-bottom: 12px; font-size: 0.82em; display: none;">
              <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                <span id="ta-proc-icon" style="font-size: 1.1em;">&#9679;</span>
                <span id="ta-proc-text" style="font-weight: 600; color: #333;">Up to date</span>
                <span id="ta-proc-detail" style="color: #666;"></span>
                <span id="ta-proc-stage" style="color: #888; font-size: 0.9em;"></span>
                <span id="ta-proc-time" style="color: #999; font-size: 0.85em; margin-left: auto;"></span>
                <span id="ta-proc-throughput" style="display: none; color: #1565c0; font-size: 0.85em; font-weight: 600;"></span>
                <span id="ta-proc-stale" style="display: none; padding: 2px 8px; border-radius: 6px; background: #fff3e0; color: #e65100; font-size: 0.8em; font-weight: 600;">&#9888; Stale</span>
              </div>
            </div>'''

# Insert before the Batch Summary div
batch_summary_marker = '            <!-- 1) Batch Summary -->'
if batch_summary_marker in content:
    content = content.replace(batch_summary_marker, PROCESSING_BANNER_HTML + '\n' + batch_summary_marker)
    print('[P1] Processing banner HTML injected')
else:
    print('[P1] WARNING: Batch Summary marker not found')

# ============================================================
# PART B: Add lane clear-filter button to each lane card HTML
# ============================================================
# Add a small clear button inside each lane card header area
for lane_name, lane_id in [('preflight', 'preflight'), ('semantic', 'semantic'), ('patch', 'patch')]:
    lane_total_marker = f"id=\"ta-{lane_id}-total\""
    if lane_total_marker not in content:
        lane_total_marker = f"id=\"ta-{'patch' if lane_name == 'patch' else lane_name}-total\""

# Actually we'll add the clear filter as part of the JS logic (simpler than modifying inline HTML)

# ============================================================
# PART C: Inject P1 JavaScript module
# ============================================================

P1_JS = r'''
    // ============================================================
    // P1: Triage Analytics — Telemetry + Stage Observability
    // ============================================================

    var TriageTelemetry = {
      _state: null,
      _prevSnapshot: null,
      _startedAt: null,
      _staleTimeoutMs: 60000,
      _staleTimer: null,
      _debounceTimer: null,
      _debounceMs: 300,
      _eventDedupeSet: {},
      _activeLaneFilter: null,

      // P1-6: Event → Stage mapping table (single source of truth)
      EVENT_STAGE_MAP: {
        'dataset_loaded':            { stage: 'loaded',                 delta: +1 },
        'file_parsed':               { stage: 'loaded',                 delta: +1 },
        'preflight_complete':        { stage: 'preflight_complete',     delta: +1 },
        'preflight_blocker_detected':{ stage: 'loaded',                 delta: 0  },
        'system_pass_complete':      { stage: 'system_pass_complete',   delta: +1 },
        'proposal_accepted':         { stage: 'system_changes_reviewed',delta: +1 },
        'proposal_rejected':         { stage: 'system_changes_reviewed',delta: +1 },
        'system_change_routed_to_patch':{ stage: 'patch_submitted',     delta: +1 },
        'patch_submitted':           { stage: 'patch_submitted',        delta: +1 },
        'rfi_submitted':             { stage: 'rfi_submitted',          delta: +1 },
        'VERIFIER_APPROVED':         { stage: 'verifier_complete',      delta: +1 },
        'VERIFIER_REJECTED':         { stage: 'verifier_complete',      delta: +1 },
        'ADMIN_APPROVED':            { stage: 'admin_promoted',         delta: +1 },
        'patch_applied':             { stage: 'applied',                delta: +1 },
        'rollback_applied':          { stage: 'loaded',                 delta: 0  },
        'schema_change':             { stage: null,                     delta: 0  }
      },

      init: function() {
        this._state = this._createEmptyState();
        this._startedAt = Date.now();
        this._eventDedupeSet = {};
        console.log('[TRIAGE-ANALYTICS][P1] telemetry_init');
      },

      _createEmptyState: function() {
        return {
          files_total: 0,
          files_processed: 0,
          processing_state: 'idle',
          lane_counts: { preflight: 0, semantic: 0, patch_review: 0 },
          lifecycle_stage_counts: {},
          lifecycle_stage_pcts: {},
          lifecycle_stage_deltas: {},
          last_updated_at: null,
          throughput: null
        };
      },

      // P1-6: Dedupe key generation
      _dedupeKey: function(eventType, payload) {
        if (payload && payload.event_id) return payload.event_id;
        var parts = [eventType];
        if (payload) {
          if (payload.record_id) parts.push(payload.record_id);
          if (payload.contract_id) parts.push(payload.contract_id);
          if (payload.field_key) parts.push(payload.field_key);
          if (payload.artifact_id) parts.push(payload.artifact_id);
        }
        return parts.join('::');
      },

      // P1-6: Process event through mapping table with dedupe
      processEvent: function(eventType, payload) {
        var key = this._dedupeKey(eventType, payload);
        if (this._eventDedupeSet[key]) {
          console.log('[TRIAGE-ANALYTICS][P1] event_dedupe_hit: ' + eventType + ' key=' + key);
          return false;
        }
        this._eventDedupeSet[key] = true;

        var mapping = this.EVENT_STAGE_MAP[eventType];
        if (mapping) {
          console.log('[TRIAGE-ANALYTICS][P1] event_stage_mapped: ' + eventType + ' -> stage=' + (mapping.stage || 'none') + ', delta=' + mapping.delta);
        }
        return true;
      },

      // P1-1: Recompute telemetry from existing stores
      recompute: function() {
        if (!TriageAnalytics._cache) return;
        var cache = TriageAnalytics._cache;
        var prevSnapshot = this._prevSnapshot ? JSON.parse(JSON.stringify(this._prevSnapshot)) : null;

        var state = this._createEmptyState();

        // Files total/processed from workbook
        if (typeof workbook !== 'undefined' && workbook.order) {
          state.files_total = workbook.order.length;
          state.files_processed = workbook.order.length;
        }

        // Lane counts from cache
        state.lane_counts.preflight = cache.lanes.preflight.total;
        state.lane_counts.semantic = cache.lanes.semantic.total;
        state.lane_counts.patch_review = cache.lanes.patch_review.total;

        // Lifecycle stage counts from cache
        var stageKeys = ['loaded','preflight_complete','system_pass_complete','system_changes_reviewed','patch_submitted','rfi_submitted','verifier_complete','admin_promoted','applied'];
        var totalContracts = cache.total_contracts || 0;
        stageKeys.forEach(function(sk) {
          var count = cache.lifecycle[sk] ? cache.lifecycle[sk].count : 0;
          state.lifecycle_stage_counts[sk] = count;
          state.lifecycle_stage_pcts[sk] = totalContracts > 0 ? Math.round((count / totalContracts) * 100) : 0;

          // P1-2: Delta since prior refresh
          var prevCount = (prevSnapshot && prevSnapshot.lifecycle_stage_counts[sk]) || 0;
          state.lifecycle_stage_deltas[sk] = count - prevCount;
        });

        // P1-5: Processing state determination
        if (state.files_total === 0) {
          state.processing_state = 'idle';
        } else if (state.files_processed < state.files_total) {
          state.processing_state = 'running';
        } else {
          state.processing_state = 'complete';
        }

        // P1-2: Throughput calculation when running
        if (state.processing_state === 'running' && this._startedAt) {
          var elapsedMin = (Date.now() - this._startedAt) / 60000;
          if (elapsedMin > 0) {
            state.throughput = Math.round(state.files_processed / elapsedMin * 10) / 10;
          }
        }

        state.last_updated_at = new Date().toISOString();
        this._prevSnapshot = JSON.parse(JSON.stringify(state));
        this._state = state;

        // P1-5: Stale detection
        this._resetStaleTimer();

        console.log('[TRIAGE-ANALYTICS][P1] telemetry_recompute: state=' + state.processing_state + ', files=' + state.files_processed + '/' + state.files_total + ', lanes=[pf:' + state.lane_counts.preflight + ',sem:' + state.lane_counts.semantic + ',pr:' + state.lane_counts.patch_review + ']');

        if (state.processing_state !== (prevSnapshot ? prevSnapshot.processing_state : 'idle')) {
          console.log('[TRIAGE-ANALYTICS][P1] processing_state_changed: ' + (prevSnapshot ? prevSnapshot.processing_state : 'idle') + ' -> ' + state.processing_state);
        }

        return state;
      },

      // P1-5: Stale timer management
      _resetStaleTimer: function() {
        var self = this;
        if (this._staleTimer) clearTimeout(this._staleTimer);
        if (this._state && this._state.processing_state !== 'idle') {
          this._staleTimer = setTimeout(function() {
            if (self._state) {
              self._state.processing_state = 'stale';
              console.log('[TRIAGE-ANALYTICS][P1] stale_state_entered: no update for ' + (self._staleTimeoutMs / 1000) + 's');
              self.renderBanner();
            }
          }, this._staleTimeoutMs);
        }
      },

      clearStale: function() {
        if (this._state && this._state.processing_state === 'stale') {
          this._state.processing_state = 'complete';
          console.log('[TRIAGE-ANALYTICS][P1] stale_state_cleared');
          this.renderBanner();
        }
      },

      // P1-7: Debounced UI refresh
      debouncedRefresh: function() {
        var self = this;
        if (this._debounceTimer) clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(function() {
          self.recompute();
          self.renderBanner();
          self.renderLifecycleDeltas();
          self.renderContractChips();
          console.log('[TRIAGE-ANALYTICS][P1] lifecycle_refresh: debounced');
        }, this._debounceMs);
      },

      // P1-5: Render processing status banner
      renderBanner: function() {
        var banner = document.getElementById('ta-processing-banner');
        if (!banner || !this._state) return;
        banner.style.display = '';

        var s = this._state;
        var icon = document.getElementById('ta-proc-icon');
        var text = document.getElementById('ta-proc-text');
        var detail = document.getElementById('ta-proc-detail');
        var stageEl = document.getElementById('ta-proc-stage');
        var timeEl = document.getElementById('ta-proc-time');
        var throughputEl = document.getElementById('ta-proc-throughput');
        var staleEl = document.getElementById('ta-proc-stale');

        // State-based styling
        var configs = {
          idle:     { color: '#9e9e9e', bg: '#f5f5f5', border: '#e0e0e0', label: 'No data loaded', icon: '&#9679;' },
          running:  { color: '#1976d2', bg: '#e3f2fd', border: '#bbdefb', label: 'Processing', icon: '&#9881;' },
          stale:    { color: '#e65100', bg: '#fff3e0', border: '#ffe0b2', label: 'Stale', icon: '&#9888;' },
          complete: { color: '#2e7d32', bg: '#e8f5e9', border: '#c8e6c9', label: 'Up to date', icon: '&#10003;' }
        };
        var cfg = configs[s.processing_state] || configs.idle;

        banner.style.background = cfg.bg;
        banner.style.borderColor = cfg.border;
        if (icon) { icon.innerHTML = cfg.icon; icon.style.color = cfg.color; }
        if (text) { text.textContent = cfg.label; text.style.color = cfg.color; }

        if (detail) {
          if (s.processing_state === 'running') {
            detail.textContent = s.files_processed + '/' + s.files_total + ' files';
          } else if (s.processing_state === 'complete') {
            detail.textContent = s.files_total + ' files processed';
          } else {
            detail.textContent = '';
          }
        }

        // Dominant stage
        if (stageEl) {
          var SL = { loaded: 'Loaded', preflight_complete: 'Pre-Flight', system_pass_complete: 'System Pass', system_changes_reviewed: 'Reviewed', patch_submitted: 'Patch', rfi_submitted: 'RFI', verifier_complete: 'Verifier', admin_promoted: 'Promoted', applied: 'Applied' };
          var dominant = this._getDominantStage();
          stageEl.textContent = dominant ? ('Stage: ' + (SL[dominant] || dominant)) : '';
        }

        if (timeEl && s.last_updated_at) {
          timeEl.textContent = 'Updated: ' + new Date(s.last_updated_at).toLocaleTimeString();
        }

        // Throughput
        if (throughputEl) {
          if (s.throughput && s.processing_state === 'running') {
            throughputEl.style.display = '';
            throughputEl.textContent = s.throughput + ' items/min';
          } else {
            throughputEl.style.display = 'none';
          }
        }

        // Stale indicator
        if (staleEl) {
          staleEl.style.display = s.processing_state === 'stale' ? '' : 'none';
        }
      },

      _getDominantStage: function() {
        if (!this._state || !this._state.lifecycle_stage_counts) return null;
        var max = 0, dominant = null;
        var counts = this._state.lifecycle_stage_counts;
        Object.keys(counts).forEach(function(k) {
          if (counts[k] > max) { max = counts[k]; dominant = k; }
        });
        return dominant;
      },

      // P1-2: Render lifecycle deltas and percentages on existing stage elements
      renderLifecycleDeltas: function() {
        if (!this._state) return;
        var stageKeys = ['loaded','preflight_complete','system_pass_complete','system_changes_reviewed','patch_submitted','rfi_submitted','verifier_complete','admin_promoted','applied'];
        var stageEls = document.querySelectorAll('.ta-lifecycle-stage');

        stageKeys.forEach(function(sk, idx) {
          if (!stageEls[idx]) return;
          var delta = this._state.lifecycle_stage_deltas[sk] || 0;
          var pct = this._state.lifecycle_stage_pcts[sk] || 0;

          // Find or create delta badge
          var deltaEl = stageEls[idx].querySelector('.ta-stage-delta');
          if (!deltaEl) {
            deltaEl = document.createElement('div');
            deltaEl.className = 'ta-stage-delta';
            deltaEl.style.cssText = 'font-size:0.65em;margin-top:2px;font-weight:600;';
            stageEls[idx].appendChild(deltaEl);
          }

          if (delta > 0) {
            deltaEl.textContent = '+' + delta;
            deltaEl.style.color = '#2e7d32';
            deltaEl.style.display = '';
          } else if (delta < 0) {
            deltaEl.textContent = '' + delta;
            deltaEl.style.color = '#c62828';
            deltaEl.style.display = '';
          } else {
            deltaEl.style.display = 'none';
          }

          // Find or create pct badge
          var pctEl = stageEls[idx].querySelector('.ta-stage-pct');
          if (!pctEl) {
            pctEl = document.createElement('div');
            pctEl.className = 'ta-stage-pct';
            pctEl.style.cssText = 'font-size:0.6em;color:#999;margin-top:1px;';
            stageEls[idx].appendChild(pctEl);
          }
          pctEl.textContent = pct + '%';
        }.bind(this));
      },

      // P1-4: Derive and render contract state chips
      renderContractChips: function() {
        var chipsEl = document.getElementById('ta-contract-summary-chips');
        if (!chipsEl || !TriageAnalytics._cache) return;

        var cache = TriageAnalytics._cache;
        var chips = {
          preflight_blocked: 0,
          semantic_pending: 0,
          patch_pending: 0,
          ready_for_verifier: 0,
          promoted: 0
        };

        (cache.contracts || []).forEach(function(c) {
          if (c.preflight_alerts > 0) chips.preflight_blocked++;
          if (c.semantic_alerts > 0) chips.semantic_pending++;
          if (c.patch_alerts > 0) chips.patch_pending++;
          if (c.current_stage === 'verifier_complete' || c.current_stage === 'system_changes_reviewed') chips.ready_for_verifier++;
          if (c.current_stage === 'admin_promoted' || c.current_stage === 'applied') chips.promoted++;
        });

        var chipDefs = [
          { key: 'preflight_blocked', label: 'PF Blocked', color: '#c62828', bg: '#ffebee' },
          { key: 'semantic_pending',  label: 'Sem. Pending', color: '#e65100', bg: '#fff3e0' },
          { key: 'patch_pending',     label: 'Patch Pending', color: '#1565c0', bg: '#e3f2fd' },
          { key: 'ready_for_verifier',label: 'Ready for Verifier', color: '#7b1fa2', bg: '#f3e5f5' },
          { key: 'promoted',          label: 'Promoted', color: '#2e7d32', bg: '#e8f5e9' }
        ];

        var html = '';
        chipDefs.forEach(function(cd) {
          if (chips[cd.key] > 0) {
            html += '<span style="padding:2px 8px;border-radius:10px;background:' + cd.bg + ';color:' + cd.color + ';font-weight:600;cursor:pointer;" onclick="TriageTelemetry.filterByChip(\'' + cd.key + '\')" title="' + cd.label + ': ' + chips[cd.key] + '">' + chips[cd.key] + ' ' + cd.label + '</span>';
          }
        });
        chipsEl.innerHTML = html;
      },

      // P1-3: Lane drill-down with deterministic filter + clear
      applyLaneFilter: function(lane) {
        if (this._activeLaneFilter === lane) {
          this.clearLaneFilter();
          return;
        }
        this._activeLaneFilter = lane;
        console.log('[TRIAGE-ANALYTICS][P1] lane_filter_applied: ' + lane);

        // Filter contract summary by lane-relevant alerts
        if (TriageAnalytics._cache && TriageAnalytics._cache.contracts) {
          var filtered = TriageAnalytics._cache.contracts.filter(function(c) {
            if (lane === 'preflight') return c.preflight_alerts > 0;
            if (lane === 'semantic') return c.semantic_alerts > 0;
            if (lane === 'patch') return c.patch_alerts > 0;
            return true;
          });
          TriageAnalytics._renderContractTable(
            Object.assign({}, TriageAnalytics._cache, { contracts: filtered }),
            null
          );
          // Expand the contract table
          var body = document.getElementById('ta-contract-body');
          var toggle = document.getElementById('ta-contract-toggle');
          if (body) body.style.display = '';
          if (toggle) toggle.style.transform = 'rotate(90deg)';
        }

        // Show clear-filter action
        this._showClearFilterButton(lane);
      },

      clearLaneFilter: function() {
        this._activeLaneFilter = null;
        console.log('[TRIAGE-ANALYTICS][P1] lane_filter_cleared');
        if (TriageAnalytics._cache) {
          TriageAnalytics._renderContractTable(TriageAnalytics._cache, null);
        }
        this._hideClearFilterButton();
      },

      _showClearFilterButton: function(lane) {
        var badge = document.getElementById('ta-contract-filter-badge');
        if (badge) {
          var labels = { preflight: 'Pre-Flight', semantic: 'Semantic', patch: 'Patch Review' };
          badge.textContent = (labels[lane] || lane) + ' \u2715';
          badge.style.display = 'inline';
          badge.style.cursor = 'pointer';
          badge.onclick = function() { TriageTelemetry.clearLaneFilter(); };
        }
      },

      _hideClearFilterButton: function() {
        var badge = document.getElementById('ta-contract-filter-badge');
        if (badge) {
          badge.textContent = '';
          badge.style.display = 'none';
          badge.onclick = null;
        }
      },

      // P1-4: Filter by contract chip
      filterByChip: function(chipKey) {
        if (!TriageAnalytics._cache) return;
        var filtered = TriageAnalytics._cache.contracts.filter(function(c) {
          if (chipKey === 'preflight_blocked') return c.preflight_alerts > 0;
          if (chipKey === 'semantic_pending') return c.semantic_alerts > 0;
          if (chipKey === 'patch_pending') return c.patch_alerts > 0;
          if (chipKey === 'ready_for_verifier') return c.current_stage === 'verifier_complete' || c.current_stage === 'system_changes_reviewed';
          if (chipKey === 'promoted') return c.current_stage === 'admin_promoted' || c.current_stage === 'applied';
          return true;
        });
        TriageAnalytics._renderContractTable(
          Object.assign({}, TriageAnalytics._cache, { contracts: filtered }),
          null
        );
        var body = document.getElementById('ta-contract-body');
        var toggle = document.getElementById('ta-contract-toggle');
        if (body) body.style.display = '';
        if (toggle) toggle.style.transform = 'rotate(90deg)';
        this._showClearFilterButton(chipKey);
      },

      getState: function() { return this._state; }
    };
    // Initialize telemetry
    TriageTelemetry.init();
'''

# Find the end of the TriageAnalytics object (before analystTriageState)
triage_analytics_end = 'var analystTriageState = {'
if triage_analytics_end in content:
    content = content.replace(triage_analytics_end, P1_JS + '\n    ' + triage_analytics_end)
    print('[P1] Telemetry JS module injected')
else:
    print('[P1] ERROR: analystTriageState marker not found')
    sys.exit(1)

# ============================================================
# PART D: Wire P1 into existing TriageAnalytics.renderHeader
# ============================================================

# Add P1 telemetry recompute and render calls at end of renderHeader
old_render_header_end = "console.log('[TRIAGE-ANALYTICS][P0.1] renderHeader: displayed=' + (header.style.display !== 'none') + ', lifecycle_stages=9, contracts=' + cache.total_contracts);"

p1_render_wire = old_render_header_end + """

        // P1: Telemetry recompute and banner render
        if (typeof TriageTelemetry !== 'undefined') {
          try {
            TriageTelemetry.recompute();
            TriageTelemetry.renderBanner();
            TriageTelemetry.renderLifecycleDeltas();
            TriageTelemetry.renderContractChips();
          } catch(e) { console.warn('[P1] Telemetry render error:', e); }
        }"""

if old_render_header_end in content:
    content = content.replace(old_render_header_end, p1_render_wire, 1)
    print('[P1] Telemetry wired into renderHeader')
else:
    print('[P1] WARNING: renderHeader log line not found for wiring')

# ============================================================
# PART E: Wire lane clicks to P1 drill-down
# ============================================================

# Enhance handleLaneClick to also apply P1 lane filter
old_handle_lane = "handleLaneClick: function(lane) {"
new_handle_lane = """handleLaneClick: function(lane) {
        // P1: Apply lane drill-down filter
        if (typeof TriageTelemetry !== 'undefined') {
          TriageTelemetry.applyLaneFilter(lane);
        }"""

if old_handle_lane in content:
    content = content.replace(old_handle_lane, new_handle_lane, 1)
    print('[P1] Lane click wired to P1 drill-down')
else:
    print('[P1] WARNING: handleLaneClick not found')

# ============================================================
# PART F: Wire P1 into data load paths for recompute triggers
# ============================================================

# After ContractIndex.build() calls, add telemetry recompute
# Find the workbook parse completion point
old_ci_build_log = "console.log('[ContractIndex] Built in '"
new_ci_build_log = """console.log('[ContractIndex] Built in '"""

# Wire into renderAnalystTriage - add debounced refresh after initial render
old_render_triage_end = "renderTriageQueueTable(analystTriageState.systemItems, 'system-queue-list', 'No system changes');"
new_render_triage_end = """renderTriageQueueTable(analystTriageState.systemItems, 'system-queue-list', 'No system changes');
      // P1: Debounced telemetry refresh
      if (typeof TriageTelemetry !== 'undefined') {
        TriageTelemetry.debouncedRefresh();
      }"""

if old_render_triage_end in content:
    content = content.replace(old_render_triage_end, new_render_triage_end, 1)
    print('[P1] Debounced refresh wired into renderAnalystTriage')
else:
    print('[P1] WARNING: renderAnalystTriage end marker not found')

# ============================================================
# PART G: Fix the duplicate closing brace issue in handleSchemaClick
# ============================================================
# There's a syntax issue: handleSchemaClick has an extra }, before handleContractClick
bad_schema = """        navigateToGridFiltered(targetFilter);
      },
      },

      handleContractClick:"""

good_schema = """        navigateToGridFiltered(targetFilter);
      },

      handleContractClick:"""

if bad_schema in content:
    content = content.replace(bad_schema, good_schema, 1)
    print('[P1] Fixed duplicate closing brace in handleSchemaClick')
else:
    print('[P1] NOTE: Duplicate brace not found (may already be fixed)')

# ============================================================
# Write output
# ============================================================
with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

new_len = len(content)
print(f'[P1] Done. File size: {original_len} -> {new_len} chars (+{new_len - original_len})')
