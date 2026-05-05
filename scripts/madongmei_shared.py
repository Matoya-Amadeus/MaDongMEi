#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

_TEXT_RE = re.compile(r"[^a-z0-9\u4e00-\u9fff]+")

def load_json(path: str | Path, fallback: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return fallback
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return fallback

def load_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict] = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def parse_iso(raw: str | None) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def normalize_text(text: str | None) -> str:
    s = str(text or "").lower()
    s = _TEXT_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()

def word_tokens(text: str | None) -> list[str]:
    return [tok for tok in normalize_text(text).split(" ") if tok]

def word_and_char_tokens(text: str | None) -> list[str]:
    words = word_tokens(text)
    compact = "".join(words)
    grams = [compact[i : i + 3] for i in range(max(0, len(compact) - 2))]
    return words + grams

def tf(items) -> dict[str, float]:
    counts: dict[str, float] = {}
    for item in items:
        key = str(item)
        counts[key] = counts.get(key, 0.0) + 1.0
    return counts

def cosine(a, b) -> float:
    if not a or not b:
        return 0.0
    dot = sum(float(v) * float(b.get(k, 0.0)) for k, v in a.items())
    na = math.sqrt(sum(float(v) * float(v) for v in a.values()))
    nb = math.sqrt(sum(float(v) * float(v) for v in b.values()))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)

def default_codex_home() -> Path:
    raw = str(os.environ.get("CODEX_HOME", "")).strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".codex"

def default_madongmei_repo() -> Path:
    raw = str(os.environ.get("MADONGMEI_REPO", "")).strip() or str(os.environ.get("MADONGMEI_REPO_DEFAULT", "")).strip()
    if raw:
        return Path(raw).expanduser()
    return Path(__file__).resolve().parent.parent

def default_workspace_root() -> Path:
    for env_name in ("WORKSPACE_SOURCE_ROOT", "WORKSPACE_ROOT"):
        raw = str(os.environ.get(env_name, "")).strip()
        if raw:
            return Path(raw).expanduser()

    raw_link = str(os.environ.get("WORKSPACE_SOURCE_LINK", "")).strip()
    if raw_link:
        link = Path(raw_link).expanduser()
        if link.name == ".agent-memory":
            return link.parent
        return link

    workspace_name = str(os.environ.get("MADONGMEI_WORKSPACE_NAME", "")).strip() or default_madongmei_repo().name or "default"
    return default_codex_home() / ".madongmei-runtime" / "workspaces" / workspace_name

def default_workspace_link() -> Path:
    raw = str(os.environ.get("WORKSPACE_SOURCE_LINK", "")).strip()
    if raw:
        return Path(raw).expanduser()
    return default_workspace_root() / ".agent-memory"

def default_personal_memory_root() -> Path:
    runtime_dir = str(os.environ.get("MEMORY_RUNTIME_DIR", "")).strip()
    if runtime_dir:
        return Path(runtime_dir).expanduser()
    return default_codex_home() / ".madongmei-runtime" / "memory"

def default_personal_db_path() -> Path:
    return default_personal_memory_root() / "personal.db"

def default_personal_runtime_dir(db_path: str | Path | None = None) -> Path:
    base_db = Path(db_path).expanduser() if db_path is not None else default_personal_db_path()
    return base_db.parent / "runtime"

def default_personal_metrics_path() -> Path:
    return default_personal_runtime_dir() / "query_metrics.jsonl"
