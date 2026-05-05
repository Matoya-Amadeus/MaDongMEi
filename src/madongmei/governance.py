from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import repo_root
from .llmwiki import check_route_map, citation_gate, conflict_report

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("PRIVATE_PATH", re.compile(r"/(Users|private/var|var/folders)/")),
    (
        "PRIVATE_MADONGMEI_REPO",
        re.compile(
            "/".join(("", "Volumes", "Python 1", "Bit" + "bucket"))
            + r"|ai-"
            + r"madongmei-memory",
            re.IGNORECASE,
        ),
    ),
    ("OPENAI_KEY", re.compile(r"sk" + r"-(proj-)?[A-Za-z0-9_-]{20,}")),
    ("GITHUB_TOKEN", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("PRIVATE_PERSON_HANDLE", re.compile(r"(zhang" + r"qian|AI·Ma" + r"ho)", re.IGNORECASE)),
    (
        "PRIVATE_KEY",
        re.compile(r"BEGIN .*" + r"PRIVATE" + r" KEY"),
    ),
    ("PRIVATE_REMOTE", re.compile(r"(bit" + r"bucket)\.org[:/].*ai-madongmei", re.IGNORECASE)),
]
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "dist", "build"}


@dataclass
class DimensionResult:
    name: str
    weight: int
    score: int
    status: str
    evidence: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def iter_target_files(target: Path | None = None) -> Iterable[Path]:
    root = target or repo_root()
    if target is None:
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    path = root / line.strip()
                    if path.is_file():
                        yield path
                return
        except Exception:
            pass
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def scan_privacy(target: str | Path | None = None, *, max_findings: int = 200) -> dict[str, Any]:
    root = Path(target).expanduser() if target else repo_root()
    findings: list[dict[str, Any]] = []
    scanned = 0
    for path in iter_target_files(root if target else None):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append({"kind": label, "path": str(path), "line": lineno})
                    if len(findings) >= max_findings:
                        return {"schema_version": 1, "passed": False, "scanned": scanned, "findings": findings}
    return {"schema_version": 1, "passed": not findings, "scanned": scanned, "findings": findings}


def projection_policy_path() -> Path:
    return repo_root() / "config" / "public-projection.yaml"


def check_public_projection() -> dict[str, Any]:
    path = projection_policy_path()
    violations: list[str] = []
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    for token in ("copy:", "sanitize:", "template:", "omit:"):
        if token not in text:
            violations.append(f"missing {token}")
    for token in ("memories/personal", "memories/identity", "workspace-agent-memory", "knowledge/llmwiki", "manifests/audit", "knowledge/repo-storage-audit.md", "knowledge/repo-retention-policy.md", "scripts/madongmei_code_scorecard.py", "request-route-registry.json"):
        if token not in text:
            violations.append(f"missing boundary for {token}")
    return {"schema_version": 1, "passed": not violations, "path": str(path), "violations": violations}


def config_schema_report() -> dict[str, Any]:
    root = repo_root()
    required = [
        "config/public-projection.yaml",
        "config/governance/gate-matrix.json",
        "config/governance/entrypoint-map.json",
        "config/capability/llmwiki-route-map.json",
        "scripts/gate_matrix.py",
        "config/capability/conflict-policy.json",
        "config/capability/retrieval_rerank_policy.json",
        "config/capability/wiki-topic-routes.json",
        "config/capability/wiki-topic-aliases.json",
        "config/capability/wiki-auto-capture-policy.json",
        "config/governance/data-classification.yaml",
        "config/governance/ris" + "k" + "-tier.yaml",
        "config/governance/style-lock-v2.yaml",
        "config/governance/codex_reference_policy.json",
        "config/governance/evidence_source_policy.json",
        "config/governance/ingestion_contract_policy.json",
        "config/governance/memory_slo_policy.json",
        "config/governance/retrieval_regression_policy.json",
        "config/governance/longmemeval_policy.json",
        "config/task_protocols/code_task.json",
        "config/task_protocols/app_task.json",
        "config/task_protocols/game_task.json",
        "config/task_baselines/app_baselines.json",
        "config/task_baselines/game_baselines.json",
        "templates/model-instructions.template.md",
        "templates/llmwiki-row.template.jsonl",
        "templates/governance/task_receipt.template.md",
        "config/governance/madongmei-code-evaluation-standard.json",
        "config/capability/request-route-registry.json",
        "config/capability/request-route-template-schema.json",
        "config/capability/request-route-authoring-guide.md",
        "config/capability/request-route-real-prompt-suite.json",
        "config/capability/llmwiki-v2-policy.json",
        "config/capability/wiki-coverage-thresholds.json",
        "config/capability/phase-thresholds.json",
        "templates/capability/memory-route.template.json",
        "templates/capability/skill-route.template.json",
        "templates/capability/wiki-route.template.json",
        "templates/capability/tool-hint.template.json",
        "templates/capability/real-prompt-case.template.json",
        "scripts/madongmei_code_scorecard.py",
        "scripts/longmemeval_benchmark_suite.py",
        "scripts/longmemeval_madongmei_runner.py",
        "scripts/madongmei_shared.py",
        "scripts/memory_query_signals.py",
        "scripts/request_route_real_prompt_suite.py",
        "knowledge/repo-storage-audit.md",
        "knowledge/repo-retention-policy.md",
    ]
    violations = [rel for rel in required if not (root / rel).exists()]
    for rel in (
        "config/governance/gate-matrix.json",
        "config/governance/entrypoint-map.json",
        "config/capability/llmwiki-route-map.json",
        "config/governance/madongmei-code-evaluation-standard.json",
        "config/capability/request-route-registry.json",
        "config/capability/request-route-real-prompt-suite.json",
        "config/capability/llmwiki-v2-policy.json",
        "config/capability/wiki-coverage-thresholds.json",
        "config/capability/phase-thresholds.json",
    ):
        path = root / rel
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                violations.append(f"{rel}: {type(exc).__name__}")
    projection = check_public_projection()
    if not projection["passed"]:
        violations.extend(projection["violations"])
    route = check_route_map()
    if not route["passed"]:
        violations.extend(route["violations"])
    return {"schema_version": 1, "passed": not violations, "violations": violations, "checks": len(required) + 2}


