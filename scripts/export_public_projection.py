#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from madongmei.governance import check_public_projection  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Check MaDongMei public projection policy.")
    parser.add_argument("--check", action="store_true", help="Validate the projection policy.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()
    payload = check_public_projection()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("[public-projection] " + ("PASS" if payload["passed"] else "FAIL"))
        for violation in payload["violations"]:
            print(f"- {violation}")
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
