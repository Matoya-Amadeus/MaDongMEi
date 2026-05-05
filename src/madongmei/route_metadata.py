from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

_WORD_RE = re.compile(r"[a-z0-9_#+.-]+", re.IGNORECASE)
_CJK_RE = re.compile(r"[\u3400-\u9fff]")

CASUAL_HINTS = {
    "hello",
    "hi",
    "weather",
    "today",
    "nice",
    "lunch",
    "thanks",
    "thank",
    "你好",
    "天气",
    "午饭",
    "谢谢",
}
CAPTURE_HINTS = {
    "capture",
    "captured",
    "promote",
    "record",
    "document",
    "decision",
    "decisions",
    "canonical",
    "policy",
    "rule",
    "wiki",
    "knowledge",
    "沉淀",
    "记录",
    "写入",
    "捕获",
    "决策",
    "规则",
    "知识库",
}
EXPLICIT_CAPTURE_HINTS = {
    "capture",
    "captured",
    "promote",
    "record",
    "document",
    "沉淀",
    "记录",
    "写入",
    "捕获",
}
VALIDATION_HINTS = {
    "validate",
    "validation",
    "quality",
    "gate",
    "release",
    "install",
    "workflow",
    "bootstrap",
    "selfcheck",
    "smoke",
    "验证",
    "质量",
    "门禁",
    "发布",
    "安装",
    "流程",
}
MEMORY_CONTEXT_HINTS = {
    "reminder",
    "remember",
    "context",
    "background",
    "pre-hook",
    "bridge",
    "背景",
    "记忆",
    "上下文",
    "注入",
}
DOCS_HINTS = {
    "openai",
    "api",
    "api docs",
    "api 文档",
    "responses api",
    "chatgpt api",
    "readme",
    "readme.md",
    "文档",
    "README",
}
SECURITY_HINTS = {
    "security",
    "安全",
    "threat model",
    "威胁建模",
    "secure",
    "best practice",
    "best practices",
    "hardening",
    "加固",
    "trust boundary",
    "abuse path",
}
MEETING_HINTS = {
    "meeting",
    "会议",
    "agenda",
    "纪要",
    "会议材料",
    "pre-read",
    "attendee",
    "talking points",
}
SKILL_GOVERNANCE_HINTS = {
    "route registry",
    "request route",
    "capability route",
    "skill tool memory wiki",
    "skill dedupe",
    "重复",
    "合并",
    "合并策略",
    "registry",
    "路由模板",
    "路由",
    "治理",
    "强制校验",
    "新增能力",
    "能力路由",
}
IMPLEMENTATION_HINTS = {
    "fix",
    "repair",
    "refactor",
    "implementation",
    "plan",
    "spec",
    "prd",
    "typescript",
    "ts",
    "component",
    "test",
    "tests",
    "push",
    "stuck",
    "recover",
    "recovery",
    "修",
    "重构",
    "测试",
    "实施",
    "计划",
    "卡住",
    "恢复",
}


@dataclass(frozen=True)
class RouteSelection:
    mode: str = "none"
    selected: str = ""
    score: float = 0.0
    threshold: float = 0.0
    reason: str = "no metadata match"
    hits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["score"] = round(float(self.score), 4)
        payload["confidence"] = round(float(self.score), 4)
        payload["threshold"] = round(float(self.threshold), 4)
        return payload


def normalize(value: Any) -> str:
    """Normalize public routing text without leaking or depending on private state."""
    text = " ".join(str(value or "").split()).lower()
    return text.replace("_", " ").replace("-", " ")


def _ascii_tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in _WORD_RE.finditer(text or "")}


def _phrase_hit(haystack: str, phrase: str) -> bool:
    needle = normalize(phrase)
    if not needle:
        return False
    if _CJK_RE.search(needle):
        return needle in haystack
    if " " in needle:
        return needle in haystack
    return needle in _ascii_tokens(haystack)


