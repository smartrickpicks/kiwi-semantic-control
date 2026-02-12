import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.ulid import generate_id
from server.api_v25 import envelope, collection_envelope, error_envelope
from server.auth import AuthClass, require_auth, require_role, Role
from server.audit import emit_audit_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

ALLOWED_MODES = ("sandbox", "production")


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


WS_COLUMNS = [
    "id", "name", "mode", "created_at", "updated_at",
    "deleted_at", "version", "metadata",
]
WS_SELECT = ", ".join(WS_COLUMNS)


@router.get("/workspaces")
def list_workspaces(
    request: Request,
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
            conditions = []
            params = []

            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            sql = "SELECT %s FROM workspaces %s ORDER BY id ASC LIMIT %%s" % (WS_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, WS_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_workspaces error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/workspaces", status_code=201)
def create_workspace(
    request: Request,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
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

    mode = body.get("mode", "sandbox")
    if mode not in ALLOWED_MODES:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "mode must be one of: %s" % ", ".join(ALLOWED_MODES)),
        )

    metadata = body.get("metadata", {})
    ws_id = generate_id("ws_")

    idempotency_key = request.headers.get("Idempotency-Key")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if idempotency_key:
                cur.execute(
                    "SELECT %s FROM workspaces WHERE metadata->>'idempotency_key' = %%s" % WS_SELECT,
                    (idempotency_key,),
                )
                existing = cur.fetchone()
                if existing:
                    conn.commit()
                    return JSONResponse(
                        status_code=201,
                        content=envelope(_row_to_dict(existing, WS_COLUMNS)),
                    )
                if not isinstance(metadata, dict):
                    metadata = {}
                metadata["idempotency_key"] = idempotency_key

            cur.execute(
                """INSERT INTO workspaces (id, name, mode, metadata)
                   VALUES (%s, %s, %s, %s)
                   RETURNING """ + WS_SELECT,
                (ws_id, name, mode, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="workspace.created",
                actor_id=auth.user_id,
                resource_type="workspace",
                resource_id=ws_id,
                detail={"name": name, "mode": mode},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, WS_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_workspace error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/workspaces/{ws_id}")
def get_workspace(
    ws_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM workspaces WHERE id = %%s AND deleted_at IS NULL" % WS_SELECT,
                (ws_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Workspace not found: %s" % ws_id),
            )
        return envelope(_row_to_dict(row, WS_COLUMNS))
    except Exception as e:
        logger.error("get_workspace error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/workspaces/{ws_id}")
def update_workspace(
    ws_id: str,
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
    if "mode" in body:
        if body["mode"] not in ALLOWED_MODES:
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "mode must be one of: %s" % ", ".join(ALLOWED_MODES)),
            )
        updates["mode"] = body["mode"]
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
                "SELECT version, deleted_at FROM workspaces WHERE id = %s",
                (ws_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Workspace not found: %s" % ws_id),
                )

            current_version = row[0]
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

            params.extend([ws_id, version])
            sql = "UPDATE workspaces SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                WS_SELECT,
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
                workspace_id=ws_id,
                event_type="workspace.updated",
                actor_id=auth.user_id,
                resource_type="workspace",
                resource_id=ws_id,
                detail={"fields": list(updates.keys()), "new_version": version + 1},
            )
        conn.commit()
        return envelope(_row_to_dict(updated, WS_COLUMNS))
    except Exception as e:
        logger.error("update_workspace error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
