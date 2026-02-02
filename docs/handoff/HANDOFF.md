# HANDOFF — Orchestrate OS

## Repository
- **Name**: smartrickpicks/kiwi-semantic-control
- **Branch**: main
- **Commit**: ee6244a

## Goal for Next Session
Complete the Evidence Pack → Document Viewer integration by wiring field-to-anchor linking and upgrading the PDF viewer stub.

## Constraints / Do-Not-Change List
- **Canonical terminology only**: Data Source, All Data Grid, Single Row Review, Verifier Review, Admin Approval; Review States; Submit Patch Request; Evidence Pack blocks (Observation, Expected, Justification, Repro)
- **Forbidden terms**: Queue, Load Data, Record Inspection, Apply Patch, Reviewer Hub
- **No runtime services**: All state is local-only (localStorage, in-memory)
- **Single-file vanilla HTML+JS**: No build step, no dependencies
- **Review State transitions**: Only in governed gate views (Verifier Review, Admin Approval)

## Context the Coder Must Know
1. Single Row Review (`#/row/:id`) is a full-page three-panel layout accessed via grid row click
2. Field Inspector uses `SRR_SCHEMA_ORDER` for deterministic ordering (V2 will load from config)
3. Patch status (Draft/Submitted) is local-only; Submit does not affect Review State
4. Evidence Pack has 4 canonical blocks: Observation, Expected, Justification, Repro
5. PDF viewer is currently a stub frame with page controls
6. No audit to address — drift list is empty

## Files Likely to Touch
- `ui/viewer/index.html` — Main viewer implementation
- `docs/ui/views/single_row_review_view.md` — View specification
- `docs/ui/ui_principles.md` — UI contracts and terminology

## Replit/Codex-Ready Prompt
```
1. Read ui/viewer/index.html and find the srrSelectField() function.
2. Add evidence anchor data structure linking fields to PDF page/bbox coordinates.
3. Update Document Viewer panel to highlight anchor regions when a field is selected.
4. Add click-to-scroll behavior in the anchor list.
5. Ensure all changes use canonical terminology only.
6. Run bash scripts/replit_smoke.sh and confirm OK output.
7. Update docs/ui/views/single_row_review_view.md if behavior changes.
```
