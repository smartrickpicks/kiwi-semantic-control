#!/usr/bin/env bash
# Replit smoke test: validate base+patch, run preview, json-aware diff vs expected
# Usage:
#   bash scripts/replit_smoke.sh               # strict (baseline; fails on any diff)
#   bash scripts/replit_smoke.sh --edge        # strict (edge-case pack)
#   bash scripts/replit_smoke.sh --allow-diff  # baseline; allows diff (prints warning)
#   bash scripts/replit_smoke.sh --edge --allow-diff  # edge-case pack + allow diff

set -euo pipefail

ALLOW_DIFF=0
EDGE=0

# Parse flags
while [[ $# -gt 0 ]]; do
  case "${1}" in
    --allow-diff)
      ALLOW_DIFF=1
      shift
      ;;
    --edge)
      EDGE=1
      shift
      ;;
    *)
      echo "Unknown argument: ${1}" >&2
      exit 2
      ;;
  esac
done

BASE="config/config_pack.base.json"
PATCH="config/config_pack.example.patch.json"

# Select dataset + expected according to mode
if [[ $EDGE -eq 1 ]]; then
  STD="examples/standardized_dataset.edge_cases.json"
  EXPECTED="examples/expected_outputs/sf_packet.edge_cases.json"
else
  STD="examples/standardized_dataset.example.json"
  EXPECTED="examples/expected_outputs/sf_packet.example.json"
fi

OUT="out/sf_packet.preview.json"

# 1) Validate configuration (shape + conflicts + base_version guard)
python3 local_runner/validate_config.py --base "$BASE" --patch "$PATCH"

# 2) Run deterministic offline preview
python3 local_runner/run_local.py \
  --base "$BASE" \
  --patch "$PATCH" \
  --standardized "$STD" \
  --out "$OUT"

echo "OK: preview wrote $OUT (mode: $([[ $EDGE -eq 1 ]] && echo edge || echo baseline))"

# 3) JSON-aware normalization and diff vs expected
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

OUT_NORM="$TMPDIR/out.norm.json"
EXP_NORM="$TMPDIR/exp.norm.json"

# Normalize JSON with sorted keys and compact separators for deterministic comparison
python3 - "$OUT" "$OUT_NORM" <<'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
with open(src, 'r', encoding='utf-8') as f:
    obj = json.load(f)
with open(dst, 'w', encoding='utf-8') as f:
    f.write(json.dumps(obj, sort_keys=True, separators=(',', ':')))
PY

python3 - "$EXPECTED" "$EXP_NORM" <<'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
with open(src, 'r', encoding='utf-8') as f:
    obj = json.load(f)
with open(dst, 'w', encoding='utf-8') as f:
    f.write(json.dumps(obj, sort_keys=True, separators=(',', ':')))
PY

set +e
DIFF_OUT="$(diff -u "$EXP_NORM" "$OUT_NORM")"
DIFF_STATUS=$?
set -e

if [[ $DIFF_STATUS -ne 0 ]]; then
  echo "" >&2
  echo "Smoke diff detected between expected and preview:" >&2
  echo "  expected: $EXPECTED" >&2
  echo "  actual  : $OUT" >&2
  echo "--- Unified diff (normalized) ---" >&2
  echo "$DIFF_OUT" >&2
  if [[ $ALLOW_DIFF -eq 1 ]]; then
    echo "WARN: Differences allowed by --allow-diff. Inspect and update expected output + CHANGELOG if intentional." >&2
    exit 0
  else
    echo "FAIL: Differences found. Fix determinism/schema in local_runner or update expected output + CHANGELOG with rationale." >&2
    exit 1
  fi
else
  echo "OK: preview output matches expected (normalized)."
fi
