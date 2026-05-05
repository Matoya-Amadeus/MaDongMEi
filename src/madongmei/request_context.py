from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from .autopilot import classify_request, plan_to_dict
from .config import ensure_layout, repo_root
from .route_metadata import (
    RouteSelection,
    choose_tool_route,
    choose_wiki_action,
    classify_intent,
    score_skill_route,
    score_wiki_route,
)
from .store import load_records, sanitize_private_text, search_records, summarize

DEFAULT_BLOCK_MAX_CHARS = 1600
NO_CONTEXT_PROFILES = {"none", "off", "disabled", "no_context", "doubao"}


def _load_request_route_registry() -> dict[str, Any]:
    path = repo_root() / "config" / "capability" / "request-route-registry.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": 1, "tool_hints": []}


def _codex_context(query: str, *, profile: str, plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "repo": "MaDongMei",
        "request_kind": "public_pre_hook",
        "context_profile": profile,
        "query_excerpt": _compact(query, 240),
        "task_intent": str(plan.get("intent") or "memory"),
        "route": str(plan.get("memory_route") or plan.get("bucket") or "memory"),
        "workspace_id": str(plan.get("workspace_id") or "public"),
    }


def _tool_route(query: str, *, plan: Mapping[str, Any], registry: Mapping[str, Any]) -> dict[str, Any]:
    lowered = str(query or "").lower()
    route = str(plan.get("memory_route") or plan.get("bucket") or "memory")
    candidates: list[dict[str, Any]] = []
    for hint in registry.get("tool_hints", []):
        if not isinstance(hint, Mapping):
            continue
        paired_routes = {str(item).strip() for item in hint.get("paired_routes", []) if str(item).strip()}
        keywords = [str(item).strip().lower() for item in hint.get("keywords", []) if str(item).strip()]
        route_matched = route in paired_routes
        keyword_hits = [keyword for keyword in keywords if keyword in lowered]
        matched = route_matched or bool(keyword_hits)
        if not matched:
            continue
        score = float(hint.get("score", 0.0) or 0.0)
        if route_matched:
            score += 0.1
        score += min(len(keyword_hits), 3) * 0.06
        candidates.append({
            "name": str(hint.get("id", "")).strip(),
            "path": str(hint.get("path", "")).strip(),
            "score": score,
            "route_matched": route_matched,
            "keyword_hits": keyword_hits,
        })
    candidates.sort(key=lambda row: (float(row.get("score", 0.0)), str(row.get("name", ""))), reverse=True)
    top = candidates[0] if candidates else {}
    selected = str(top.get("name", ""))
    return {
        "mode": "auto_hint" if selected else "none",
        "selected": selected,
        "selected_path": str(top.get("path", "")),
        "score": round(float(top.get("score", 0.0) or 0.0), 4),
        "confidence": round(float(top.get("score", 0.0) or 0.0), 4),
        "threshold": 0.6,
        "reason": f"selected={selected}; source=public-registry" if selected else "no-tool-match",
        "candidates": candidates[:5],
        "auto_execute": False,
    }


