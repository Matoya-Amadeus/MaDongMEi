from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import repo_root, skill_dir, wiki_dir
from .store import (
    capture_record,
    load_records,
    prune_expired_records,
    sanitize_private_text,
    search_records,
)

SKILL_HINTS = (
    "how to",
    "bootstrap",
    "install",
    "setup",
    "configure",
    "workflow",
    "command",
    "script",
    "run ",
    "validate",
    "verification",
    "smoke",
    "troubleshoot",
    "debug",
    "fix",
    "repair",
    "automate",
    "自动化",
    "安装",
    "配置",
    "脚本",
    "验证",
    "排障",
    "修复",
)
WIKI_HINTS = (
    "rule",
    "policy",
    "canonical",
    "contract",
    "definition",
    "reference",
    "principle",
    "standard",
    "fact",
    "facts",
    "document",
    "knowledge",
    "wiki",
    "规则",
    "原则",
    "定义",
    "规范",
    "事实",
    "文档",
    "知识",
)
DECISION_HINTS = (
    "decision",
    "decide",
    "selected",
    "choose",
    "chosen",
    "approved",
    "adopt",
    "final",
    "we will",
    "go with",
    "决定",
    "选定",
    "采用",
    "确认",
)
FAQ_HINTS = (
    "?",
    "what ",
    "why ",
    "how ",
    "can ",
    "could ",
    "should ",
    "does ",
    "do ",
    "whether",
    "是否",
    "能否",
    "为什么",
    "怎样",
    "怎么",
)
MEMORY_HINTS = (
    "remember",
    "note",
    "memo",
    "background",
    "context",
    "keep",
    "缓存",
    "记忆",
    "背景",
)


@dataclass(frozen=True)
class RequestPlan:
    query: str
    title: str
    workspace_id: str
    source_ref: str
    idempotency_key: str
    memory_route: str
    skill_route: str
    wiki_action: str
    confidence: float
    reason: str
    bucket: str
    recall_id: str = ""
    recall_bucket: str = ""
    recall_score: float = 0.0
    proposal_path: str = ""


def plan_to_dict(plan: RequestPlan) -> dict[str, Any]:
    return asdict(plan)


def _collapse(text: str) -> str:
    return " ".join(str(text).split())


def _first_line(text: str) -> str:
    for line in str(text).splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def normalize_query(text: str | None) -> str:
    return _collapse(sanitize_private_text(text or "").strip())


def derive_title(query: str, fallback: str = "Autopilot note") -> str:
    first = _first_line(query)
    if not first:
        return fallback
    words = first.split()
    if len(words) <= 12 and len(first) <= 80:
        return first
    snippet = " ".join(words[:12]).strip()
    return snippet[:80].rstrip() or fallback


def stable_hash(*parts: str) -> str:
    payload = "\n".join(_collapse(part) for part in parts if part is not None)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _matches(text: str, needles: Iterable[str]) -> list[str]:
    hits: list[str] = []
    haystack = text.lower()
    for needle in needles:
        if needle.lower() in haystack:
            hits.append(needle)
    return hits


def _score_bucket(text: str, *, needles: Iterable[str], base: float, per_hit: float) -> tuple[float, list[str]]:
    hits = _matches(text, needles)
    score = base + (per_hit * len(hits))
    if "?" in text and any(token in {"faq", "how ", "why ", "what "} for token in needles):
        score += 0.05
    return min(score, 0.99), hits


def _best_route(text: str) -> tuple[str, float, list[str]]:
    skill_score, skill_hits = _score_bucket(text, needles=SKILL_HINTS, base=0.24, per_hit=0.13)
    wiki_score, wiki_hits = _score_bucket(text, needles=WIKI_HINTS, base=0.22, per_hit=0.11)
    decision_score, decision_hits = _score_bucket(text, needles=DECISION_HINTS, base=0.2, per_hit=0.14)
    faq_score, faq_hits = _score_bucket(text, needles=FAQ_HINTS, base=0.18, per_hit=0.09)
    memory_score, memory_hits = _score_bucket(text, needles=MEMORY_HINTS, base=0.2, per_hit=0.08)

    candidates = {
        "skill": (skill_score, skill_hits),
        "wiki": (wiki_score, wiki_hits),
        "decision": (decision_score, decision_hits),
        "faq": (faq_score, faq_hits),
        "memory": (memory_score, memory_hits),
    }
    bucket, (score, hits) = max(candidates.items(), key=lambda item: item[1][0])
    if score < 0.55:
        return "memory", max(score, 0.38), hits
    if bucket == "faq" and score < 0.65 and len(text.split()) < 6:
        return "memory", 0.42, hits
    return bucket, score, hits


