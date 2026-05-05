#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from madongmei.request_context import prepare_public_request_context  # noqa: E402


def _actual(payload: Mapping[str, Any]) -> dict[str, Any]:
    routes = payload.get("route_trace", {}).get("routes", {}) if isinstance(payload.get("route_trace", {}), Mapping) else {}
    skill = routes.get("skill", {}) if isinstance(routes.get("skill", {}), Mapping) else {}
    wiki = routes.get("wiki", {}) if isinstance(routes.get("wiki", {}), Mapping) else {}
    tool = payload.get("tool_route", {}) if isinstance(payload.get("tool_route", {}), Mapping) else {}
    return {
        "intent": payload.get("plan", {}).get("intent", ""),
        "memory_route": payload.get("plan", {}).get("memory_route", ""),
        "skill_mode": skill.get("mode", "none"),
        "skill": skill.get("selected", ""),
        "wiki_mode": wiki.get("mode", "none"),
        "wiki": wiki.get("selected", ""),
        "tool_mode": tool.get("mode", "none"),
        "tool_route": tool.get("selected", ""),
        "wiki_action": payload.get("plan", {}).get("wiki_action", "skip"),
    }


def _matches(actual: Mapping[str, Any], expect: Mapping[str, Any]) -> bool:
    for key, expected in expect.items():
        if key == "tool":
            key = "tool_route"
        if actual.get(key, "") != expected:
            return False
    return True


def run_suite() -> dict[str, Any]:
    suite_path = ROOT / "config" / "capability" / "request-route-real-prompt-suite.json"
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    cases = []
    passed = True
    with tempfile.TemporaryDirectory(prefix="madongmei-route-suite-", dir=str(ROOT)) as tmp:
        tmp_root = Path(tmp)
        env = {
            "CODEX_HOME": str(tmp_root / ".codex"),
            "MADONGMEI_HOME": str(tmp_root / "home"),
            "MADONGMEI_WIKI_DIR": str(tmp_root / "knowledge" / "wiki"),
            "MADONGMEI_SKILL_DIR": str(tmp_root / "skills" / "public-autopilot"),
        }
        for case in suite.get("cases", []):
            payload = prepare_public_request_context(str(case.get("query", "")), env=env)
            expect = case.get("expect", {}) if isinstance(case.get("expect", {}), dict) else {}
            actual = _actual(payload)
            case_passed = _matches(actual, expect)
            cases.append(
                {
                    "id": case.get("id", ""),
                    "query": case.get("query", ""),
                    "capability_id": case.get("capability_id", ""),
                    "case_tags": list(case.get("case_tags", [])) if isinstance(case.get("case_tags", []), list) else [],
                    "passed": case_passed,
                    "actual": actual,
                    "expect": expect,
                }
            )
            passed = passed and case_passed
    return {"schema_version": 1, "passed": passed, "case_count": len(cases), "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay public request route real-prompt cases.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument("--no-record", action="store_true", help="Compatibility flag; this suite is read-only.")
    args = parser.parse_args()
    payload = run_suite()
    if args.json or True:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
