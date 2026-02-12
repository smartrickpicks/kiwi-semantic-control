import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from server.db import get_conn, put_conn
from server.api_v25 import envelope, error_envelope
from server.jwt_utils import sign_jwt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2.5/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")


@router.post("/google/verify")
async def verify_google_token(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    credential = body.get("credential", "").strip()
    workspace_id = body.get("workspace_id", "").strip()

    if not credential:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Missing 'credential' (Google ID token)"),
        )

    if not workspace_id:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Missing 'workspace_id'"),
        )

    if not GOOGLE_CLIENT_ID:
        return JSONResponse(
            status_code=500,
            content=error_envelope("CONFIG_ERROR", "Google OAuth is not configured on the server"),
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        logger.warning("Google token verification failed: %s", e)
        return JSONResponse(
            status_code=401,
            content=error_envelope("UNAUTHORIZED", "Invalid Google ID token"),
        )

    google_email = idinfo.get("email", "").strip().lower()
    google_sub = idinfo.get("sub", "")
    google_name = idinfo.get("name", "")
    google_picture = idinfo.get("picture", "")

    if not google_email:
        return JSONResponse(
            status_code=401,
            content=error_envelope("UNAUTHORIZED", "Google token missing email claim"),
        )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, display_name, status FROM users WHERE LOWER(email) = %s",
                (google_email,),
            )
            user_row = cur.fetchone()

            if not user_row:
                return JSONResponse(
                    status_code=403,
                    content=error_envelope(
                        "FORBIDDEN",
                        "Not authorized for this workspace. Contact your administrator.",
                    ),
                )

            user_id, user_email, display_name, user_status = user_row

            if user_status != "active":
                return JSONResponse(
                    status_code=403,
                    content=error_envelope(
                        "FORBIDDEN",
                        "Your account is inactive. Contact your administrator.",
                    ),
                )

            cur.execute(
                "SELECT role FROM user_workspace_roles WHERE user_id = %s AND workspace_id = %s",
                (user_id, workspace_id),
            )
            role_row = cur.fetchone()

            if not role_row:
                return JSONResponse(
                    status_code=403,
                    content=error_envelope(
                        "FORBIDDEN",
                        "Not authorized for this workspace. No role assigned.",
                    ),
                )

            role = role_row[0]

            cur.execute(
                """UPDATE users SET google_sub = %s, avatar_url = COALESCE(avatar_url, %s),
                   display_name = COALESCE(display_name, %s), updated_at = NOW()
                   WHERE id = %s""",
                (google_sub, google_picture, google_name, user_id),
            )
        conn.commit()

        app_token = sign_jwt({
            "sub": user_id,
            "email": user_email,
            "name": display_name or google_name,
            "role": role,
            "workspace_id": workspace_id,
        })

        return JSONResponse(
            status_code=200,
            content=envelope({
                "token": app_token,
                "user": {
                    "id": user_id,
                    "email": user_email,
                    "display_name": display_name or google_name,
                    "avatar_url": google_picture,
                    "role": role,
                    "workspace_id": workspace_id,
                },
            }),
        )

    except Exception as e:
        conn.rollback()
        logger.error("Google auth error: %s", e)
        return JSONResponse(
            status_code=500,
            content=error_envelope("INTERNAL_ERROR", "Authentication processing failed"),
        )
    finally:
        put_conn(conn)


@router.get("/config")
async def get_auth_config():
    return JSONResponse(
        status_code=200,
        content=envelope({
            "google_client_id": GOOGLE_CLIENT_ID or None,
            "configured": bool(GOOGLE_CLIENT_ID),
        }),
    )


@router.get("/me")
async def get_current_user(request: Request):
    from server.auth import resolve_auth
    auth_result, auth_type = resolve_auth(request)

    if auth_result is None:
        return JSONResponse(
            status_code=401,
            content=error_envelope("UNAUTHORIZED", "Authentication required"),
        )

    return JSONResponse(
        status_code=200,
        content=envelope({
            "user_id": auth_result.user_id,
            "email": auth_result.email,
            "display_name": auth_result.display_name,
            "role": auth_result.role,
            "workspace_id": auth_result.workspace_id,
        }),
    )
