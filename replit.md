# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed to define, validate, and preview semantic rules offline. It acts as a single source of semantic truth, enabling rule authoring and review as configuration. The project aims to improve operator ergonomics, streamline the patch request and review pipeline, and provide an analyst-first reference with clear interfaces for explicit, deterministic, and auditable decisions. It captures semantic decisions as reviewable configuration artifacts and operates offline-first, ensuring deterministic outputs using only the Python standard library for local previews.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The core design involves capturing semantic decisions as reviewable configuration artifacts. Data handling employs a canonical join strategy (`contract_key` → `file_url` → `file_name`) and a Config Pack Model (`config_pack.base.json` for baseline, `config_pack.patch.json` for changes) with strict version matching. The system supports an 11-status lifecycle for patch requests, including comment systems and role-based access control (Analyst, Verifier, Admin).

The UI features a dashboard with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are presented in a workflow-ordered view with Plain-English, Payload, and Master tabs. A Patch Studio enables drafting, preflight checks, and evidence packing with live previews and revision tracking. UI elements include color-coded grid highlighting, Excel-style column headers with drag-and-drop reordering, and a PDF viewer. Record Inspection (SRR) provides navigation and auto-advances.

Data handling supports CSV/XLSX import, a Field Inspector for search-filtered fields, inline editing, and a lock-on-commit mechanism. A change map engine tracks cell-level changes, propagating entries to canonical stores. The Verifier Triage uses a 4-queue system, and a localStorage-backed mock filesystem manages artifacts. Workbook session caching persists uploaded Excel data to IndexedDB, supporting multi-session storage and auto-save.

Semantic rules generate deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Rules follow a WHEN/THEN pattern. Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`. The system uses email-based access control with Google sign-in for production OAuth.

Features include "Catalog Items Group" for batch adding and deduplication, and a `_document_type` and `_capabilities` object per record, with document types loaded from `config/document_types.json`. Export functionality generates XLSX files including all data sheets, change logs, signals summaries, and metadata. An Audit Timeline system uses an IndexedDB-backed store for all governance actions, accessible via a UI with filtering options and exportable to XLSX.

The system incorporates a Schema Tree Editor for managing the canonical rules bundle, including `field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`, `document_types.json`, and `column_aliases.json`. It supports column alias resolution and tracking of schema changes. A Batch Merge feature allows combining source batches into a single governance container, with explicit rule promotion for tenant rules.

Document roles (`Root Agreement`, `Amendment`, etc.) are distinct from document types and are inferred with user confirmation. A `SystemPass` module provides a deterministic, rerunnable, proposal-only engine for system changes, routed to a "System Changes" triage bucket. Pre-Flight triage buckets handle blockers like unknown columns or unreadable OCR. A Contract Index Engine builds a hierarchy of batch→contract→document→sheet→row, persisting summary references to SessionDB.

### Hinge-Governed Apply + Undo vs Rollback (v2.2 P1)
`SystemPass.acceptProposal()` for hinge-field proposals auto-creates a `system_suggested` patch artifact in `PATCH_REQUEST_STORE` and routes through the standard patch lifecycle (Draft → Submitted → Verifier → Admin → Applied). Non-hinge proposals remain directly acceptable. Emits `system_change_routed_to_patch` audit event.

`UndoManager` provides local, session-scoped undo for draft-only SRR inline edits. Window-based buffer (5 min / 50 entries max). Cannot undo approved/submitted artifacts. Emits `undo_local` audit event. Wired into `FIELD_CORRECTED` flow.

`RollbackEngine` creates governed rollback artifacts at 4 scopes (field, patch, contract, batch). Two-phase flow: `createRollback()` → `rollback_created` event, then `applyRollback()` → `rollback_applied` event. Append-only — never deletes history; captures before/after state snapshots. References original event/artifact IDs.

Rollback-triggered rerun: If `applyRollback()` detects hinge-field modifications, auto-calls `SystemPass.run('rollback_hinge_affected')` and renders new proposals.

Audit alignment: `undo_local`, `rollback_created`, `rollback_applied`, `system_change_routed_to_patch` registered in `_canonicalAuditEventName` aliases, `AUDIT_TYPE_CATEGORIES.rollback`, `_inferAuditScope`, and audit filter dropdown ("Undo / Rollback"). Docs: `docs/UNDO_VS_ROLLBACK.md`.

## External Dependencies
A FastAPI server acts as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF. SheetJS (XLSX) is loaded via CDN for Excel import/export functionality.