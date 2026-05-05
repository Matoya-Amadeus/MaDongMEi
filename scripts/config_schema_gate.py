#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from madongmei.governance import config_schema_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public MaDongMei config schema.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()
    payload = config_schema_report()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("[config-schema] " + ("PASS" if payload["passed"] else "FAIL"))
        for violation in payload["violations"]:
            print(f"- {violation}")
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
