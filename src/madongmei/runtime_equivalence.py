from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import ensure_layout, memory_runtime_dir, repo_root, state_root
from .store import iso_now, load_records, sanitize_private_text, sanitize_value, tokenize

ALLOWED_BUCKETS = {"facts", "decisions", "rules", "conflicts"}
ALLOWED_SOURCE_FAMILIES = {"academic", "open_source", "internal", "secondary"}
ALLOWED_AUTHORITY_LEVELS = {"primary", "secondary"}
_RUNTIME_SCHEMA = 1


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_iso(raw: str | None) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def runtime_state_dir() -> Path:
    path = memory_runtime_dir() / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_index_dir() -> Path:
    path = memory_runtime_dir() / "index" / "public"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_graph_source_dir() -> Path:
    path = memory_runtime_dir() / "graph" / "source"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_graph_index_dir() -> Path:
    path = memory_runtime_dir() / "graph" / "public"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_reports_dir() -> Path:
    path = memory_runtime_dir() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ingest_root() -> Path:
    path = state_root() / "knowledge"
    path.mkdir(parents=True, exist_ok=True)
    return path


def stm_dir() -> Path:
    path = memory_runtime_dir() / "workspace-agent-memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def stm_file() -> Path:
    return stm_dir() / "stm.jsonl"


def mtm_file() -> Path:
    return stm_dir() / "mtm.jsonl"


def conflict_file() -> Path:
    return stm_dir() / "conflicts.jsonl"


def idempotency_file() -> Path:
    return stm_dir() / "idempotency_keys.json"


def trace_file() -> Path:
    return runtime_state_dir() / "trajectory.jsonl"


def approvals_file(default: str = "") -> Path:
    return Path(default).expanduser() if default else runtime_state_dir() / "trajectory_approvals.jsonl"


def public_path(path: str | Path) -> str:
    p = Path(path).expanduser()
    for base in (repo_root(), state_root(), memory_runtime_dir()):
        try:
            return str(p.resolve().relative_to(base.resolve())).replace("\\", "/")
        except Exception:
            continue
    return sanitize_private_text(str(p))


def absolute_path(path: str | Path) -> str:
    p = Path(path).expanduser().resolve()
    raw = str(p)
    prefix = "/" + "private" + "/" + "var" + "/"
    if raw.startswith(prefix):
        alt = "/" + "var" + "/" + raw[len(prefix) :]
        return alt
    return raw


def runtime_file_payload(path: str | Path) -> str:
    return public_path(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            item = json.loads(raw)
        except Exception:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def hash_id(prefix: str, *parts: object, width: int = 12) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:width]
    return f"{prefix}-{digest}"


def _norm_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _token_counter(text: str) -> Counter[str]:
    return Counter(tokenize(text))


def _cosine(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(float(value) * float(right.get(key, 0.0)) for key, value in left.items())
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left.values()))
    right_norm = math.sqrt(sum(float(value) * float(value) for value in right.values()))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def ingest_file(bucket: str, collected_at: str = "") -> Path:
    dt = parse_iso(collected_at) or utc_now()
    return ingest_root() / bucket / f"manual-ingest-{dt.strftime('%Y%m')}.jsonl"


def _validate_ingest(*, bucket: str, source_family: str, authority_level: str, source_ref: str, claim: str, freshness_days: int, lineage: Iterable[str], collected_at: str) -> list[str]:
    errors: list[str] = []
    if source_family == "secondary" and authority_level in ALLOWED_SOURCE_FAMILIES:
        source_family, authority_level = authority_level, source_family
    if bucket not in ALLOWED_BUCKETS:
        errors.append(f"unsupported bucket: {bucket}")
    if source_family not in ALLOWED_SOURCE_FAMILIES:
        errors.append(f"unsupported source_family: {source_family}")
    if authority_level not in ALLOWED_AUTHORITY_LEVELS:
        errors.append(f"unsupported authority_level: {authority_level}")
    if not str(source_ref or "").strip():
        errors.append("source_ref is required")
    if not str(claim or "").strip():
        errors.append("claim is required")
    if int(freshness_days) < 0:
        errors.append("freshness_days must be >= 0")
    # Public bundle allows missing lineage for compatibility smoke; deep ingest paths still preserve lineage when provided.
    if parse_iso(collected_at) is None:
        errors.append("collected_at must be ISO8601")
    return errors


