"""
Deterministic Preflight Engine for Orchestrate OS.

Locked thresholds (P1E):
  Page mode:
    SEARCHABLE: chars_on_page >= 50 AND image_coverage_ratio <= 0.70
    SCANNED:    chars_on_page < 50 AND image_coverage_ratio >= 0.30
    else MIXED

  Doc mode aggregation:
    SEARCHABLE: >= 80% pages are SEARCHABLE
    SCANNED:    >= 80% pages are SCANNED
    else MIXED

  Gate:
    RED:    replacement_char_ratio > 0.05 OR control_char_ratio > 0.03
    YELLOW: not RED AND (doc_mode == MIXED OR avg_chars_per_page < 30 OR >80% pages have <10 chars)
    GREEN:  otherwise
"""
import hashlib
import logging
import re

logger = logging.getLogger(__name__)

# --- Locked page mode thresholds ---
PAGE_CHARS_MIN_SEARCHABLE = 50
PAGE_IMAGE_MAX_SEARCHABLE = 0.70
PAGE_CHARS_MAX_SCANNED = 50
PAGE_IMAGE_MIN_SCANNED = 0.30

# --- Locked doc mode thresholds ---
DOC_MODE_SUPERMAJORITY = 0.80

# --- Locked gate thresholds ---
GATE_RED_REPLACEMENT_RATIO = 0.05
GATE_RED_CONTROL_RATIO = 0.03
GATE_YELLOW_AVG_CHARS = 30
GATE_YELLOW_SPARSE_RATIO = 0.80
GATE_YELLOW_SPARSE_CHARS = 10


def classify_page(chars_on_page, image_coverage_ratio):
    """Classify a single page as SEARCHABLE, SCANNED, or MIXED."""
    if chars_on_page >= PAGE_CHARS_MIN_SEARCHABLE and image_coverage_ratio <= PAGE_IMAGE_MAX_SEARCHABLE:
        return "SEARCHABLE"
    if chars_on_page < PAGE_CHARS_MAX_SCANNED and image_coverage_ratio >= PAGE_IMAGE_MIN_SCANNED:
        return "SCANNED"
    return "MIXED"


def classify_document(page_modes):
    """Aggregate page modes into a document-level mode."""
    if not page_modes:
        return "MIXED"
    total = len(page_modes)
    searchable_count = sum(1 for m in page_modes if m == "SEARCHABLE")
    scanned_count = sum(1 for m in page_modes if m == "SCANNED")
    if searchable_count / total >= DOC_MODE_SUPERMAJORITY:
        return "SEARCHABLE"
    if scanned_count / total >= DOC_MODE_SUPERMAJORITY:
        return "SCANNED"
    return "MIXED"


def compute_text_metrics(pages_text):
    """Compute replacement_char_ratio, control_char_ratio from extracted text list."""
    total_chars = 0
    replacement_chars = 0
    control_chars = 0
    for text in pages_text:
        total_chars += len(text)
        replacement_chars += text.count('\ufffd')
        for ch in text:
            code = ord(ch)
            if code < 32 and code not in (9, 10, 13):
                control_chars += 1
    if total_chars == 0:
        return 0.0, 0.0
    return replacement_chars / total_chars, control_chars / total_chars


def compute_gate(doc_mode, replacement_char_ratio, control_char_ratio,
                 avg_chars_per_page, page_char_counts, pages_text=None):
    """
    Compute gate color and reason codes.
    RED is evaluated immediately — must short-circuit before YELLOW.
    Returns (gate_color, reasons) where reasons is a list of strings.
    """
    reasons = []

    # RED checks (immediate)
    if replacement_char_ratio > GATE_RED_REPLACEMENT_RATIO:
        reasons.append("replacement_char_ratio_exceeded:%.4f>%.4f" % (replacement_char_ratio, GATE_RED_REPLACEMENT_RATIO))
    if control_char_ratio > GATE_RED_CONTROL_RATIO:
        reasons.append("control_char_ratio_exceeded:%.4f>%.4f" % (control_char_ratio, GATE_RED_CONTROL_RATIO))
    if reasons:
        return "RED", reasons

    # YELLOW checks
    if doc_mode == "MIXED":
        reasons.append("doc_mode_mixed")
    if avg_chars_per_page < GATE_YELLOW_AVG_CHARS:
        reasons.append("avg_chars_per_page_low:%.1f<%d" % (avg_chars_per_page, GATE_YELLOW_AVG_CHARS))
    if page_char_counts:
        sparse_pages = sum(1 for c in page_char_counts if c < GATE_YELLOW_SPARSE_CHARS)
        sparse_ratio = sparse_pages / len(page_char_counts)
        if sparse_ratio > GATE_YELLOW_SPARSE_RATIO:
            reasons.append("sparse_pages_exceeded:%.2f>%.2f" % (sparse_ratio, GATE_YELLOW_SPARSE_RATIO))
    if reasons:
        return "YELLOW", reasons

    return "GREEN", ["all_checks_passed"]


def derive_cache_identity(workspace_id, file_url):
    """Generate deterministic doc identity when doc_id is missing."""
    raw = "%s|%s" % (workspace_id or "", file_url or "")
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return "doc_derived_%s" % h


def run_preflight(pages_data):
    """
    Run full preflight analysis on extracted page data.
    
    pages_data: list of dicts with keys:
      - page (int): 1-indexed page number
      - text (str): extracted text
      - char_count (int, optional): precomputed char count
      - image_coverage_ratio (float, optional): 0.0-1.0, defaults to 0.0
    
    Returns dict with:
      - doc_mode
      - gate_color
      - gate_reasons
      - page_classifications: list of per-page results
      - metrics: computed metrics
    """
    if not pages_data:
        return {
            "doc_mode": "MIXED",
            "gate_color": "RED",
            "gate_reasons": ["no_pages"],
            "page_classifications": [],
            "metrics": {},
        }

    page_modes = []
    page_char_counts = []
    pages_text = []
    page_results = []

    for p in pages_data:
        text = p.get("text", "")
        char_count = p.get("char_count", len(text))
        image_ratio = p.get("image_coverage_ratio", 0.0)
        mode = classify_page(char_count, image_ratio)
        page_modes.append(mode)
        page_char_counts.append(char_count)
        pages_text.append(text)
        page_results.append({
            "page": p.get("page", 0),
            "mode": mode,
            "char_count": char_count,
            "image_coverage_ratio": image_ratio,
        })

    doc_mode = classify_document(page_modes)
    replacement_ratio, control_ratio = compute_text_metrics(pages_text)
    total_chars = sum(page_char_counts)
    avg_chars = total_chars / len(page_char_counts) if page_char_counts else 0.0

    gate_color, gate_reasons = compute_gate(
        doc_mode, replacement_ratio, control_ratio,
        avg_chars, page_char_counts, pages_text
    )

    return {
        "doc_mode": doc_mode,
        "gate_color": gate_color,
        "gate_reasons": gate_reasons,
        "page_classifications": page_results,
        "metrics": {
            "total_pages": len(pages_data),
            "total_chars": total_chars,
            "avg_chars_per_page": round(avg_chars, 2),
            "replacement_char_ratio": round(replacement_ratio, 6),
            "control_char_ratio": round(control_ratio, 6),
            "searchable_pages": sum(1 for m in page_modes if m == "SEARCHABLE"),
            "scanned_pages": sum(1 for m in page_modes if m == "SCANNED"),
            "mixed_pages": sum(1 for m in page_modes if m == "MIXED"),
        },
    }
