#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from madongmei.governance import code_scorecard  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Readonly MaDongMei public code scorecard.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--no-record", action="store_true", help="Kept for compatibility; the public scorecard is always readonly.")
    parser.add_argument("--require-push-readiness", action="store_true", help="Include strict push readiness as a zero-weight blocker.")
    parser.add_argument("--reference-style", action="store_true", help="Emit the readonly reference-style parity summary.")
    args = parser.parse_args()
    payload = code_scorecard(
        require_push_readiness=args.require_push_readiness,
        style="reference_style" if args.reference_style else "public",
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        style_label = "reference-style" if args.reference_style else "public"
        print(f"MaDongMei {style_label} scorecard: {'PASS' if payload['passed'] else 'FAIL'} score={payload['score']}/{payload['max_score']}")
        if "checks" in payload:
            for name, check in payload["checks"].items():
                status = "PASS" if check.get("passed", True) else "FAIL"
                print(f"- {name}: {status} weight={check.get('weight', 0)}")
        else:
            for row in payload.get("dimensions", []):
                status = "PASS" if row.get("status") == "pass" else row.get("status", "FAIL").upper()
                print(f"- {row.get('name')}: {status} weight={row.get('weight', 0)}")
    return 0 if payload.get("passed", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
