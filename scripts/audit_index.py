#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from _public_gate import report
import json
payload = report("audit_index", sys.argv[1:])
print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
raise SystemExit(0 if payload.get("passed", True) else 2)
