#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
TARGET=""
JSON_OUTPUT=0
MAX_FINDINGS="${MAX_FINDINGS:-200}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:-}"; shift 2 ;;
    --json) JSON_OUTPUT=1; shift ;;
    --max-findings) MAX_FINDINGS="${2:-200}"; shift 2 ;;
    -h|--help) echo "Usage: scripts/privacy_audit.sh [--target PATH] [--json]"; exit 0 ;;
    *) echo "privacy_audit: unknown argument: $1" >&2; exit 2 ;;
  esac
done
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 - "$TARGET" "$JSON_OUTPUT" "$MAX_FINDINGS" <<'PY'
import json, sys
from madongmei.governance import scan_privacy

target = sys.argv[1] or None
json_output = sys.argv[2] == "1"
max_findings = int(sys.argv[3])
payload = scan_privacy(target, max_findings=max_findings)
if json_output:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
else:
    status = "PASS" if payload["passed"] else "FAIL"
    print(f"[privacy-audit] {status}: scanned={payload['scanned']} findings={len(payload['findings'])}")
    for finding in payload["findings"][:20]:
        print(f"- {finding['kind']} {finding['path']}:{finding['line']}")
raise SystemExit(0 if payload["passed"] else 2)
PY