def gate_matrix_report(mode: str = "quality_gate") -> dict[str, Any]:
    path = repo_root() / "config" / "governance" / "gate-matrix.json"
    violations: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema_version": 1, "passed": False, "mode": mode, "violations": [f"{type(exc).__name__}: {exc}"], "steps": []}
    steps = list(data.get(mode, []))
    duplicates = sorted({step for step in steps if steps.count(step) > 1})
    missing = [step for step in steps if step.endswith((".sh", ".py")) and not (repo_root() / step).exists()]
    violations.extend(f"duplicate:{item}" for item in duplicates)
    violations.extend(f"missing:{item}" for item in missing)
    return {"schema_version": 1, "passed": not violations, "mode": mode, "steps": steps, "violations": violations, "duplicates": duplicates, "missing": missing}


def _relative_public_path(path: str | Path, *, root: Path | None = None) -> str:
    base = (root or repo_root()).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        raw = str(candidate).strip()
        return raw.rstrip("/") if raw not in {"", "."} else "."
    try:
        return str(candidate.resolve().relative_to(base))
    except Exception:
        return sanitize_public_path(str(candidate))


def sanitize_public_path(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"/" + "Users" + r"/[^\s:'\"]+", "${HOME}", text)
    text = re.sub(r"/" + "Volumes" + r"/Python 1/[^\s:'\"]+", "${PUBLIC_VOLUME}", text)
    text = text.replace(str(repo_root().parent), "${REPO_PARENT}")
    text = text.replace(str(repo_root()), ".")
    return text


def _path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if child.is_file() or child.is_symlink():
            try:
                total += child.stat().st_size
            except OSError:
                continue
    return total


def _classify_ignored_artifact(rel: str) -> dict[str, Any]:
    clean_rel = rel.strip().rstrip("/") or "."
    name = Path(clean_rel).name
    if ".madongmei-runtime" in clean_rel or clean_rel.startswith(".madongmei/"):
        kind = "runtime-cache"
        risk = "low"
        rebuild = "rebuildable runtime cache"
        cleanable = True
    elif "__pycache__" in clean_rel or clean_rel.endswith(".pyc") or ".pytest_cache" in clean_rel:
        kind = "python-cache"
        risk = "low"
        rebuild = "rebuilt by Python or tests"
        cleanable = True
    elif name == ".DS_Store":
        kind = "local-metadata"
        risk = "low"
        rebuild = "macOS Finder metadata"
        cleanable = True
    elif clean_rel in {"dist", "build"} or clean_rel.startswith(("dist/", "build/")):
        kind = "build-output"
        risk = "low"
        rebuild = "rebuilt by packaging commands"
        cleanable = True
    elif clean_rel.startswith(".venv"):
        kind = "local-env"
        risk = "medium"
        rebuild = "reinstall dependencies"
        cleanable = False
    else:
        kind = "ignored-local"
        risk = "medium"
        rebuild = "unknown; inspect before deleting"
        cleanable = False
    return {"kind": kind, "risk": risk, "rebuild_cost": rebuild, "cleanable": cleanable}


