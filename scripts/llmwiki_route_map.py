#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from madongmei.llmwiki import check_route_map, load_route_map, route_map_path, template_route_map  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or print the public LLMWiki route map.")
    parser.add_argument("--check", action="store_true", help="Validate route map.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()
    payload = check_route_map() if args.check else load_route_map()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("[llmwiki-route-map] " + ("PASS" if payload.get("passed", True) else "FAIL"))
        print(f"route_map={route_map_path()}")
    return 0 if payload.get("passed", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
