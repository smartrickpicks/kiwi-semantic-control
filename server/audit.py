import json
import logging
from datetime import datetime, timezone

from server.ulid import generate_id

logger = logging.getLogger(__name__)


def emit_audit_event(cur, workspace_id, event_type, actor_id,
                     resource_type=None, resource_id=None,
                     detail=None, actor_role=None,
                     batch_id=None, patch_id=None, dataset_id=None,
                     record_id=None, field_key=None,
                     before_value=None, after_value=None,
                     timestamp_iso=None):
    audit_id = generate_id("aud_")
    if timestamp_iso is None:
        timestamp_iso = datetime.now(timezone.utc).isoformat()

    meta = detail if isinstance(detail, dict) else {}
    if resource_type:
        meta["resource_type"] = resource_type
    if resource_id:
        meta["resource_id"] = resource_id
    metadata_json = json.dumps(meta) if meta else "{}"

    cur.execute(
        """INSERT INTO audit_events
           (id, workspace_id, event_type, actor_id, actor_role,
            timestamp_iso, dataset_id, batch_id, record_id,
            field_key, patch_id, before_value, after_value, metadata)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)""",
        (audit_id, workspace_id, event_type, actor_id, actor_role,
         timestamp_iso, dataset_id, batch_id, record_id,
         field_key, patch_id, before_value, after_value, metadata_json),
    )
    return audit_id
