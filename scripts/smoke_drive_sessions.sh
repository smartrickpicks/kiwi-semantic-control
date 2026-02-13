#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:5000/api/v2.5"
PASS=0
FAIL=0
TOTAL=0

ok()   { PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); echo "  FAIL: $1 — $2" >&2; }

echo "=== Drive + Session Smoke Tests ==="
echo ""

WS_ID="ws_SEED0100000000000000000000"
USER_ID="usr_01KMCG0100000000000000KYLE"

TOKEN_RESP=$(curl -s -X POST "$BASE/auth/google/verify" \
  -H "Content-Type: application/json" \
  -d "{\"credential\":\"$USER_ID\",\"workspace_id\":\"$WS_ID\"}")

TOKEN=$(echo "$TOKEN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('token',''))" 2>/dev/null || echo "")
if [ -z "$TOKEN" ]; then
  TOKEN="$USER_ID"
fi
AUTH="Authorization: Bearer $TOKEN"

echo "--- Migration Evidence ---"

TABLES=$(curl -s "$BASE/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
if [ "$TABLES" = "ok" ]; then
  ok "T-MIG-01: Health check passes (DB connected)"
else
  fail "T-MIG-01" "Health check failed"
fi

echo ""
echo "--- Session Continuity Tests ---"

RESP=$(curl -s -X POST "$BASE/workspaces/$WS_ID/sessions" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"environment":"sandbox","source_type":"local","source_ref":"contracts.xlsx","session_data":{"sheet":"Sheet1"}}')
STATUS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('status',''))" 2>/dev/null)
SID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)
HTTP_CREATED=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('wbs_' in d.get('data',{}).get('id',''))" 2>/dev/null)

if [ "$STATUS" = "active" ] && [ "$HTTP_CREATED" = "True" ]; then
  ok "T-SES-01: Create session for local file (status=active, id=wbs_*)"
else
  fail "T-SES-01" "Expected active session with wbs_ prefix: $RESP"
fi

RESP2=$(curl -s -X POST "$BASE/workspaces/$WS_ID/sessions" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"environment":"sandbox","source_type":"local","source_ref":"contracts.xlsx","session_data":{"sheet":"Sheet2"}}')
SID2=$(echo "$RESP2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)

if [ "$SID" = "$SID2" ]; then
  ok "T-SES-02: Dedupe — same file returns same session (no duplicate)"
else
  fail "T-SES-02" "Expected same session ID ($SID), got $SID2"
fi

RESP3=$(curl -s -X POST "$BASE/workspaces/$WS_ID/sessions" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"environment":"sandbox","source_type":"local","source_ref":"billing.xlsx"}')
SID3=$(echo "$RESP3" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)

if [ "$SID" != "$SID3" ] && [ -n "$SID3" ]; then
  ok "T-SES-03: Different file creates new session"
else
  fail "T-SES-03" "Expected different session ID"
fi

RESP4=$(curl -s -X POST "$BASE/workspaces/$WS_ID/sessions" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"environment":"production","source_type":"local","source_ref":"contracts.xlsx"}')
SID4=$(echo "$RESP4" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)

if [ "$SID" != "$SID4" ] && [ -n "$SID4" ]; then
  ok "T-SES-04: Different environment creates new session"
else
  fail "T-SES-04" "Expected different session for production env"
fi

RESP5=$(curl -s -X POST "$BASE/workspaces/$WS_ID/sessions" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"environment":"sandbox","source_type":"drive","source_ref":"DRIVE_FILE_123"}')
SID5=$(echo "$RESP5" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)
ST5=$(echo "$RESP5" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('source_type',''))" 2>/dev/null)

if [ "$ST5" = "drive" ] && [ "$SID" != "$SID5" ]; then
  ok "T-SES-06: Drive source creates separate session"
else
  fail "T-SES-06" "Expected drive session distinct from local"
fi

RESP6=$(curl -s -X POST "$BASE/workspaces/$WS_ID/sessions" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"environment":"sandbox","source_type":"drive","source_ref":"DRIVE_FILE_123"}')
SID6=$(echo "$RESP6" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null)

if [ "$SID5" = "$SID6" ]; then
  ok "T-SES-07: Dedupe — same Drive file returns same session"
else
  fail "T-SES-07" "Expected same session for same Drive file"
fi

echo ""
echo "--- Auto-Resume Tests ---"

ACTIVE=$(curl -s "$BASE/workspaces/$WS_ID/sessions/active?environment=sandbox" -H "$AUTH")
ACTIVE_ID=$(echo "$ACTIVE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id','') if d.get('data') else 'null')" 2>/dev/null)

if [ -n "$ACTIVE_ID" ] && [ "$ACTIVE_ID" != "null" ]; then
  ok "T-RES-01: GET /sessions/active returns most recent active session"
else
  fail "T-RES-01" "Expected active session, got: $ACTIVE"
fi

curl -s -X PATCH "$BASE/workspaces/$WS_ID/sessions/$SID" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"session_data":{"sheet":"UpdatedSheet","auto_save":true}}' > /dev/null

