#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "config" / "governance" / "gate-matrix.json"


def load_matrix() -> dict:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def report(mode: str) -> dict:
    data = load_matrix()
    steps = list(data.get(mode, []))
    duplicates = sorted({step for step in steps if steps.count(step) > 1})
    missing = [step for step in steps if step.endswith((".sh", ".py")) and not (ROOT / step).exists()]
    return {
        "schema_version": 1,
        "passed": not duplicates and not missing,
        "mode": mode,
        "steps": steps,
        "duplicates": duplicates,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect MaDongMei public gate matrix.")
    parser.add_argument("command", nargs="?", default="report", choices=["report"])
    parser.add_argument("--mode", default="quality_gate", choices=["quality_gate", "push_readiness"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = report(args.mode)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("[gate-matrix] " + ("PASS" if payload["passed"] else "FAIL") + f" mode={args.mode} steps={len(payload['steps'])}")
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
