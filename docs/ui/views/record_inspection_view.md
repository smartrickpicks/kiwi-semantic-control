# View: Record Inspection

> Detail view for examining individual records, field values, and associated issues.

## Entry Conditions

| Condition | Required |
|-----------|----------|
| Dataset loaded | Yes |
| Record selected | Yes (via grid click or URL param) |
| User authenticated | Yes (any role) |
| Minimum role | Analyst |

## Visible Artifacts

| Artifact | Description | Required |
|----------|-------------|----------|
| Record ID | contract_key, file_url, or file_name | Yes |
| Field values | All columns for the selected record | Yes |
| Current status | sf_contract_status | Yes |
| Subtype | sf_contract_subtype if present | If available |
| Issues list | sf_issues for this record | If any |
| Comments | Associated comments/RFIs | If any |

## Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| View all fields | Yes | Yes | Yes |
| Copy field values | Yes | Yes | Yes |
| Add comment/RFI | Yes | Yes | Yes |
| Elevate comment to Patch Request | Yes | Yes | Yes |
| Navigate to Patch Studio | Yes | Yes | Yes |
| Close drawer | Yes | Yes | Yes |

## Disallowed Actions

| Action | Reason |
|--------|--------|
| Edit field values directly | Read-only inspection |
| Change record status | Use Patch Studio for semantic changes |
| Delete record | Not supported |
| Bulk operations | Single-record view |

## Audit/Evidence Requirements

| Event | Logged | Evidence |
|-------|--------|----------|
| Add comment | Yes | timestamp, actor, comment_text, record_id |
| Elevate to Patch Request | Yes | timestamp, actor, comment_id, patch_request_id |

## State Transitions

| From State | To State | Action | Role |
|------------|----------|--------|------|
| (comment) Open | (comment) Resolved | Resolve Comment | Any |
| (comment) Open | (comment) ElevatedToPatchRequest | Elevate | Any |

## Related Documents

- [triage_view.md](triage_view.md) — Triage navigation hub
- [patch_authoring_view.md](patch_authoring_view.md) — Patch Studio
- [analyst.md](../roles/analyst.md) — Analyst role permissions