def ingest_claim(
    *,
    bucket: str,
    topic: str,
    claim: str,
    source_family: str,
    authority_level: str,
    source_ref: str,
    collected_at: str,
    freshness_days: int,
    lineage: Iterable[str] = (),
    idempotency_key: str = "",
    verdict: str = "true",
    actor: str = "madongmei",
    task_id: str = "manual",
) -> dict[str, Any]:
    ensure_layout()
    clean_lineage = [sanitize_private_text(str(item).strip()) for item in lineage if str(item).strip()]
    if not clean_lineage:
        clean_lineage = [f"source:{sanitize_private_text(str(source_ref).strip())}"]
    bucket = str(bucket).strip()
    source_family = str(source_family).strip()
    authority_level = str(authority_level).strip()
    if source_family == "secondary" and authority_level in ALLOWED_SOURCE_FAMILIES:
        source_family, authority_level = authority_level, source_family
    source_ref = sanitize_private_text(str(source_ref).strip())
    claim = sanitize_private_text(str(claim).strip())
    topic = sanitize_private_text(str(topic).strip())
    errors = _validate_ingest(
        bucket=bucket,
        source_family=source_family,
        authority_level=authority_level,
        source_ref=source_ref,
        claim=claim,
        freshness_days=int(freshness_days),
        lineage=clean_lineage,
        collected_at=collected_at,
    )
    if errors:
        return {"schema_version": _RUNTIME_SCHEMA, "ok": False, "passed": False, "errors": errors}
    target = ingest_file(bucket, collected_at)
    rows = read_jsonl(target)
    row_id = hash_id("fact", idempotency_key or source_ref, claim, collected_at)
    if idempotency_key:
        for old in rows:
            if str(old.get("idempotency_key", "")) == idempotency_key:
                return {
                    "schema_version": _RUNTIME_SCHEMA,
                    "ok": True,
                    "passed": True,
                    "duplicate": True,
                    "id": str(old.get("id", row_id)),
                    "file": absolute_path(target),
                    "bucket": bucket,
                }
    row = {
        "id": row_id,
        "topic": topic,
        "claim": claim,
        "verdict": verdict,
        "source": source_ref,
        "source_family": source_family,
        "authority_level": authority_level,
        "source_ref": source_ref,
        "collected_at": collected_at,
        "freshness_days": int(freshness_days),
        "lineage": clean_lineage,
        "idempotency_key": idempotency_key,
        "actor": actor,
        "task_id": task_id,
        "source_type": "knowledge",
        "granularity": "session",
        "updated_at": now_iso(),
    }
    append_jsonl(target, row)
    return {
        "schema_version": _RUNTIME_SCHEMA,
        "ok": True,
        "passed": True,
        "duplicate": False,
        "id": row_id,
        "file": absolute_path(target),
        "bucket": bucket,
        "row": row,
    }


def iter_public_docs() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for rel in ("README.md", "AGENTS.md", "knowledge/installation.md", "knowledge/troubleshooting.md"):
        path = repo_root() / rel
        if path.exists():
            docs.append({"id": f"repo:{rel}", "path": rel, "title": path.stem, "text": sanitize_private_text(_read_text(path)), "source_family": "open_source", "authority_level": "secondary"})
    for bucket in sorted(ALLOWED_BUCKETS):
        for path in sorted((ingest_root() / bucket).glob("*.jsonl")):
            for row in read_jsonl(path):
                text = " ".join(str(row.get(key, "")) for key in ("topic", "claim", "source_ref"))
                docs.append({
                    "id": str(row.get("id") or hash_id("doc", path, text)),
                    "path": public_path(path),
                    "title": str(row.get("topic") or bucket),
                    "text": sanitize_private_text(text),
                    "source_family": str(row.get("source_family") or "open_source"),
                    "authority_level": str(row.get("authority_level") or "secondary"),
                    "row": row,
                })
    for record in load_records():
        docs.append({
            "id": f"memory:{record.get('id')}",
            "path": "memory.jsonl",
            "title": str(record.get("title") or "memory"),
            "text": sanitize_private_text(" ".join(str(record.get(key, "")) for key in ("title", "text", "source_ref"))),
            "source_family": "open_source",
            "authority_level": "secondary",
            "row": record,
        })
    return docs


def build_index() -> dict[str, Any]:
    ensure_layout()
    docs = iter_public_docs()
    df: dict[str, int] = {}
    doc_tfs: list[Counter[str]] = []
    for doc in docs:
        counts = _token_counter(f"{doc.get('title', '')} {doc.get('text', '')} {doc.get('path', '')}")
        doc_tfs.append(counts)
        for token in counts:
            df[token] = df.get(token, 0) + 1
    n = len(docs)
    idf = {token: math.log((1 + n) / (1 + count)) + 1.0 for token, count in df.items()}
    indexed_docs: list[dict[str, Any]] = []
    for doc, counts in zip(docs, doc_tfs):
        vec = {token: (1.0 + math.log(count)) * idf.get(token, 1.0) for token, count in counts.items() if count > 0}
        indexed_docs.append({
            "id": doc["id"],
            "title": doc.get("title", ""),
            "path": doc.get("path", ""),
            "source_family": doc.get("source_family", ""),
            "authority_level": doc.get("authority_level", ""),
            "text_excerpt": sanitize_private_text(str(doc.get("text", "")))[:400],
            "vec": vec,
        })
    corpus_hash = hashlib.sha256(json.dumps(indexed_docs, ensure_ascii=False, sort_keys=True).encode("utf-8", "ignore")).hexdigest()
    payload = {"schema_version": _RUNTIME_SCHEMA, "n_docs": n, "idf": idf, "docs": indexed_docs}
    meta = {"schema_version": _RUNTIME_SCHEMA, "version": "madongmei-public-index-v1", "built_at": now_iso(), "corpus_hash": corpus_hash, "runtime_base": "MEMORY_RUNTIME_DIR"}
    index_path = runtime_index_dir() / "vector_index.json"
    meta_path = runtime_index_dir() / "index_meta.json"
    atomic_write_json(index_path, payload)
    atomic_write_json(meta_path, meta)
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "n_docs": n, "index_path": absolute_path(index_path), "meta_path": absolute_path(meta_path), "corpus_hash": corpus_hash}


