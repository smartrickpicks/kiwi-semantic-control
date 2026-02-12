# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed for defining, validating, and previewing semantic rules offline. It serves as a single source of semantic truth, aiming to streamline patch requests, improve operator ergonomics, and provide an analyst-first reference for explicit, deterministic, and auditable decisions. The system captures semantic decisions as reviewable configuration artifacts, operates offline-first, and ensures deterministic outputs using only the Python standard library for local previews. The business vision is to improve semantic rule management, reduce errors, and enhance decision-making efficiency.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system captures semantic decisions as reviewable configuration artifacts and employs a canonical join strategy for data handling. It uses a Config Pack Model with strict version matching, supporting an 11-status lifecycle for patch requests, including comment systems and role-based access control (Analyst, Verifier, Admin, Architect).

The UI features a dashboard with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are organized into six tabs: Governance, Schema & Standards, Patch Ops, People & Access, QA Runner, and Runtime Config. A Patch Studio facilitates drafting, preflight checks, and evidence packing with live previews and revision tracking. UI elements include color-coded grid highlighting, Excel-style column headers, and a PDF viewer.

Data handling supports CSV/XLSX import, inline editing, and a lock-on-commit mechanism with a change map engine tracking cell-level changes. Workbook session caching persists uploaded Excel data to IndexedDB. Triage Analytics uses normalized key comparison and `COLUMN_ALIAS_MAP` for schema matching.

