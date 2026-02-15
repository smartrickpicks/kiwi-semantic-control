# Preflight Sync — Task List

## Completed Tasks
1. Canonicalize flag behavior (PREFLIGHT_GATE_SYNC + PREFLIGHT_GATE_SYNC_V251 alias)
2. Admin-only sandbox RBAC gate on preflight endpoints
3. GET /api/pdf/text_layout with shared SSRF protections
4. Deterministic preflight engine with locked thresholds
5. POST /api/preflight/run + GET /api/preflight/{doc_id} with workspace isolation
6. Non-materialized document handling
7. Anchor payload rules (page dimensions, coord_space)
8. UI preflight panel with canonical state
9. Submit gating via validateSubmissionGates()
10. Admin-only UI disable/hide behavior
11. Documentation

## Acceptance Criteria
- Non-admin requests rejected with FORBIDDEN and exact message "Preflight is in admin sandbox mode."
- Non-admin UI displays "Admin-only sandbox." and disables/hides preflight action controls
- Page/doc classification and gate thresholds match locked P1E policy
- RED computed immediately after first-pass extraction
- Patch metadata keys: preflight_summary, system_evidence_pack_id