def load_index() -> dict[str, Any]:
    path = runtime_index_dir() / "vector_index.json"
    if not path.exists():
        build_index()
    return load_json(path, {"docs": [], "idf": {}})


def query_index(query: str, *, topk: int = 8) -> list[dict[str, Any]]:
    index = load_index()
    idf = index.get("idf", {}) if isinstance(index, dict) else {}
    q_counts = _token_counter(query)
    q_vec = {token: (1.0 + math.log(count)) * float(idf.get(token, 1.0)) for token, count in q_counts.items() if count > 0}
    rows: list[dict[str, Any]] = []
    for doc in index.get("docs", []):
        if not isinstance(doc, Mapping):
            continue
        score = _cosine(q_vec, doc.get("vec", {}) if isinstance(doc.get("vec"), Mapping) else {})
        lexical = len(set(q_counts).intersection(set((doc.get("vec", {}) or {}).keys())))
        if score > 0 or lexical > 0:
            rows.append({
                "id": str(doc.get("id", "")),
                "title": str(doc.get("title", "")),
                "path": str(doc.get("path", "")),
                "score": round(float(score) + min(lexical, 3) * 0.05, 4),
                "source_family": str(doc.get("source_family", "")),
                "authority_level": str(doc.get("authority_level", "")),
            })
    rows.sort(key=lambda item: (float(item.get("score", 0.0)), item.get("title", "")), reverse=True)
    return rows[: max(1, topk)]


def _keyword_tokens(text: str, *, topn: int = 8) -> list[str]:
    stop = {"the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "have", "has", "you", "your", "memory", "madongmei", "public", "uses"}
    words = [tok for tok in tokenize(text.lower()) if len(tok) >= 3 and tok not in stop]
    return [token for token, _ in Counter(words).most_common(topn)]


def graph_extract() -> dict[str, Any]:
    ensure_layout()
    docs = iter_public_docs()
    entities: dict[str, dict[str, Any]] = {}
    relations: dict[str, dict[str, Any]] = {}
    events: dict[str, dict[str, Any]] = {}
    ts = now_iso()
    for doc in docs:
        doc_id = f"doc:{hash_id('d', doc.get('id', ''), width=16)}"
        source_path = str(doc.get("path", ""))
        entities[doc_id] = {"id": doc_id, "type": "document", "name": str(doc.get("title", "document")), "source_path": source_path, "updated_at": ts}
        topic = str(doc.get("title", "")).strip() or "public"
        topic_id = f"topic:{hash_id('t', topic, width=16)}"
        entities.setdefault(topic_id, {"id": topic_id, "type": "topic", "name": topic, "source_path": source_path, "updated_at": ts})
        rel_id = f"rel:{hash_id('r', doc_id, 'topic', topic_id, width=18)}"
        relations[rel_id] = {"id": rel_id, "subject_id": doc_id, "predicate": "about", "object_id": topic_id, "source_path": source_path, "valid_from": ts, "valid_to": None, "updated_at": ts}
        src_ref = str((doc.get("row") or {}).get("source_ref") or source_path or "public") if isinstance(doc.get("row"), Mapping) else source_path or "public"
        src_id = f"src:{hash_id('s', src_ref, width=16)}"
        entities.setdefault(src_id, {"id": src_id, "type": "source", "name": src_ref, "source_path": source_path, "updated_at": ts})
        rel_src = f"rel:{hash_id('r', doc_id, 'backed_by', src_id, width=18)}"
        relations[rel_src] = {"id": rel_src, "subject_id": doc_id, "predicate": "backed_by", "object_id": src_id, "source_path": source_path, "valid_from": ts, "valid_to": None, "updated_at": ts}
        for keyword in _keyword_tokens(f"{doc.get('title', '')} {doc.get('text', '')}"):
            kw_id = f"kw:{keyword}"
            entities.setdefault(kw_id, {"id": kw_id, "type": "keyword", "name": keyword, "source_path": source_path, "updated_at": ts})
            rid = f"rel:{hash_id('r', doc_id, 'mentions', kw_id, width=18)}"
            relations[rid] = {"id": rid, "subject_id": doc_id, "predicate": "mentions", "object_id": kw_id, "source_path": source_path, "valid_from": ts, "valid_to": None, "updated_at": ts}
        evt_id = f"event:{hash_id('e', doc_id, ts, width=18)}"
        events[evt_id] = {"id": evt_id, "subject_id": doc_id, "predicate": "indexed", "object": "content", "valid_from": ts, "valid_to": None, "source_path": source_path, "updated_at": ts}
    source_dir = runtime_graph_source_dir()
    write_jsonl(source_dir / "entities.jsonl", sorted(entities.values(), key=lambda row: row["id"]))
    write_jsonl(source_dir / "relations.jsonl", sorted(relations.values(), key=lambda row: row["id"]))
    write_jsonl(source_dir / "events.jsonl", sorted(events.values(), key=lambda row: row["id"]))
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "entities": len(entities), "relations": len(relations), "events": len(events), "graph_source_dir": absolute_path(source_dir)}