Semantic rules generate deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Rules follow a WHEN/THEN pattern. Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`. The system uses email-based access control with Google sign-in for production OAuth.

Features include a "Contract Line Item Wizard" for batch adding and deduplication and export functionality for XLSX files including data, change logs, signals summaries, and metadata. An Audit Timeline system uses an IndexedDB-backed store for all governance actions.

A Schema Tree Editor manages the canonical rules bundle, including `field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`, `document_types.json`, and `column_aliases.json`. A Batch Merge feature allows combining source batches into a single governance container, with explicit rule promotion for tenant rules.

A `SystemPass` module provides a deterministic, rerunnable, proposal-only engine for system changes. Pre-Flight triage buckets handle blockers like unknown columns or unreadable OCR. A Contract Index Engine builds a hierarchy of batch, contract, document, contract section, row.

`UndoManager` provides local, session-scoped undo for draft-only inline edits. `RollbackEngine` creates governed rollback artifacts at four scopes (field, patch, contract, batch), capturing before/after state snapshots.

The Triage Analytics module aggregates metrics. Record Inspector Guidance provides section-specific advice. Sandbox mode is permissionless; Production uses strict role gates. A TruthPack module with an `architect` role enables a clean-room state machine for calibration and baseline marking. A Role Registry with stable role IDs, permission-based access checks, and a People workspace are integrated.

The system routes to triage by default for all roles. Contract-first navigation is implemented in the All Data Grid. Grid Mode introduces inline cell editing and pending patch context tracking. A combined interstitial Data Quality Check for duplicate accounts and incomplete addresses fires automatically after workbook load. The `ADDRESS_INCOMPLETE_CANDIDATE` Matching System provides deterministic candidate matching for incomplete addresses, routing warnings and blockers to Pre-Flight.

The architecture is modular, with components and engines extracted into namespaces like `window.AppModules.Components.*` and `window.AppModules.Engines.*`.

## AppModules Registry (44 total: 40 explicit + 4 dynamic Phase C)

### Phase C Dynamic Modules (4)
| Module | Registration | Delegate Target |
|---|---|---|
| `Components.MetricStrip` | `register()` | Metric strip rendering |
| `Components.LifecycleRail` | `register()` | Lifecycle rail rendering |
| `Components.ContractSummaryTable` | `register()` | Contract summary table rendering |
| `Components.PreflightIssueTable` | `register()` | Preflight issue table rendering |

### Grid Modules — Phase D1 (3)
| Module | Delegate Target |
|---|---|
| `Engines.GridState` | filter get/set, sort, column visibility |
| `Components.GridHeader` | header render with sort indicators |
| `Components.GridTable` | row render, cell render, selection |

### Record Inspector Modules — Phase D2 (4)
| Module | Delegate Target |
|---|---|
| `Engines.RecordInspectorState` | state access, open/close, record get/set |
| `Components.RecordInspectorHeader` | header with navigation, close button |
| `Components.RecordInspectorFieldList` | field rows with signal badges |
| `Components.RecordInspectorPatchRail` | patch context, draft actions |

### PDF Viewer Modules — Phase D3 (3)
| Module | Delegate Target |
|---|---|
| `Engines.PdfViewerState` | state access, document load, anchor search |
| `Components.PdfViewerToolbar` | toolbar buttons, page nav, zoom |
| `Components.PdfViewerFrame` | frame render, page display |

### Admin Panel Modules — Phase D4 (8)
| Module | Delegate Target |
|---|---|
| `Engines.AdminTabState` | tab get/set, visibility |
| `Components.AdminTabsNav` | tab bar with active indicator |
| `Components.AdminTabGovernance` | governance settings render |
| `Components.AdminTabSchemaStandards` | schema tree editor render |
| `Components.AdminTabPatchOps` | patch operations render |
| `Components.AdminTabPeopleAccess` | people workspace render |
| `Components.AdminTabQARunner` | test suite render |
| `Components.AdminTabRuntimeConfig` | runtime settings render |

### Audit Timeline Modules — Phase D5 (3)
| Module | Delegate Target |
|---|---|
| `Engines.AuditTimelineState` | memCache access, query, actor resolution, canonical event names |
| `Components.AuditTimelinePanel` | panel open/close, badge, dropdown, export |
| `Components.AuditTimelineFilters` | filter get/set, quick chips, presets |

### DataSource/Import Modules — Phase D6 (3)
| Module | Delegate Target |
|---|---|
| `Engines.ImportState` | Import state tracking, file type detection, parse status |
| `Engines.WorkbookSessionStore` | Workbook cache save/load/clear, named session save/load/list |
| `Components.DataSourcePanel` | panel open/close, file input |

### System Pass Modules — Phase D7 (3)
| Module | Delegate Target |
|---|---|
| `Engines.SystemPassState` | Proposals, run/rerun, accept/reject, bulk actions, hinge detection, sort/filter |
| `Components.SystemPassPanel` | panel open/close, rerun, render |
| `Components.SystemPassActions` | Single and bulk proposal actions with delegate wiring |

### Contract Health Score Modules — Phase D8 (3)
| Module | Delegate Target |
|---|---|
| `Engines.ContractHealthState` | Scores, penalties, bands, computeAll, sortByHealth, getFilteredContracts, computeScore |
| `Components.ContractHealthPanel` | Health cell render, filter chip UI, band filter action |
| `Components.ContractHealthBadges` | Badge rendering in triage/patch/queue tables |

### Data Quality Check Modules — Phase D9 (3)
| Module | Delegate Target |
|---|---|
| `Engines.DataQualityState` | DQ state access, run/detect/rerun, card update, duplicate/address item access |
| `Components.DataQualityModal` | Modal show/close, tab switch, tab badge update, current item render |
| `Components.DataQualityActions` | Account dismiss/merge/link, address accept/reject |

### Batch Merge Modules — Phase D10 (3)
| Module | Delegate Target |
|---|---|
| `Engines.BatchMergeState` | Merged batch state access, session restore, reset, active filter |
| `Components.BatchMergePanel` | Source list refresh, merged panel render, lineage view, filter change |
| `Components.BatchMergeActions` | Merge execution (try/catch guarded), delete, tenant rule promotion |

### Grid Context Menu Modules — Phase D11 (3)
| Module | Delegate Target |
|---|---|
| `Engines.GridContextState` | Context state, role matrix, current role, system field check, action state, record resolve, findClosest |
| `Components.GridContextMenu` | Menu open/close, item render, isOpen check |
| `Components.GridContextActions` | Action dispatch, action state query |

### Patch Validation: Future-Only Fields
- `blacklist_category` and `rfi_target` are defined in the patch draft schema but are future-only features with no current required/optional enforcement. They appear as empty-string placeholders and must not be treated as active validation fields.

### Deterministic Logs
- `[APP-MODULES][P1C] registered:` module registration
- `[APP-MODULES][P1C] bootstrap_complete` Phase B engine registration
- `[APP-MODULES][P1D1] grid_modules_registered` Phase D1 grid module registration
- `[APP-MODULES][P1D2] inspector_modules_registered` Phase D2 all 4 inspector modules registered
- `[APP-MODULES][P1D3] pdf_viewer_modules_registered` Phase D3 all 3 PDF viewer modules registered
- `[APP-MODULES][P1D4] admin_modules_registered` Phase D4 all 8 admin modules registered
- `[APP-MODULES][P1D5] audit_timeline_modules_registered` Phase D5 all 3 audit timeline modules registered
- `[APP-MODULES][P1D6] datasource_modules_registered` Phase D6 all 3 datasource modules registered
- `[IMPORT-D6] source_opened/parse_started/parse_finished/session_saved/session_loaded` import flow observability
- `[APP-MODULES][P1D7] systempass_modules_registered` Phase D7 all 3 system pass modules registered
- `[SYSTEMPASS-D7] panel_opened` system pass reason picker opened
- `[SYSTEMPASS-D7] rerun_started/rerun_finished` system pass rerun lifecycle
- `[SYSTEMPASS-D7] proposal_action` single proposal accept/reject
- `[SYSTEMPASS-D7] bulk_action` bulk accept/reject action
- `[APP-MODULES][P1D8] health_modules_registered` Phase D8 all 3 health modules registered
- `[HEALTH-D8] score_calculated` health scores computed for all contracts
- `[HEALTH-D8] panel_rendered` health cell rendered in contract table
- `[HEALTH-D8] badge_rendered` health badge rendered in grid/queue
- `[HEALTH-D8] health_refreshed` health filter band changed
- `[APP-MODULES][P1D9] dq_modules_registered` Phase D9 all 3 data quality modules registered
- `[DQ-D9] dq_started` data quality check run/rerun initiated
- `[DQ-D9] dq_finished` data quality check run/rerun completed
- `[DQ-D9] modal_opened` data quality modal displayed
- `[DQ-D9] action_taken` account/address action executed (dismiss, merge, link, accept, reject)
- `[APP-MODULES][P1D10] merge_modules_registered` Phase D10 all 3 batch merge modules registered
- `[MERGE-D10] panel_opened` batch merge panel rendered (renderMergedBatchPanel)
- `[MERGE-D10] merge_started` batch merge execution initiated
- `[MERGE-D10] merge_finished` batch merge execution completed (success path only)
- `[MERGE-D10] merge_failed` batch merge execution failed (error path)
- `[MERGE-D10] action_taken` batch merge action executed (delete, promote_tenant_rule, prompt_promote_rule)
- `[APP-MODULES][P1D11] gridctx_modules_registered` Phase D11 all 3 grid context menu modules registered
- `[GRIDCTX-D11] menu_opened` grid context menu opened (inside _gridCtxOpen)
- `[GRIDCTX-D11] menu_closed` grid context menu closed (inside _gridCtxClose, wasOpen guard)
- `[GRIDCTX-D11] action_invoked` grid context action dispatched (inside _gridCtxAction, enabled path)
- `[GRIDCTX-D11] action_blocked` grid context action blocked (inside _gridCtxAction, disabled path)
- `[PATCH-COMP][P1B]` patch panel operations (open, submit, cancel, draft)

## External Dependencies
- **FastAPI server**: Acts as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF.
- **SheetJS (XLSX)**: Loaded via CDN for Excel import/export functionality.
- **Contract Composite Grid**: Enhances the All Data Grid with nested, collapsible contract sections.
- **Batch PDF Scan**: Adds batch-level PDF scanning for mojibake/non-searchable content.
- **Canonical Contract Triage View**: Adds canonical triage metrics and contract-centric terminology.
- **PDF Reliability Spike**: Diagnoses and hardens PDF anchor search reliability.
- **Contract Health Pre-Flight Table**: Replaces card-based grouping with a single unified nested table for contract health.
- **Real-Time Pre-Flight Intake**: Provides real-time visibility into batch PDF scanning.
- **Clean-to-SystemPass Routing**: Routes clean-scanned contracts to the System Pass queue.
- **Contract Health Score**: A lifecycle-wide health scoring engine tracking contract health with a 0-100 score.
- **Data Quality Check (Combined Interstitial)**: A unified modal for duplicate account detection and incomplete address candidate matching.
- **ADDRESS_INCOMPLETE_CANDIDATE Matching System**: Deterministic candidate matching for incomplete addresses.