def _recall_hit(query: str, records: Iterable[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    if not query.strip():
        return None
    matches = search_records(query, records=records, limit=3)
    return matches[0] if matches else None


def classify_request(
    query: str,
    *,
    title: str = "",
    workspace_id: str = "",
    source_ref: str = "",
    idempotency_key: str = "",
    records: Iterable[dict[str, Any]] | None = None,
) -> RequestPlan:
    clean_query = normalize_query(query)
    resolved_title = _collapse(title).strip() or derive_title(clean_query)
    workspace = _collapse(workspace_id).strip() or "public"
    source = sanitize_private_text(source_ref).strip() or "public-input"
    recall = _recall_hit(clean_query, records)

    bucket, confidence, hits = _best_route(clean_query)
    reason_parts: list[str] = []
    if hits:
        reason_parts.append(f"matched {bucket} hints: {', '.join(hits[:4])}")
    else:
        reason_parts.append("no strong route hints")

    if recall and float(recall.get("_score", 0.0)) >= 0.75:
        recall_bucket = str(recall.get("bucket") or recall.get("route") or "memory")
        if recall_bucket in {"memory", "decision", "faq", "wiki", "skill"} and (
            recall_bucket == bucket or bucket == "memory"
        ):
            bucket = recall_bucket
            confidence = max(confidence, float(recall.get("_score", 0.0)))
            reason_parts.append(
                f"recall matched {sanitize_private_text(str(recall.get('title') or recall.get('id') or 'record'))}"
            )
        elif float(recall.get("_score", 0.0)) > confidence:
            confidence = float(recall.get("_score", 0.0))
            reason_parts.append(f"recall reinforced {recall_bucket}")

    if bucket == "memory" and confidence < 0.55:
        reason_parts.append("fallback to memory-only")

    route = bucket
    wiki_action = "promote" if bucket in {"wiki", "decision", "faq"} and confidence >= 0.55 else "skip"
    skill_route = ""
    proposal_path = ""
    if bucket == "skill" and confidence >= 0.55:
        slug = slugify(resolved_title or clean_query or "skill")
        skill_route = display_path(skill_dir() / "published" / slug / "SKILL.md")
        proposal_path = skill_route
        wiki_action = "skip"
    elif bucket in {"wiki", "decision", "faq"} and confidence >= 0.55:
        slug = slugify(resolved_title or clean_query or bucket)
        proposal_path = display_path(wiki_dir() / bucket / f"{slug}.md")

    if not idempotency_key.strip():
        idempotency_key = stable_hash(workspace, source, route, resolved_title, clean_query)

    recall_id = str(recall.get("id") or "") if recall else ""
    recall_bucket = str(recall.get("bucket") or recall.get("route") or "") if recall else ""
    return RequestPlan(
        query=clean_query,
        title=resolved_title,
        workspace_id=workspace,
        source_ref=source,
        idempotency_key=idempotency_key,
        memory_route=route,
        skill_route=skill_route,
        wiki_action=wiki_action,
        confidence=round(confidence, 4),
        reason="; ".join(reason_parts),
        bucket=route,
        recall_id=recall_id,
        recall_bucket=recall_bucket,
        recall_score=round(float(recall.get("_score", 0.0)), 4) if recall else 0.0,
        proposal_path=proposal_path,
    )


def slugify(text: str) -> str:
    cleaned = normalize_query(text).lower()
    cleaned = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    if cleaned:
        return cleaned[:80]
    return "item"


def display_path(path: Path) -> str:
    root = repo_root().resolve()
    try:
        return str(path.resolve().relative_to(root))
    except Exception:
        return sanitize_private_text(str(path))


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id", ""),
        "title": record.get("title", ""),
        "route": record.get("route", ""),
        "bucket": record.get("bucket", ""),
        "confidence": record.get("confidence", 0.0),
        "reason": record.get("reason", ""),
        "source_ref": record.get("source_ref", ""),
        "workspace_id": record.get("workspace_id", ""),
        "idempotency": record.get("idempotency", ""),
        "ttl": record.get("ttl"),
        "created_at": record.get("created_at", ""),
    }


def render_wiki_page(record: dict[str, Any], plan: RequestPlan) -> str:
    title = str(record.get("title") or plan.title or "Untitled")
    body = str(record.get("text") or "").strip()
    tags = ", ".join(str(tag) for tag in record.get("tags", []))
    lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"id: {json.dumps(str(record.get('id', '')), ensure_ascii=False)}",
        f"route: {json.dumps(str(record.get('route', '')), ensure_ascii=False)}",
        f"bucket: {json.dumps(str(record.get('bucket', '')), ensure_ascii=False)}",
        f"confidence: {json.dumps(str(record.get('confidence', 0.0)), ensure_ascii=False)}",
        f"source_ref: {json.dumps(str(record.get('source_ref', '')), ensure_ascii=False)}",
        f"workspace_id: {json.dumps(str(record.get('workspace_id', '')), ensure_ascii=False)}",
        f"idempotency: {json.dumps(str(record.get('idempotency', '')), ensure_ascii=False)}",
        "---",
        f"# {title}",
        "",
        body or "No body provided.",
        "",
        "## Metadata",
        f"- route: {record.get('route', '')}",
        f"- bucket: {record.get('bucket', '')}",
        f"- confidence: {record.get('confidence', 0.0)}",
        f"- reason: {record.get('reason', '')}",
        f"- source_ref: {record.get('source_ref', '')}",
        f"- workspace_id: {record.get('workspace_id', '')}",
        f"- idempotency: {record.get('idempotency', '')}",
    ]
    if tags:
        lines.append(f"- tags: {tags}")
    return "\n".join(lines).strip() + "\n"


