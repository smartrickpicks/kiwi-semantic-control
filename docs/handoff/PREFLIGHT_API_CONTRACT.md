# Preflight API Contract

## Authentication
All `/api/preflight/*` endpoints require v2.5 Either auth (Bearer token or API key).

## Admin Sandbox RBAC
`/api/preflight/*` requires ADMIN role in addition to feature-flag enablement.

If caller is non-admin, return v2.5 error envelope:
- code: `FORBIDDEN`
- message: `"Preflight is in admin sandbox mode."`

This applies to:
- `POST /api/preflight/run`
- `GET /api/preflight/{doc_id}`
- `POST /api/preflight/action`

## Endpoints

### POST /api/preflight/run
Run preflight analysis on a document.

**Request:**
```json
{
  "file_url": "https://...",
  "doc_id": "optional_doc_id"
}
```

**Headers:** Authorization (Bearer/API key), X-Workspace-Id (fallback)

**Response (200):**
```json
{
  "data": {
    "doc_id": "...",
    "workspace_id": "...",
    "doc_mode": "SEARCHABLE|SCANNED|MIXED",
    "gate_color": "GREEN|YELLOW|RED",
    "gate_reasons": ["..."],
    "page_classifications": [...],
    "metrics": {
      "total_pages": 10,
      "avg_chars_per_page": 1234.5,
      "replacement_char_ratio": 0.001,
      "control_char_ratio": 0.0005,
      "searchable_pages": 8,
      "scanned_pages": 1,
      "mixed_pages": 1
    },
    "materialized": false,
    "timestamp": "..."
  }
}
```

### GET /api/preflight/{doc_id}
Read cached preflight result.

### POST /api/preflight/action
Handle Accept Risk or Escalate OCR.

**Request:**
```json
{
  "doc_id": "...",
  "action": "accept_risk|escalate_ocr",
  "patch_id": "optional"
}
```

## Workspace Resolution
1. Auth-resolved workspace first
2. Fallback: X-Workspace-Id header
3. Body field: workspace_id

## Derived Cache Identity
When doc_id is missing: `doc_derived_<sha256(workspace_id + file_url)[:24]>`
