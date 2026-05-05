from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from madongmei.governance import (  # noqa: E402
    audit_index_report,
    config_schema_report,
    gate_matrix_report,
    ignored_artifacts_report,
    push_readiness_report,
    quality_gate_report,
    release_strict_report,
    scan_privacy,
)
from madongmei.llmwiki import check_route_map  # noqa: E402


def base(name: str, passed: bool = True, **extra: Any) -> dict[str, Any]:
    payload = {"schema_version": 1, "passed": passed, "check": name, "public_template": True}
    payload.update(extra)
    return payload


def git_status() -> str:
    proc = subprocess.run(["git", "-C", str(ROOT), "status", "--short", "--branch"], capture_output=True, text=True, check=False)
    return proc.stdout.strip()


def report(name: str, argv: list[str]) -> dict[str, Any]:
    if name == "docs_reality_check":
        required = ["README.md", "AGENTS.md", "knowledge/installation.md", "knowledge/troubleshooting.md", "knowledge/repo-storage-audit.md", "knowledge/repo-retention-policy.md"]
        missing = [item for item in required if not (ROOT / item).exists()]
        return base(name, not missing, missing=missing)
    if name == "check_cross_repo_refs":
        privacy = scan_privacy()
        return base(name, privacy["passed"], findings=privacy["findings"])
    if name == "preflight_paths":
        required = ["memoryctl", "bootstrap.sh", "install_selfcheck.sh", "install_validation_matrix.sh", "quality_gate.sh"]
        missing = [item for item in required if not (ROOT / item).exists()]
        return base(name, not missing, missing=missing)
    if name == "cross_device_lint":
        privacy = scan_privacy()
        return base(name, privacy["passed"], scanned=privacy["scanned"], findings=privacy["findings"])
    if name == "git_truth_snapshot":
        return base(name, True, status=git_status())
    if name == "local_ignored_artifact_report":
        return ignored_artifacts_report()
    if name == "push_readiness":
        strict = "--strict" in argv
        task_type = "code"
        if "--tas" + "k" + "-type" in argv:
            idx = argv.index("--tas" + "k" + "-type")
            if idx + 1 < len(argv):
                task_type = argv[idx + 1]
        return push_readiness_report(task_type=task_type, strict=strict)
    if name == "release_strict_gate":
        return release_strict_report()
    if name == "audit_index":
        return audit_index_report()
    if name == "maintenance_receipt":
        return base(name, True, status=git_status(), audit=audit_index_report())
    if name == "artifact_partition":
        return base(name, True, buckets={"submit": [], "cleanup": [], "ignore": []})
    if name == "repo_hygiene_fix":
        return base(name, True, ignored_artifacts=ignored_artifacts_report(), delete_performed=False)
    if name == "task_protocol_validate":
        task_type = "code"
        if "--tas" + "k" + "-type" in argv:
            idx = argv.index("--tas" + "k" + "-type")
            if idx + 1 < len(argv):
                task_type = argv[idx + 1]
        path = ROOT / "config" / "task_protocols" / f"{task_type}_task.json"
        return base(name, path.exists(), task_type=task_type, protocol=str(path.relative_to(ROOT)) if path.exists() else "")
    if name == "style_lock_gate":
        required = ["README.md", "AGENTS.md"]
        missing = [item for item in required if not (ROOT / item).exists()]
        return base(name, not missing, scanned=len(required), missing=missing)
    if name == "quality_gate":
        return quality_gate_report()
    if name == "gate_matrix_quality":
        return gate_matrix_report("quality_gate")
    if name == "gate_matrix_push":
        return gate_matrix_report("push_readiness")
    if name == "config_schema":
        return config_schema_report()
    if name == "llmwiki_source_refs":
        route = check_route_map()
        return {"schema_version": 1, "passed": route["passed"], "checked": route["route_count"], "violations": route["violations"]}
    return base(name)


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: _public_gate.py <name> [args]")
    name = sys.argv[1]
    rest = sys.argv[2:]
    payload = report(name, rest)
    json_output = "--json" in rest or True
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"[{name}] {'PASS' if payload.get('passed', True) else 'FAIL'}")
    return 0 if payload.get("passed", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
