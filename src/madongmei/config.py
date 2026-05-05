from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "madongmei"
BRIDGE_RUNTIME_NAME = ".madongmei-runtime"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def codex_home() -> Path:
    value = os.environ.get("CODEX_HOME")
    return Path(value).expanduser() if value else Path.home() / ".codex"


def state_root() -> Path:
    home = os.environ.get("MADONGMEI_HOME")
    if home:
        return Path(home).expanduser()
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg).expanduser() / APP_NAME
    return Path.home() / f".{APP_NAME}"


def data_dir() -> Path:
    value = os.environ.get("MADONGMEI_DATA_DIR")
    return Path(value).expanduser() if value else state_root() / "data"


def logs_dir() -> Path:
    value = os.environ.get("MADONGMEI_LOG_DIR")
    return Path(value).expanduser() if value else state_root() / "logs"


def cache_dir() -> Path:
    value = os.environ.get("MADONGMEI_CACHE_DIR")
    return Path(value).expanduser() if value else state_root() / "cache"


def db_path() -> Path:
    value = os.environ.get("MADONGMEI_DB_PATH")
    return Path(value).expanduser() if value else data_dir() / "memory.jsonl"


def graph_dir() -> Path:
    value = os.environ.get("MADONGMEI_GRAPH_DIR")
    return Path(value).expanduser() if value else memory_runtime_dir() / "graph"


def graph_db_path() -> Path:
    value = os.environ.get("MADONGMEI_GRAPH_DB_PATH")
    return Path(value).expanduser() if value else graph_dir() / "personal.db"


def graph_snapshot_dir() -> Path:
    value = os.environ.get("MADONGMEI_GRAPH_SNAPSHOT_DIR")
    return Path(value).expanduser() if value else graph_dir() / "snapshots"


def bridge_root() -> Path:
    value = os.environ.get("MADONGMEI_BRIDGE_ROOT")
    return Path(value).expanduser() if value else codex_home() / BRIDGE_RUNTIME_NAME


def workspace_root() -> Path:
    value = os.environ.get("WORKSPACE_SOURCE_ROOT") or os.environ.get("WORKSPACE_ROOT")
    return Path(value).expanduser() if value else bridge_root() / "workspaces" / repo_root().name


def workspace_link() -> Path:
    value = os.environ.get("WORKSPACE_SOURCE_LINK")
    return Path(value).expanduser() if value else workspace_root() / ".agent-memory"


def memory_runtime_dir() -> Path:
    value = os.environ.get("MEMORY_RUNTIME_DIR")
    return Path(value).expanduser() if value else bridge_root() / "memory"


def workspace_registry_path() -> Path:
    value = os.environ.get("WORKSPACE_REGISTRY_FILE")
    return Path(value).expanduser() if value else memory_runtime_dir() / "state" / "workspace_registry.json"


def wiki_dir() -> Path:
    value = os.environ.get("MADONGMEI_WIKI_DIR")
    return Path(value).expanduser() if value else repo_root() / "knowledge" / "wiki"


def skill_dir() -> Path:
    value = os.environ.get("MADONGMEI_SKILL_DIR")
    return Path(value).expanduser() if value else repo_root() / "skills" / "public-autopilot"


def ensure_layout() -> dict[str, Path]:
    root = state_root()
    data = data_dir()
    logs = logs_dir()
    cache = cache_dir()
    graph = graph_dir()
    graph_db = graph_db_path()
    graph_snapshot = graph_snapshot_dir()
    bridge = bridge_root()
    workspace = workspace_root()
    link = workspace_link()
    memory = memory_runtime_dir()
    registry = workspace_registry_path()
    wiki = wiki_dir()
    skill = skill_dir()
    for path in (root, data, logs, cache, graph, graph_db.parent, graph_snapshot, bridge, workspace, link, memory, registry.parent, wiki, skill):
        path.mkdir(parents=True, exist_ok=True)
    db = db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    if not db.exists():
        db.touch()
    if not graph_db.exists():
        graph_db.touch()
    return {
        "root": root,
        "data": data,
        "logs": logs,
        "cache": cache,
        "db": db,
        "graph": graph,
        "graph_db": graph_db,
        "graph_snapshot": graph_snapshot,
        "bridge": bridge,
        "workspace": workspace,
        "workspace_link": link,
        "memory_runtime": memory,
        "workspace_registry": registry,
        "wiki": wiki,
        "skill": skill,
    }