def contains_any(text: str, needles: Iterable[Any]) -> list[str]:
    haystack = normalize(text)
    hits: list[str] = []
    seen: set[str] = set()
    for raw in needles:
        needle = str(raw or "").strip()
        key = normalize(needle)
        if not key or key in seen:
            continue
        if _phrase_hit(haystack, key):
            hits.append(needle)
            seen.add(key)
    return hits


def threshold_value(policy: Mapping[str, Any] | None, *keys: str, default: float = 0.45) -> float:
    if not isinstance(policy, Mapping):
        return default
    for key in keys:
        try:
            value = float(policy.get(key))
        except (TypeError, ValueError):
            continue
        if 0.0 <= value <= 1.0:
            return value
    return default


def classify_intent(query: str) -> str:
    text = normalize(query)
    validation_hits = contains_any(text, VALIDATION_HINTS)
    capture_hits = contains_any(text, EXPLICIT_CAPTURE_HINTS)
    casual_hits = contains_any(text, CASUAL_HINTS)
    memory_context_hits = contains_any(text, MEMORY_CONTEXT_HINTS)
    docs_hits = contains_any(text, DOCS_HINTS)
    security_hits = contains_any(text, SECURITY_HINTS)
    meeting_hits = contains_any(text, MEETING_HINTS)
    governance_hits = contains_any(text, SKILL_GOVERNANCE_HINTS)
    implementation_hits = contains_any(text, IMPLEMENTATION_HINTS)
    if casual_hits and not any((security_hits, meeting_hits, governance_hits, docs_hits, validation_hits, capture_hits, implementation_hits)) and len(_ascii_tokens(text)) <= 8:
        return "casual"
    if security_hits:
        return "security"
    if meeting_hits:
        return "meeting"
    if capture_hits:
        return "knowledge_capture"
    if governance_hits:
        return "skill_governance"
    if docs_hits and not capture_hits:
        return "docs"
    push_recovery_hits = contains_any(text, ["push", "推送", "recover", "recovery", "恢复", "卡住", "stuck", "失败"])
    if push_recovery_hits and (contains_any(text, ["fix", "repair", "修", "how", "怎么", "处理", "恢复"]) or validation_hits):
        return "implementation"
    action_validation_hits = [hit for hit in validation_hits if normalize(hit) not in {"install", "安装", "workflow", "流程", "bootstrap"}]
    if memory_context_hits and not any((capture_hits, docs_hits, security_hits, meeting_hits, governance_hits, push_recovery_hits, action_validation_hits)):
        return "memory"
    if implementation_hits or action_validation_hits:
        return "implementation"
    if docs_hits:
        return "docs"
    if memory_context_hits:
        return "memory"
    return "memory"