def _route_trace(
    *,
    plan: Mapping[str, Any],
    tool_route: Mapping[str, Any],
    skill_route: RouteSelection,
    wiki_route: RouteSelection,
    capture_route: RouteSelection,
) -> dict[str, Any]:
    route = str(plan.get("memory_route") or plan.get("bucket") or "memory")
    return {
        "schema_version": 1,
        "injection_order": ["codex_context", "memory", "skill", "wiki", "tool", "capture"],
        "routes": {
            "memory": {
                "mode": "classified",
                "selected": route,
                "confidence": float(plan.get("confidence", 0.0) or 0.0),
                "reason": str(plan.get("reason", "")),
            },
            "skill": skill_route.to_dict(),
            "wiki": wiki_route.to_dict(),
            "tool": dict(tool_route),
            "capture": capture_route.to_dict(),
        },
    }


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _compact(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    text = sanitize_private_text(text)
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def context_profile(env: Mapping[str, str] | None = None) -> str:
    env_map = os.environ if env is None else env
    if _truthy(env_map.get("MADONGMEI_REQUEST_NO_CONTEXT")):
        return "no_context"
    raw = env_map.get("MADONGMEI_REQUEST_CONTEXT_PROFILE") or env_map.get("MADONGMEI_REQUEST_CONTEXT_PROFILE") or "default"
    profile = str(raw).strip().lower().replace("-", "_").replace(" ", "_") or "default"
    if profile in {"none", "off", "disabled"}:
        return "no_context"
    return profile


def request_context_enabled(env: Mapping[str, str] | None = None) -> bool:
    env_map = os.environ if env is None else env
    if context_profile(env_map) in NO_CONTEXT_PROFILES:
        return False
    raw = env_map.get("MADONGMEI_REQUEST_PREHOOK") or env_map.get("MEMORY_REQUEST_PREHOOK")
    if raw is None:
        return True
    return _truthy(raw)


def build_public_memory_block(payload: Mapping[str, Any], *, max_chars: int = DEFAULT_BLOCK_MAX_CHARS) -> str:
    lines = ["[MADONGMEI MEMORY]"]
    query = _compact(payload.get("query", ""), 220)
    if query:
        lines.append(f"query: {query}")
    summary = _compact(payload.get("summary", ""), 420)
    if summary:
        lines.append(f"summary: {summary}")
    plan = payload.get("plan", {})
    if isinstance(plan, Mapping):
        route = _compact(plan.get("memory_route") or plan.get("bucket") or "memory", 80)
        confidence = plan.get("confidence", 0)
        lines.append(f"route: {route} | confidence={float(confidence or 0):.3f}")
    rows = payload.get("retrieved_memories", [])
    if isinstance(rows, list) and rows:
        lines.append("hits:")
        for row in rows[:3]:
            if not isinstance(row, Mapping):
                continue
            title = _compact(row.get("title", "(untitled)"), 96)
            text = _compact(row.get("text", ""), 180)
            score = row.get("_score", row.get("score", 0))
            try:
                score_text = f" score={float(score):.3f}"
            except Exception:
                score_text = ""
            if text:
                lines.append(f"- {title}{score_text} — {text}")
            else:
                lines.append(f"- {title}{score_text}")
    else:
        lines.append("hits: none")
    block = "\n".join(lines).strip()
    if len(block) <= max_chars:
        return block
    return block[: max(1, max_chars - 1)].rstrip() + "…"


def prepare_public_request_context(
    query: str,
    *,
    env: Mapping[str, str] | None = None,
    topk: int = 5,
    max_chars: int = DEFAULT_BLOCK_MAX_CHARS,
) -> dict[str, Any]:
    ensure_layout()
    env_map = dict(os.environ if env is None else env)
    clean_query = _compact(query, 2048)
    enabled = request_context_enabled(env_map)
    records = load_records()
    summary = summarize(records, limit=3)
    plan = classify_request(clean_query or "public request", records=records)
    rows = search_records(clean_query, records=records, limit=topk) if clean_query else []
    plan_payload = plan_to_dict(plan)
    registry = _load_request_route_registry()
    intent = classify_intent(clean_query)
    plan_payload["intent"] = intent
    skill_route = score_skill_route(clean_query, registry, intent=intent)
    wiki_route = score_wiki_route(clean_query, registry, intent=intent)
    if wiki_route.mode == "selected":
        plan_payload["memory_route"] = "wiki"
        plan_payload["bucket"] = "wiki"
    elif skill_route.mode == "selected":
        plan_payload["memory_route"] = "skill"
        plan_payload["bucket"] = "skill"
    capture_route = choose_wiki_action(clean_query, wiki_route=wiki_route, plan=plan_payload, intent=intent)
    plan_payload["wiki_action"] = capture_route.selected or "skip"
    tool_route = choose_tool_route(
        clean_query,
        registry,
        memory_route=str(plan_payload.get("memory_route") or plan_payload.get("bucket") or "memory"),
        skill_route=skill_route,
        wiki_route=wiki_route,
        intent=intent,
    )
    payload: dict[str, Any] = {
        "schema_version": 1,
        "public": True,
        "enabled": enabled,
        "used": False,
        "query": clean_query,
        "context_profile": context_profile(env_map),
        "summary": f"{summary['count']} public record(s); buckets={summary.get('bucket_counts', [])}",
        "plan": plan_payload,
        "retrieved_memories": rows,
        "personal_recall": {
            "route": {
                "mode": "public-summary",
                "summary_count": len(rows),
                "raw_count": 0,
                "reason": "public MaDongMei records only",
            },
            "rows": rows,
        },
        "repo": repo_root().name,
        "codex_context": _codex_context(clean_query, profile=context_profile(env_map), plan=plan_payload),
        "tool_route": tool_route,
        "route_trace": _route_trace(
            plan=plan_payload,
            tool_route=tool_route,
            skill_route=skill_route,
            wiki_route=wiki_route,
            capture_route=capture_route,
        ),
        "reason": "ok" if enabled else "disabled",
    }
    block = build_public_memory_block(payload, max_chars=max_chars) if enabled else ""
    payload["block"] = block
    payload["block_chars"] = len(block)
    payload["used"] = bool(block)
    return json.loads(json.dumps(payload, ensure_ascii=False, default=str))
