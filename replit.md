# Orchestrate OS — Semantic Control Board (v1.5.1)

## Overview

This repository is a **governance-only semantic control plane** for DataDash + Kiwi. It defines, validates, and previews semantic rules offline so decisions are explicit, deterministic, and auditable.

**Product Identity:**
- Product name: Orchestrate OS
- Primary surface: Semantic Control Board
- Logo asset: `assets/brand/orchestrate-os-logo.svg` (SVG canonical)
- Logo is informational only (not navigational)

**Core Purpose:**
- Single source of semantic truth: rules, templates, examples, and governance documents
- Offline harness to validate and preview semantics deterministically
- Rule authoring and review as configuration (not code)
- Analyst-first reference with clear interfaces and checklists

**v1.2 Dashboard Shell:**
- Queue-centric sidebar: To Do, Needs Review, Flagged, Blocked, Finalized with live counts
- Right-side drawers: Data Sources Drawer, Record Detail Drawer
- Role-based navigation: Analyst (default), Verifier, Admin
- Session management: Data Sources, Evidence Status, Reset Session
- First-Run Configure Wizard: Multi-step setup for data sources and workflow defaults
- Admin Config Flows: Workflow-ordered view of config artifacts with Plain-English, Payload, Master tabs

**v1.2.1 Phase 2 Features (D1-D4):**
- D1 Masterline Autoload: Dev toggle in Admin, artifact registry with Loaded/Missing status chips, localStorage persistence
- D2 Admin Workflow Map: 8-stage vertical pipeline with clickable nodes (Load Data → PR Ready)
- D3 Standardizer: CSV parsing with delimiter inference, header normalization, merged_dataset.json output, error model
- D4 Tooltips & Plain English: NOMENCLATURE maps, info icons with tooltips, humanLabel()/getTooltip() helpers

**v1.2.2 Patch Queue as Admin Status Pipeline:**
- Comment (RFI) System: 5-status lifecycle (Open → Resolved → ElevatedToPatchRequest), localStorage persistence
- Patch Request Pipeline: 11-status lifecycle with Kiwi handshake (SentToKiwi → KiwiReturned → Applied)
- Admin Patch Console: 7 queue tabs with live counts, batch selection, export/import actions
- Patch Request Detail Drawer: Plain-English Intent, Kiwi Payload viewer, Apply Checklist
- Comment UI: Add Comment modal, Elevate to Patch Request flow, Comments panel in Record Drawer

**v1.2.3 Patch Studio + Role-Gated Review Pipeline:**
- Role-Based Access Control: Analyst, Verifier, Admin with permission gating
- Extended 12-status lifecycle: Needs_Clarification, Reviewer_Responded, Admin_Hold
- Patch Studio as Workbench Tab: Draft, Preflight, Evidence Pack sub-tabs
- Submit to Patch Queue CTA with audit logging
- Preflight Checks with pass/warn/fail badges and Copy Report
- Evidence Pack: 4 structured blocks (Observation, Expected, Justification, Repro)
- Verifier Actions: Request Clarification, Approve, Reject, Review Notes
- Admin Actions: Admin Approve, Admin Hold, Export to Kiwi, Paste Return, Mark Applied
- Revision Tracking: revisions array with diff summaries and snapshots
- Append-only Audit Log with event types

**v1.2.4 Structured Intent + UI Cleanup:**
- Structured Intent Authoring: Target Field selector, Condition Type dropdown, Action Type dropdown
- "Other" escape hatch for edge cases with custom text input
- Live Intent Preview showing rendered WHEN/THEN/BECAUSE
- Updated PatchRequestV1 schema with intent_structured and intent_rendered fields
- Form validation with required fields and character limits
- Removed legacy Patch Studio overlay panel (no more stacked drawers)

**v1.2.5 Loader + Testability:**
- Loader as first-class nav item (top of sidebar, "Start" section)
- Loader page: Load Sample Dataset, Import CSV/XLSX, Attach PDF
- Deterministic sample dataset (examples/datasets/sample_v1.json) with one-click load
- Test Utilities: Reset Demo State, Rebuild Field Index
- Dataset summary card after load with CTA to Spreadsheet View
- CSV import with delimiter inference and header normalization

**v1.3.0 UI-ADMIN-ENTITY-SEPARATION:**
- Hard page separation: navigateTo() properly hides all pages before showing target (no bleed-through)
- RBAC route guards: Non-admin redirected to triage with toast notification
- Admin section markers: data-admin-section="true" for smoke test assertions
- Dev-only assertion: console.error if admin sections found in triage DOM
- Page labels: Explicit route context (PAGE: TRIAGE, PAGE: ADMIN-GOVERNANCE, etc)