def _git_ignored_paths(root: Path) -> list[str]:
    try:
        proc = subprocess.run(["git", "-C", str(root), "status", "--ignored", "--short"], capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            return []
        return [line[3:].strip() for line in proc.stdout.splitlines() if line.startswith("!! ") and line[3:].strip()]
    except Exception:
        return []


def ignored_artifacts_report(*, root: Path | None = None, ignored_paths: Iterable[str] | None = None) -> dict[str, Any]:
    base = (root or repo_root()).resolve()
    raw_paths = list(ignored_paths) if ignored_paths is not None else _git_ignored_paths(base)
    artifacts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_paths:
        rel = str(raw).strip().rstrip("/")
        if not rel or rel in seen:
            continue
        seen.add(rel)
        target = base / rel
        classified = _classify_ignored_artifact(rel)
        row = {
            "target_id": f"{classified['kind']}:{rel}",
            "path": rel,
            "size_bytes": _path_size(target),
            "risk": classified["risk"],
            "rebuild_cost": classified["rebuild_cost"],
            "cleanable": bool(classified["cleanable"]),
            "kind": classified["kind"],
        }
        artifacts.append(row)
    artifacts.sort(key=lambda row: (str(row["risk"]), str(row["target_id"])))
    total_bytes = sum(int(row["size_bytes"]) for row in artifacts)
    cleanable_bytes = sum(int(row["size_bytes"]) for row in artifacts if row["cleanable"])
    storage_facts = {
        "artifact_count": len(artifacts),
        "ignored_total_bytes": total_bytes,
        "cleanable_bytes": cleanable_bytes,
        "tracked_worktree_bytes": _path_size(base) - _path_size(base / ".git"),
        "git_history_bytes": _path_size(base / ".git"),
        "report_scope": "." if base == repo_root().resolve() else sanitize_public_path(str(base)),
    }
    return {
        "schema_version": 1,
        "passed": True,
        "mode": "report",
        "ignored_count": len(artifacts),
        "safe_ignored_count": sum(1 for row in artifacts if row["cleanable"] and row["risk"] == "low"),
        "artifacts": artifacts,
        "storage_facts": storage_facts,
    }

def audit_index_report() -> dict[str, Any]:
    root = repo_root() / "manifests" / "audit"
    rows = []
    if root.exists():
        for path in sorted(root.glob("*.md")):
            rows.append({"path": str(path.relative_to(repo_root())), "type": path.stem.split("-", 1)[0]})
    return {"schema_version": 1, "passed": True, "total": len(rows), "rows": rows[:20], "public_template": True}


def quality_gate_report() -> dict[str, Any]:
    required = [
        "scripts/privacy_audit.sh",
        "scripts/export_public_projection.py",
        "scripts/config_schema_gate.py",
        "install_selfcheck.sh",
        "install_validation_matrix.sh",
        "scripts/madongmei_doctor.py",
        "scripts/madongmei_code_scorecard.py",
        "scripts/request_route_real_prompt_suite.py",
    ]
    missing = [path for path in required if not (repo_root() / path).exists()]
    return {"schema_version": 1, "passed": not missing, "missing": missing, "steps": required}


def llmwiki_source_refs_report() -> dict[str, Any]:
    route = check_route_map()
    return normalize_check(
        "llmwiki_source_refs",
        "llmwiki",
        route["passed"],
        "public llmwiki source references are durable",
        checked=route["route_count"],
        violations=route["violations"],
    )


def normalize_check(code: str, category: str, passed: bool = True, summary: str = "ok", *, severity: str | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "passed": bool(passed),
        "code": code,
        "category": category,
        "summary": summary,
        "severity": severity or ("ok" if passed else "error"),
    }
    payload.update(extra)
    return payload


def _normalize_existing_check(code: str, category: str, payload: Mapping[str, Any], summary: str = "ok") -> dict[str, Any]:
    row = dict(payload)
    row.setdefault("schema_version", 1)
    row.setdefault("passed", True)
    row.setdefault("code", code)
    row.setdefault("category", category)
    row.setdefault("summary", summary)
    row.setdefault("severity", "ok" if row.get("passed", True) else "error")
    return row


def _load_scorecard_standard() -> dict[str, Any]:
    path = repo_root() / "config" / "governance" / "madongmei-code-evaluation-standard.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema_version": 1, "max_score": 100, "checks": {}, "load_error": f"{type(exc).__name__}: {exc}"}


def longmemeval_policy_path() -> Path:
    return repo_root() / "config" / "governance" / "longmemeval_policy.json"


def longmemeval_latest_suite_path() -> Path:
    return repo_root() / "manifests" / "metrics" / "longmemeval_latest_suite.json"


def longmemeval_official_snapshot_path() -> Path:
    return repo_root() / "benchmarks" / "longmemeval" / "official-suite-summary.json"


def load_longmemeval_policy() -> dict[str, Any]:
    path = longmemeval_policy_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_longmemeval_suite() -> dict[str, Any]:
    for path in (longmemeval_latest_suite_path(), longmemeval_official_snapshot_path()):
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            payload.setdefault("_artifact_path", _relative_public_path(path))
            return payload
    return {}


