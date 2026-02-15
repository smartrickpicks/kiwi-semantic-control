# Preflight Data Persistence

## Cache Semantics
- Preflight results are cached in-memory, workspace-scoped
- Cache key: `{workspace_id}::{doc_id}`
- No database writes for preflight results (no schema changes)

## RBAC Persistence Guard
Preflight persistence side-effects (Accept Risk / Escalate OCR) are ADMIN-only in sandbox stage. Non-admin callers do not create evidence-pack linkage updates or escalation side-effects through preflight actions.

## Evidence Pack Attach Semantics
- **Before patch exists:** Cache/session only — no FK-bound writes
- **After patch exists (Accept Risk / Escalate OCR):** Creates evidence pack ID, writes locked patch metadata keys

## Patch Metadata Keys
```json
{
  "patch.metadata.preflight_summary": {
    "doc_id": "...",
    "gate_color": "YELLOW",
    "doc_mode": "MIXED",
    "action": "accept_risk",
    "metrics": { ... }
  },
  "patch.metadata.system_evidence_pack_id": "evp_..."
}
```

## Non-Materialized Documents
- Skip FK-bound writes
- Still return full payload
- Cache/session still written
- UI gating still enforced regardless of persistence state
