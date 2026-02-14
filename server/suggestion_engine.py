import re
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

DOCUMENT_TYPE_KEYWORDS = {
    "financial": [
        "payment", "revenue", "royalty", "rate", "amount", "fee", "cost",
        "price", "billing", "invoice", "currency", "term", "frequency",
    ],
    "identity": [
        "account", "name", "contact", "email", "phone", "address",
        "city", "state", "country", "zip", "postal",
    ],
    "contract": [
        "contract", "agreement", "effective", "expiration", "start", "end",
        "status", "type", "category", "opportunity", "deal",
    ],
    "catalog": [
        "title", "artist", "album", "track", "isrc", "upc", "label",
        "genre", "release", "catalog", "territory", "rights",
    ],
}


def normalize_field_name(name):
    s = name.strip()
    s = re.sub(r'__c$', '', s)
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    s = s.replace('_', ' ').replace('-', ' ')
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s


def _levenshtein_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()


def _keyword_score(source_norm, term_key_norm, term_category):
    keywords = DOCUMENT_TYPE_KEYWORDS.get(term_category, [])
    if not keywords:
        return 0.0
    source_words = set(source_norm.split())
    matched = sum(1 for kw in keywords if kw in source_words)
    term_words = set(term_key_norm.split())
    overlap = len(source_words & term_words)
    base = matched * 0.1
    boost = overlap * 0.15
    return min(base + boost, 0.6)


def generate_suggestions(cur, workspace_id, document_id):
    cur.execute(
        "SELECT metadata FROM documents WHERE id = %s AND workspace_id = %s AND deleted_at IS NULL",
        (document_id, workspace_id),
    )
    doc_row = cur.fetchone()
    if not doc_row:
        return []

    doc_meta = doc_row[0] if doc_row[0] else {}
    source_fields = doc_meta.get("column_headers", [])

    if not source_fields:
        logger.info("[SUGGEST] No column_headers in document %s metadata", document_id)
        return []

    cur.execute(
        """SELECT id, field_key, display_name, category
           FROM glossary_terms
           WHERE workspace_id = %s AND deleted_at IS NULL""",
        (workspace_id,),
    )
    terms = cur.fetchall()
    if not terms:
        logger.info("[SUGGEST] No glossary terms found for workspace %s", workspace_id)
        return []

    term_list = []
    for t in terms:
        term_list.append({
            "id": t[0],
            "field_key": t[1],
            "display_name": t[2] or t[1],
            "category": t[3] or "",
            "normalized": normalize_field_name(t[1]),
        })

    cur.execute(
        """SELECT normalized_alias, term_id
           FROM glossary_aliases
           WHERE workspace_id = %s AND deleted_at IS NULL""",
        (workspace_id,),
    )
    alias_map = {}
    for row in cur.fetchall():
        alias_map[row[0]] = row[1]

    suggestions = []
    for source_field in source_fields:
        source_norm = normalize_field_name(source_field)

        alias_term_id = alias_map.get(source_norm)
        if alias_term_id:
            term_match = next((t for t in term_list if t["id"] == alias_term_id), None)
            if term_match:
                suggestions.append({
                    "source_field": source_field,
                    "suggested_term_id": term_match["id"],
                    "match_score": 1.0,
                    "match_method": "exact",
                    "candidates": [{
                        "term_id": term_match["id"],
                        "score": 1.0,
                        "method": "exact",
                    }],
                })
                continue

        candidates = []
        for term in term_list:
            exact_check = source_norm == term["normalized"]
            if exact_check:
                candidates.append({
                    "term_id": term["id"],
                    "score": 1.0,
                    "method": "exact",
                })
                continue

            fuzzy_score = _levenshtein_ratio(source_norm, term["normalized"])
            if fuzzy_score >= 0.6:
                candidates.append({
                    "term_id": term["id"],
                    "score": round(fuzzy_score, 3),
                    "method": "fuzzy",
                })
                continue

            kw_score = _keyword_score(source_norm, term["normalized"], term["category"])
            if kw_score >= 0.2:
                candidates.append({
                    "term_id": term["id"],
                    "score": round(kw_score, 3),
                    "method": "keyword",
                })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        top3 = candidates[:3]

        if top3:
            best = top3[0]
            suggestions.append({
                "source_field": source_field,
                "suggested_term_id": best["term_id"],
                "match_score": best["score"],
                "match_method": best["method"],
                "candidates": top3,
            })
        else:
            suggestions.append({
                "source_field": source_field,
                "suggested_term_id": None,
                "match_score": 0.0,
                "match_method": "none",
                "candidates": [],
            })

    return suggestions