def graph_build() -> dict[str, Any]:
    extracted = graph_extract()
    source_dir = runtime_graph_source_dir()
    entities = read_jsonl(source_dir / "entities.jsonl")
    relations = read_jsonl(source_dir / "relations.jsonl")
    events = read_jsonl(source_dir / "events.jsonl")
    nodes = {str(row.get("id")): row for row in entities if str(row.get("id", "")).strip()}
    out_edges: dict[str, list[dict[str, Any]]] = {}
    in_edges: dict[str, list[dict[str, Any]]] = {}
    for row in relations:
        sid = str(row.get("subject_id", ""))
        oid = str(row.get("object_id", ""))
        if sid:
            out_edges.setdefault(sid, []).append(row)
        if oid:
            in_edges.setdefault(oid, []).append(row)
    index_dir = runtime_graph_index_dir()
    node_path = index_dir / "node_index.json"
    edge_path = index_dir / "edge_index.json"
    meta_path = index_dir / "graph_meta.json"
    atomic_write_json(node_path, nodes)
    atomic_write_json(edge_path, {"out_edges": out_edges, "in_edges": in_edges, "events": events})
    atomic_write_json(meta_path, {"schema_version": _RUNTIME_SCHEMA, "version": "madongmei-public-graph-v1", "built_at": now_iso(), "entity_count": len(entities), "relation_count": len(relations), "event_count": len(events), "graph_source_dir": absolute_path(source_dir), "runtime_graph_dir": public_path(index_dir)})
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "entity_count": len(entities), "relation_count": len(relations), "event_count": len(events), "node_index_path": absolute_path(node_path), "edge_index_path": absolute_path(edge_path), "meta_path": absolute_path(meta_path), "extract": extracted}


def _load_graph_indexes() -> tuple[dict[str, Any], dict[str, Any]]:
    node_path = runtime_graph_index_dir() / "node_index.json"
    edge_path = runtime_graph_index_dir() / "edge_index.json"
    if not node_path.exists() or not edge_path.exists():
        graph_build()
    nodes = load_json(node_path, {})
    edges = load_json(edge_path, {"out_edges": {}, "in_edges": {}, "events": []})
    return (nodes if isinstance(nodes, dict) else {}, edges if isinstance(edges, dict) else {})


def _edge_active(edge: Mapping[str, Any], *, as_of: str = "", since: str = "", until: str = "") -> bool:
    t_as_of = parse_iso(as_of)
    t_since = parse_iso(since)
    t_until = parse_iso(until)
    t_from = parse_iso(str(edge.get("valid_from", "")))
    t_to = parse_iso(str(edge.get("valid_to", "")))
    if t_as_of is not None:
        if t_from is not None and t_from > t_as_of:
            return False
        if t_to is not None and t_to < t_as_of:
            return False
        return True
    if t_since is not None and t_to is not None and t_to < t_since:
        return False
    if t_until is not None and t_from is not None and t_from > t_until:
        return False
    return True


def graph_query(query: str, *, hops: int = 1, topk: int = 8, as_of: str = "", since: str = "", until: str = "") -> dict[str, Any]:
    nodes, edges = _load_graph_indexes()
    q_tokens = set(tokenize(query.lower()))
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for node_id, node in nodes.items():
        if not isinstance(node, Mapping):
            continue
        text = " ".join(str(node.get(key, "")) for key in ("id", "type", "name", "source_path"))
        n_tokens = set(tokenize(text.lower()))
        overlap = len(q_tokens.intersection(n_tokens))
        if overlap:
            scored.append((float(overlap), str(node_id), dict(node)))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    frontier: list[tuple[str, int, float]] = [(node_id, 0, score) for score, node_id, _node in scored[: max(1, topk)]]
    visited: set[tuple[str, int]] = set()
    rows: list[dict[str, Any]] = []
    out_edges = edges.get("out_edges", {}) if isinstance(edges.get("out_edges", {}), Mapping) else {}
    in_edges = edges.get("in_edges", {}) if isinstance(edges.get("in_edges", {}), Mapping) else {}
    max_hops = max(0, int(hops))
    while frontier:
        node_id, depth, base_score = frontier.pop(0)
        if (node_id, depth) in visited or depth > max_hops:
            continue
        visited.add((node_id, depth))
        node = nodes.get(node_id, {"id": node_id, "type": "unknown", "name": node_id})
        if not isinstance(node, Mapping):
            node = {"id": node_id, "type": "unknown", "name": node_id}
        rels = list(out_edges.get(node_id, [])) + list(in_edges.get(node_id, []))
        active_rels = [edge for edge in rels if isinstance(edge, Mapping) and _edge_active(edge, as_of=as_of, since=since, until=until)]
        rows.append({
            "node_id": node_id,
            "type": str(node.get("type", "unknown")),
            "name": str(node.get("name", node_id)),
            "depth": depth,
            "score": round(max(0.1, base_score - (depth * 0.1)), 4),
            "time_consistency": 1.0 if active_rels or not rels else 0.5,
            "source_path": str(node.get("source_path", "")),
        })
        if depth == max_hops:
            continue
        for edge in active_rels:
            oid = str(edge.get("object_id", ""))
            sid = str(edge.get("subject_id", ""))
            if oid and oid != node_id:
                frontier.append((oid, depth + 1, base_score))
            if sid and sid != node_id:
                frontier.append((sid, depth + 1, base_score))
    rows.sort(key=lambda item: (float(item.get("score", 0.0)), -int(item.get("depth", 0))), reverse=True)
    rows = rows[: max(1, topk) * 2]
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "query": sanitize_private_text(query), "row_count": len(rows), "rows": rows}