UPDATED=$(curl -s "$BASE/workspaces/$WS_ID/sessions/active?environment=sandbox" -H "$AUTH")
UPDATED_DATA=$(echo "$UPDATED" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('session_data',{}).get('auto_save',''))" 2>/dev/null)

if [ "$UPDATED_DATA" = "True" ]; then
  ok "T-RES-08: PATCH /sessions/{id} updates session_data (auto-save)"
else
  fail "T-RES-08" "Expected session_data to be updated"
fi

echo ""
echo "--- Session Controls ---"

curl -s -X PATCH "$BASE/workspaces/$WS_ID/sessions/$SID3" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"status":"archived"}' > /dev/null

ARCHIVED=$(curl -s "$BASE/workspaces/$WS_ID/sessions?status=archived&environment=sandbox" -H "$AUTH")
ARC_COUNT=$(echo "$ARCHIVED" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null)

if [ "$ARC_COUNT" -ge 1 ]; then
  ok "T-CTRL-01: Archive session works"
else
  fail "T-CTRL-01" "Expected at least 1 archived session"
fi

curl -s -X DELETE "$BASE/workspaces/$WS_ID/sessions/$SID4" -H "$AUTH" > /dev/null
DELETED=$(curl -s "$BASE/workspaces/$WS_ID/sessions?status=deleted&environment=production" -H "$AUTH")
DEL_COUNT=$(echo "$DELETED" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null)

if [ "$DEL_COUNT" -ge 1 ]; then
  ok "T-CTRL-02: Soft-delete session works"
else
  fail "T-CTRL-02" "Expected at least 1 deleted session"
fi

echo ""
echo "--- Drive Status Tests ---"

DSTATUS=$(curl -s "$BASE/workspaces/$WS_ID/drive/status" -H "$AUTH")
CONNECTED=$(echo "$DSTATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('connected',''))" 2>/dev/null)

if [ "$CONNECTED" = "False" ]; then
  ok "T-DRV-01: Drive status shows not connected (no connection yet)"
else
  fail "T-DRV-01" "Expected connected=False, got: $DSTATUS"
fi

echo ""
echo "--- Drive Import History (no imports yet) ---"

HIST=$(curl -s "$BASE/workspaces/$WS_ID/drive/import-history?source_file_id=NONEXISTENT" -H "$AUTH")
HIST_COUNT=$(echo "$HIST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null)

if [ "$HIST_COUNT" = "0" ]; then
  ok "T-VER-HIST: Import history returns empty for nonexistent file"
else
  fail "T-VER-HIST" "Expected 0 items, got $HIST_COUNT"
fi

echo ""
echo "--- Validation Tests ---"

BAD_ENV=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/workspaces/$WS_ID/sessions" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"environment":"invalid","source_type":"local","source_ref":"test.xlsx"}')

if [ "$BAD_ENV" = "400" ]; then
  ok "T-VAL-01: Invalid environment returns 400"
else
  fail "T-VAL-01" "Expected 400, got $BAD_ENV"
fi

BAD_SRC=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/workspaces/$WS_ID/sessions" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"environment":"sandbox","source_type":"ftp","source_ref":"test.xlsx"}')

if [ "$BAD_SRC" = "400" ]; then
  ok "T-VAL-02: Invalid source_type returns 400"
else
  fail "T-VAL-02" "Expected 400, got $BAD_SRC"
fi

NO_REF=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/workspaces/$WS_ID/sessions" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"environment":"sandbox","source_type":"local","source_ref":""}')

if [ "$NO_REF" = "400" ]; then
  ok "T-VAL-03: Empty source_ref returns 400"
else
  fail "T-VAL-03" "Expected 400, got $NO_REF"
fi

NOAUTH=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/workspaces/$WS_ID/sessions/active")

if [ "$NOAUTH" = "401" ]; then
  ok "T-VAL-04: Unauthenticated request returns 401"
else
  fail "T-VAL-04" "Expected 401, got $NOAUTH"
fi

echo ""
echo "==================================="
echo "Results: $PASS/$TOTAL passed, $FAIL failed"

if [ $FAIL -gt 0 ]; then
  exit 1
fi
echo "ALL SMOKE TESTS PASSED"
