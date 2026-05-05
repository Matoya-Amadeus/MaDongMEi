from __future__ import annotations

import json
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import db_path, ensure_layout

WORD_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")
PRIVATE_PATH_PATTERNS = [
    re.compile(r"(?i)(?:/Users|/Volumes|/private|/var/folders|/Library|/tmp)(?:/[^\s'\"`<>]+|(?:\s+[^\s'\"`<>]+))*"),
    re.compile(r"(?i)~(?:/[^\s'\"`<>]+)+"),
    re.compile(r"(?i)[A-Za-z]:\\[^\s'\"`<>]+(?:\\[^\s'\"`<>]+)*"),
]
PUBLIC_BUCKETS = ("memory", "decision", "faq", "wiki", "skill")
DEFAULT_TTL_DAYS: dict[str, int | None] = {
    "memory": 30,
    "decision": 365,
    "faq": 365,
    "wiki": None,
    "skill": None,
}
ROUTE_ALIASES = {
    "doc": "wiki",
    "docs": "wiki",
    "document": "wiki",
    "notes": "memory",
    "note": "memory",
    "procedure": "skill",
    "playbook": "skill",
    "guide": "skill",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sanitize_private_text(text: str) -> str:
    value = str(text)
    for pattern in PRIVATE_PATH_PATTERNS:
        value = pattern.sub("<private-path>", value)
    return value


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_private_text(value).strip()
    if isinstance(value, dict):
        return {str(key): sanitize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_value(item) for item in value]
    return value


def normalize_tags(tags: Any) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        tags = [tags]
    cleaned: list[str] = []
    for tag in tags:
        item = str(tag).strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for chunk in WORD_RE.findall(text.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", chunk):
            tokens.append(chunk)
            tokens.extend(chunk[i : i + 2] for i in range(len(chunk) - 1))
        else:
            tokens.append(chunk)
    return [token for token in tokens if token]


def normalize_route(value: Any) -> str:
    route = str(value or "").strip().lower()
    route = ROUTE_ALIASES.get(route, route)
    if route not in PUBLIC_BUCKETS:
        return "memory"
    return route


def normalize_ttl(value: Any, *, route: str) -> int | None:
    default = DEFAULT_TTL_DAYS.get(route, 30)
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        ttl = int(value)
        return None if ttl < 0 else ttl
    text = str(value).strip().lower()
    if not text:
        return default
    if text in {"none", "never", "infinite", "permanent", "perma"}:
        return None
    if text.endswith("days"):
        text = text[:-4]
    elif text.endswith("day"):
        text = text[:-3]
    elif text.endswith("d"):
        text = text[:-1]
    text = text.strip()
    if not text:
        return default
    try:
        ttl = int(float(text))
    except ValueError:
        match = re.search(r"(\d+)", text)
        if not match:
            return default
        ttl = int(match.group(1))
    return None if ttl < 0 else ttl


def default_route(payload: dict[str, Any]) -> str:
    for key in ("route", "bucket", "kind"):
        value = payload.get(key)
        if value:
            return normalize_route(value)
    return "memory"


def ensure_record(payload: dict[str, Any], *, default_source: str = "import") -> dict[str, Any]:
    record = sanitize_value(dict(payload))
    route = default_route(record)
    bucket = normalize_route(record.get("bucket") or route)
    source = str(record.get("source") or default_source).strip() or default_source
    reason = str(record.get("reason") or "").strip()
    source_ref = str(record.get("source_ref") or "").strip()
    workspace_id = str(record.get("workspace_id") or "").strip()
    idempotency = str(record.get("idempotency") or "").strip()

    record["id"] = str(record.get("id") or uuid.uuid4().hex)
    record["schema"] = int(record.get("schema") or 2)
    record["created_at"] = str(record.get("created_at") or iso_now())
    record["updated_at"] = str(record.get("updated_at") or record["created_at"])
    record["title"] = str(record.get("title") or "").strip()
    record["text"] = str(record.get("text") or "").strip()
    record["tags"] = normalize_tags(record.get("tags"))
    record["source"] = source
    record["kind"] = bucket
    record["bucket"] = bucket
    record["route"] = route
    record["confidence"] = max(0.0, min(1.0, float(record.get("confidence") or 0.0)))
    record["reason"] = reason
    record["source_ref"] = source_ref
    record["workspace_id"] = workspace_id
    record["idempotency"] = idempotency
    record["ttl"] = normalize_ttl(record.get("ttl"), route=bucket)
    return record


def record_is_expired(record: dict[str, Any], *, now: datetime | None = None) -> bool:
    ttl = record.get("ttl")
    if ttl is None:
        return False
    try:
        ttl_days = int(ttl)
    except (TypeError, ValueError):
        return False
    if ttl_days < 0:
        return False
    created_at = str(record.get("created_at", ""))
    if not created_at:
        return False
    try:
        created = parse_iso(created_at)
    except ValueError:
        return False
    horizon = created + timedelta(days=ttl_days)
    return (now or utc_now()) >= horizon


def prune_expired_records(
    records: Iterable[dict[str, Any]] | None = None,
    *,
    now: datetime | None = None,
    persist: bool = False,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    pool = list(records) if records is not None else load_records(path, prune=False)
    active = [record for record in pool if not record_is_expired(record, now=now)]
    if persist and len(active) != len(pool):
        write_records(active, path)
    return active


def load_records(path: Path | None = None, *, prune: bool = True) -> list[dict[str, Any]]:
    path = path or db_path()
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(ensure_record(payload))
    if prune:
        records = prune_expired_records(records)
    return records


def write_records(records: Iterable[dict[str, Any]], path: Path | None = None) -> None:
    path = path or db_path()
    default_path = db_path()
    if Path(path).expanduser() == default_path.expanduser():
        ensure_layout()
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
    payload = prune_expired_records(records)
    with path.open("w", encoding="utf-8") as handle:
        for record in payload:
            handle.write(json.dumps(ensure_record(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def capture_record(
    *,
    title: str,
    text: str,
    tags: Iterable[str] | None = None,
    source: str = "manual",
    kind: str = "memory",
    route: str | None = None,
    bucket: str | None = None,
    confidence: float = 0.0,
    reason: str = "",
    source_ref: str = "",
    ttl: int | float | str | None = None,
    idempotency: str = "",
    workspace_id: str = "",
    extra: dict[str, Any] | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    path = path or db_path()
    bucket_name = normalize_route(bucket or route or kind)
    payload: dict[str, Any] = {
        "title": title.strip(),
        "text": text.strip(),
        "tags": normalize_tags(tags),
        "source": source,
        "kind": bucket_name,
        "bucket": bucket_name,
        "route": normalize_route(route or bucket_name),
        "confidence": confidence,
        "reason": reason,
        "source_ref": source_ref,
        "ttl": ttl,
        "idempotency": idempotency,
        "workspace_id": workspace_id,
    }
    if extra:
        payload.update(extra)
    record = ensure_record(payload, default_source=source)
    records = load_records(path, prune=False)
    if record["idempotency"]:
        for existing in records:
            if str(existing.get("idempotency")) == record["idempotency"]:
                return existing
    records = prune_expired_records(records)
    records.append(record)
    write_records(records, path)
    return record


def bag(text: str) -> Counter[str]:
    return Counter(tokenize(text))


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = set(left) & set(right)
    dot = sum(left[token] * right[token] for token in intersection)
    if not dot:
        return 0.0
    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def score_record(query: str, record: dict[str, Any]) -> float:
    query_bag = bag(query)
    if not query_bag:
        return 0.0
    tags = " ".join(record.get("tags", []))
    doc_bag = bag(" ".join([
        str(record.get("title", "")),
        str(record.get("text", "")),
        tags,
        str(record.get("source", "")),
        str(record.get("kind", "")),
        str(record.get("bucket", "")),
        str(record.get("route", "")),
        str(record.get("reason", "")),
        str(record.get("source_ref", "")),
        str(record.get("workspace_id", "")),
    ]))
    if not doc_bag:
        return 0.0
    overlap = sum(min(query_bag[token], doc_bag[token]) for token in query_bag)
    coverage = overlap / max(sum(query_bag.values()), 1)
    cosine = cosine_similarity(query_bag, doc_bag)
    tag_hits = sum(1 for token in query_bag if token in {tag.lower() for tag in record.get("tags", [])})
    bucket_hits = sum(1 for token in query_bag if token in {record.get("bucket", ""), record.get("route", "")})
    tag_boost = min(0.2, 0.05 * (tag_hits + bucket_hits))
    score = min(1.0, (0.68 * coverage) + (0.32 * cosine) + tag_boost)
    return round(score, 4)


def search_records(
    query: str,
    records: Iterable[dict[str, Any]] | None = None,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    pool = list(records) if records is not None else load_records()
    if not query.strip():
        return recent_records(pool, limit=limit)
    scored: list[dict[str, Any]] = []
    for record in pool:
        score = score_record(query, record)
        if score > 0:
            item = dict(record)
            item["_score"] = score
            scored.append(item)
    scored.sort(key=lambda item: (float(item.get("_score", 0.0)), item.get("created_at", "")), reverse=True)
    return scored[:limit]


def recent_records(records: Iterable[dict[str, Any]] | None = None, *, limit: int = 10) -> list[dict[str, Any]]:
    pool = list(records) if records is not None else load_records()
    pool.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return pool[:limit]


def records_in_window(
    records: Iterable[dict[str, Any]] | None = None,
    *,
    days: int = 7,
) -> list[dict[str, Any]]:
    cutoff = utc_now() - timedelta(days=days)
    pool = list(records) if records is not None else load_records()
    selected: list[dict[str, Any]] = []
    for record in pool:
        created_at = str(record.get("created_at", ""))
        try:
            if parse_iso(created_at) >= cutoff:
                selected.append(record)
        except ValueError:
            continue
    selected.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return selected


def top_tags(records: Iterable[dict[str, Any]] | None = None, *, limit: int = 5) -> list[tuple[str, int]]:
    pool = list(records) if records is not None else load_records()
    counts: Counter[str] = Counter()
    for record in pool:
        counts.update(tag.lower() for tag in record.get("tags", []))
    return counts.most_common(limit)


def bucket_counts(records: Iterable[dict[str, Any]] | None = None, *, limit: int = 5) -> list[tuple[str, int]]:
    pool = list(records) if records is not None else load_records()
    counts: Counter[str] = Counter(str(record.get("bucket", "memory")) for record in pool)
    return counts.most_common(limit)


def route_counts(records: Iterable[dict[str, Any]] | None = None, *, limit: int = 5) -> list[tuple[str, int]]:
    pool = list(records) if records is not None else load_records()
    counts: Counter[str] = Counter(str(record.get("route", "memory")) for record in pool)
    return counts.most_common(limit)


def summarize(records: Iterable[dict[str, Any]] | None = None, *, limit: int = 5) -> dict[str, Any]:
    pool = list(records) if records is not None else load_records()
    return {
        "count": len(pool),
        "top_tags": top_tags(pool, limit=limit),
        "bucket_counts": bucket_counts(pool, limit=limit),
        "route_counts": route_counts(pool, limit=limit),
        "recent": recent_records(pool, limit=limit),
    }


def weekly_snapshot(records: Iterable[dict[str, Any]] | None = None, *, days: int = 7, limit: int = 5) -> dict[str, Any]:
    pool = records_in_window(records, days=days)
    return {
        "days": days,
        "count": len(pool),
        "top_tags": top_tags(pool, limit=limit),
        "bucket_counts": bucket_counts(pool, limit=limit),
        "route_counts": route_counts(pool, limit=limit),
        "recent": recent_records(pool, limit=limit),
    }


def export_jsonl(records: Iterable[dict[str, Any]] | None = None) -> str:
    pool = list(records) if records is not None else load_records()
    return "\n".join(json.dumps(ensure_record(record), ensure_ascii=False, sort_keys=True) for record in pool)


def import_jsonl(payload: str, *, replace: bool = False, path: Path | None = None) -> int:
    path = path or db_path()
    existing = [] if replace else load_records(path, prune=False)
    seen_ids = {str(item.get("id")) for item in existing if item.get("id")}
    seen_idempotency = {
        str(item.get("idempotency"))
        for item in existing
        if str(item.get("idempotency"))
    }
    added = 0
    for raw in payload.splitlines():
        line = raw.strip()
        if not line:
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            continue
        record = ensure_record(item)
        if record["id"] in seen_ids or (
            record["idempotency"] and record["idempotency"] in seen_idempotency
        ):
            continue
        existing.append(record)
        seen_ids.add(record["id"])
        if record["idempotency"]:
            seen_idempotency.add(record["idempotency"])
        added += 1
    write_records(existing, path)
    return added
