# View: Patch Authoring (Patch Studio)

> Workbench for authoring structured intent, running preflight checks, and assembling evidence packs.

## Entry Conditions

| Condition | Required |
|-----------|----------|
| Dataset loaded | Yes |
| User authenticated | Yes (any role) |
| Minimum role | Analyst |
| Issue identified | Recommended (from Single Row Review) |

## Visible Artifacts

| Artifact | Description | Required |
|----------|-------------|----------|
| Structured Intent Form | Target Field, Condition Type, Action Type | Yes |
| Intent Preview | Rendered WHEN/THEN/BECAUSE | Yes (live update) |
| Preflight Results | Pass/Warn/Fail badges | After preflight run |
| Evidence Pack Form | Observation, Expected, Justification, Repro | Yes |
| Revision History | Previous revisions if editing | If editing |

## Sub-Tabs

| Tab | Purpose |
|-----|---------|
| Draft | Structured intent authoring |
| Preflight | Validation results and badge summary |
| Evidence Pack | 4-block evidence assembly |

## Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| Edit structured intent | Yes | Yes | Yes |
| Select target field | Yes | Yes | Yes |
| Select condition/action type | Yes | Yes | Yes |
| Use "Other" escape hatch | Yes | Yes | Yes |
| Run Preflight | Yes | Yes | Yes |
| View preflight report | Yes | Yes | Yes |
| Copy preflight report | Yes | Yes | Yes |
| Edit evidence pack | Yes | Yes | Yes |
| Submit Patch Request | Yes | Yes | Yes |

## Disallowed Actions

| Action | Reason |
|--------|--------|
| Submit without preflight pass | gate_preflight not satisfied |
| Submit without evidence pack | gate_evidence not satisfied |
| Approve own patch | Requires different actor at review |
| Skip structured intent | All fields required |

## Gate Ownership

This view owns two gates (see [gate_view_mapping.md](../gate_view_mapping.md)):

| Gate | Condition | On Failure |
|------|-----------|------------|
| gate_preflight | All checks pass or warn (no fail) | Block submission, show errors |
| gate_evidence | All 4 blocks populated | Block submission, highlight missing |

## Audit/Evidence Requirements

| Event | Logged | Evidence |
|-------|--------|----------|
| Preflight run | Yes | timestamp, patch_id, badge_summary |
| Submit Patch Request | Yes | timestamp, patch_id, actor, intent_rendered |

## State Transitions

| From State | To State | Action | Role |
|------------|----------|--------|------|
| Draft | Submitted | Submit Patch Request | Analyst, Verifier, Admin |
| Needs_Clarification | Submitted | Respond to Clarification | Author |

## Form Validation

| Field | Required | Max Length |
|-------|----------|------------|
| Target Field | Yes | - |
| Condition Type | Yes | - |
| Action Type | Yes | - |
| Other (if selected) | Yes | 500 chars |
| Observation | Yes | 1000 chars |
| Expected | Yes | 1000 chars |
| Justification | Yes | 1000 chars |
| Repro | Yes | 2000 chars |

## Related Documents

- [gate_view_mapping.md](../gate_view_mapping.md) — Gate ownership
- [single_row_review_view.md](single_row_review_view.md) — Issue identification
- [verifier_review_view.md](verifier_review_view.md) — Next stage after submit
- [analyst.md](../roles/analyst.md) — Analyst role permissions

Note: “Submit Patch Request” routes to Verifier Review and sets patch status to Submitted. No “queue” semantics are implied.