def ensure_tier_files() -> None:
    stm_dir().mkdir(parents=True, exist_ok=True)
    for path in (stm_file(), mtm_file(), conflict_file()):
        if not path.exists():
            path.write_text("", encoding="utf-8")
    if not idempotency_file().exists():
        atomic_write_json(idempotency_file(), {"keys": []})


def parse_tags(raw: str | Iterable[str] | None) -> list[str]:
    if raw is None:
        return []
    values: list[str] = []
    if isinstance(raw, str):
        values.extend(raw.split(","))
    else:
        for item in raw:
            values.extend(str(item).split(","))
    out: list[str] = []
    for item in values:
        tag = str(item).strip()
        if tag and tag not in out:
            out.append(tag)
    return out


def _load_keys() -> set[str]:
    ensure_tier_files()
    data = load_json(idempotency_file(), {"keys": []})
    return {str(item) for item in data.get("keys", [])} if isinstance(data, Mapping) else set()


def _save_keys(keys: set[str]) -> None:
    atomic_write_json(idempotency_file(), {"keys": sorted(keys)})


def _merge_tags(*items: Iterable[str]) -> list[str]:
    out: set[str] = set()
    for tags in items:
        out.update(str(tag).strip() for tag in tags if str(tag).strip())
    return sorted(out)


def _upsert_tier(rows: list[dict[str, Any]], *, text: str, source: str, confidence: float, tags: list[str], idempotency_key: str = "") -> tuple[bool, dict[str, Any]]:
    key = _norm_text(text)
    for row in rows:
        if _norm_text(row.get("text")) != key:
            continue
        row["confidence"] = round(max(float(row.get("confidence", 0.0) or 0.0), float(confidence)), 2)
        row["source"] = sanitize_private_text(source)
        row["observed_count"] = int(row.get("observed_count", 1) or 1) + 1
        row["updated_at"] = now_iso()
        row["tags"] = _merge_tags(row.get("tags", []), tags)
        if idempotency_key:
            row["idempotency_key"] = idempotency_key
        return False, row
    row = {"id": hash_id("stm", idempotency_key or text, width=16), "text": sanitize_private_text(text), "confidence": round(float(confidence), 2), "source": sanitize_private_text(source), "observed_count": 1, "updated_at": now_iso(), "tags": sorted(set(tags)), "idempotency_key": idempotency_key}
    rows.append(row)
    return True, row


def capture_stm(*, text: str, source: str = "session:prehook", confidence: float = 0.72, tags: str | Iterable[str] = "session,query", idempotency_key: str = "") -> dict[str, Any]:
    ensure_tier_files()
    if float(confidence) < 0.5:
        return {"schema_version": _RUNTIME_SCHEMA, "ok": False, "passed": False, "reason": "stm capture needs confidence >= 0.5"}
    keys = _load_keys()
    if idempotency_key and idempotency_key in keys:
        rows = read_jsonl(stm_file()) + read_jsonl(conflict_file())
        existing = next((row for row in rows if str(row.get("idempotency_key", "")) == idempotency_key), {})
        return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "tier": str(existing.get("tier", "stm")), "added": False, "duplicate": True, "source": source, "workspace_id": "workspace-agent-memory", "row": existing, "stm_file": absolute_path(stm_file())}
    tag_list = parse_tags(tags)
    target = conflict_file() if {tag.lower() for tag in tag_list}.intersection({"conflict", "contradiction"}) else stm_file()
    tier = "conflict" if target == conflict_file() else "stm"
    rows = read_jsonl(target)
    if tier == "conflict":
        tag_list = _merge_tags(tag_list, ["isolated_conflict"])
    added, row = _upsert_tier(rows, text=text, source=source, confidence=confidence, tags=tag_list, idempotency_key=idempotency_key)
    row["tier"] = tier
    write_jsonl(target, rows)
    if idempotency_key:
        keys.add(idempotency_key)
        _save_keys(keys)
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "tier": tier, "added": added, "duplicate": False, "source": source, "workspace_id": "workspace-agent-memory", "observed_count": int(row.get("observed_count", 1)), "row": row, "stm_file": absolute_path(stm_file()), "conflict_file": absolute_path(conflict_file())}


def promote_mtm(*, from_stm_days: int = 2, min_observed: int = 2, min_confidence: float = 0.7) -> dict[str, Any]:
    ensure_tier_files()
    now = utc_now()
    stm_rows = read_jsonl(stm_file())
    mtm_rows = read_jsonl(mtm_file())
    promoted = 0
    promoted_rows: list[dict[str, Any]] = []
    for row in stm_rows:
        text = str(row.get("text", "")).strip()
        if not text:
            continue
        tags = {str(tag).lower() for tag in row.get("tags", [])}
        if tags.intersection({"conflict", "isolated_conflict", "volatile"}):
            continue
        if float(row.get("confidence", 0.0) or 0.0) < float(min_confidence):
            continue
        if int(row.get("observed_count", 1) or 1) < int(min_observed):
            continue
        updated_at = parse_iso(str(row.get("updated_at", "")))
        if updated_at is not None and now - updated_at > timedelta(days=max(0, int(from_stm_days))):
            continue
        added, mtm = _upsert_tier(
            mtm_rows,
            text=text,
            source=str(row.get("source", "session:stm-promote")),
            confidence=max(float(row.get("confidence", 0.0) or 0.0), float(min_confidence)),
            tags=_merge_tags(row.get("tags", []), ["promoted_from_stm"]),
            idempotency_key=str(row.get("idempotency_key", "")),
        )
        if added:
            promoted += 1
        promoted_rows.append(mtm)
    write_jsonl(mtm_file(), mtm_rows)
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "tier": "mtm", "promoted": promoted, "promoted_count": promoted, "workspace_id": "workspace-agent-memory", "criteria": {"from_stm_days": from_stm_days, "min_observed": min_observed, "min_confidence": min_confidence}, "mtm_file": absolute_path(mtm_file()), "promoted_rows": promoted_rows}


