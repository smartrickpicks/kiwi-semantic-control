#!/usr/bin/env python3
# Stdlib-only MCP install link generator (deterministic)
# Prints: ENCODED payload, full LINK, and BADGE_MARKDOWN (Replit badge image)
# Usage:
#   python3 scripts/mcp_link_gen.py \
#       --display-name "Kiwi Semantic Control Board" \
#       --base-url "https://YOUR_REPLIT_DEPLOYMENT_URL/mcp" \
#       --caption "Add to Replit" \
#       --header "Authorization: Bearer YOUR_TOKEN_PLACEHOLDER"  # optional, repeatable

import argparse
import base64
import json
import sys
import urllib.parse
from typing import List, Dict


def parse_headers(items: List[str]) -> List[Dict[str, str]]:
    parsed = []
    for h in items or []:
        if ":" not in h:
            continue
        k, v = h.split(":", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        parsed.append({"key": k, "value": v})
    # Deterministic order by key, then value
    parsed.sort(key=lambda x: (x["key"].lower(), x["value"]))
    return parsed


def main():
    ap = argparse.ArgumentParser(description="Deterministic MCP install link generator")
    ap.add_argument("--display-name", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--caption", default="Add to Replit")
    ap.add_argument("--header", action="append", help="Header in 'Key: Value' form; repeatable", default=[])
    args = ap.parse_args()

    payload = {
        "displayName": args.display_name,
        "baseUrl": args.base_url,
    }

    headers = parse_headers(args.header)
    if headers:
        payload["headers"] = headers

    # Deterministic JSON: sorted keys, compact separators
    json_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(json_str.encode("utf-8")).decode("ascii")
    link = f"https://replit.com/integrations?mcp={encoded}"

    # Badge markdown using Replit badge image; caption is URL-encoded for safety
    # Note: Keep captions concise (recommended <= 30 chars) for readability
    caption = args.caption
    caption_enc = urllib.parse.quote(caption, safe="")
    badge_img = f"https://replit.com/badge?caption={caption_enc}"
    badge_md = f"[![{caption}]({badge_img})]({link})"

    # Stable output
    print("ENCODED=" + encoded)
    print("LINK=" + link)
    print("BADGE_MARKDOWN=" + badge_md)


if __name__ == "__main__":
    sys.exit(main())