**v1.3.1 Pre-Staging Cleanup:**
- Admin Console with tabbed interface: Governance, Config, Inspector, Standardizer, Patch Console, Evidence
- Role downgrade triggers teardownAdminState() for clean state management
- Loader as drawer-only (URL stays #/triage)
- Analyst/Reviewer surfaces have zero admin widgets
- Exclusive route rendering (no append/portal patterns)

**v1.4.0 DataDash V1 Operator Ergonomics:**
- All-Data Grid (#/grid): Primary operator surface with dense spreadsheet view
- Deterministic filtering: Query params (f=, sheet=, q=) with stable sort order
- Triage as Alert Lens: Summary cards navigate to filtered grid views
- Row Review (#/row/:id): Consistent entry point for single-row review
- Default route: #/grid when dataset loaded, #/triage otherwise
- RBAC preserved: Admin UI only under #/admin/*

**v1.4.16 PDF Proxy + Field Resolution:**
- FastAPI PDF proxy server (`server/pdf_proxy.py`) for CORS-safe PDF fetching
- Host allowlist (default: S3 buckets) with SSRF guards (no private IPs)
- `srrResolveFieldValue()` handles Salesforce-style columns (File_URL_c, File_Name_c)
- Proxy returns PDFs with `Content-Disposition: inline` (no download prompt)
- Size limit: 25MB configurable via `PDF_PROXY_MAX_SIZE_MB` env var
- Fallback: Direct iframe if proxy unavailable

**v1.4.18 Field Inspector Patch Flow:**
- Search input filters fields by name or value (case-insensitive)
- Filter chips: All / Changed / Unchanged (replaced old Edited/Needs Patch/RFI)
- Inline field editing: Click to edit, Enter/blur commits
- Lock-on-commit: Changed fields lock with Changed marker and 🔒 icon
- Patch Editor block in right panel: Old/New values with bidirectional sync
- Evidence Pack restructured: Dropdown selectors + optional notes for each block
- Observation/Expected/Justification/Repro dropdowns with standardized options
- Repro file attachment support
- Submit validation: Observation type + Expected type + at least one field change
- Patch Request creation via existing createPatchRequest/submitPatchRequest functions
- Submitted patches visible in Patch Console

**v1.4.19 Patch Editor Refinement:**
- Patch Type selector (Correction/Blacklist Flag/RFI) with conditional form sections
- Old/New value styling: Old subdued with strikethrough, New prominent with green border
- Conditional form sections: Override toggle, Blacklist Subject, RFI Target
- Simplified Evidence Pack: Dropdown-only Observation/Expected (no textarea notes)
- Patch-type-driven validation: Correction requires full Evidence Pack, Blacklist/RFI require only Justification
- Override toggle appears when Observation="Override Needed" OR Expected="Allow Override"
- Repro block hidden for Blacklist/RFI patch types and when Override enabled

**v1.5.0 Verifier Triage + Payload System:**
- Verifier Triage view with 4-queue system (Pending, Clarification, To Admin, Resolved)
- Automatic view swap: Analyst Triage ↔ Verifier Triage based on role
- RFI/Correction/Blacklist submissions generate verifier payloads
- Verifier Review detail with type-specific content blocks (RFI chat, Correction diff, Blacklist subject)
- Clickable triage rows navigate to Verifier Review
- RFI rows show view-only actions (Open Review, Open Record)
- Patch Editor reset after submission to prevent carry-over

**v1.5.1 Artifact Store + Role Handoff Routing:**
- localStorage-backed mock filesystem (fs: prefix) with environment scoping
- Artifact envelope contract: workspace_id, environment, dataset_id, record_id, field_key, artifact_type, status, thread_id
- Deterministic artifact IDs: hash(dataset_id + record_id + field_key + timestamp)
- Event log (events.jsonl): RFI_CREATED, RFI_REPLIED, PATCH_DRAFT_CREATED, PATCH_REQUEST_SUBMITTED, VERIFIER_APPROVED, VERIFIER_REJECTED, VERIFIER_CLARIFICATION_REQUESTED, ADMIN_APPROVED
- Thread system for RFI conversations with message history
- Queue routing via record_id lookup (not row index) for stable navigation
- Playground mode: Environment selector (Playground/Prod), Reset Playground button
- Environment scoping: playground keys isolated, prod locked for now
- Backwards compatibility: Legacy verifierQueueState preserved alongside artifact store
- Verifier Approval → Admin Patch Queue handoff:
  - Verifier Approve on Correction/Blacklist sets status='sent_to_admin' and logs VERIFIER_APPROVED
  - Verifier Request Clarification sets status='needs_clarification' and logs VERIFIER_CLARIFICATION_REQUESTED
  - Verifier Reject sets status='rejected' and logs VERIFIER_REJECTED
  - Admin Panel (renamed from Admin Console) with Patch Queue as second tab
  - Patch Queue tab shows artifacts with status='sent_to_admin' (badge counts patch_request only)
  - Admin Review detail view (reuses Verifier Review with Finalize/Reject buttons)
  - Admin Finalize sets status='resolved' and logs ADMIN_APPROVED
- Verifier/Admin SRR (Read-Only Inspector) + Patch Tester:
  - SSR opens with artifact context: dataset_id + row_id + patch_request_id binding
  - Row Inspector renders read-only (no edit actions, no inline editing)
  - Action buttons hidden in read-only mode
  - Patch Tester tab visible for Verifier AND Admin roles (not just Reviewer)
  - Patch Tester hidden for RFI artifacts (only shows for Correction/Blacklist)
  - vrOpenSingleRowReview() passes artifact context to SRR
  - srrState.isReadOnly flag controls edit permissions
  - Send Back to Analyst: status='needs_clarification', logs PATCH_TESTER_FEEDBACK, appends thread message
  - Thread message includes: Field, Proposed Value, Adjusted Value (if different), Notes

**What This Is NOT:**
- Not a runtime system
- Not connected to any external APIs
- Not a store for credentials, secrets, or endpoints
- Not a place for LLM prompts or prompt engineering
- No DataDash pipeline, Salesforce integration, extraction, resolution, or enrichment logic

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Repository Structure

| Directory | Purpose |
|-----------|---------|
| `docs/` | Operator-facing documentation and governance (start with `docs/INDEX.md`) |
| `rules/` | Analyst-friendly rule authoring templates (Salesforce, QA, Resolver) |
| `config/` | Semantic config base + patch files (no credentials) |
| `examples/` | Synthetic sample data for offline preview |
| `local_runner/` | Offline validation and preview tools |
| `scripts/` | Utility scripts (MCP link generation, smoke tests) |
| `ui/` | Placeholder UI skeleton (non-executing) |

### Core Design Decisions

**1. Governance-Only Control Plane**
- All semantic decisions are captured as reviewable configuration artifacts
- No runtime execution, no APIs, no credentials, no prompts
- Changelog documents "why" changes were made, not just "what"

**2. Offline-First Determinism**
- Same inputs must produce identical outputs
- All previews run locally without network access
- Stdlib-only Python (no external dependencies)

**3. Join Strategy**
- Canonical join order: `contract_key` → `file_url` → `file_name`
- No fabricated identifiers
- Unmatched cases surface as explicit issues

**4. Config Pack Model**
- `config_pack.base.json`: Versioned baseline semantic model
- `config_pack.patch.json`: Changes array (`add_rule`, `deprecate_rule`)
- Patch `base_version` must exactly match base `version`

### Key Commands

**Validate configuration:**
```bash
python3 local_runner/validate_config.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json
```

**Run deterministic preview:**
```bash
python3 local_runner/run_local.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json \
  --standardized examples/standardized_dataset.example.json \
  --out out/sf_packet.preview.json
```

**Smoke test (required before PRs):**
```bash
bash scripts/replit_smoke.sh
```

### Rule Schema

Rules follow a WHEN/THEN pattern:
- `rule_id`: Unique identifier (e.g., `SF_R1_LABEL_NOT_ARTIST`)
- `when`: Condition with `sheet`, `field`, `operator`, `value`
- `then`: Actions with `action`, `sheet`, `field`, `severity`

Allowed operators: `IN`, `EQ`, `NEQ`, `CONTAINS`, `EXISTS`, `NOT_EXISTS`
Allowed actions: `REQUIRE_BLANK`, `REQUIRE_PRESENT`, `SET_VALUE`
Severity levels: `info`, `warning`, `blocking`

### Output Format

Preview generates `sf_packet` with:
- `sf_summary`: Contract counts by status (ready/needs_review/blocked)
- `sf_contract_results`: Per-contract status and subtype
- `sf_field_actions`: Rule-triggered field actions
- `sf_issues`: Detected problems

## External Dependencies

**None by design.** This repository uses Python standard library only.

- No external Python packages (see `requirements.txt`)
- No database connections
- No API integrations
- No runtime services
- No credentials or secrets

The repository is intentionally isolated as a governance-only control plane, separate from any execution environments.