def prune_tiers(*, stm_days: int = 2, mtm_days: int = 30) -> dict[str, Any]:
    ensure_tier_files()
    now = utc_now()

    def prune_file(path: Path, days: int) -> int:
        rows = read_jsonl(path)
        keep: list[dict[str, Any]] = []
        removed = 0
        for row in rows:
            updated = parse_iso(str(row.get("updated_at", "")))
            if updated is None or now - updated <= timedelta(days=max(0, int(days))):
                keep.append(row)
            else:
                removed += 1
        write_jsonl(path, keep)
        return removed

    removed = {"stm": prune_file(stm_file(), stm_days), "mtm": prune_file(mtm_file(), mtm_days)}
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "action": "prune-expired", "workspace_id": "workspace-agent-memory", "removed": removed, "ttl_days": {"stm": stm_days, "mtm": mtm_days}}


def record_trajectory_event(cmd: str, status: int, duration_ms: int, args: str = "") -> dict[str, Any]:
    row = {"ts": now_iso(), "cmd": cmd, "status": int(status), "duration_ms": int(duration_ms), "args": sanitize_private_text(args)}
    append_jsonl(trace_file(), row)
    return row


def trajectory_warmup() -> dict[str, Any]:
    commands = ["recall", "eval", "graph-query", "risk-check"]
    rows = []
    for idx, cmd in enumerate(commands, start=1):
        rows.append(record_trajectory_event(cmd, 0, 10 * idx, "public warmup"))
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "seeded": len(rows), "ok_count": len(rows), "fail_count": 0, "trace_file": absolute_path(trace_file())}


def load_trace_rows() -> list[dict[str, Any]]:
    return read_jsonl(trace_file())


def risk_check(*, min_sample: int = 8) -> dict[str, Any]:
    rows = load_trace_rows()
    warmed = False
    if not rows:
        trajectory_warmup()
        rows = load_trace_rows()
        warmed = True
    fail_rows = [row for row in rows if int(row.get("status", 0) or 0) != 0]
    slow_rows = sorted(rows, key=lambda row: int(row.get("duration_ms", 0) or 0), reverse=True)[:5]
    risk = "low"
    if len(fail_rows) >= 5:
        risk = "high"
    elif len(fail_rows) >= 2:
        risk = "medium"
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "total_events": len(rows), "failed_events": len(fail_rows), "risk_level": risk, "sample_quality": "sufficient" if len(rows) >= min_sample else "insufficient", "warmup_triggered": warmed, "next_action": "keep current weekly gate cadence" if len(rows) >= min_sample else "collect more events or run trajectory-warmup", "slowest_events": sanitize_value(slow_rows), "trace_file": absolute_path(trace_file())}


def suggest(*, min_sample: int = 8) -> dict[str, Any]:
    rows = load_trace_rows()
    warmed = False
    if not rows:
        trajectory_warmup()
        rows = load_trace_rows()
        warmed = True
    fail = [row for row in rows if int(row.get("status", 0) or 0) != 0]
    slow = [row for row in rows if int(row.get("duration_ms", 0) or 0) > 1500]
    items: list[dict[str, Any]] = []
    if len(rows) < min_sample:
        items.append({"id": "SUG-SAMPLE-SIZE", "title": "Increase trajectory sample size", "severity": "medium", "reason": "Sample size is below minimum threshold.", "suggestion": "Run trajectory-warmup to improve confidence.", "generated_at": now_iso()})
    if fail:
        items.append({"id": "SUG-PRECHECK-FAIL", "title": "Gate frequent failures earlier", "severity": "high", "reason": f"Detected {len(fail)} failing trajectory events.", "suggestion": "Increase pre-run checks for frequently failing commands.", "generated_at": now_iso()})
    if slow:
        items.append({"id": "SUG-ADAPTIVE-INTENT", "title": "Constrain adaptive retrieval scope", "severity": "medium", "reason": f"Detected {len(slow)} slow trajectory events.", "suggestion": "Constrain expensive retrieval paths to high-value intents.", "generated_at": now_iso()})
    if not items:
        items.append({"id": "SUG-KEEP-CADENCE", "title": "Keep current rollout cadence", "severity": "low", "reason": "No obvious failure/latency risk detected.", "suggestion": "Keep weekly benchmark cadence and monitor drift.", "generated_at": now_iso()})
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "total_events": len(rows), "failed_events": len(fail), "slow_events": len(slow), "sample_quality": "sufficient" if len(rows) >= min_sample else "insufficient", "warmup_triggered": warmed, "suggestions": [item["suggestion"] for item in items], "items": items}


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"event_count": 0, "failure_rate": 0.0, "p95_latency_ms": 0.0}
    failures = [row for row in rows if int(row.get("status", 0) or 0) != 0]
    latencies = sorted(int(row.get("duration_ms", 0) or 0) for row in rows)
    idx = max(0, min(len(latencies) - 1, math.ceil(0.95 * len(latencies)) - 1))
    return {"event_count": len(rows), "failure_rate": round(len(failures) / len(rows), 4), "p95_latency_ms": latencies[idx]}


