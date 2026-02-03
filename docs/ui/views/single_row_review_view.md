# Single Row Review View — Authoritative, Per-Record Inspection

Contract: This document defines the record-level inspection surface. It supports Evidence Pack authoring and Patch Draft creation by Analysts while remaining read-only for Verifier/Admin with respect to gates and Review State transitions.

> **UI Label vs Canonical Name**
> - **UI Label (user-facing):** Record Inspection
> - **Canonical Name (specs/audit/routes):** Single Row Review
>
> The user-facing label "Record Inspection" appears in the UI header and navigation. All internal tokens, routes, specs, and audit logs retain the canonical name `single_row_review`.

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

## Layout (Three-Panel)

### Top Bar
- Back to Grid button
- Record identity (contract_key or record_id)
- Review State badge (read-only display)
- Open Audit Log button (read-only link)

### Left Panel: Field Inspector (v1.4.18)

**Layout:**
- Search input (filters by field name or value)
- Filter chips: All, Changed, Unchanged
- Field Cards (not simple list items)

**Field Card Structure:**
- Header: Label (human-friendly) + API name (monospace), status chips
- Body: Editable value display (click to edit)
- Lock-on-commit: Changed fields lock with Changed marker and 🔒 icon

**Status Chips:**
- Changed (green): Field value has been committed
- Locked (🔒): Field is locked after commit (use Patch Editor to modify)
- Required (purple): Schema-defined required field

**Field Ordering Rule (canonical):**
- Primary: Schema order (deterministic, from `SRR_SCHEMA_ORDER`)
- Fallback: Alphabetical for unknown fields not in schema

**Inline Editing Behavior:**
- Click value display to enter edit mode
- On blur/Enter: Commit edit, lock field, auto-create Proposed Change
- Locked fields cannot be edited inline (use Patch Editor)

**Filters:**
- All: Show all fields
- Changed: Show only locked/committed fields
- Unchanged: Show fields not yet modified

### Center Panel: Document Viewer (v1.4.17)
- **PDF Rendering**: Displays PDFs via browser's native PDF viewer (iframe-based)
- **PDF Proxy**: Network PDFs are fetched via proxy to avoid CORS issues
  - Primary: Supabase Edge Function
  - Fallback: FastAPI on port 8000
- **Offline Cache**: Successfully fetched PDFs are cached in IndexedDB

### Right Panel: Patch Editor + Evidence Pack (v1.4.19)

**Patch Type Selector:**
Three chips at top of panel:
- **Correction** (blue) — Default, for field value fixes
- **Blacklist Flag** (red) — Flag values for blacklist
- **RFI** (purple) — Request for information/clarification

**Changed Fields Section:**
- Shows count of committed changes
- Per-field blocks with:
  - Field label + remove button
  - Old value (locked, subdued, strikethrough)
  - New value (editable input, prominent green border)
- Editing new value syncs to Field Inspector display

**Override Toggle (Correction only):**
- Appears when Observation = "Override Needed" OR Expected = "Allow Override"
- When enabled: Repro block hidden, Override badge shown in header
- Purpose: Skip repro requirement for documented exceptions

**Blacklist Subject (Blacklist Flag only):**
- Read-only display derived from selected field/value

**RFI Target (RFI only):**
- Optional text input for routing (e.g., Team Lead, Legal, Data Steward)

## Evidence Pack (v1.4.19)

Simplified structure with dropdowns only (no free-text observation/expected notes):

### Observation (WHEN) — Correction only
Dropdown options:
- Incorrect Value
- Missing Value
- Formatting Issue
- Duplicate Entry
- Inconsistent Data
- Override Needed

### Expected (THEN) — Correction only
Dropdown options:
- Use Correct Value
- Populate Empty Field
- Standardize Format
- Remove Duplicate
- Align with Source Document
- Allow Override

### Justification (BECAUSE) — All patch types
Single narrative textarea explaining the change/flag/question.

### Repro Method — Correction only (when not Override)
Dropdown options:
- Breaks Salesforce Rule
- Breaks QA Gate
- Resolver Mismatch
- Doc Evidence Mismatch (requires file attachment)

## Patch Type Behavior

| Type | Required Fields | Optional |
|------|-----------------|----------|
| Correction | Observation + Expected + Justification + Repro (unless Override) + Field changes | Override |
| Blacklist Flag | Justification (min 10 chars) | Field changes |
| RFI | Justification (min 10 chars) | RFI Target, Field changes |

## Validation Rules

### Correction
- Observation type: Required
- Expected type: Required
- At least one field change: Required
- Repro method: Required (unless Override enabled)
- File attachment: Required if Repro = "Doc Evidence Mismatch"

### Blacklist Flag / RFI
- Justification: Required (minimum 10 characters)
- Field changes: Optional

## Audit Integration
- Opening this view emits a VIEWED event (context: "record").
- All Evidence Pack authoring emits the appropriate PATCH_* events.
- No STATE_MARKED events originate from this view.

## Unsaved Changes Guard

If the user attempts to navigate away with edited fields that have incomplete patch data, a modal appears:

| Button | Action |
|--------|--------|
| Cancel | Close modal, stay on Single Row Review |
| Discard Changes | Clear all edits and Proposed Changes, navigate to Grid |
| Save Patch Draft | Save current patch draft, then navigate to Grid |

## Navigation
- From All Data Grid → Single Row Review (this view).
- From this view:
  - Open Audit Log detail (read-only overlay or linked panel).
  - Navigate to governed gating views via explicit links.
  - Back to Grid (guarded if unsaved changes exist).

## Read-Only & Gate Separation
- No approve, promote, or finalize actions are available in this view.
- Review State transitions are owned exclusively by governed gate views.

## Acceptance Tests (v1.4.19)

| ID | Test | Expected |
|----|------|----------|
| SRR-PT-01 | Old/New values visually distinct | Old: subdued, strikethrough; New: prominent green border |
| SRR-PT-02 | Observation/Expected are dropdowns only | No textarea for observation/expected notes |
| SRR-PT-03 | Patch Type changes visible form sections | Blacklist/RFI hide Observation/Expected/Repro |
| SRR-PT-04 | Repro controls appear only when required | Hidden for Blacklist/RFI or when Override enabled |
| SRR-PT-05 | Override badge appears and suppresses repro | Badge visible in header, repro block hidden |

## References

- [Field Inspector Patch Flow](single_row_review_field_inspector_patch_flow.md)
- [Human-Agent-Workflow-V1.json](../../specs/Human-Agent-Workflow-V1.json) — single_row_review node
- [Gate View Mapping](../gate_view_mapping.md)
