import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.ulid import generate_id
from server.api_v25 import envelope, collection_envelope, error_envelope
from server.auth import AuthClass, require_auth
from server.audit import emit_audit_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

ALLOWED_SOURCES = ("upload", "merge", "import")
ALLOWED_STATUSES = ("active", "archived")

BATCH_COLUMNS = [
    "id", "workspace_id", "name", "source", "batch_fingerprint",
    "status", "record_count", "created_at", "updated_at",
    "deleted_at", "version", "metadata",
]
BATCH_SELECT = ", ".join(BATCH_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/workspaces/{ws_id}/batches")
def list_batches(
    ws_id: str,
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    include_deleted: bool = Query(False),
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM workspaces WHERE id = %s AND deleted_at IS NULL", (ws_id,))
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Workspace not found: %s" % ws_id),
                )

            conditions = ["workspace_id = %s"]
            params = [ws_id]

            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM batches %s ORDER BY id ASC LIMIT %%s" % (BATCH_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, BATCH_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_batches error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/workspaces/{ws_id}/batches", status_code=201)
def create_batch(
    ws_id: str,
    request: Request,
    body: dict,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    name = body.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "name is required and must be a non-empty string"),
        )
    name = name.strip()

    source = body.get("source", "upload")
    if source not in ALLOWED_SOURCES:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "source must be one of: %s" % ", ".join(ALLOWED_SOURCES)),
        )

    batch_fingerprint = body.get("batch_fingerprint")
    metadata = body.get("metadata", {})
    bat_id = generate_id("bat_")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM workspaces WHERE id = %s AND deleted_at IS NULL", (ws_id,))
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Workspace not found: %s" % ws_id),
                )

            cur.execute(
                """INSERT INTO batches (id, workspace_id, name, source, batch_fingerprint, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING """ + BATCH_SELECT,
                (bat_id, ws_id, name, source, batch_fingerprint, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="batch.created",
                actor_id=auth.user_id,
                resource_type="batch",
                resource_id=bat_id,
                detail={"name": name, "source": source},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, BATCH_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_batch error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/batches/{bat_id}")
def get_batch(
    bat_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM batches WHERE id = %%s AND deleted_at IS NULL" % BATCH_SELECT,
                (bat_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Batch not found: %s" % bat_id),
            )
        return envelope(_row_to_dict(row, BATCH_COLUMNS))
    except Exception as e:
        logger.error("get_batch error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/batches/{bat_id}")
def update_batch(
    bat_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    version = body.get("version")
    if version is None or not isinstance(version, int):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "version (integer) is required for PATCH"),
        )

    updates = {}
    if "name" in body:
        n = body["name"]
        if not isinstance(n, str) or not n.strip():
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "name must be a non-empty string"),
            )
        updates["name"] = n.strip()
    if "status" in body:
        if body["status"] not in ALLOWED_STATUSES:
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "status must be one of: %s" % ", ".join(ALLOWED_STATUSES)),
            )
        updates["status"] = body["status"]
    if "metadata" in body:
        updates["metadata"] = body["metadata"]

    if not updates:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "No updatable fields provided"),
        )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT version, deleted_at, workspace_id FROM batches WHERE id = %s",
                (bat_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Batch not found: %s" % bat_id),
                )

            current_version = row[0]
            workspace_id = row[2]
            if current_version != version:
                return JSONResponse(
                    status_code=409,
                    content=error_envelope(
                        "STALE_VERSION",
                        "Resource has been modified since your last read",
                        details={"current_version": current_version, "provided_version": version},
                    ),
                )

            set_clauses = []
            params = []
            for k, v in updates.items():
                if k == "metadata":
                    set_clauses.append("metadata = %s::jsonb")
                    params.append(json.dumps(v))
                else:
                    set_clauses.append("%s = %%s" % k)
                    params.append(v)
            set_clauses.append("version = version + 1")
            set_clauses.append("updated_at = NOW()")

            params.extend([bat_id, version])
            sql = "UPDATE batches SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                BATCH_SELECT,
            )
            cur.execute(sql, params)
            updated = cur.fetchone()

            if not updated:
                conn.rollback()
                return JSONResponse(
                    status_code=409,
                    content=error_envelope("STALE_VERSION", "Concurrent modification detected"),
                )

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="batch.updated",
                actor_id=auth.user_id,
                resource_type="batch",
                resource_id=bat_id,
                detail={"fields": list(updates.keys()), "new_version": version + 1},
            )
        conn.commit()
        return envelope(_row_to_dict(updated, BATCH_COLUMNS))
    except Exception as e:
        logger.error("update_batch error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
