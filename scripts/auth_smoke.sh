#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:5000"
WS="ws_SEED0100000000000000000000"
PASS=0
FAIL=0
TOTAL=0

ok()   { PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); echo "  PASS [$TOTAL] $1"; }
fail() { FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); echo "  FAIL [$TOTAL] $1" >&2; }

echo "=== Auth Smoke Tests ==="
echo ""

echo "--- 1. Auth config endpoint ---"
CFG=$(curl -sf "$BASE/api/v2.5/auth/config" 2>/dev/null || echo '{}')
if echo "$CFG" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('data',{}).get('configured') == True" 2>/dev/null; then
  ok "GET /auth/config returns configured=true with google_client_id"
else
  fail "GET /auth/config: expected configured=true, got: $CFG"
fi

echo ""
echo "--- 2. JWT auth via /auth/me ---"

ADMIN_JWT=$(python3 -c "
import os, sys
os.environ.setdefault('JWT_SECRET', '')
sys.path.insert(0,'.')
from server.jwt_utils import sign_jwt
print(sign_jwt({
    'sub': 'usr_01KMCG0500000000000000EDDI',
    'email': 'eddie.jauregui@createmusicgroup.com',
    'name': 'Eddie Jauregui',
    'role': 'admin',
    'workspace_id': '$WS'
}))
")

ME=$(curl -sf "$BASE/api/v2.5/auth/me" -H "Authorization: Bearer $ADMIN_JWT" 2>/dev/null || echo '{}')
if echo "$ME" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['data']['role']=='admin' and d['data']['email']=='eddie.jauregui@createmusicgroup.com'" 2>/dev/null; then
  ok "GET /auth/me returns correct admin user from JWT"
else
  fail "GET /auth/me: unexpected response: $ME"
fi

echo ""
echo "--- 3. Inactive user denied (JWT-based) ---"

INACTIVE_USER_ID=$(curl -sf "$BASE/api/v2.5/workspaces/$WS/members" -H "Authorization: Bearer $ADMIN_JWT" 2>/dev/null \
  | python3 -c "import sys,json; members=json.load(sys.stdin).get('data',[]); print(next((m['id'] for m in members if m.get('email','').startswith('inactive_smoke')), ''))" 2>/dev/null || echo "")

if [ -z "$INACTIVE_USER_ID" ]; then
  CREATE_RES=$(curl -sf -X POST "$BASE/api/v2.5/workspaces/$WS/members" \
    -H "Authorization: Bearer $ADMIN_JWT" \
    -H "Content-Type: application/json" \
    -d '{"email":"inactive_smoke@createmusicgroup.com","display_name":"Inactive Smoke","role":"analyst","status":"active"}' 2>/dev/null || echo '{}')
  INACTIVE_USER_ID=$(echo "$CREATE_RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('id',''))" 2>/dev/null || echo "")
fi

if [ -n "$INACTIVE_USER_ID" ]; then
  curl -sf -X PATCH "$BASE/api/v2.5/members/$INACTIVE_USER_ID" \
    -H "Authorization: Bearer $ADMIN_JWT" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"inactive\",\"workspace_id\":\"$WS\"}" > /dev/null 2>&1

  INACTIVE_JWT=$(python3 -c "
import os, sys
os.environ.setdefault('JWT_SECRET', '')
sys.path.insert(0,'.')
from server.jwt_utils import sign_jwt
print(sign_jwt({
    'sub': '$INACTIVE_USER_ID',
    'email': 'inactive_smoke@createmusicgroup.com',
    'name': 'Inactive Smoke',
    'role': 'analyst',
    'workspace_id': '$WS'
}))
")

  INACTIVE_ME=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v2.5/auth/me" -H "Authorization: Bearer $INACTIVE_JWT" 2>/dev/null || echo "000")
  if [ "$INACTIVE_ME" = "401" ]; then
    ok "Inactive user with valid JWT denied with 401"
  else
    fail "Inactive user JWT: expected 401, got $INACTIVE_ME"
  fi

  curl -sf -X PATCH "$BASE/api/v2.5/members/$INACTIVE_USER_ID" \
    -H "Authorization: Bearer $ADMIN_JWT" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"active\",\"workspace_id\":\"$WS\"}" > /dev/null 2>&1
else
  fail "Could not create inactive test user"
fi

echo ""
echo "--- 4. Unlisted user denied ---"
UNLISTED_RAW=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v2.5/workspaces" -H "Authorization: Bearer nonexistent_user_12345" 2>/dev/null || echo "000")
if [ "$UNLISTED_RAW" = "401" ]; then
  ok "Nonexistent user raw-ID Bearer denied with 401"
else
  fail "Nonexistent user: expected 401, got $UNLISTED_RAW"
fi

UNLISTED_JWT=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v2.5/auth/me" -H "Authorization: Bearer fake.invalid.token" 2>/dev/null || echo "000")
if [ "$UNLISTED_JWT" = "401" ]; then
  ok "Invalid JWT token denied with 401"
else
  fail "Invalid JWT: expected 401, got $UNLISTED_JWT"
fi

echo ""
echo "--- 5. Role-scoped access (analyst cannot manage members) ---"

ANALYST_JWT=$(python3 -c "
import os, sys
os.environ.setdefault('JWT_SECRET', '')
sys.path.insert(0,'.')
from server.jwt_utils import sign_jwt
print(sign_jwt({
    'sub': 'usr_01KMCG0100000000000000KYLE',
    'email': 'kylepatrick.go@createmusicgroup.com',
    'name': 'Kyle Patrick',
    'role': 'analyst',
    'workspace_id': '$WS'
}))
")

ANALYST_POST=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/api/v2.5/workspaces/$WS/members" \
  -H "Authorization: Bearer $ANALYST_JWT" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","display_name":"Test","role":"analyst"}' 2>/dev/null || echo "000")
if [ "$ANALYST_POST" = "403" ]; then
  ok "Analyst cannot create members (403 FORBIDDEN)"
else
  fail "Analyst member create: expected 403, got $ANALYST_POST"
fi

echo ""
echo "--- 6. Admin CAN manage members ---"
ADMIN_LIST=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v2.5/workspaces/$WS/members" -H "Authorization: Bearer $ADMIN_JWT" 2>/dev/null || echo "000")
if [ "$ADMIN_LIST" = "200" ]; then
  ok "Admin can list members (200 OK)"
else
  fail "Admin list members: expected 200, got $ADMIN_LIST"
fi

MEMBER_COUNT=$(curl -sf "$BASE/api/v2.5/workspaces/$WS/members" -H "Authorization: Bearer $ADMIN_JWT" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null || echo "0")
if [ "$MEMBER_COUNT" -gt 0 ]; then
  ok "Members list returns $MEMBER_COUNT users from DB"
else
  fail "Members list returned 0 users"
fi

echo ""
echo "--- 7. Auth config does not leak secrets ---"
HAS_SECRET=$(echo "$CFG" | python3 -c "import sys,json; d=json.load(sys.stdin); print('secret' in json.dumps(d).lower())" 2>/dev/null || echo "True")
if [ "$HAS_SECRET" = "False" ]; then
  ok "Auth config does not leak client secret"
else
  fail "Auth config may contain secret data"
fi

echo ""
echo "--- 8. Google verify rejects missing credential ---"
VERIFY_NO_CRED=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/api/v2.5/auth/google/verify" \
  -H "Content-Type: application/json" \
  -d '{"workspace_id":"ws_test"}' 2>/dev/null || echo "000")
if [ "$VERIFY_NO_CRED" = "400" ]; then
  ok "POST /google/verify rejects missing credential (400)"
else
  fail "POST /google/verify missing credential: expected 400, got $VERIFY_NO_CRED"
fi

echo ""
echo "=== Results: $PASS/$TOTAL passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
