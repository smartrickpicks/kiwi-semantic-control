# UI Principles (V1)

> Human authority governs all semantic decisions. The UI exists to surface evidence, enable decisions, and record audit trails.

## Core Principles

### 1. Evidence-First Display
- Every view must show the artifacts required to make a decision
- No action button appears without visible supporting evidence
- Missing evidence forces a hold or flag state

### 2. Role-Gated Actions
- Actions are hidden (not just disabled) when the user lacks permission
- Role escalation is explicit and logged
- Degraded views show read-only content with clear "no permission" messaging

### 3. State-Driven Navigation
- Navigation reflects data state (empty → load, loaded → triage/grid)
- Gates block forward progression until conditions are met
- Backward navigation preserves context (no data loss)

### 4. Audit by Design
- Every decision-bearing action writes to the audit log
- Timestamps use ISO 8601 format
- Actor identity is captured with role at time of action

### 5. Offline-First Rendering
- All views render from local state (no network fetch for display)
- Evidence artifacts are snapshots, not live queries
- Determinism: same state produces identical UI

## Review State Transition Matrix

This matrix defines the allowed state transitions for patch requests. Only the specified roles may initiate each transition.

| From State | To State | Initiating Role | Trigger Action |
|------------|----------|-----------------|----------------|
| Draft | Submitted | Analyst, Verifier, Admin | Submit to Queue |
| Submitted | Under_Review | Verifier, Admin | Begin Review |
| Under_Review | Needs_Clarification | Verifier, Admin | Request Clarification |
| Needs_Clarification | Submitted | Analyst, Verifier, Admin | Respond to Clarification |
| Under_Review | Verifier_Approved | Verifier, Admin | Approve (Verifier) |
| Under_Review | Rejected | Verifier, Admin | Reject |
| Verifier_Approved | Admin_Approved | Admin | Approve (Admin) |
| Verifier_Approved | Admin_Hold | Admin | Hold |
| Admin_Hold | Under_Review | Admin | Release Hold |
| Admin_Approved | Applied | Admin | Promote Patch to Baseline |
| Applied | Promoted | Admin | Export to PR |

## Gate Enforcement

Gates are checkpoints that must be satisfied before proceeding. See [gate_view_mapping.md](gate_view_mapping.md) for gate-to-view ownership.

| Gate | Owning View | Required Evidence |
|------|-------------|-------------------|
| gate_parse | load_data | row_count, column_headers, parse_timestamp |
| gate_preflight | patch_authoring_view | preflight_report, badge_summary (no fail) |
| gate_evidence | patch_authoring_view | 4-block evidence pack complete |
| gate_verifier | verifier_review_view | review_notes, decision_status |
| gate_admin | admin_approval_view | admin_action_log |

## Terminology

- **Verifier**: Primary term for the review role (Stage 9)
- **Admin**: Final approval authority (Stage 10-12)
- **Analyst**: Default operator role (Stages 1-8)
- **Promote Patch to Baseline**: Stakeholder-facing label for the `apply_patch` permission

## Related Documents

- [Flow-Doctrine.md](../V1/Flow-Doctrine.md) — Workflow stages and authority model
- [gate_view_mapping.md](gate_view_mapping.md) — Gate-to-view ownership
- [REVIEW_CHECKLIST.md](../REVIEW_CHECKLIST.md) — Approval checklist items
