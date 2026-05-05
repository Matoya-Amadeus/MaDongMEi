from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import __version__
from .codex_bridge import (
    install_bridge_scaffold,
    public_framework_templates,
    render_request_context_template,
)
from .config import db_path, ensure_layout
from .personal_graph import PersonalGraphStore
from .request_context import prepare_public_request_context
from .store import (
    capture_record,
    load_records,
    recent_records,
    search_records,
    summarize,
    weekly_snapshot,
)
from .workspace import (
    cleanup_workspaces,
    format_registry_rows,
    load_registry,
    normalize_root,
    remove_workspace,
    save_registry,
    status_summary,
    upsert_workspace,
)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


def build_tool_manifest() -> list[ToolSpec]:
    return [
        ToolSpec("memory_search", "Search public memory records.", {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}}),
        ToolSpec("memory_capture", "Capture a public memory record.", {"type": "object", "properties": {"title": {"type": "string"}, "text": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}}),
        ToolSpec("memory_review", "Summarize current public memory state.", {"type": "object", "properties": {"limit": {"type": "integer"}}}),
        ToolSpec("memory_weekly_review", "Summarize the last seven days of public memory.", {"type": "object", "properties": {"days": {"type": "integer"}, "limit": {"type": "integer"}}}),
        ToolSpec("memory_doctor", "Inspect the public memory layout.", {"type": "object", "properties": {}}),
        ToolSpec("memory_autopilot", "Recall, classify, capture, and promote public notes.", {"type": "object", "properties": {"query": {"type": "string"}, "title": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}}),
        ToolSpec("memory_pre_hook", "Build public request-time memory context.", {"type": "object", "properties": {"query": {"type": "string"}, "topk": {"type": "integer"}}}),
        ToolSpec("memory_health", "Inspect public memory health.", {"type": "object", "properties": {}}),
        ToolSpec("graph_search", "Search the personal graph framework.", {"type": "object", "properties": {"query": {"type": "string"}, "topk": {"type": "integer"}}}),
        ToolSpec("graph_capture", "Capture a graph page.", {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}, "source_ref": {"type": "string"}, "idempotency_key": {"type": "string"}}}),
        ToolSpec("graph_connect", "Connect two graph pages.", {"type": "object", "properties": {"from_page_id": {"type": "string"}, "to_page_id": {"type": "string"}, "relation": {"type": "string"}}}),
        ToolSpec("graph_timeline", "List graph pages in time order.", {"type": "object", "properties": {"topk": {"type": "integer"}}}),
        ToolSpec("graph_review", "Summarize graph state.", {"type": "object", "properties": {}}),
        ToolSpec("graph_doctor", "Inspect graph database health.", {"type": "object", "properties": {}}),
        ToolSpec("graph_snapshot", "Create a personal graph snapshot.", {"type": "object", "properties": {}}),
        ToolSpec("graph_restore", "Restore a personal graph snapshot.", {"type": "object", "properties": {"snapshot_path": {"type": "string"}}, "required": ["snapshot_path"]}),
        ToolSpec("workspace_status", "Report workspace registry and bridge layout.", {"type": "object", "properties": {}}),
        ToolSpec("workspace_list", "List registered workspaces.", {"type": "object", "properties": {}}),
        ToolSpec("workspace_register", "Register a workspace root.", {"type": "object", "properties": {"root": {"type": "string"}, "label": {"type": "string"}, "enabled": {"type": "boolean"}, "primary": {"type": "boolean"}}, "required": ["root"]}),
        ToolSpec("workspace_remove", "Remove a registered workspace root.", {"type": "object", "properties": {"root": {"type": "string"}}, "required": ["root"]}),
        ToolSpec("workspace_unregister", "Alias for removing a registered workspace root.", {"type": "object", "properties": {"root": {"type": "string"}}, "required": ["root"]}),
        ToolSpec("workspace_cleanup", "Prune stale workspace entries.", {"type": "object", "properties": {"active_root": {"type": "string"}, "stale_days": {"type": "integer"}}}),
        ToolSpec("context_template", "Render the public request context template.", {"type": "object", "properties": {"query": {"type": "string"}, "workspace_id": {"type": "string"}, "profile": {"type": "string"}}}),
        ToolSpec("context_templates", "List the public framework templates.", {"type": "object", "properties": {}}),
        ToolSpec("bridge_install", "Create the public context bridge scaffold.", {"type": "object", "properties": {"home": {"type": "string"}}}),
    ]


def _response(result: Any, *, id_value: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0"}
    if id_value is not None:
        payload["id"] = id_value
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    return payload


def _tool_rows() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "inputSchema": spec.input_schema,
        }
        for spec in build_tool_manifest()
    ]


