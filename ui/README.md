# UI Skeleton (Placeholder Only)

## Status
This is a **placeholder UI skeleton only**. No executable code, no dependencies, no servers.

## Purpose
Establish the folder structure for a future Control Board UI implementation. This skeleton is non-executing and exists solely to reserve the directory layout.

---

## Planned Screens

Based on governance documentation, the UI will eventually include:

1. **Dashboard** - Overview of contract processing status (READY, NEEDS_REVIEW, BLOCKED)
2. **Rule Browser** - View and search active Salesforce rules from config_pack
3. **Preview Runner** - Trigger offline preview harness and view sf_packet results
4. **Issue Viewer** - Display sf_issues, sf_field_actions, and sf_change_log
5. **Manual Review Queue** - List contracts requiring operator attention
6. **Changelog Viewer** - Browse version history and audit trail

---

## I/O Contracts

All UI I/O contracts are defined in:
- `docs/INTERFACES.md` - Data structures for sf_packet, standardized_dataset, config_pack

The UI will consume and display these artifacts without modification.

---

## Execution Model

When implemented, the UI will:
- Call the local harness via **shell commands** (e.g., `python3 local_runner/run_local.py`)
- Read JSON artifacts from the filesystem (no network calls)
- Remain **offline-first** and **deterministic**

No API servers, no external dependencies, no credentials.

---

## Directory Structure

```
ui/
├── README.md           # This file
├── .gitkeep
├── src/
│   ├── pages/          # Page components (placeholder)
│   │   └── .gitkeep
│   ├── components/     # Reusable UI components (placeholder)
│   │   └── .gitkeep
│   └── lib/            # Utility functions (placeholder)
│       └── .gitkeep
└── scripts/            # Build/dev scripts (placeholder)
    └── .gitkeep
```

---

## Implementation Notes

- No `package.json` or runtime dependencies until implementation phase
- No servers or build processes
- UI framework TBD (will be chosen during implementation)
- All data flows through filesystem artifacts, not APIs
