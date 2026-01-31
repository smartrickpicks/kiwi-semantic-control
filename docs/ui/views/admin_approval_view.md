# View: Admin Approval

> Final approval surface for Admin decisions before baseline promotion.

## Entry Conditions

| Condition | Required |
|-----------|----------|
| Patch in Verifier_Approved or Admin_Hold state | Yes |
| User authenticated | Yes |
| Minimum role | Admin |
| gate_verifier passed | Yes |

**Note:** Verifiers can view this page in read-only mode but cannot take approval actions.

## Visible Artifacts

| Artifact | Description | Required |
|----------|-------------|----------|
| Structured Intent | Rendered WHEN/THEN/BECAUSE | Yes |
| Evidence Pack | All 4 blocks | Yes |
| Preflight Report | Badge summary | Yes |
| Verifier Decision | Approval notes and timestamp | Yes |
| Revision History | All revisions with diff summaries | Yes |
| Smoke Test Status | Pass/fail indicator | Yes |
| Changelog Preview | Proposed changelog entry | Yes |

## Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| View all artifacts | No | Read-only | Yes |
| Admin Approve | No | No | Yes |
| Admin Hold | No | No | Yes |
| Release Hold | No | No | Yes |
| Add admin notes | No | No | Yes |
| Export preview | No | No | Yes |

## Disallowed Actions

| Action | Reason |
|--------|--------|
| Edit intent or evidence | Locked after verifier approval |
| Revert to Under_Review | Use Admin Hold instead |
| Promote without smoke pass | gate_admin requires smoke evidence |
| Skip changelog | Required for promotion |

## Gate Ownership

This view owns one gate (see [gate_view_mapping.md](../gate_view_mapping.md)):

| Gate | Condition | On Failure |
|------|-----------|------------|
| gate_admin | Admin decision recorded + smoke pass | Patch remains in Verifier_Approved |

## REVIEW_CHECKLIST Enforcement

Before Admin Approve, the Admin must confirm ALL checklist sections (see [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md)):

| Section | Check |
|---------|-------|
| Intent Clarity | Confirmed by Verifier |
| Schema Correctness | Confirmed by Verifier |
| Preview Validity | Confirmed by Verifier |
| Conflict Assessment | Confirmed by Verifier |
| Downstream Risk Awareness | Confirmed by Verifier |
| Smoke Verification | **Must be currently passing** (not just at submit time) |
| Versioning and Changelog | Version increment, changelog entry present |

**Contract:** If smoke test is not currently passing, the Admin MUST use "Admin Hold". If changelog is missing, the Admin MUST request it before approval. Promotion without passing smoke and complete changelog is a contract violation.

## Audit/Evidence Requirements

| Event | Logged | Evidence |
|-------|--------|----------|
| Admin Approve | Yes | timestamp, patch_id, admin_actor, smoke_evidence_ref |
| Admin Hold | Yes | timestamp, patch_id, admin_actor, hold_reason |
| Release Hold | Yes | timestamp, patch_id, admin_actor |

## State Transitions

| From State | To State | Action | Role |
|------------|----------|--------|------|
| Verifier_Approved | Admin_Approved | Admin Approve | Admin |
| Verifier_Approved | Admin_Hold | Admin Hold | Admin |
| Admin_Hold | Under_Review | Release Hold | Admin |

## Related Documents

- [gate_view_mapping.md](../gate_view_mapping.md) — Gate ownership
- [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md) — Full checklist
- [admin.md](../roles/admin.md) — Admin role permissions
- [promotion_view.md](promotion_view.md) — Next stage after admin approval