def render_skill_doc(record: dict[str, Any], plan: RequestPlan) -> str:
    title = str(record.get("title") or plan.title or "Untitled")
    body = str(record.get("text") or "").strip()
    lines = [
        f"# {title}",
        "",
        "## When to use",
        f"- Use this public skill when the request matches: {plan.reason}.",
        "",
        "## Steps",
    ]
    if body:
        for line in body.splitlines():
            stripped = line.strip()
            if stripped:
                lines.append(f"- {stripped}")
    else:
        lines.append("- No steps provided.")
    lines.extend(
        [
            "",
            "## Metadata",
            f"- route: {record.get('route', '')}",
            f"- bucket: {record.get('bucket', '')}",
            f"- confidence: {record.get('confidence', 0.0)}",
            f"- source_ref: {record.get('source_ref', '')}",
            f"- workspace_id: {record.get('workspace_id', '')}",
            f"- idempotency: {record.get('idempotency', '')}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def write_wiki_page(record: dict[str, Any], plan: RequestPlan, root: Path | None = None) -> Path:
    root = root or wiki_dir()
    slug = slugify(str(record.get("title") or plan.title or record.get("id") or "wiki"))
    path = root / str(record.get("bucket") or plan.bucket) / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_wiki_page(record, plan), encoding="utf-8")
    return path


def write_skill_doc(record: dict[str, Any], plan: RequestPlan, root: Path | None = None) -> Path:
    root = root or skill_dir()
    slug = slugify(str(record.get("title") or plan.title or record.get("id") or "skill"))
    path = root / "published" / slug / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_skill_doc(record, plan), encoding="utf-8")
    return path


