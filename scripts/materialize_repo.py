#!/usr/bin/env python3
# Stdlib-only repo materializer
# Reads a JSON array of {path, content} from stdin and writes files.

import json
import os
from pathlib import Path


def main():
    data = json.load(os.sys.stdin)
    if not isinstance(data, list):
        raise SystemExit("Expected a JSON list of {path, content}")

    for item in data:
        p = Path(item["path"])
        content = item.get("content", "")
        p.parent.mkdir(parents=True, exist_ok=True)
        # Always write utf-8, normalize newline behavior to '\n'
        if isinstance(content, str):
            content = content.replace("\r\n", "\n")
        else:
            content = json.dumps(content, ensure_ascii=False, indent=2)
        p.write_text(content, encoding="utf-8")

    print(f"Wrote {len(data)} files")


if __name__ == "__main__":
    main()
