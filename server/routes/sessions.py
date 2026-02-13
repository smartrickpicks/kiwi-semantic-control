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
router = APIRouter(prefix="/api/v2.5", tags=["sessions"])

SESSION_COLUMNS = [
    "id", "user_id", "workspace_id", "environment",
    "source_type", "source_ref", "session_data", "status",
    "created_at", "updated_at", "last_accessed_at", "metadata",
]
SESSION_SELECT = ", ".join(SESSION_COLUMNS)

VALID_ENVIRONMENTS = ("sandbox", "production")
VALID_SOURCE_TYPES = ("local", "drive")
VALID_STATUSES = ("active", "archived", "deleted")


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/workspaces/{ws_id}/sessions/active")
def get_active_session(
    ws_id: str,
    auth=Depends(require_auth(AuthClass.BEARER)),
    environment: str = Query("sandbox"),
):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT %s FROM workbook_sessions
                   WHERE user_id = %%s AND workspace_id = %%s
                     AND environment = %%s AND status = 'active'
                   ORDER BY last_accessed_at DESC
                   LIMIT 1""" % SESSION_SELECT,
                (auth.user_id, ws_id, environment),
            )
            row = cur.fetchone()

        if not row:
            return envelope(None)

        return envelope(_row_to_dict(row, SESSION_COLUMNS))
    except Exception as e:
        logger.error("get_active_session error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/workspaces/{ws_id}/sessions", status_code=201)
async def create_session(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    environment = body.get("environment", "sandbox")
    source_type = body.get("source_type", "").strip()
    source_ref = body.get("source_ref", "").strip()
    session_data = body.get("session_data", {})

    if environment not in VALID_ENVIRONMENTS:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "environment must be one of: %s" % ", ".join(VALID_ENVIRONMENTS)),
        )

    if source_type not in VALID_SOURCE_TYPES:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "source_type must be one of: %s" % ", ".join(VALID_SOURCE_TYPES)),
        )

    if not source_ref:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "source_ref is required"),
        )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT %s FROM workbook_sessions
                   WHERE user_id = %%s AND workspace_id = %%s
                     AND environment = %%s AND source_type = %%s AND source_ref = %%s
                     AND status != 'deleted'""" % SESSION_SELECT,
                (auth.user_id, ws_id, environment, source_type, source_ref),
            )
            existing = cur.fetchone()

            if existing:
                cur.execute(
                    """UPDATE workbook_sessions
                       SET last_accessed_at = NOW(), updated_at = NOW(),
                           status = 'active'
                       WHERE id = %s
                       RETURNING """ + SESSION_SELECT,
                    (existing[0],),
                )
                updated = cur.fetchone()
                conn.commit()
                return JSONResponse(
                    status_code=200,
                    content=envelope(_row_to_dict(updated, SESSION_COLUMNS)),
                )

            session_id = generate_id("wbs_")
            cur.execute(
                """INSERT INTO workbook_sessions
                   (id, user_id, workspace_id, environment, source_type, source_ref, session_data)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + SESSION_SELECT,
                (session_id, auth.user_id, ws_id, environment, source_type, source_ref,
                 json.dumps(session_data)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="SESSION_CREATED",
                actor_id=auth.user_id,
                actor_role=auth.role,
                resource_type="workbook_session",
                resource_id=session_id,
                detail={
                    "environment": environment,
                    "source_type": source_type,
                    "source_ref": source_ref,
                },
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, SESSION_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_session error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/workspaces/{ws_id}/sessions")
def list_sessions(
    ws_id: str,
    auth=Depends(require_auth(AuthClass.BEARER)),
    status: str = Query(None),
    environment: str = Query("sandbox"),
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    conn = get_conn()
    try:
        conditions = ["user_id = %s", "workspace_id = %s", "environment = %s"]
        params = [auth.user_id, ws_id, environment]

        if status:
            valid_statuses = [s.strip() for s in status.split(",") if s.strip() in VALID_STATUSES]
            if valid_statuses:
                placeholders = ", ".join(["%s"] * len(valid_statuses))
                conditions.append("status IN (%s)" % placeholders)
                params.extend(valid_statuses)
        else:
            conditions.append("status != 'deleted'")

        if cursor:
            conditions.append("id < %s")
            params.append(cursor)

        where = " AND ".join(conditions)
        params.append(limit + 1)

        with conn.cursor() as cur:
            cur.execute(
                """SELECT %s FROM workbook_sessions
                   WHERE %s
                   ORDER BY last_accessed_at DESC
                   LIMIT %%s""" % (SESSION_SELECT, where),
                params,
            )
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, SESSION_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_sessions error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/workspaces/{ws_id}/sessions/{session_id}")
async def update_session(ws_id: str, session_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, status FROM workbook_sessions WHERE id = %s AND workspace_id = %s",
                (session_id, ws_id),
            )
            existing = cur.fetchone()

            if not existing:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Session not found: %s" % session_id),
                )

            if existing[1] != auth.user_id:
                return JSONResponse(
                    status_code=403,
                    content=error_envelope("FORBIDDEN", "You can only update your own sessions"),
                )

            set_clauses = ["updated_at = NOW()", "last_accessed_at = NOW()"]
            params = []

            if "session_data" in body:
                set_clauses.append("session_data = %s::jsonb")
                params.append(json.dumps(body["session_data"]))

            if "status" in body:
                new_status = body["status"]
                if new_status not in VALID_STATUSES:
                    return JSONResponse(
                        status_code=400,
                        content=error_envelope("VALIDATION_ERROR", "status must be one of: %s" % ", ".join(VALID_STATUSES)),
                    )
                set_clauses.append("status = %s")
                params.append(new_status)

            if "metadata" in body:
                set_clauses.append("metadata = %s::jsonb")
                params.append(json.dumps(body["metadata"]))

            params.extend([session_id, ws_id])
            sql = "UPDATE workbook_sessions SET %s WHERE id = %%s AND workspace_id = %%s RETURNING %s" % (
                ", ".join(set_clauses), SESSION_SELECT,
            )
            cur.execute(sql, params)
            row = cur.fetchone()

            if "status" in body and body["status"] in ("archived", "deleted"):
                event_type = "SESSION_ARCHIVED" if body["status"] == "archived" else "SESSION_DELETED"
                emit_audit_event(
                    cur,
                    workspace_id=ws_id,
                    event_type=event_type,
                    actor_id=auth.user_id,
                    actor_role=auth.role,
                    resource_type="workbook_session",
                    resource_id=session_id,
                )

        conn.commit()
        return envelope(_row_to_dict(row, SESSION_COLUMNS))
    except Exception as e:
        logger.error("update_session error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.delete("/workspaces/{ws_id}/sessions/{session_id}")
def delete_session(ws_id: str, session_id: str, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id FROM workbook_sessions WHERE id = %s AND workspace_id = %s",
                (session_id, ws_id),
            )
            existing = cur.fetchone()

            if not existing:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Session not found: %s" % session_id),
                )

            if existing[1] != auth.user_id:
                return JSONResponse(
                    status_code=403,
                    content=error_envelope("FORBIDDEN", "You can only delete your own sessions"),
                )

            cur.execute(
                """UPDATE workbook_sessions SET status = 'deleted', updated_at = NOW()
                   WHERE id = %s RETURNING """ + SESSION_SELECT,
                (session_id,),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="SESSION_DELETED",
                actor_id=auth.user_id,
                actor_role=auth.role,
                resource_type="workbook_session",
                resource_id=session_id,
            )
        conn.commit()
        return envelope(_row_to_dict(row, SESSION_COLUMNS))
    except Exception as e:
        logger.error("delete_session error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.delete("/workspaces/{ws_id}/sessions")
def clear_archived_sessions(ws_id: str, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE workbook_sessions SET status = 'deleted', updated_at = NOW()
                   WHERE user_id = %s AND workspace_id = %s AND status = 'archived'""",
                (auth.user_id, ws_id),
            )
            count = cur.rowcount

            if count > 0:
                emit_audit_event(
                    cur,
                    workspace_id=ws_id,
                    event_type="SESSION_DELETED",
                    actor_id=auth.user_id,
                    actor_role=auth.role,
                    detail={"action": "clear_archived", "count": count},
                )
        conn.commit()
        return envelope({"deleted_count": count})
    except Exception as e:
        logger.error("clear_archived_sessions error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
