# scripts/ — Operator Script Index

All scripts are stdlib-only and offline. No secrets, no external APIs.

## mcp_link_gen.py
Purpose: Generate a deterministic Replit MCP install-link payload and badge.

Outputs:
- ENCODED — base64(json) with sorted keys and compact separators
- LINK — https://replit.com/integrations?mcp=...
- BADGE_MARKDOWN — `[![<caption>](https://replit.com/badge?caption=...)](LINK)`

Usage:
```
python3 scripts/mcp_link_gen.py \
  --display-name "Kiwi Semantic Control Board" \
  --base-url "https://YOUR_REPLIT_DEPLOYMENT_URL/mcp" \
  --caption "Add to Replit" \
  --header "Authorization: Bearer YOUR_TOKEN_PLACEHOLDER"
```
Notes:
- Use placeholder headers only; do not commit secrets.
- Caption is URL-encoded; keep ≤ 30 chars for readability.

## replit_smoke.sh
Purpose: Validate base+patch, run deterministic preview, and compare against expected output.

Strict mode (default):
```
bash scripts/replit_smoke.sh
```
- Pass: exit 0; prints "OK: preview output matches expected (normalized)."
- Fail: exit 1; prints unified diff and guidance.

Allow differences temporarily:
```
bash scripts/replit_smoke.sh --allow-diff
```
- Exit 0 with a warning; inspect diff and update expected + CHANGELOG if intentional.

Tips:
- Optional: `chmod +x scripts/mcp_link_gen.py scripts/replit_smoke.sh` to run directly.
