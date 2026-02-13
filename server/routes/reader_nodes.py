import hashlib
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.ulid import generate_id
from server.api_v25 import envelope, error_envelope
from server.auth import AuthClass, require_auth
from server.audit import emit_audit_event
from server.feature_flags import require_evidence_inspector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


def _deterministic_node_id(document_id, page_number, block_index):
    raw = "%s|%d|%d" % (document_id, page_number, block_index)
    return "rn_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _detect_quality(nodes, page_count):
    if not nodes or page_count == 0:
        return "missing_text_layer"
    total_text = sum(len(n.get("text", "")) for n in nodes)
    if total_text == 0:
        return "missing_text_layer"
    mojibake_chars = 0
    for n in nodes:
        txt = n.get("text", "")
        for ch in txt:
            if ord(ch) > 0xFFFD or (0xFFF0 <= ord(ch) <= 0xFFFD):
                mojibake_chars += 1
    ratio = mojibake_chars / max(total_text, 1)
    if ratio > 0.15:
        return "unreadable"
    if ratio > 0.02:
        return "suspect_mojibake"
    return "ok"


CACHE_COLUMNS = [
    "id", "document_id", "source_pdf_hash", "ocr_version",
    "quality_flag", "nodes", "page_count", "created_at", "metadata",
]
CACHE_SELECT = ", ".join(CACHE_COLUMNS)


@router.get("/documents/{doc_id}/reader-nodes")
def get_reader_nodes(
    doc_id: str,
    source_pdf_hash: str = Query(None),
    ocr_version: str = Query("v1"),
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth
    gate = require_evidence_inspector()
    if gate:
        return gate

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM documents WHERE id = %s AND deleted_at IS NULL",
                (doc_id,),
            )
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Document not found: %s" % doc_id),
                )

            if source_pdf_hash:
                cur.execute(
                    "SELECT %s FROM reader_node_cache WHERE document_id = %%s AND source_pdf_hash = %%s AND ocr_version = %%s" % CACHE_SELECT,
                    (doc_id, source_pdf_hash, ocr_version),
                )
                row = cur.fetchone()
                if row:
                    data = _row_to_dict(row, CACHE_COLUMNS)
                    data["cached"] = True
                    return envelope(data)

            return envelope({
                "document_id": doc_id,
                "nodes": [],
                "quality_flag": "missing_text_layer",
                "page_count": 0,
                "cached": False,
            })
    except Exception as e:
        logger.error("get_reader_nodes error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.put("/documents/{doc_id}/reader-nodes")
def upsert_reader_nodes(
    doc_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth
    gate = require_evidence_inspector()
    if gate:
        return gate

    source_pdf_hash = body.get("source_pdf_hash")
    ocr_version = body.get("ocr_version", "v1")
    raw_nodes = body.get("nodes", [])
    page_count = body.get("page_count", 0)

    if not source_pdf_hash:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "source_pdf_hash is required"),
        )

    nodes = []
    for i, rn in enumerate(raw_nodes):
        pg = rn.get("page_number", 1)
        block_idx = rn.get("block_index", i)
        node_id = _deterministic_node_id(doc_id, pg, block_idx)
        nodes.append({
            "node_id": node_id,
            "page_number": pg,
            "block_index": block_idx,
            "text": rn.get("text", ""),
            "bbox": rn.get("bbox"),
        })

    quality_flag = body.get("quality_flag") or _detect_quality(nodes, page_count)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, workspace_id FROM documents WHERE id = %s AND deleted_at IS NULL",
                (doc_id,),
            )
            doc_row = cur.fetchone()
            if not doc_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Document not found: %s" % doc_id),
                )
            workspace_id = doc_row[1]

            cache_id = generate_id("doc_")
            cur.execute(
                """INSERT INTO reader_node_cache
                   (id, document_id, source_pdf_hash, ocr_version, quality_flag, nodes, page_count, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, '{}'::jsonb)
                   ON CONFLICT ON CONSTRAINT reader_cache_key
                   DO UPDATE SET
                     quality_flag = EXCLUDED.quality_flag,
                     nodes = EXCLUDED.nodes,
                     page_count = EXCLUDED.page_count,
                     updated_at = NOW()
                   RETURNING """ + CACHE_SELECT,
                (cache_id, doc_id, source_pdf_hash, ocr_version, quality_flag,
                 json.dumps(nodes), page_count),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="reader_node_cache.upserted",
                actor_id=auth.user_id,
                resource_type="reader_node_cache",
                resource_id=row[0],
                detail={
                    "document_id": doc_id,
                    "source_pdf_hash": source_pdf_hash,
                    "ocr_version": ocr_version,
                    "quality_flag": quality_flag,
                    "node_count": len(nodes),
                    "page_count": page_count,
                },
            )
        conn.commit()

        data = _row_to_dict(row, CACHE_COLUMNS)
        data["cached"] = True
        return envelope(data)
    except Exception as e:
        logger.error("upsert_reader_nodes error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
