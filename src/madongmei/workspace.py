from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .codex_bridge import ensure_bridge_layout, registry_path, workspace_root


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def normalize_root(root: str | Path) -> str:
    text = str(root).strip()
    if not text:
        return ""
    return str(Path(text).expanduser().resolve())


def workspace_label(root: str | Path) -> str:
    normalized = normalize_root(root)
    if not normalized:
        return "workspace"
    return Path(normalized).name or "workspace"


def _default_registry() -> dict[str, Any]:
    default_root = normalize_root(workspace_root())
    return {
        "version": 1,
        "primary_root": default_root,
        "workspaces": [
            {
                "root": default_root,
                "label": workspace_label(default_root),
                "enabled": True,
                "primary": True,
                "registered_at": now_iso(),
                "updated_at": now_iso(),
                "last_seen_at": now_iso(),
            }
        ],
    }


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_file = Path(path).expanduser() if path is not None else registry_path()
    if not registry_file.exists():
        return _default_registry()

    try:
        payload = json.loads(registry_file.read_text(encoding="utf-8"))
    except Exception:
        return _default_registry()

    if not isinstance(payload, dict):
        return _default_registry()

    workspaces = payload.get("workspaces", [])
    if not isinstance(workspaces, list):
        workspaces = []

    normalized: list[dict[str, Any]] = []
    for row in workspaces:
        if not isinstance(row, dict):
            continue
        root = normalize_root(row.get("root", ""))
        if not root:
            continue
        normalized.append(
            {
                "root": root,
                "label": str(row.get("label", "")).strip() or workspace_label(root),
                "enabled": bool(row.get("enabled", True)),
                "primary": bool(row.get("primary", False)),
                "registered_at": str(row.get("registered_at", "")).strip() or now_iso(),
                "updated_at": str(row.get("updated_at", "")).strip() or now_iso(),
                "last_seen_at": str(row.get("last_seen_at", "")).strip() or now_iso(),
            }
        )

    if not normalized:
        return _default_registry()

    primary_root = str(payload.get("primary_root", "")).strip()
    if primary_root:
        primary_root = normalize_root(primary_root)
    if not primary_root or not any(row["root"] == primary_root for row in normalized):
        primary_root = next((row["root"] for row in normalized if row.get("primary")), normalized[0]["root"])

    for row in normalized:
        row["primary"] = row["root"] == primary_root

    return {
        "version": int(payload.get("version", 1) or 1),
        "primary_root": primary_root,
        "workspaces": sorted(
            normalized,
            key=lambda row: (not bool(row.get("primary")), str(row.get("label", "")).lower(), row["root"]),
        ),
    }