def render_receipt(receipt: dict[str, Any]) -> str:
    plan = receipt["plan"]
    lines = [
        "Autopilot receipt",
        f"- route: {plan['memory_route']}",
        f"- bucket: {plan['bucket']}",
        f"- confidence: {plan['confidence']}",
        f"- reason: {plan['reason']}",
        f"- dry_run: {receipt['dry_run']}",
    ]
    if receipt.get("record"):
        record = receipt["record"]
        lines.append(f"- record: {record['id']} ({record['title']})")
    wiki = receipt.get("wiki", {})
    if wiki.get("path"):
        lines.append(f"- wiki: {wiki['action']} {wiki['path']}")
    skill = receipt.get("skill", {})
    if skill.get("path"):
        lines.append(f"- skill: {skill['path']}")
    if receipt.get("cleanup", {}).get("pruned"):
        lines.append(f"- pruned: {receipt['cleanup']['pruned']}")
    return "\n".join(lines)


def run_autopilot(
    query: str,
    *,
    title: str = "",
    tags: Iterable[str] | None = None,
    workspace_id: str = "",
    source_ref: str = "",
    idempotency_key: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    layout = dict()
    layout["wiki_dir"] = wiki_dir()
    layout["skill_dir"] = skill_dir()
    records = load_records(prune=False)
    pruned = prune_expired_records(records, persist=True)
    plan = classify_request(
        query,
        title=title,
        workspace_id=workspace_id,
        source_ref=source_ref,
        idempotency_key=idempotency_key,
        records=pruned,
    )
    proposed_record = {
        "id": stable_hash(plan.workspace_id, plan.source_ref, plan.idempotency_key, plan.query),
        "title": plan.title,
        "text": plan.query,
        "tags": ["autopilot", plan.bucket, *(list(tags or []))],
        "source": "autopilot",
        "kind": plan.bucket,
        "route": plan.memory_route,
        "bucket": plan.bucket,
        "confidence": plan.confidence,
        "reason": plan.reason,
        "source_ref": plan.source_ref,
        "workspace_id": plan.workspace_id,
        "idempotency": plan.idempotency_key,
        "ttl": None if plan.bucket in {"wiki", "skill"} else 365,
    }
    receipt: dict[str, Any] = {
        "dry_run": dry_run,
        "query": plan.query,
        "plan": plan_to_dict(plan),
        "recall": None,
        "record": _record_summary(proposed_record),
        "wiki": {"action": plan.wiki_action, "path": ""},
        "skill": {"path": ""},
        "cleanup": {"pruned": max(0, len(records) - len(pruned))},
        "layout": {key: display_path(value) for key, value in layout.items()},
    }
    if plan.recall_id:
        receipt["recall"] = {
            "id": plan.recall_id,
            "bucket": plan.recall_bucket,
            "score": plan.recall_score,
        }

    if dry_run:
        if plan.proposal_path:
            if plan.bucket == "skill":
                receipt["skill"]["path"] = plan.proposal_path
            else:
                receipt["wiki"]["path"] = plan.proposal_path
        return receipt

    record = capture_record(
        title=plan.title,
        text=plan.query,
        tags=proposed_record["tags"],
        source="autopilot",
        kind=plan.bucket,
        route=plan.memory_route,
        bucket=plan.bucket,
        confidence=plan.confidence,
        reason=plan.reason,
        source_ref=plan.source_ref,
        ttl=proposed_record["ttl"],
        idempotency=plan.idempotency_key,
        workspace_id=plan.workspace_id,
        extra={"autopilot": True, "id": proposed_record["id"]},
    )
    receipt["record"] = _record_summary(record)

    if plan.wiki_action == "promote":
        wiki_path = write_wiki_page(record, plan)
        receipt["wiki"] = {"action": plan.wiki_action, "path": display_path(wiki_path)}
    if plan.bucket == "skill" and plan.confidence >= 0.55:
        skill_path = write_skill_doc(record, plan)
        receipt["skill"] = {"path": display_path(skill_path)}
    return receipt


def load_public_snapshot(query: str, *, limit: int = 3) -> list[dict[str, Any]]:
    return [dict(item) for item in search_records(query, limit=limit)]
