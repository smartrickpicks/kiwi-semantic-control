# Single Row Review View — Authoritative, Per-Record Inspection

Contract: This document defines the record-level inspection surface. It supports Evidence Pack authoring and Patch Draft creation by Analysts while remaining read-only for Verifier/Admin with respect to gates and Review State transitions.

## Purpose
- Provide authoritative, per-record context: baseline values, deltas, flags, evidence, and audit trail.
- Enable Analysts to author Evidence Packs and create Patch Drafts with explicit rationale and evidence anchoring.
- Maintain strict separation of duties: no direct Review State transitions from this view.

## Roles & Permissions
- Analyst:
  - May edit the Evidence Pack panel to create or update Patch Drafts.
  - May save a Patch Draft and submit as Patch Request for verification; this emits PATCH_DRAFTED and/or PATCH_SUBMITTED and REVIEW_REQUESTED audit events.
  - May add or clear flags with rationale (FLAG_ADDED / FLAG_CLEARED).
- Verifier/Admin:
  - Read-only in this view (inspect baseline, deltas, evidence, and audit log).
  - Gate decisions (STATE_MARKED) occur only in their dedicated governed views (verifier_review_view, admin_approval_view).

## Layout (High-Level)
- Left pane: Field inspector
  - Shows fields in a deterministic order (e.g., schema order), each with indicators:
    - System-derived (neutral icon)
    - User-modified (delta icon)
    - Flagged (flag icon with severity)
  - Field row affordances (read-only for Verifier/Admin): expand to see baseline, proposed value, and field audit subset.
- Right pane: Evidence Pack editor panel (Analyst-only interactive)
  - Structured editor with 4 canonical blocks:
    - **Observation** (helper alias: WHEN)
    - **Expected** (helper alias: THEN)
    - **Justification** (helper alias: BECAUSE)
    - **Repro** (no alias)
  - Action buttons: Save Patch Draft (emits PATCH_DRAFTED), Submit Patch Request (emits PATCH_SUBMITTED + REVIEW_REQUESTED). No state transition occurs here.
- Bottom or drawer: Evidence viewer (embedded PDF and anchors)
  - Inline PDF viewer with highlight overlay.
  - Evidence list with anchors; selection syncs to current highlight.

## Field-Level Indicators (Deterministic)
For each field:
- state: system_derived | user_modified | flagged
- delta_count: integer (0 for system_derived)
- evidence_count: integer for anchors referencing this field
- last_event_at: timestamp from audit

## Evidence Pack Authoring Contract

The Evidence Pack uses 4 canonical blocks with optional authoring aliases (helper text only):

| Block | Alias | Purpose |
|-------|-------|---------|
| **Observation** | WHEN | Preconditions or context that define applicability |
| **Expected** | THEN | One or more changes (deltas) with path, before, after |
| **Justification** | BECAUSE | Evidence references and plain-language rationale |
| **Repro** | (none) | Steps to reproduce the issue |

Patch Draft authoring emits deterministic events:
- Save Patch Draft → PATCH_DRAFTED with payload { patch_id, changes[], rationale }.
- Submit Patch Request → PATCH_SUBMITTED with payload { patch_id, submission_notes } and REVIEW_REQUESTED { target: "patch", patch_id, reason }.

## Embedded PDF Viewer & Highlights
- The viewer must be read-only and offline.
- Evidence anchors define the page and bbox to highlight.
- Click-through mapping:
  - Clicking a field with an associated evidence anchor scrolls the viewer to the anchor's page and highlights the bbox.
  - Selecting a highlight focuses the corresponding field in the inspector pane.

## Audit Integration
- Opening this view emits a VIEWED event (context: "record").
- All Evidence Pack authoring emits the appropriate PATCH_* events and EVIDENCE_ATTACHED when anchors are added.
- No STATE_MARKED events originate from this view.

## Flags & Warnings
- Analysts can add or clear flags (FLAG_ADDED / FLAG_CLEARED) with category, severity (info | warning | error | critical), and rationale.
- Block conditions are displayed but cannot be resolved here.

## Navigation
- From All Data Grid → Single Row Review (this view).
- From this view:
  - Open Audit Log detail (read-only overlay or linked panel).
  - Navigate to governed gating views (verifier_review_view, admin_approval_view) via explicit links that do not perform transitions themselves.

## Read-Only & Gate Separation
- No approve, promote, or finalize actions are available in this view.
- Review State transitions are owned exclusively by governed gate views.

## Accessibility & Ergonomics
- Keyboard shortcuts:
  - Up/Down: move between fields
  - Enter: expand/collapse field details
  - Ctrl/Cmd+S: Save Patch Draft
  - Ctrl/Cmd+Enter: Submit Patch Request
- Clear legends for indicators and evidence.
- Deterministic ordering and stable scroll positions to aid verification.