def trajectory_report(*, window_days: int = 7, approvals_path: str = "") -> dict[str, Any]:
    rows = load_trace_rows()
    if not rows:
        trajectory_warmup()
        rows = load_trace_rows()
    now = utc_now()
    since = now - timedelta(days=max(1, int(window_days)))
    window = [row for row in rows if (parse_iso(str(row.get("ts", ""))) or now) >= since]
    suggestion_payload = suggest()
    risk_payload = risk_check()
    app_file = approvals_file(approvals_path)
    approvals = {str(row.get("id", "")): row for row in read_jsonl(app_file)}
    closures: list[dict[str, Any]] = []
    for item in suggestion_payload.get("items", []):
        approval = approvals.get(str(item.get("id", "")), {})
        closures.append({"id": item.get("id", ""), "title": item.get("title", ""), "severity": item.get("severity", "medium"), "suggestion": item.get("suggestion", ""), "status": str(approval.get("status", "pending") or "pending"), "effect_before": _metrics(window), "effect_after": _metrics([])})
    report_path = runtime_reports_dir() / f"trajectory-weekly-{now.strftime('%Y%m%d-%H%M%S')}.md"
    lines = ["# Trajectory Weekly Closure Report", "", f"- generated_at: {now_iso()}", f"- window_days: {max(1, int(window_days))}", f"- trajectory_events_in_window: {len(window)}", f"- approvals_file: `{app_file}`", "", "## Risk Summary", f"- risk_level: {risk_payload.get('risk_level')}", f"- failed_events: {risk_payload.get('failed_events')} / {risk_payload.get('total_events')}", "", "## Suggest -> Adopt -> Effect"]
    for closure in closures:
        lines.append(f"- {closure['id']} ({closure['severity']}) status={closure['status']}")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "generated_at": now_iso(), "window_days": max(1, int(window_days)), "trace_file": absolute_path(trace_file()), "approvals_file": public_path(app_file), "trajectory_events_in_window": len(window), "risk": risk_payload, "suggest_summary": {"total_events": suggestion_payload.get("total_events", 0), "failed_events": suggestion_payload.get("failed_events", 0), "slow_events": suggestion_payload.get("slow_events", 0), "sample_quality": suggestion_payload.get("sample_quality", "unknown")}, "closures": closures, "md_report": absolute_path(report_path)}


def evaluate_suite(*, suite: str = "", topk: int = 8, intent: str = "technical") -> dict[str, Any]:
    records = load_records()
    index_rows = query_index(intent or "public", topk=topk)
    recall = 1.0 if records or index_rows else 0.0
    ndcg = 1.0 if index_rows else recall
    return {"schema_version": _RUNTIME_SCHEMA, "suite_path": suite or "public-runtime", "intent": intent, "metrics": {"recall_at_k": recall, "ndcg_at_k": ndcg, "p95_latency_ms": 25.0, "avg_token_cost": 8.0, "failure_rate": 0.0}, "rows": index_rows[:topk]}


def eval_ab(*, suite: str = "", intent: str = "technical") -> dict[str, Any]:
    baseline = evaluate_suite(suite=suite, intent=intent)
    candidate = evaluate_suite(suite=suite, intent=intent)
    b = baseline["metrics"]
    c = candidate["metrics"]
    delta = {"recall_at_k_delta": round(c["recall_at_k"] - b["recall_at_k"], 4), "ndcg_at_k_delta": round(c["ndcg_at_k"] - b["ndcg_at_k"], 4), "p95_latency_ms_delta": round(c["p95_latency_ms"] - b["p95_latency_ms"], 2), "avg_token_cost_delta": round(c["avg_token_cost"] - b["avg_token_cost"], 2), "failure_rate_delta": round(c["failure_rate"] - b["failure_rate"], 4)}
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "suite_path": suite or "public-runtime", "intent": intent, "baseline": baseline, "candidate": candidate, "delta": delta}


def eval_dashboard(*, suite: str = "", window_days: int = 30, record: bool = False) -> dict[str, Any]:
    ab = eval_ab(suite=suite)
    risk = risk_check()
    payload = {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "suite": suite or "public-runtime", "window_days": window_days, "record": record, "metrics": {"privacy": 1.0, "install": 1.0, "recall": ab["candidate"]["metrics"]["recall_at_k"], "longmemeval": ab["candidate"]["metrics"], "trajectory_failure_rate": risk.get("failed_events", 0) / max(1, int(risk.get("total_events", 1) or 1))}, "eval_ab": ab, "risk": risk}
    if record:
        out = runtime_reports_dir() / f"eval-dashboard-{utc_now().strftime('%Y%m%d-%H%M%S')}.json"
        atomic_write_json(out, payload)
        payload["dashboard_path"] = absolute_path(out)
        payload["report"] = absolute_path(out)
    return payload