def _route_terms(route: Mapping[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in ("aliases", "positive_examples"):
        values = route.get(key, [])
        if isinstance(values, list):
            terms.extend(str(item) for item in values)
    for key in ("id", "name", "intent", "topic_id"):
        value = route.get(key)
        if value:
            terms.append(str(value))
    return terms


def _score_terms(query: str, route: Mapping[str, Any], *, id_key: str, threshold: float) -> tuple[float, list[str]]:
    text = normalize(query)
    alias_hits = contains_any(text, route.get("aliases", []))
    example_hits = contains_any(text, route.get("positive_examples", []))
    id_hits = contains_any(text, [route.get(id_key, ""), route.get("name", ""), route.get("intent", "")])
    negative_hits = contains_any(text, route.get("negative_examples", []))
    hits = [*alias_hits, *example_hits, *id_hits]
    score = 0.0
    if alias_hits:
        score += 0.18 * len(alias_hits)
    if example_hits:
        score += 0.32
    if id_hits:
        score += 0.08 * len(id_hits)
    if negative_hits:
        score -= 0.18 * len(negative_hits)
    boost = 0.0
    policy = route.get("threshold_policy", {})
    if isinstance(policy, Mapping):
        try:
            boost = float(policy.get("boost", 0.0) or 0.0)
        except (TypeError, ValueError):
            boost = 0.0
    return max(0.0, min(0.99, score + boost)), hits


def _suppressed(route: Mapping[str, Any], intent: str, score: float) -> str:
    rules = route.get("suppression_rules", [])
    if not isinstance(rules, list):
        return ""
    for rule in rules:
        if not isinstance(rule, Mapping):
            continue
        when_intent = str(rule.get("when_intent", "")).strip()
        if when_intent and when_intent == intent and score < 0.65:
            return str(rule.get("id", "suppressed")) or "suppressed"
    return ""


def score_skill_route(query: str, registry: Mapping[str, Any], *, intent: str | None = None) -> RouteSelection:
    resolved_intent = intent or classify_intent(query)
    best: RouteSelection | None = None
    for route in registry.get("skill_routes", []):
        if not isinstance(route, Mapping):
            continue
        route_id = str(route.get("id", "")).strip()
        if not route_id:
            continue
        threshold = threshold_value(route.get("threshold_policy"), "auto_load_threshold", "select_threshold", default=0.45)
        score, hits = _score_terms(query, route, id_key="id", threshold=threshold)
        if str(route.get("intent", "")).strip() == resolved_intent:
            score = min(0.99, score + 0.08)
        suppression = _suppressed(route, resolved_intent, score)
        if suppression:
            candidate = RouteSelection("none", "", score, threshold, f"metadata suppressed by {suppression}", hits)
        elif score >= threshold and hits:
            candidate = RouteSelection("selected", route_id, score, threshold, "metadata skill route selected", hits)
        else:
            candidate = RouteSelection("none", "", score, threshold, "metadata score below threshold", hits)
        if best is None or candidate.score > best.score or (candidate.score == best.score and candidate.selected > best.selected):
            best = candidate
    if best and best.mode == "selected":
        return best
    if best and best.score > 0:
        return RouteSelection("none", "", best.score, best.threshold, best.reason, best.hits)
    return RouteSelection()


def score_wiki_route(query: str, registry: Mapping[str, Any], *, intent: str | None = None) -> RouteSelection:
    resolved_intent = intent or classify_intent(query)
    best: RouteSelection | None = None
    for route in registry.get("wiki_routes", []):
        if not isinstance(route, Mapping):
            continue
        route_id = str(route.get("topic_id", "")).strip()
        if not route_id:
            continue
        band = route.get("route_threshold_band", {}) if isinstance(route.get("route_threshold_band", {}), Mapping) else {}
        threshold = threshold_value(band, "select", default=0.45)
        score, hits = _score_terms(query, route, id_key="topic_id", threshold=threshold)
        if resolved_intent == "knowledge_capture":
            score = min(0.99, score + 0.1)
        negative_route_hits = contains_any(query, route.get("negative_routes", []))
        if negative_route_hits:
            score = max(0.0, score - 0.25)
        if score >= threshold and hits:
            candidate = RouteSelection("selected", route_id, score, threshold, "metadata wiki route selected", hits)
        else:
            candidate = RouteSelection("none", "", score, threshold, "metadata score below threshold", hits)
        if best is None or candidate.score > best.score or (candidate.score == best.score and candidate.selected > best.selected):
            best = candidate
    if best and best.mode == "selected":
        return best
    if best and best.score > 0:
        return RouteSelection("none", "", best.score, best.threshold, best.reason, best.hits)
    return RouteSelection()


def choose_wiki_action(
    query: str,
    *,
    wiki_route: RouteSelection,
    plan: Mapping[str, Any] | None = None,
    intent: str | None = None,
) -> RouteSelection:
    resolved_intent = intent or classify_intent(query)
    plan_action = str((plan or {}).get("wiki_action", "") or "").strip()
    if wiki_route.mode == "selected" and resolved_intent == "knowledge_capture":
        return RouteSelection("selected", "promote", max(wiki_route.score, 0.55), wiki_route.threshold, "metadata capture route selected", wiki_route.hits)
    if wiki_route.mode == "selected" and contains_any(query, CAPTURE_HINTS):
        return RouteSelection("selected", "promote", max(wiki_route.score, 0.55), wiki_route.threshold, "metadata capture hint selected", wiki_route.hits)
    if plan_action and plan_action != "skip":
        return RouteSelection("selected", plan_action, float((plan or {}).get("confidence", 0.0) or 0.0), 0.55, "classified plan capture action", [])
    return RouteSelection("none", "skip", 0.0, 0.0, "no capture action", [])


def choose_tool_route(
    query: str,
    registry: Mapping[str, Any],
    *,
    memory_route: str,
    skill_route: RouteSelection,
    wiki_route: RouteSelection,
    intent: str | None = None,
) -> dict[str, Any]:
    resolved_intent = intent or classify_intent(query)
    candidates: list[dict[str, Any]] = []
    route_names = {memory_route}
    if skill_route.selected:
        route_names.update({"skill", skill_route.selected})
    if wiki_route.selected:
        route_names.update({"wiki", "decision", "faq", wiki_route.selected})
    for hint in registry.get("tool_hints", []):
        if not isinstance(hint, Mapping):
            continue
        hint_id = str(hint.get("id", "")).strip()
        if not hint_id:
            continue
        paired_routes = {str(item).strip() for item in hint.get("paired_routes", []) if str(item).strip()}
        paired_skills = {str(item).strip() for item in hint.get("paired_skills", []) if str(item).strip()}
        paired_intents = {str(item).strip() for item in hint.get("paired_intents", []) if str(item).strip()}
        keyword_hits = contains_any(query, hint.get("keywords", []))
        route_matched = bool(route_names & paired_routes) and resolved_intent != "casual"
        skill_matched = bool(skill_route.selected and skill_route.selected in paired_skills)
        intent_matched = bool(resolved_intent in paired_intents)
        matched = bool(keyword_hits) or route_matched or skill_matched or intent_matched
        if not matched:
            continue
        try:
            base_score = float(hint.get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            base_score = 0.0
        score = base_score
        if keyword_hits:
            score += min(len(keyword_hits), 4) * 0.04
            if resolved_intent == "memory" and not (skill_matched or intent_matched):
                score = min(score, base_score + min(len(keyword_hits), 2) * 0.02)
        if route_matched:
            score += 0.08
        if skill_matched:
            score += 0.1
        if intent_matched:
            score += 0.05
        threshold = threshold_value(hint.get("threshold_policy") if isinstance(hint.get("threshold_policy"), Mapping) else hint, "auto_hint_threshold", "threshold", default=0.6)
        if keyword_hits and resolved_intent == "memory" and not (skill_matched or intent_matched):
            score = min(score, max(0.0, base_score - 0.2 + min(len(keyword_hits), 2) * 0.02))
        if not (keyword_hits or skill_matched or intent_matched) and route_matched:
            score = min(score, base_score + 0.02)
        if resolved_intent == "memory" and route_matched and not (skill_matched or intent_matched):
            score = min(score, base_score + 0.02)
        if score < threshold:
            continue
        candidates.append(
            {
                "name": hint_id,
                "path": str(hint.get("path", "")).strip(),
                "score": round(min(score, 0.99), 4),
                "threshold": threshold,
                "route_matched": route_matched,
                "skill_matched": skill_matched,
                "intent_matched": intent_matched,
                "keyword_hits": keyword_hits,
            }
        )
    candidates.sort(key=lambda row: (float(row.get("score", 0.0)), str(row.get("name", ""))), reverse=True)
    top = candidates[0] if candidates else {}
    selected = str(top.get("name", ""))
    score = round(float(top.get("score", 0.0) or 0.0), 4)
    threshold = round(float(top.get("threshold", 0.6) or 0.6), 4)
    return {
        "mode": "auto_hint" if selected else "none",
        "selected": selected,
        "selected_path": str(top.get("path", "")),
        "score": score,
        "confidence": score,
        "threshold": threshold,
        "reason": f"selected={selected}; source=public-metadata" if selected else "no-tool-match",
        "candidates": candidates[:5],
        "auto_execute": False,
    }
