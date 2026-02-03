# TASKS_UI (Handoff — UI Backlog)

Audience: Governance reviewers and UI operators
Purpose: Track UI tasks with governance constraints and evidence links
Scope: UI copy and contracts only; no runtime or implementation claims
Non-Goals: No claims of completion without evidence (commit/PR URL)
Authority Level: Informational; defers to canonical docs
Owner Agent: Kiwi (documentation architect)
Update Rules: Each task must include scope, files likely to touch, and acceptance tests; if evidence missing, mark "Unknown — requires audit"

Repository: smartrickpicks/kiwi-semantic-control (branch: main)
Open PRs: unknown/none

## Backlog

### SRR: Field Order & Guard Modal (docs-only)
- Scope: Ensure Field Cards/Groups/Filters/Proposed Change/mini prompt/guard modal copy present in SRR doc
- Files likely to touch: docs/ui/views/single_row_review_view.md
- Acceptance: sections added; no runtime claims; Evidence link: Unknown — requires audit

### Data Source: Rotation/Disconnect copy parity
- Scope: Mirror rotation (Active→Saved) and Disconnect guidance in viewer copy
- Files likely to touch: docs/ui/views/data_source_view.md; ui/viewer/index.html
- Acceptance: copy present and consistent; Evidence link: Unknown — requires audit

### Spec/Mapping Canonicalization
- Scope: Update Human-Agent-Workflow-V1.json ids/labels/edges; gate_view_mapping owner token
- Files likely to touch: docs/specs/Human-Agent-Workflow-V1.json; docs/ui/gate_view_mapping.md
- Acceptance: spec uses data_source/single_row_review/submit_patch_request; gate_parse owner is data_source_panel; Evidence link: Unknown — requires audit

### SRR: Evidence Pack + Patch Editor Refinement (v1.4.19)
- Scope: Refine Evidence Pack to reduce analyst load; make patch semantics deterministic and patch-type driven
- Files likely to touch: ui/viewer/index.html; docs/ui/views/single_row_review_view.md
- Acceptance tests:
  - Old/New values visually distinct (Old locked subdued; New prominent editable)
  - Observation/Expected are dropdown-only (no text areas)
  - Patch Type selector changes visible form sections
  - Repro controls appear only when required
  - Override badge appears and suppresses repro requirement
  - Docs updated to match UI
- Evidence link: Unknown — requires audit

### SRR: Mini-Queue + Auto Patch Type Semantics (v1.4.20 — docs-only)
- Scope: Document Field Inspector as mini-queue with field states and auto Patch Type behavior
- Files likely to touch: docs/ui/views/single_row_review_view.md
- Acceptance tests:
  - SRR doc includes mini-queue field states (TODO, VERIFIED, RFI, PATCHED)
  - SRR doc includes field actions (Verify, Blacklist Flag, RFI, Patch)
  - SRR doc includes auto Patch Type behavior (read-only, action-driven)
  - SRR doc includes Blacklist category dropdown + subject derivation
  - SRR doc includes RFI behavior (Justification = question)
  - SRR doc includes guard modal for unresolved PATCHED/RFI fields
  - No UI code files modified
- Evidence link: Unknown — requires audit

### SRR: Field Inspector Mini-Queue UI Implementation (v1.4.20)
- Scope: Implement Field Inspector mini-queue behavior with field states, actions, filters, and guard modal
- Files likely to touch: ui/viewer/index.html
- Acceptance tests:
  - AT-01: Verify action sets VERIFIED and removes field from TODO list
  - AT-02: Blacklist action sets PATCHED + auto Patch Type = Blacklist Flag, without editing value
  - AT-03: RFI action sets RFI + auto Patch Type = RFI
  - AT-04: Editing a field sets PATCHED + auto Patch Type = Correction
  - AT-05: Filter chips reflect correct counts (TODO/Verified/RFI/Patched/All)
  - AT-06: Guard modal appears when leaving SRR with unresolved PATCHED/RFI fields
  - AT-07: Patch Type is not user-editable (read-only display)
- Evidence link: Unknown — requires audit
