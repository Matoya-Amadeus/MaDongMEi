#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from madongmei.llmwiki import citation_gate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public LLMWiki citations.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()
    payload = citation_gate()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("[llmwiki-citation] " + ("PASS" if payload["passed"] else "FAIL"))
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
