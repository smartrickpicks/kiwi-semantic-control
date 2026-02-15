"""
Tests for Preflight Engine thresholds and gate logic.
Run: python scripts/test_preflight.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.preflight_engine import (
    classify_page, classify_document, compute_text_metrics,
    compute_gate, derive_cache_identity, run_preflight
)

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
        print("  PASS: %s" % name)
    else:
        failed += 1
        print("  FAIL: %s — expected %s, got %s" % (name, expected, actual))

print("=== Page Classification ===")
check("searchable: 100 chars, 0.0 images", classify_page(100, 0.0), "SEARCHABLE")
check("searchable: 50 chars, 0.70 images", classify_page(50, 0.70), "SEARCHABLE")
check("scanned: 10 chars, 0.80 images", classify_page(10, 0.80), "SCANNED")
check("scanned: 0 chars, 0.30 images", classify_page(0, 0.30), "SCANNED")
check("mixed: 100 chars, 0.80 images", classify_page(100, 0.80), "MIXED")
check("mixed: 10 chars, 0.20 images", classify_page(10, 0.20), "MIXED")
check("boundary: 49 chars, 0.29 images", classify_page(49, 0.29), "MIXED")
check("boundary: 50 chars, 0.71 images", classify_page(50, 0.71), "MIXED")

print("\n=== Document Classification ===")
check("all searchable", classify_document(["SEARCHABLE"] * 10), "SEARCHABLE")
check("all scanned", classify_document(["SCANNED"] * 10), "SCANNED")
check("80% searchable", classify_document(["SEARCHABLE"] * 8 + ["MIXED"] * 2), "SEARCHABLE")
check("80% scanned", classify_document(["SCANNED"] * 8 + ["MIXED"] * 2), "SCANNED")
check("79% searchable (mixed)", classify_document(["SEARCHABLE"] * 79 + ["MIXED"] * 21), "MIXED")
check("50/50 mixed", classify_document(["SEARCHABLE"] * 5 + ["SCANNED"] * 5), "MIXED")
check("empty", classify_document([]), "MIXED")

print("\n=== Text Metrics ===")
r1, c1 = compute_text_metrics(["hello world"])
check("clean text replacement", r1, 0.0)
check("clean text control", c1, 0.0)
r2, c2 = compute_text_metrics(["\ufffd" * 6 + "x" * 94])
check("6% replacement (>5% threshold)", r2 > 0.05, True)
r3, c3 = compute_text_metrics([chr(1) * 4 + "x" * 96])
check("4% control (>3% threshold)", c3 > 0.03, True)
r4, c4 = compute_text_metrics([""])
check("empty text replacement", r4, 0.0)
check("empty text control", c4, 0.0)

print("\n=== Gate Computation ===")
g1, reasons1 = compute_gate("SEARCHABLE", 0.0, 0.0, 500, [500] * 10)
check("clean doc = GREEN", g1, "GREEN")
g2, reasons2 = compute_gate("SEARCHABLE", 0.06, 0.0, 500, [500] * 10)
check("high replacement = RED", g2, "RED")
check("RED has replacement reason", "replacement_char_ratio_exceeded" in reasons2[0], True)
g3, reasons3 = compute_gate("SEARCHABLE", 0.0, 0.04, 500, [500] * 10)
check("high control = RED", g3, "RED")
g4, reasons4 = compute_gate("MIXED", 0.0, 0.0, 500, [500] * 10)
check("mixed mode = YELLOW", g4, "YELLOW")
g5, reasons5 = compute_gate("SEARCHABLE", 0.0, 0.0, 20, [20] * 10)
check("low avg chars = YELLOW", g5, "YELLOW")
g6, reasons6 = compute_gate("SEARCHABLE", 0.0, 0.0, 500, [5] * 9 + [5000])
check("sparse pages = YELLOW", g6, "YELLOW")

print("\n=== Cache Identity ===")
id1 = derive_cache_identity("ws_123", "https://example.com/doc.pdf")
id2 = derive_cache_identity("ws_123", "https://example.com/doc.pdf")
id3 = derive_cache_identity("ws_456", "https://example.com/doc.pdf")
check("deterministic same input", id1, id2)
check("different workspace different id", id1 != id3, True)
check("starts with doc_derived_", id1.startswith("doc_derived_"), True)

print("\n=== Full Preflight Run ===")
result = run_preflight([
    {"page": 1, "text": "Hello world " * 100, "image_coverage_ratio": 0.1},
    {"page": 2, "text": "More text " * 100, "image_coverage_ratio": 0.2},
])
check("run returns GREEN for good text", result["gate_color"], "GREEN")
check("run returns SEARCHABLE mode", result["doc_mode"], "SEARCHABLE")
check("run has 2 pages", result["metrics"]["total_pages"], 2)

empty_result = run_preflight([])
check("empty run returns RED", empty_result["gate_color"], "RED")

scanned_result = run_preflight([
    {"page": 1, "text": "", "char_count": 0, "image_coverage_ratio": 0.9},
    {"page": 2, "text": "", "char_count": 0, "image_coverage_ratio": 0.95},
])
check("scanned doc mode", scanned_result["doc_mode"], "SCANNED")

print("\n=== Results ===")
print("Passed: %d, Failed: %d" % (passed, failed))
if failed > 0:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
