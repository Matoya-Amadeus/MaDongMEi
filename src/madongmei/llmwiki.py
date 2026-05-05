from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import repo_root


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def template_route_map() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at_utc": now_iso(),
        "public_template": True,
        "topic_count": 3,
        "routes": [
            {
                "topic": "public_memory_installation",
                "preferred_surface": "wiki",
                "query": "public memory installation",
                "route": "knowledge/wiki/README.md",
                "source_ref": "templates/llmwiki-row.template.jsonl",
                "claim": "Installation guidance is represented as a public template.",
            },
            {
                "topic": "public_skill_template",
                "preferred_surface": "skill",
                "query": "public reusable workflow skill",
                "route": "templates/skill-page.template.md",
                "source_ref": "templates/skill-page.template.md",
                "claim": "Skill bodies are template-only in the public bundle.",
            },
            {
                "topic": "public_privacy_boundary",
                "preferred_surface": "governance",
                "query": "privacy boundary public projection",
                "route": "config/public-projection.yaml",
                "source_ref": "config/public-projection.yaml",
                "claim": "Private content is omitted or templated by projection policy.",
            },
        ],
    }


def route_map_path() -> Path:
    return repo_root() / "config" / "capability" / "llmwiki-route-map.json"


def load_route_map() -> dict[str, Any]:
    path = route_map_path()
    if not path.exists():
        return template_route_map()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return template_route_map()
    if not isinstance(data, dict):
        return template_route_map()
    data.setdefault("schema_version", 1)
    data.setdefault("public_template", True)
    data.setdefault("routes", [])
    data["topic_count"] = len(data.get("routes", []))
    return data


def check_route_map() -> dict[str, Any]:
    data = load_route_map()
    violations: list[str] = []
    for idx, row in enumerate(data.get("routes", [])):
        if not isinstance(row, dict):
            violations.append(f"routes[{idx}] is not object")
            continue
        for key in ("topic", "route", "source_ref", "claim"):
            if not str(row.get(key, "")).strip():
                violations.append(f"routes[{idx}].{key} missing")
        ref = str(row.get("source_ref", ""))
        if ref.startswith(("/", "tmp/", "var/")) or ".." in Path(ref).parts:
            violations.append(f"routes[{idx}].source_ref is not public relative")
    return {
        "schema_version": 1,
        "passed": not violations,
        "route_count": len(data.get("routes", [])),
        "violations": violations,
        "public_template": True,
    }


def citation_gate() -> dict[str, Any]:
    check = check_route_map()
    return {
        "schema_version": 1,
        "passed": check["passed"],
        "grounded": 1.0 if check["passed"] else 0.0,
        "citation_complete": check["route_count"],
        "violations": check["violations"],
    }


def conflict_report() -> dict[str, Any]:
    data = load_route_map()
    topics: dict[str, int] = {}
    for row in data.get("routes", []):
        if isinstance(row, dict):
            topic = str(row.get("topic", "")).strip()
            if topic:
                topics[topic] = topics.get(topic, 0) + 1
    conflicts = [topic for topic, count in topics.items() if count > 1]
    return {
        "schema_version": 1,
        "passed": not conflicts,
        "total_groups": len(topics),
        "conflict_groups": len(conflicts),
        "unresolved_conflicts": len(conflicts),
        "conflicts": conflicts,
    }
