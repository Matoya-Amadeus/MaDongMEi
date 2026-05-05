#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from madongmei.governance import doctor_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only MaDongMei doctor dashboard.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()
    payload = doctor_report()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("MaDongMei doctor: " + ("PASS" if payload["passed"] else "FAIL"))
        for name, check in payload["checks"].items():
            if isinstance(check, dict):
                print(f"- {name}: {'PASS' if check.get('passed', True) else 'FAIL'}")
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