def save_registry(data: dict[str, Any], path: str | Path | None = None) -> None:
    registry_file = Path(path).expanduser() if path is not None else registry_path()
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": int(data.get("version", 1) or 1),
        "primary_root": str(data.get("primary_root", "")).strip(),
        "workspaces": list(data.get("workspaces", [])),
        "updated_at": now_iso(),
    }
    tmp = registry_file.with_suffix(registry_file.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(registry_file)


def upsert_workspace(
    data: dict[str, Any],
    root: str | Path,
    *,
    label: str = "",
    enabled: bool = True,
    primary: bool = False,
) -> dict[str, Any]:
    root = normalize_root(root)
    label = label.strip() or workspace_label(root)
    now = now_iso()
    workspaces = list(data.get("workspaces", []))
    updated = False

    for row in workspaces:
        if str(row.get("root", "")).strip() != root:
            continue
        row["label"] = label
        row["enabled"] = bool(enabled)
        row["primary"] = bool(primary)
        row["updated_at"] = now
        row["last_seen_at"] = now
        updated = True
        break

    if not updated:
        workspaces.append(
            {
                "root": root,
                "label": label,
                "enabled": bool(enabled),
                "primary": bool(primary),
                "registered_at": now,
                "updated_at": now,
                "last_seen_at": now,
            }
        )

    if primary:
        for row in workspaces:
            row["primary"] = str(row.get("root", "")).strip() == root
    elif not any(bool(row.get("primary")) for row in workspaces):
        workspaces[0]["primary"] = True

    data["workspaces"] = sorted(
        workspaces,
        key=lambda row: (not bool(row.get("primary")), str(row.get("label", "")).lower(), str(row.get("root", ""))),
    )
    data["primary_root"] = next(
        (str(row.get("root", "")).strip() for row in data["workspaces"] if bool(row.get("primary"))),
        root,
    )
    return data


def remove_workspace(data: dict[str, Any], root: str | Path) -> dict[str, Any]:
    root = normalize_root(root)
    workspaces = [row for row in list(data.get("workspaces", [])) if str(row.get("root", "")).strip() != root]
    if not workspaces:
        data["workspaces"] = []
        data["primary_root"] = ""
        return data

    if not any(bool(row.get("primary")) for row in workspaces):
        workspaces[0]["primary"] = True

    data["workspaces"] = sorted(
        workspaces,
        key=lambda row: (not bool(row.get("primary")), str(row.get("label", "")).lower(), str(row.get("root", ""))),
    )
    data["primary_root"] = next(
        (str(row.get("root", "")).strip() for row in data["workspaces"] if bool(row.get("primary"))),
        "",
    )
    return data


def cleanup_workspaces(
    data: dict[str, Any],
    *,
    active_root: str | Path = "",
    stale_days: int = 14,
) -> dict[str, Any]:
    active_root = normalize_root(active_root) if str(active_root).strip() else ""
    cutoff = datetime.now(timezone.utc).astimezone() - timedelta(days=max(int(stale_days), 0))
    now = now_iso()

    kept: list[dict[str, Any]] = []
    for row in list(data.get("workspaces", [])):
        if not isinstance(row, dict):
            continue
        root = normalize_root(row.get("root", ""))
        if not root:
            continue

        row["label"] = str(row.get("label", "")).strip() or workspace_label(root)
        row["last_seen_at"] = (
            str(row.get("last_seen_at", "")).strip()
            or str(row.get("updated_at", "")).strip()
            or str(row.get("registered_at", "")).strip()
            or now
        )

        if root == active_root:
            row["enabled"] = True
            row["primary"] = True
            row["updated_at"] = now
            row["last_seen_at"] = now
            kept.append(row)
            continue

        if not Path(root).exists():
            continue

        try:
            last_seen = datetime.fromisoformat(str(row["last_seen_at"]).replace("Z", "+00:00"))
        except Exception:
            last_seen = None
        if last_seen is not None and last_seen.astimezone(timezone.utc) < cutoff.astimezone(timezone.utc):
            continue
        kept.append(row)

    if not kept:
        return _default_registry()

    if not any(bool(row.get("primary")) for row in kept):
        kept[0]["primary"] = True

    data["workspaces"] = sorted(
        kept,
        key=lambda row: (not bool(row.get("primary")), str(row.get("label", "")).lower(), str(row.get("root", ""))),
    )
    data["primary_root"] = next(
        (str(row.get("root", "")).strip() for row in data["workspaces"] if bool(row.get("primary"))),
        data["workspaces"][0]["root"],
    )
    return data


def list_workspaces(path: str | Path | None = None) -> list[dict[str, Any]]:
    return list(load_registry(path).get("workspaces", []))


def status_summary(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    layout = ensure_bridge_layout(env)
    registry = load_registry()
    return {
        "registry_path": str(registry_path()),
        "workspace_registry_path": str(registry_path()),
        "primary_root": registry.get("primary_root", ""),
        "workspace_count": len(registry.get("workspaces", [])),
        "workspace_root": str(layout["workspace_root"]),
        "workspace_link": str(layout["workspace_link"]),
        "memory_runtime_dir": str(layout["memory_runtime_dir"]),
        "graph_db_path": str(layout["graph_db_path"]),
        "graph_snapshot_dir": str(layout["graph_snapshot_dir"]),
        "bridge_root": str(layout["bridge_root"]),
    }


def format_registry_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in list(data.get("workspaces", [])):
        rows.append(
            {
                "root": str(row.get("root", "")).strip(),
                "label": str(row.get("label", "")).strip(),
                "enabled": bool(row.get("enabled", True)),
                "primary": bool(row.get("primary", False)),
                "registered_at": str(row.get("registered_at", "")).strip(),
                "updated_at": str(row.get("updated_at", "")).strip(),
                "last_seen_at": str(row.get("last_seen_at", "")).strip(),
            }
        )
    return rows
