from __future__ import annotations

import json
import math
import shutil
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .codex_bridge import render_graph_page_template
from .config import graph_db_path, graph_snapshot_dir
from .store import normalize_tags, sanitize_private_text, tokenize


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


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
    return dt


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


class PersonalGraphStore:
    def __init__(self, db_path_value: str | Path | None = None, *, snapshot_root: str | Path | None = None) -> None:
        self.db_path = Path(db_path_value).expanduser() if db_path_value is not None else graph_db_path()
        self.snapshot_root = Path(snapshot_root).expanduser() if snapshot_root is not None else graph_snapshot_dir()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pages (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    source TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY(page_id) REFERENCES pages(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_page_id TEXT NOT NULL,
                    to_page_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(from_page_id) REFERENCES pages(id) ON DELETE CASCADE,
                    FOREIGN KEY(to_page_id) REFERENCES pages(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS tags (
                    name TEXT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS page_tags (
                    page_id TEXT NOT NULL,
                    tag_name TEXT NOT NULL,
                    PRIMARY KEY(page_id, tag_name),
                    FOREIGN KEY(page_id) REFERENCES pages(id) ON DELETE CASCADE,
                    FOREIGN KEY(tag_name) REFERENCES tags(name) ON DELETE CASCADE
                );
                """
            )
            row = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()
            if row is None:
                conn.execute("INSERT INTO schema_version(version) VALUES (1)")

    def _page_by_source_ref(self, source_ref: str) -> str | None:
        if not source_ref:
            return None
        with self._conn() as conn:
            row = conn.execute("SELECT id FROM pages WHERE source_ref=? LIMIT 1", (source_ref,)).fetchone()
        return str(row["id"]) if row else None

    def _page_by_idempotency(self, idempotency_key: str) -> str | None:
        if not idempotency_key:
            return None
        with self._conn() as conn:
            row = conn.execute("SELECT id FROM pages WHERE idempotency_key=? LIMIT 1", (idempotency_key,)).fetchone()
        return str(row["id"]) if row else None

    def capture(
        self,
        title: str,
        content: str,
        *,
        tags: Iterable[str] | None = None,
        source_ref: str = "manual",
        source: str = "manual",
        kind: str = "note",
        idempotency_key: str = "",
        created_at: str | None = None,
    ) -> str:
        self.init_db()
        title_text = sanitize_private_text(str(title or "").strip() or "Untitled")
        content_text = sanitize_private_text(str(content or "").strip() or render_graph_page_template(title_text))
        source_ref_text = sanitize_private_text(str(source_ref or "").strip() or "manual")
        source_text = sanitize_private_text(str(source or "").strip() or "manual")
        kind_text = sanitize_private_text(str(kind or "").strip() or "note")
        tags_list = normalize_tags(tags)

        page_id = self._page_by_idempotency(idempotency_key) or self._page_by_source_ref(source_ref_text)
        if page_id:
            return page_id

        page_id = uuid.uuid4().hex
        timestamp = str(created_at or now_iso())

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO pages(id, title, content, source_ref, source, kind, created_at, updated_at, idempotency_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    page_id,
                    title_text,
                    content_text,
                    source_ref_text,
                    source_text,
                    kind_text,
                    timestamp,
                    timestamp,
                    str(idempotency_key or "").strip(),
                ),
            )
            for ordinal, block in enumerate(content_text.splitlines() or [content_text], start=1):
                if not str(block).strip():
                    continue
                conn.execute(
                    "INSERT INTO blocks(page_id, ordinal, content) VALUES (?, ?, ?)",
                    (page_id, ordinal, str(block).strip()),
                )
            for tag in tags_list:
                conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag,))
                conn.execute("INSERT OR IGNORE INTO page_tags(page_id, tag_name) VALUES (?, ?)", (page_id, tag))
        return page_id

    def connect(self, from_page_id: str, to_page_id: str, *, relation: str = "related_to") -> None:
        self.init_db()
        if not from_page_id or not to_page_id:
            raise ValueError("from_page_id and to_page_id are required")
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO links(from_page_id, to_page_id, relation, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(from_page_id).strip(),
                    str(to_page_id).strip(),
                    str(relation or "related_to").strip() or "related_to",
                    now_iso(),
                ),
            )

    def _page_blob_rows(self, as_of: str | None = None) -> list[dict[str, Any]]:
        self.init_db()
        clause = ""
        args: list[Any] = []
        if as_of:
            clause = "WHERE created_at <= ?"
            args.append(as_of)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT p.id AS page_id,
                       p.title,
                       p.content,
                       p.created_at,
                       p.updated_at,
                       p.source_ref,
                       p.source,
                       p.kind,
                       GROUP_CONCAT(DISTINCT t.name) AS tags
                FROM pages p
                LEFT JOIN page_tags pt ON pt.page_id = p.id
                LEFT JOIN tags t ON t.name = pt.tag_name
                {clause}
                GROUP BY p.id
                """,
                args,
            ).fetchall()
        return [dict(r) for r in rows]

    def search(self, query: str, *, topk: int = 8, as_of: str | None = None) -> list[dict[str, Any]]:
        self.init_db()
        q_tokens = tokenize(query)
        q_counter = Counter(q_tokens)
        q_set = set(q_tokens)
        page_rows = self._page_blob_rows(as_of=as_of)

        link_degree: dict[str, int] = {}
        with self._conn() as conn:
            for row in conn.execute("SELECT from_page_id, COUNT(*) AS c FROM links GROUP BY from_page_id").fetchall():
                link_degree[str(row["from_page_id"])] = int(row["c"])

        now = datetime.now(timezone.utc)
        scored: list[dict[str, Any]] = []
        for row in page_rows:
            text = f"{row.get('title', '')} {row.get('content', '')} {row.get('tags', '')}".strip()
            tokens = tokenize(text)
            d_counter = Counter(tokens)
            d_set = set(tokens)

            lexical = (len(q_set.intersection(d_set)) / max(1, len(q_set))) if q_set else 0.0
            vector = cosine_similarity(q_counter, d_counter)
            graph = min(1.0, float(link_degree.get(row["page_id"], 0)) / 10.0)

            final = 0.45 * lexical + 0.4 * vector + 0.15 * graph
            created = parse_iso(str(row.get("created_at", "")))
            age_days = ((now - created).total_seconds() / 86400.0) if created else 0.0
            scored.append(
                {
                    "page_id": row["page_id"],
                    "title": row.get("title", ""),
                    "score": round(final, 6),
                    "lexical_score": round(lexical, 6),
                    "vector_score": round(vector, 6),
                    "graph_score": round(graph, 6),
                    "stale_score": round(max(0.0, min(1.0, age_days / 90.0)), 6),
                    "created_at": row.get("created_at", ""),
                    "evidence": {
                        "source_ref": row.get("source_ref", ""),
                        "freshness_days": int(max(0.0, age_days)),
                        "collected_at": row.get("created_at", ""),
                    },
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[: max(1, int(topk))]

    def timeline(self, *, as_of: str | None = None, topk: int = 20) -> list[dict[str, Any]]:
        self.init_db()
        clause = ""
        args: list[Any] = []
        if as_of:
            clause = "WHERE created_at <= ?"
            args.append(as_of)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT id AS page_id, title, created_at, updated_at, source_ref
                FROM pages
                {clause}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                args + [max(1, int(topk))],
            ).fetchall()
        return [dict(row) for row in rows]

    def review(self) -> dict[str, Any]:
        recent = self.timeline(topk=10)
        followups = [row for row in self.search("todo followup next action pending", topk=5) if row["score"] > 0]
        return {
            "generated_at": now_iso(),
            "recent_decisions": recent[:5],
            "followups": followups,
            "suggestions": [
                "Review stale_score > 0.7 pages and reconfirm validity.",
                "Link this week's decisions to active tasks for traceability.",
            ],
        }

    def doctor(self) -> dict[str, Any]:
        self.init_db()
        checks: list[dict[str, Any]] = []
        checks.append({"name": "db_exists", "ok": self.db_path.exists()})
        try:
            with self._conn() as conn:
                row = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()
                page_count = int(conn.execute("SELECT COUNT(*) AS c FROM pages").fetchone()["c"])
                link_count = int(conn.execute("SELECT COUNT(*) AS c FROM links").fetchone()["c"])
            checks.append({"name": "schema_readable", "ok": True})
        except Exception as exc:
            row = None
            page_count = 0
            link_count = 0
            checks.append({"name": "schema_readable", "ok": False, "error": str(exc)})
        return {
            "ok": all(bool(item.get("ok")) for item in checks),
            "db_path": str(self.db_path),
            "schema_version": int(row["version"]) if row else 0,
            "page_count": page_count,
            "link_count": link_count,
            "checks": checks,
        }

    def export_jsonl(self, output_path: str | Path) -> Path:
        self.init_db()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            pages = conn.execute("SELECT * FROM pages ORDER BY created_at").fetchall()
            rows: list[dict[str, Any]] = []
            for page in pages:
                pid = str(page["id"])
                blocks = conn.execute(
                    "SELECT content FROM blocks WHERE page_id=? ORDER BY ordinal",
                    (pid,),
                ).fetchall()
                tags = conn.execute(
                    """
                    SELECT t.name
                    FROM tags t
                    INNER JOIN page_tags pt ON pt.tag_name=t.name
                    WHERE pt.page_id=?
                    ORDER BY t.name
                    """,
                    (pid,),
                ).fetchall()
                rows.append(
                    {
                        "id": pid,
                        "title": page["title"],
                        "content": "\n".join(str(block["content"]) for block in blocks),
                        "tags": [str(tag["name"]) for tag in tags],
                        "source_ref": page["source_ref"],
                        "created_at": page["created_at"],
                    }
                )
        with out.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return out

    def import_jsonl(self, input_path: str | Path) -> int:
        self.init_db()
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"jsonl not found: {path}")
        count = 0
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            raw = line.strip()
            if not raw:
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                continue
            self.capture(
                title=str(row.get("title", "")),
                content=str(row.get("content", "")),
                tags=list(row.get("tags", [])),
                source_ref=str(row.get("source_ref", "jsonl-import")),
                created_at=str(row.get("created_at", "")) or None,
            )
            count += 1
        return count

    def create_snapshot(self) -> Path:
        self.init_db()
        self.snapshot_root.mkdir(parents=True, exist_ok=True)
        snapshot = self.snapshot_root / f"personal-graph-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(self.db_path, snapshot)
        return snapshot

    def restore_snapshot(self, snapshot_path: str | Path) -> None:
        snapshot = Path(snapshot_path).expanduser()
        if not snapshot.exists():
            raise FileNotFoundError(f"snapshot not found: {snapshot}")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot, self.db_path)

    def mcp_tool_call(self, tool_name: str, arguments: Mapping[str, Any], *, allow_write: bool = False) -> dict[str, Any]:
        if tool_name == "graph_search":
            return {"rows": self.search(str(arguments.get("query", "")), topk=int(arguments.get("topk", 8)), as_of=arguments.get("as_of"))}
        if tool_name == "graph_timeline":
            return {"rows": self.timeline(as_of=arguments.get("as_of"), topk=int(arguments.get("topk", 20)))}
        if tool_name == "graph_review":
            return self.review()
        if tool_name == "graph_doctor":
            return self.doctor()
        if tool_name == "graph_snapshot":
            if not allow_write:
                raise PermissionError("write disabled")
            snapshot = self.create_snapshot()
            return {"ok": True, "snapshot": str(snapshot)}
        if tool_name == "graph_restore":
            if not allow_write:
                raise PermissionError("write disabled")
            snapshot_path = str(arguments.get("snapshot_path", "")).strip()
            if not snapshot_path:
                raise ValueError("snapshot_path is required")
            self.restore_snapshot(snapshot_path)
            return {"ok": True, "snapshot": str(Path(snapshot_path).expanduser())}
        if tool_name == "graph_capture":
            if not allow_write:
                raise PermissionError("write disabled")
            page_id = self.capture(
                title=str(arguments.get("title", "")),
                content=str(arguments.get("content", "")),
                tags=list(arguments.get("tags", [])),
                source_ref=str(arguments.get("source_ref", "mcp")),
                idempotency_key=str(arguments.get("idempotency_key", "")),
            )
            return {"ok": True, "page_id": page_id}
        if tool_name == "graph_connect":
            if not allow_write:
                raise PermissionError("write disabled")
            self.connect(
                str(arguments.get("from_page_id", "")),
                str(arguments.get("to_page_id", "")),
                relation=str(arguments.get("relation", "related_to")),
            )
            return {"ok": True}
        raise ValueError(f"unknown tool: {tool_name}")
