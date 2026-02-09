# Pre-Flight Calibration Suite

Deterministic calibration tests for Orchestrate OS pre-flight detectors.

## Fixtures

| ID | Description |
|---|---|
| PF_PASS_BASELINE | Clean dataset, all known columns, no issues |
| PF_FAIL_UNKNOWN_WARN | 1-3 unknown columns (warning severity) |
| PF_FAIL_UNKNOWN_BLOCKER | >3 unknown columns (blocker severity) |
| PF_FAIL_OCR_UNREADABLE | Mojibake/encoding artifacts (OCR family) |
| PF_FAIL_DOCUMENT_TYPE | Missing document type values |
| PF_FAIL_LOW_CONFIDENCE | Low extraction confidence |
| PF_FAIL_MIXED | Multiple issues + meta/ref sheets (leakage test) |

## Policy Checks

- Unknown columns: >0 non-empty = warning, >3 non-empty = blocker
- Mojibake folded under OCR Unreadable family
- DOCUMENT_TYPE_MISSING registered as preflight blocker type
- No meta/glossary/internal sheet leakage into actionable queues

## Running

```bash
python3 scripts/preflight_calibration_runner.py
```

## Runtime Hooks

After injection:
- `window.runPreflightCalibration(fixtureId)` — run single fixture
- `window.runPreflightCalibrationSuite()` — run all fixtures

## Log Prefixes

- `[PREFLIGHT-CAL][RUN]` — execution events
- `[PREFLIGHT-CAL][RESULT]` — results and verdicts