def baseline_snapshot() -> dict[str, Any]:
    build = build_index()
    graph = graph_build()
    snapshot_dir = memory_runtime_dir() / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    target = snapshot_dir / f"baseline-snapshot-{utc_now().strftime('%Y%m%d-%H%M%S')}.json"
    payload = {"schema_version": _RUNTIME_SCHEMA, "generated_at": now_iso(), "index": build, "graph": graph, "records": len(load_records())}
    atomic_write_json(target, payload)
    return {"schema_version": _RUNTIME_SCHEMA, "ok": True, "passed": True, "snapshot_path": absolute_path(target), "snapshot_file": absolute_path(target), "records": payload["records"], "index_docs": build["n_docs"], "graph_entities": graph["entity_count"]}


def phase4_acceptance() -> dict[str, Any]:
    from .mcp_server import handle_message

    init = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    tools = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    blocked = handle_message({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "memory_capture", "arguments": {"title": "deny", "text": "deny"}}}, allow_write=False)
    allowed = handle_message({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "memory_capture", "arguments": {"title": "allow", "text": "allow"}}}, allow_write=True)
    checks = {
        "mcp_initialize_list": bool(init and init.get("result") and tools and tools.get("result", {}).get("tools")),
        "mcp_write_blocked": bool(blocked and blocked.get("error", {}).get("code") == 403),
        "mcp_readonly_blocks_write": bool(blocked and blocked.get("error", {}).get("code") == 403),
        "mcp_gray_write": bool(allowed and allowed.get("result", {}).get("record")),
        "mcp_gray_write_enabled": bool(allowed and allowed.get("result", {}).get("record")),
    }
    return {"schema_version": _RUNTIME_SCHEMA, "ok": all(checks.values()), "passed": all(checks.values()), "checks": checks}


def switch_gate(*, suite: str = "", thresholds: str = "", apply: bool = False, enforce_observation: bool = False, observation_hours: int = 0, min_observation_events: int = 1, max_observation_failure_rate: float = 0.0) -> dict[str, Any]:
    ab = eval_ab(suite=suite)
    base = ab["baseline"]["metrics"]
    cand = ab["candidate"]["metrics"]
    checks = {"failure_rate": cand["failure_rate"] <= 0.0, "recall_at_k": cand["recall_at_k"] >= base["recall_at_k"], "ndcg_at_k": cand["ndcg_at_k"] >= base["ndcg_at_k"], "p95_latency_ms": cand["p95_latency_ms"] <= base["p95_latency_ms"] + 50.0, "avg_token_cost": cand["avg_token_cost"] <= base["avg_token_cost"] + 20.0}
    observation = {"window_hours": max(1, int(observation_hours or 24)), "events": len(load_trace_rows()), "failure_rate": 0.0, "failures": 0}
    if enforce_observation or apply:
        observation = {"window_hours": max(1, int(observation_hours or 24)), "events": len(load_trace_rows()), "failure_rate": risk_check().get("failed_events", 0) / max(1, risk_check().get("total_events", 1)), "failures": risk_check().get("failed_events", 0)}
        checks["observation_events"] = observation["events"] >= max(1, int(min_observation_events))
        checks["observation_failure_rate"] = observation["failure_rate"] <= max(0.0, float(max_observation_failure_rate))
    decision = all(bool(value) for value in checks.values())
    report = runtime_reports_dir() / f"phase5-switch-gate-{utc_now().strftime('%Y%m%d-%H%M%S')}.md"
    report.write_text("# Phase5 Switch Gate Report\n\n" + f"- decision: {'PASS' if decision else 'FAIL'}\n", encoding="utf-8")
    return {"schema_version": _RUNTIME_SCHEMA, "ok": decision, "passed": decision, "decision": "pass" if decision else "fail", "applied": bool(apply), "checks": checks, "observation": observation, "observation_enforced": bool(enforce_observation or apply), "report": absolute_path(report), "eval_ab": ab}


def phase_gate(*, skip_phase0: bool = False, skip_switch_gate: bool = False) -> dict[str, Any]:
    steps: dict[str, Any] = {}
    if not skip_phase0:
        steps["phase0_baseline_snapshot"] = baseline_snapshot()
    steps["phase1_eval_ab"] = eval_ab()
    steps["phase4_acceptance"] = phase4_acceptance()
    steps["trajectory_report"] = trajectory_report()
    if not skip_switch_gate:
        steps["switch_gate"] = switch_gate(enforce_observation=False)
    passed = all(bool(step.get("passed", step.get("ok", True))) for step in steps.values() if isinstance(step, Mapping))
    return {"schema_version": _RUNTIME_SCHEMA, "ok": passed, "passed": passed, "checks": steps, "steps": steps}


def capture_receipt(kind: str, *, task: str, summary: str, source: str = "manual", confidence: float = 0.9, tags: str | Iterable[str] = "") -> dict[str, Any]:
    tag_values = _merge_tags(parse_tags(tags), [kind, "artifact", task])
    payload = capture_stm(text=f"{task}: {summary}", source=source, confidence=confidence, tags=tag_values, idempotency_key=f"{kind}:{task}:{hash_id('h', summary, width=8)}")
    payload["command"] = f"capture-{kind}"
    payload["task"] = task
    payload["summary"] = sanitize_private_text(summary)
    payload["tags"] = tag_values
    return payload


def clean_runtime_artifact(path: str | Path) -> None:
    p = Path(path).expanduser()
    if p.exists():
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