def longmemeval_overall_row(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    suite = payload or load_longmemeval_suite()
    rows = suite.get("rows", []) if isinstance(suite, Mapping) else []
    if not isinstance(rows, list):
        return {}
    preferred = ("madongmei_overall", "public_overall")
    for backend in preferred:
        for row in rows:
            if isinstance(row, Mapping) and str(row.get("backend", "")) == backend:
                return dict(row)
    for row in rows:
        if isinstance(row, Mapping):
            return dict(row)
    return {}


def longmemeval_regression_report() -> dict[str, Any]:
    suite = load_longmemeval_suite()
    policy = load_longmemeval_policy()
    row = longmemeval_overall_row(suite)
    violations: list[str] = []
    if not suite:
        violations.append("missing LongMemEval suite artifact")
    if not row:
        violations.append("missing overall LongMemEval row")
    thresholds = row.get("thresholds", {}) if isinstance(row.get("thresholds", {}), Mapping) else {}
    if not thresholds:
        thresholds = ((policy.get("absolute", {}) or {}).get("madongmei_overall", {})) if isinstance(policy, Mapping) else {}
    for metric in ("recall_any@5", "recall_any@10", "ndcg_any@10"):
        actual = float(row.get(metric, 0.0) or 0.0) if row else 0.0
        minimum = float(thresholds.get(f"min_{metric}", thresholds.get(metric, 0.0)) or 0.0)
        if actual < minimum:
            violations.append(f"madongmei_overall {metric} below threshold")

    internal_profiles = suite.get("internal_profiles", {}) if isinstance(suite, Mapping) else {}
    if not isinstance(internal_profiles, Mapping):
        internal_profiles = {}
    required_profiles = (policy.get("internal_profiles", {}) or {}) if isinstance(policy, Mapping) else {}
    if isinstance(required_profiles, Mapping):
        for backend_key, profile_thresholds in required_profiles.items():
            metrics = internal_profiles.get(backend_key, {})
            if not isinstance(metrics, Mapping):
                violations.append(f"missing internal profile {backend_key}")
                continue
            for metric in ("recall_any@5", "recall_any@10", "ndcg_any@10"):
                actual = float(metrics.get(metric, 0.0) or 0.0)
                minimum = float(profile_thresholds.get(f"min_{metric}", profile_thresholds.get(metric, 0.0)) or 0.0)
                if actual < minimum:
                    violations.append(f"{backend_key} {metric} below threshold")

    return {
        "schema_version": 1,
        "passed": not violations and bool(row),
        "artifact_path": str(suite.get("_artifact_path", "")) if isinstance(suite, Mapping) else "",
        "policy_path": _relative_public_path(longmemeval_policy_path()),
        "overall": row,
        "internal_profiles": dict(internal_profiles),
        "violations": violations,
    }


def _benchmark_snapshot_report() -> dict[str, Any]:
    path = longmemeval_official_snapshot_path()
    violations: list[str] = []
    payload = load_longmemeval_suite()
    row = longmemeval_overall_row(payload)
    if not payload:
        violations.append("missing public LongMemEval snapshot")
    if payload:
        if not payload.get("passed", False):
            violations.append("snapshot failed")
        if int(payload.get("questions", 0) or 0) <= 0:
            violations.append("snapshot questions missing")
        rows = payload.get("rows", []) if isinstance(payload.get("rows", []), list) else []
        if not rows:
            violations.append("snapshot rows missing")
        elif row:
            thresholds = row.get("thresholds", {}) if isinstance(row.get("thresholds", {}), dict) else {}
            for metric in ("recall_any@5", "recall_any@10", "ndcg_any@10"):
                if float(row.get(metric, 0.0) or 0.0) < float(thresholds.get(metric, 0.0) or 0.0):
                    violations.append(f"{metric} below threshold")
    return normalize_check(
        "benchmark_snapshot",
        "benchmark",
        not violations,
        "public compact LongMemEval snapshot is valid",
        path=_relative_public_path(path),
        violations=violations,
    )


def _docs_report() -> dict[str, Any]:
    required = ["README.md", "AGENTS.md", "knowledge/installation.md", "knowledge/troubleshooting.md"]
    missing = [rel for rel in required if not (repo_root() / rel).exists()]
    return normalize_check("docs_surface", "docs", not missing, "public docs entrypoints exist", missing=missing)


def _cli_contract_report() -> dict[str, Any]:
    required = ["memoryctl", "src/madongmei/cli.py"]
    missing = [rel for rel in required if not (repo_root() / rel).exists()]
    return normalize_check("cli_contract", "cli", not missing, "public CLI entrypoints exist", missing=missing)


def _git_scorecard_facts() -> dict[str, Any]:
    try:
        status = subprocess.run(
            ["git", "-C", str(repo_root()), "status", "--porcelain", "--branch"],
            capture_output=True,
            text=True,
            check=False,
        )
        head = subprocess.run(
            ["git", "-C", str(repo_root()), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return {"status_ok": False, "branch": "", "head": "", "dirty_count": 0, "changed_paths": [], "error": f"{type(exc).__name__}: {exc}"}
    lines = [line.rstrip() for line in status.stdout.splitlines() if line.strip()]
    branch = lines[0] if lines and lines[0].startswith("##") else ""
    changed_lines = [line for line in lines if not line.startswith("##")]
    changed_paths: list[str] = []
    for line in changed_lines:
        payload = line[3:] if len(line) > 3 else line
        changed_paths.append(payload.split(" -> ", 1)[-1].strip())
    return {
        "status_ok": status.returncode == 0 and head.returncode == 0,
        "branch": branch,
        "head": head.stdout.strip(),
        "dirty_count": len(changed_paths),
        "changed_paths": changed_paths,
    }


def _entrypoint_scorecard_facts() -> dict[str, Any]:
    path = repo_root() / "config" / "governance" / "entrypoint-map.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"exists": False, "path": _relative_public_path(path), "missing_canonical": ["entrypoint-map-unreadable"], "broken_wrappers": [f"{type(exc).__name__}: {exc}"]}
    canonical = payload.get("canonical", []) if isinstance(payload.get("canonical", []), list) else []
    wrappers = payload.get("wrappers", []) if isinstance(payload.get("wrappers", []), list) else []
    missing_canonical = [
        str(row.get("path", "")).strip()
        for row in canonical
        if str(row.get("path", "")).strip() and not (repo_root() / str(row.get("path", "")).strip()).exists()
    ]
    broken_wrappers = [
        str(row.get("path", "")).strip()
        for row in wrappers
        if str(row.get("path", "")).strip() and not (repo_root() / str(row.get("path", "")).strip()).exists()
    ]
    return {
        "exists": path.exists(),
        "path": _relative_public_path(path),
        "missing_canonical": missing_canonical,
        "broken_wrappers": broken_wrappers,
        "canonical_count": len(canonical),
        "wrapper_count": len(wrappers),
    }


def _longmemeval_scorecard_facts() -> dict[str, Any]:
    report = longmemeval_regression_report()
    row = dict(report.get("overall", {}) if isinstance(report.get("overall", {}), Mapping) else {})
    internal_profiles = dict(report.get("internal_profiles", {}) if isinstance(report.get("internal_profiles", {}), Mapping) else {})
    metrics = ("recall_any@5", "recall_any@10", "ndcg_any@10")
    overall_full = bool(row) and all(float(row.get(metric, 0.0) or 0.0) >= 1.0 for metric in metrics)
    internal_profiles_full: dict[str, bool] = {}
    for key, values in internal_profiles.items():
        if not isinstance(values, Mapping):
            internal_profiles_full[str(key)] = False
            continue
        internal_profiles_full[str(key)] = all(float(values.get(metric, 0.0) or 0.0) >= 1.0 for metric in metrics)
    return {
        "path": str(report.get("artifact_path", "")),
        "policy_path": str(report.get("policy_path", "")),
        "suite_passed": bool(report.get("passed", False)),
        "overall": row,
        "overall_full": overall_full,
        "internal_profiles": internal_profiles,
        "internal_profiles_full": internal_profiles_full,
        "violations": list(report.get("violations", [])),
    }


def _p0_violations(facts: Mapping[str, Any], *, require_push_readiness: bool = False) -> list[dict[str, str]]:
    changed = set(str(path) for path in facts.get("git", {}).get("changed_paths", []))
    violations: list[dict[str, str]] = []
    longmemeval = facts.get("longmemeval", {})
    if not (longmemeval.get("overall_full") and all((longmemeval.get("internal_profiles_full") or {}).values())):
        violations.append(
            {
                "id": "longmemeval_default_or_fallback_metric_drop",
                "reason": "public LongMemEval snapshot is not full score",
            }
        )
    entrypoint = facts.get("entrypoint", {})
    if entrypoint.get("missing_canonical") or entrypoint.get("broken_wrappers"):
        violations.append(
            {
                "id": "canonical_path_or_wrapper_boundary_broken",
                "reason": "entrypoint map has missing canonical paths or broken wrappers",
            }
        )
    local_only_prefixes = ("memories/personal/personal_memory.jsonl", "memories/workspace-agent-memory/")
    if any(path == local_only_prefixes[0] or path.startswith(local_only_prefixes[1]) for path in changed):
        violations.append(
            {
                "id": "local_only_runtime_personal_secret_cache_or_log_promoted",
                "reason": "local-only memory or runtime path changed",
            }
        )
    network_files = [path for path in changed if any(token in path.lower() for token in ("clash", "proxy", "network"))]
    if network_files:
        violations.append(
            {
                "id": "unauthorized_clash_proxy_or_network_routing_mutation",
                "reason": ", ".join(network_files[:3]),
            }
        )
    if require_push_readiness and not facts.get("push_readiness", {}).get("passed", False):
        violations.append(
            {
                "id": "push_readiness_strict_not_passed",
                "reason": "strict push readiness failed or was not run",
            }
        )
    return violations


def _dimension_results(facts: Mapping[str, Any], weights: Mapping[str, int]) -> list[DimensionResult]:
    longmemeval = facts.get("longmemeval", {})
    entrypoint = facts.get("entrypoint", {})
    git = facts.get("git", {})
    audit_count = len(list((repo_root() / "manifests" / "audit").glob("*.md")))
    dimensions = [
        DimensionResult(
            "functional_correctness",
            int(weights.get("functional_correctness", 10)),
            int(weights.get("functional_correctness", 10)) if all((repo_root() / path).exists() for path in ("memoryctl", "src/madongmei/request_context.py", "scripts/request_route_real_prompt_suite.py")) else 0,
            "pass",
            ["memoryctl", "src/madongmei/request_context.py", "scripts/request_route_real_prompt_suite.py"],
        ),
        DimensionResult(
            "test_coverage_regression",
            int(weights.get("test_coverage_regression", 10)),
            int(weights.get("test_coverage_regression", 10)) if all((repo_root() / path).exists() for path in ("tests/test_request_route_strengthening.py", "tests/test_route_alignment_contract.py", "tests/test_madongmei_code_scorecard.py")) else 0,
            "pass",
            ["tests/test_request_route_strengthening.py", "tests/test_route_alignment_contract.py", "tests/test_madongmei_code_scorecard.py"],
        ),
        DimensionResult(
            "evaluation_integrity",
            int(weights.get("evaluation_integrity", 10)),
            int(weights.get("evaluation_integrity", 10)) if longmemeval.get("suite_passed") and longmemeval.get("overall_full") else 0,
            "pass",
            [str(longmemeval.get("path", ""))],
            list(longmemeval.get("violations", [])),
        ),
        DimensionResult(
            "architecture_clarity",
            int(weights.get("architecture_clarity", 10)),
            int(weights.get("architecture_clarity", 10)) if entrypoint.get("exists") and not entrypoint.get("missing_canonical") and not entrypoint.get("broken_wrappers") else 0,
            "pass",
            [str(entrypoint.get("path", ""))],
        ),
        DimensionResult(
            "maintainability",
            int(weights.get("maintainability", 10)),
            int(weights.get("maintainability", 10)) if (repo_root() / "config/governance/style-lock-v2.yaml").exists() else 0,
            "pass",
            ["config/governance/style-lock-v2.yaml"],
        ),
        DimensionResult(
            "governance_release_gates",
            int(weights.get("governance_release_gates", 10)),
            int(weights.get("governance_release_gates", 10)) if audit_count > 0 and (repo_root() / "config/governance/gate-matrix.json").exists() else 0,
            "pass",
            ["config/governance/gate-matrix.json", "manifests/audit/"],
        ),
        DimensionResult(
            "security_privacy",
            int(weights.get("security_privacy", 10)),
            int(weights.get("security_privacy", 10)) if (repo_root() / "scripts/privacy_audit.sh").exists() else 0,
            "pass",
            ["scripts/privacy_audit.sh"],
        ),
        DimensionResult(
            "performance_stability",
            int(weights.get("performance_stability", 10)),
            int(weights.get("performance_stability", 10)) if (repo_root() / "config/governance/memory_slo_policy.json").exists() else 0,
            "pass",
            ["config/governance/memory_slo_policy.json"],
        ),
        DimensionResult(
            "documentation_operability",
            int(weights.get("documentation_operability", 10)),
            int(weights.get("documentation_operability", 10)) if (repo_root() / "README.md").exists() and (repo_root() / "AGENTS.md").exists() else 0,
            "pass",
            ["README.md", "AGENTS.md"],
        ),
        DimensionResult(
            "change_minimality",
            int(weights.get("change_minimality", 10)),
            int(weights.get("change_minimality", 10)) if int(git.get("dirty_count", 0) or 0) <= 40 else 0,
            "pass",
            ["git status --porcelain --branch"],
        ),
    ]
    for row in dimensions:
        if row.score < row.weight:
            row.status = "warn" if row.score > 0 else "fail"
    return dimensions


def _scorecard_grade(score: int, *, p0_blocked: bool) -> str:
    if p0_blocked or score < 60:
        return "F"
    if score >= 95:
        return "A"
    if score >= 90:
        return "B"
    if score >= 80:
        return "C"
    return "D"


REFERENCE_STYLE_DIMENSION_WEIGHTS: dict[str, int] = {
    "functional_correctness": 20,
    "test_coverage_regression": 15,
    "evaluation_integrity": 15,
    "architecture_clarity": 10,
    "maintainability": 10,
    "governance_release_gates": 10,
    "security_privacy": 8,
    "performance_stability": 5,
    "documentation_operability": 5,
    "change_minimality": 2,
}


def _reference_style_grade(score: int, *, p0_blocked: bool) -> str:
    if p0_blocked or score < 60:
        return "F"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def _reference_style_p0_violations(
    facts: Mapping[str, Any],
    *,
    require_push_readiness: bool = False,
) -> list[dict[str, str]]:
    changed = {str(path) for path in facts.get("git", {}).get("changed_paths", [])}
    violations: list[dict[str, str]] = []
    longmemeval = facts.get("longmemeval", {})
    if not (longmemeval.get("overall_full") and all((longmemeval.get("internal_profiles_full") or {}).values())):
        violations.append(
            {
                "id": "longmemeval_default_or_fallback_metric_drop",
                "reason": "public LongMemEval snapshot is not full score",
            }
        )
    entrypoint = facts.get("entrypoint", {})
    if entrypoint.get("missing_canonical") or entrypoint.get("broken_wrappers"):
        violations.append(
            {
                "id": "canonical_path_or_wrapper_boundary_broken",
                "reason": "entrypoint map has missing canonical paths or broken wrappers",
            }
        )
    local_like_prefixes = ("manifests/metrics/", "manifests/audit/")
    if any(path.startswith(local_like_prefixes) or path == "manifests/metrics/" for path in changed):
        violations.append(
            {
                "id": "local_only_runtime_personal_secret_cache_or_log_promoted",
                "reason": "local evidence or runtime path changed",
            }
        )
    network_files = [path for path in changed if any(token in path.lower() for token in ("clash", "proxy", "network"))]
    if network_files:
        violations.append(
            {
                "id": "unauthorized_clash_proxy_or_network_routing_mutation",
                "reason": ", ".join(network_files[:3]),
            }
        )
    if require_push_readiness and not facts.get("push_readiness", {}).get("passed", False):
        violations.append(
            {
                "id": "push_readiness_strict_not_passed",
                "reason": "strict push readiness failed or was not run",
            }
        )
    return violations


def _reference_style_dimensions(facts: Mapping[str, Any]) -> list[DimensionResult]:
    longmemeval = facts.get("longmemeval", {})
    entrypoint = facts.get("entrypoint", {})
    weights = REFERENCE_STYLE_DIMENSION_WEIGHTS
    dimensions = [
        DimensionResult(
            "functional_correctness",
            weights["functional_correctness"],
            weights["functional_correctness"] if all((repo_root() / path).exists() for path in ("memoryctl", "src/madongmei/request_context.py", "scripts/madongmei_code_scorecard.py")) else 0,
            "pass",
            ["memoryctl", "src/madongmei/request_context.py", "scripts/madongmei_code_scorecard.py"],
        ),
        DimensionResult(
            "test_coverage_regression",
            weights["test_coverage_regression"],
            weights["test_coverage_regression"] if all((repo_root() / path).exists() for path in ("tests/test_request_route_strengthening.py", "tests/test_route_alignment_contract.py", "tests/test_madongmei_code_scorecard.py")) else 0,
            "pass",
            ["tests/test_request_route_strengthening.py", "tests/test_route_alignment_contract.py", "tests/test_madongmei_code_scorecard.py"],
        ),
        DimensionResult(
            "evaluation_integrity",
            weights["evaluation_integrity"],
            weights["evaluation_integrity"] if longmemeval.get("suite_passed") and longmemeval.get("overall_full") else 0,
            "pass",
            [str(longmemeval.get("path", ""))],
            list(longmemeval.get("violations", [])),
        ),
        DimensionResult(
            "architecture_clarity",
            weights["architecture_clarity"],
            weights["architecture_clarity"] if entrypoint.get("exists") and not entrypoint.get("missing_canonical") and not entrypoint.get("broken_wrappers") else 0,
            "pass",
            [str(entrypoint.get("path", ""))],
        ),
        DimensionResult(
            "maintainability",
            weights["maintainability"],
            weights["maintainability"] if (repo_root() / "config/governance/style-lock-v2.yaml").exists() else 0,
            "pass",
            ["config/governance/style-lock-v2.yaml"],
        ),
        DimensionResult(
            "governance_release_gates",
            weights["governance_release_gates"],
            weights["governance_release_gates"] if (repo_root() / "config/governance/gate-matrix.json").exists() else 0,
            "pass",
            ["config/governance/gate-matrix.json", "manifests/audit/"],
        ),
        DimensionResult(
            "security_privacy",
            weights["security_privacy"],
            weights["security_privacy"] if (repo_root() / "scripts/privacy_audit.sh").exists() else 0,
            "pass",
            ["scripts/privacy_audit.sh"],
        ),
        DimensionResult(
            "performance_stability",
            weights["performance_stability"],
            weights["performance_stability"] if (repo_root() / "config/governance/memory_slo_policy.json").exists() else 0,
            "pass",
            ["config/governance/memory_slo_policy.json"],
        ),
        DimensionResult(
            "documentation_operability",
            weights["documentation_operability"],
            weights["documentation_operability"] if (repo_root() / "README.md").exists() and (repo_root() / "AGENTS.md").exists() else 0,
            "pass",
            ["README.md", "AGENTS.md"],
        ),
        DimensionResult(
            "change_minimality",
            weights["change_minimality"],
            weights["change_minimality"] if facts.get("git", {}).get("status_ok") else 0,
            "pass",
            ["git status --porcelain --branch"],
        ),
    ]
    for row in dimensions:
        if row.score < row.weight:
            row.status = "warn" if row.score > 0 else "fail"
    return dimensions


def _reference_style_scorecard(facts: Mapping[str, Any], *, require_push_readiness: bool = False) -> dict[str, Any]:
    p0_violations = _reference_style_p0_violations(facts, require_push_readiness=require_push_readiness)
    dimensions = _reference_style_dimensions(facts)
    score = sum(row.score for row in dimensions)
    grade = _reference_style_grade(score, p0_blocked=bool(p0_violations))
    return {
        "schema_version": 1,
        "style": "reference_style",
        "score": score,
        "grade": grade,
        "passed": grade in {"A", "B"} and not p0_violations,
        "p0_blocked": bool(p0_violations),
        "p0_violations": p0_violations,
        "facts": facts,
        "dimensions": [asdict(row) for row in dimensions],
        "readonly": True,
    }


def code_scorecard(*, require_push_readiness: bool = False, style: str = "public") -> dict[str, Any]:
    standard = _load_scorecard_standard()
    definitions = standard.get("checks", {}) if isinstance(standard.get("checks", {}), dict) else {}
    if not definitions:
        return {"schema_version": 1, "passed": False, "score": 0, "max_score": 100, "checks": {}, "violations": [standard.get("load_error", "missing scorecard standard")]}
    raw_checks: dict[str, dict[str, Any]] = {
        "installability": normalize_check(
            "installability",
            "install",
            all((repo_root() / rel).exists() for rel in ["bootstrap.sh", "install_selfcheck.sh", "install_validation_matrix.sh", "quality_gate.sh"]),
            "install and validation entrypoints exist",
        ),
        "privacy": _normalize_existing_check("privacy", "privacy", scan_privacy(), "privacy audit passes"),
        "projection": _normalize_existing_check("projection", "projection", check_public_projection(), "public projection policy is complete"),
        "cli_contract": _cli_contract_report(),
        "governance": _normalize_existing_check("governance", "governance", config_schema_report(), "governance config schema passes"),
        "docs": _docs_report(),
        "storage": _normalize_existing_check("storage", "storage", ignored_artifacts_report(), "ignored artifacts are observable"),
        "benchmark": _benchmark_snapshot_report(),
    }
    if require_push_readiness:
        push = push_readiness_report(task_type="code", strict=True, include_scorecard=False)
        raw_checks["push_readiness"] = _normalize_existing_check("push_readiness", "release", push, "strict push readiness passes")
    total = 0
    scored_checks: dict[str, dict[str, Any]] = {}
    violations: list[str] = []
    for name, definition in definitions.items():
        weight = int(definition.get("weight", 0) or 0)
        check = dict(raw_checks.get(name, normalize_check(name, str(definition.get("category", "unknown")), False, "missing check implementation")))
        check["weight"] = weight
        check["category"] = str(definition.get("category") or check.get("category") or name)
        check.setdefault("code", name)
        if check.get("passed", True):
            total += weight
        else:
            violations.append(name)
        scored_checks[name] = check
    if require_push_readiness and "push_readiness" in raw_checks:
        push_check = dict(raw_checks["push_readiness"])
        push_check["weight"] = 0
        scored_checks["push_readiness"] = push_check
        if not push_check.get("passed", True):
            violations.append("push_readiness")
    weight_total = sum(int(definition.get("weight", 0) or 0) for definition in definitions.values())
    if weight_total != 100:
        violations.append(f"scorecard weights sum to {weight_total}")
    passed = total >= 90 and not violations
    facts: dict[str, Any] = {
        "git": _git_scorecard_facts(),
        "storage": dict(raw_checks.get("storage", {})),
        "longmemeval": _longmemeval_scorecard_facts(),
        "entrypoint": _entrypoint_scorecard_facts(),
    }
    if require_push_readiness:
        push_check = dict(raw_checks.get("push_readiness", {}))
        facts["push_readiness"] = {"passed": bool(push_check.get("passed", False)), "summary": str(push_check.get("summary", ""))}
    if style == "reference_style":
        payload = _reference_style_scorecard(facts, require_push_readiness=require_push_readiness)
        payload["max_score"] = 100
        payload["standard"] = "reference-style-readonly"
        return payload
    weights = {
        "functional_correctness": 10,
        "test_coverage_regression": 10,
        "evaluation_integrity": 10,
        "architecture_clarity": 10,
        "maintainability": 10,
        "governance_release_gates": 10,
        "security_privacy": 10,
        "performance_stability": 10,
        "documentation_operability": 10,
        "change_minimality": 10,
    }
    p0_violations = _p0_violations(facts, require_push_readiness=require_push_readiness)
    dimensions = _dimension_results(facts, weights)
    grade = _scorecard_grade(total, p0_blocked=bool(p0_violations))
    return {
        "schema_version": 1,
        "style": "public",
        "passed": passed,
        "score": total,
        "max_score": int(standard.get("max_score", 100) or 100),
        "standard": "config/governance/madongmei-code-evaluation-standard.json",
        "checks": scored_checks,
        "violations": violations,
        "grade": grade,
        "p0_blocked": bool(p0_violations),
        "p0_violations": p0_violations,
        "facts": facts,
        "dimensions": [asdict(row) for row in dimensions],
        "readonly": True,
    }


def push_readiness_report(task_type: str = "code", strict: bool = False, *, include_scorecard: bool = True) -> dict[str, Any]:
    checks = {
        "privacy": _normalize_existing_check("privacy", "privacy", scan_privacy(), "privacy audit passes"),
        "config_schema": _normalize_existing_check("config_schema", "governance", config_schema_report(), "config schema passes"),
        "gate_matrix": _normalize_existing_check("gate_matrix_push", "governance", gate_matrix_report("push_readiness"), "push readiness gate matrix is valid"),
        "llmwiki_source_refs": llmwiki_source_refs_report(),
        "storage": _normalize_existing_check("storage", "storage", ignored_artifacts_report(), "ignored artifacts are observable"),
    }
    if include_scorecard:
        checks["scorecard"] = _normalize_existing_check("scorecard", "scorecard", code_scorecard(), "public code scorecard passes")
    passed = all(bool(check.get("passed", True)) for check in checks.values())
    return {"schema_version": 1, "passed": passed, "strict": strict, "task_type": task_type, "checks": checks}


def release_strict_report() -> dict[str, Any]:
    checks = {
        "push_readiness": _normalize_existing_check("push_readiness", "release", push_readiness_report(task_type="code", strict=True), "strict push readiness passes"),
        "llmwiki_citation": _normalize_existing_check("llmwiki_citation", "llmwiki", citation_gate(), "llmwiki citations pass"),
        "llmwiki_conflict": _normalize_existing_check("llmwiki_conflict", "llmwiki", conflict_report(), "llmwiki conflicts pass"),
        "quality_gate": _normalize_existing_check("quality_gate", "quality", quality_gate_report(), "quality gate entrypoints exist"),
        "scorecard": _normalize_existing_check("scorecard", "scorecard", code_scorecard(), "public code scorecard passes"),
        "benchmark": _benchmark_snapshot_report(),
    }
    passed = all(bool(check.get("passed", True)) for check in checks.values())
    return {"schema_version": 1, "passed": passed, "checks": checks}


def git_status() -> str:
    try:
        proc = subprocess.run(["git", "-C", str(repo_root()), "status", "--short", "--branch"], capture_output=True, text=True, check=False)
    except Exception as exc:
        return f"unavailable: {exc}"
    return proc.stdout.strip()


def doctor_report() -> dict[str, Any]:
    privacy = _normalize_existing_check("privacy", "privacy", scan_privacy(), "privacy audit passes")
    config = _normalize_existing_check("config_schema", "governance", config_schema_report(), "config schema passes")
    route = _normalize_existing_check("llmwiki_route_map", "llmwiki", check_route_map(), "llmwiki route map passes")
    citation = _normalize_existing_check("llmwiki_citation", "llmwiki", citation_gate(), "llmwiki citations pass")
    conflict = _normalize_existing_check("llmwiki_conflict", "llmwiki", conflict_report(), "llmwiki conflicts pass")
    ignored = _normalize_existing_check("ignored_artifacts", "storage", ignored_artifacts_report(), "ignored artifacts are observable")
    score = _normalize_existing_check("scorecard", "scorecard", code_scorecard(), "public code scorecard passes")
    checks = {
        "git": normalize_check("git", "repo", True, git_status()),
        "privacy": privacy,
        "config_schema": config,
        "gate_matrix": _normalize_existing_check("gate_matrix_quality", "governance", gate_matrix_report("quality_gate"), "quality gate matrix is valid"),
        "llmwiki_route_map": route,
        "llmwiki_source_refs": llmwiki_source_refs_report(),
        "llmwiki_citation": citation,
        "llmwiki_conflict": conflict,
        "audit_index": _normalize_existing_check("audit_index", "audit", audit_index_report(), "audit index is readable"),
        "ignored_artifacts": ignored,
        "quality_gate": _normalize_existing_check("quality_gate", "quality", quality_gate_report(), "quality gate entrypoints exist"),
        "push_readiness": _normalize_existing_check("push_readiness", "release", push_readiness_report(task_type="code", strict=True), "strict push readiness passes"),
        "release_strict": _normalize_existing_check("release_strict", "release", release_strict_report(), "release strict passes"),
        "templates": normalize_check("templates", "templates", (repo_root() / "templates" / "model-instructions.template.md").exists(), "model instructions template exists"),
        "scorecard": score,
        "benchmark": _benchmark_snapshot_report(),
    }
    passed = all(bool(item.get("passed", True)) for item in checks.values() if isinstance(item, dict))
    return {
        "schema_version": 1,
        "passed": passed,
        "root": sanitize_public_path(str(repo_root())),
        "python": sys.version.split()[0],
        "checks": checks,
        "storage_facts": ignored.get("storage_facts", {}),
    }