def dispatch_tool(name: str, arguments: Mapping[str, Any], *, allow_write: bool = False) -> dict[str, Any]:
    if name == "memory_search":
        rows = search_records(str(arguments.get("query", "")), limit=int(arguments.get("limit", 5)))
        return {"rows": rows}
    if name == "memory_capture":
        if not allow_write:
            raise PermissionError("write disabled")
        record = capture_record(
            title=str(arguments.get("title", "")) or "Untitled",
            text=str(arguments.get("text", "")),
            tags=list(arguments.get("tags", [])),
            source="mcp",
            kind="memory",
        )
        return {"record": record}
    if name == "memory_review":
        return summarize(limit=int(arguments.get("limit", 5)))
    if name == "memory_weekly_review":
        return weekly_snapshot(days=int(arguments.get("days", 7)), limit=int(arguments.get("limit", 5)))
    if name == "memory_doctor":
        layout = ensure_layout()
        return {
            "db_path": str(db_path()),
            "db_exists": layout["db"].exists(),
            "record_count": len(load_records()),
        }
    if name == "memory_autopilot":
        if not allow_write:
            raise PermissionError("write disabled")
        from .autopilot import run_autopilot

        return run_autopilot(
            str(arguments.get("query", "")),
            title=str(arguments.get("title", "")),
            tags=list(arguments.get("tags", [])),
            workspace_id=str(arguments.get("workspace_id", "")),
            source_ref=str(arguments.get("source_ref", "")),
            idempotency_key=str(arguments.get("idempotency_key", "")),
            dry_run=bool(arguments.get("dry_run", False)),
        )
    if name == "memory_pre_hook":
        return prepare_public_request_context(
            str(arguments.get("query", "")),
            topk=int(arguments.get("topk", 5)),
        )
    if name == "memory_health":
        layout = ensure_layout()
        return {
            "ok": layout["db"].exists(),
            "record_count": len(load_records()),
            "public_template": True,
        }

    graph = PersonalGraphStore()
    if name.startswith("graph_"):
        return graph.mcp_tool_call(name, arguments, allow_write=allow_write)

    if name == "workspace_status":
        return status_summary()
    if name == "workspace_list":
        return {"workspaces": format_registry_rows(load_registry())}
    if name == "workspace_register":
        if not allow_write:
            raise PermissionError("write disabled")
        root = normalize_root(str(arguments.get("root", "")))
        if not root:
            raise ValueError("root is required")
        registry = load_registry()
        updated = upsert_workspace(
            registry,
            root,
            label=str(arguments.get("label", "")),
            enabled=bool(arguments.get("enabled", True)),
            primary=bool(arguments.get("primary", False)),
        )
        save_registry(updated)
        return {"workspaces": format_registry_rows(updated)}
    if name == "workspace_remove":
        if not allow_write:
            raise PermissionError("write disabled")
        root = normalize_root(str(arguments.get("root", "")))
        if not root:
            raise ValueError("root is required")
        registry = load_registry()
        cleaned = remove_workspace(registry, root)
        save_registry(cleaned)
        return {"workspaces": format_registry_rows(cleaned)}
    if name == "workspace_unregister":
        if not allow_write:
            raise PermissionError("write disabled")
        root = normalize_root(str(arguments.get("root", "")))
        if not root:
            raise ValueError("root is required")
        registry = load_registry()
        cleaned = remove_workspace(registry, root)
        save_registry(cleaned)
        return {"workspaces": format_registry_rows(cleaned)}
    if name == "workspace_cleanup":
        if not allow_write:
            raise PermissionError("write disabled")
        registry = load_registry()
        cleaned = cleanup_workspaces(
            registry,
            active_root=str(arguments.get("active_root", "")),
            stale_days=int(arguments.get("stale_days", 14)),
        )
        save_registry(cleaned)
        return {"workspaces": format_registry_rows(cleaned)}

    if name == "context_template":
        return {
            "template": render_request_context_template(
                str(arguments.get("query", "")),
                workspace_id=str(arguments.get("workspace_id", "")),
                profile=str(arguments.get("profile", "default")),
            )
        }
    if name == "context_templates":
        return public_framework_templates().to_dict()
    if name == "bridge_install":
        if not allow_write:
            raise PermissionError("write disabled")
        return install_bridge_scaffold(home=arguments.get("home"))

    raise ValueError(f"unknown tool: {name}")


def handle_message(message: Mapping[str, Any], *, allow_write: bool = False) -> dict[str, Any] | None:
    method = str(message.get("method", "")).strip()
    msg_id = message.get("id")
    params = message.get("params", {})
    if method == "initialize":
        return _response(
            {
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "madongmei-mcp", "version": __version__},
                "capabilities": {"tools": {}},
            },
            id_value=msg_id,
        )
    if method == "tools/list":
        return _response({"tools": _tool_rows()}, id_value=msg_id)
    if method == "tools/call":
        if not isinstance(params, Mapping):
            return _response(None, id_value=msg_id, error={"code": -32602, "message": "invalid params"})
        name = str(params.get("name", "")).strip()
        arguments = params.get("arguments", {})
        if not isinstance(arguments, Mapping):
            arguments = {}
        try:
            result = dispatch_tool(name, arguments, allow_write=allow_write)
        except PermissionError as exc:
            return _response(None, id_value=msg_id, error={"code": 403, "message": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive
            return _response(None, id_value=msg_id, error={"code": 500, "message": f"{type(exc).__name__}: {exc}"})
        return _response(result, id_value=msg_id)
    if method == "ping":
        return _response({"ok": True}, id_value=msg_id)
    return None


def serve_stdio(*, allow_write: bool = False) -> int:
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except Exception:
            continue
        if not isinstance(message, Mapping):
            continue
        response = handle_message(message, allow_write=allow_write)
        if response is None:
            continue
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


def build_manifest_payload() -> dict[str, Any]:
    return {
        "server": {"name": "madongmei-mcp", "version": __version__},
        "tools": _tool_rows(),
        "templates": public_framework_templates().to_dict(),
    }
