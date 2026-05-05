from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .store import sanitize_private_text

BRIDGE_RUNTIME_NAME = ".madongmei-runtime"
DEFAULT_CONTEXT_PROFILE = "default"
DEFAULT_QUERY_PLACEHOLDER = "<query>"
DEFAULT_WORKSPACE_PLACEHOLDER = "<workspace>"
DEFAULT_NOTE_PLACEHOLDER = "<public content template>"


def _env_lookup(env: Mapping[str, str] | None, key: str) -> str | None:
    if env is None:
        return os.environ.get(key)
    return env.get(key)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def templates_root() -> Path:
    return repo_root() / "templates"


def _template_text(name: str, fallback: str) -> str:
    path = templates_root() / name
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return fallback


def _render_template(template: str, replacements: Mapping[str, Any], *, json_safe: bool = False) -> str:
    rendered = str(template)
    for key, value in replacements.items():
        text = _normalize_text(value)
        if json_safe:
            text = json.dumps(text, ensure_ascii=False)[1:-1]
        else:
            text = sanitize_private_text(text)
        rendered = rendered.replace(f"{{{{{key}}}}}", text)
    return rendered


def codex_home(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "CODEX_HOME") or _env_lookup(env, "MADONGMEI_CODEX_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".codex"


def bridge_root(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "MADONGMEI_BRIDGE_ROOT")
    if raw:
        return Path(raw).expanduser()
    return codex_home(env) / BRIDGE_RUNTIME_NAME


def workspace_name(env: Mapping[str, str] | None = None) -> str:
    for key in ("MADONGMEI_WORKSPACE_NAME", "WORKSPACE_NAME"):
        raw = _env_lookup(env, key)
        if raw and str(raw).strip():
            return str(raw).strip()
    return repo_root().name or "workspace"


def workspace_root(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "WORKSPACE_SOURCE_ROOT") or _env_lookup(env, "WORKSPACE_ROOT")
    if raw:
        return Path(raw).expanduser()
    return bridge_root(env) / "workspaces" / workspace_name(env)


def workspace_link(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "WORKSPACE_SOURCE_LINK")
    if raw:
        return Path(raw).expanduser()
    return workspace_root(env) / ".agent-memory"


def memory_runtime_dir(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "MEMORY_RUNTIME_DIR")
    if raw:
        return Path(raw).expanduser()
    return bridge_root(env) / "memory"


def graph_runtime_dir(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "MADONGMEI_GRAPH_RUNTIME_DIR")
    if raw:
        return Path(raw).expanduser()
    return memory_runtime_dir(env) / "graph"


def registry_path(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "WORKSPACE_REGISTRY_FILE")
    if raw:
        return Path(raw).expanduser()
    return memory_runtime_dir(env) / "state" / "workspace_registry.json"


def graph_db_path(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "MADONGMEI_GRAPH_DB_PATH")
    if raw:
        return Path(raw).expanduser()
    return graph_runtime_dir(env) / "personal.db"


def graph_snapshot_dir(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "MADONGMEI_GRAPH_SNAPSHOT_DIR")
    if raw:
        return Path(raw).expanduser()
    return graph_runtime_dir(env) / "snapshots"


def model_instructions_path(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "MADONGMEI_MODEL_INSTRUCTIONS_FILE")
    if raw:
        return Path(raw).expanduser()
    return bridge_root(env) / "config" / "model_instructions.md"


def codex_config_toml(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "CODEX_CONFIG_TOML")
    if raw:
        return Path(raw).expanduser()
    return codex_home(env) / "config.toml"


def install_config_path(env: Mapping[str, str] | None = None) -> Path:
    raw = _env_lookup(env, "MADONGMEI_BRIDGE_CONFIG")
    if raw:
        return Path(raw).expanduser()
    raw_home = _env_lookup(env, "MADONGMEI_HOME")
    if raw_home:
        return Path(raw_home).expanduser() / "context-bridge.env"
    return repo_root() / "context-bridge.env"


def ensure_bridge_layout(env: Mapping[str, str] | None = None) -> dict[str, Path]:
    root = bridge_root(env)
    workspace = workspace_root(env)
    link = workspace_link(env)
    runtime = memory_runtime_dir(env)
    graph = graph_runtime_dir(env)
    registry = registry_path(env)
    graph_db = graph_db_path(env)
    graph_snapshot = graph_snapshot_dir(env)
    model_file = model_instructions_path(env)
    config_toml = codex_config_toml(env)
    for path in (
        root,
        workspace,
        link,
        runtime,
        graph,
        graph_snapshot,
        registry.parent,
        graph_db.parent,
        model_file.parent,
        config_toml.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "codex_home": codex_home(env),
        "bridge_root": root,
        "workspace_root": workspace,
        "workspace_link": link,
        "memory_runtime_dir": runtime,
        "graph_runtime_dir": graph,
        "graph_snapshot_dir": graph_snapshot,
        "registry_path": registry,
        "graph_db_path": graph_db,
        "model_instructions_file": model_file,
        "codex_config_toml": config_toml,
    }


def render_request_context_template(
    query: str = "",
    *,
    workspace_id: str = "",
    profile: str = DEFAULT_CONTEXT_PROFILE,
    memory_summary: str = "",
    wiki_summary: str = "",
    skill_summary: str = "",
    install_note: str = "",
) -> str:
    template = _template_text(
        "request-context.template.md",
        """# MaDongMei Request Context Template

## Request
- query: {{query}}
- workspace: {{workspace_id}}
- profile: {{profile}}

## Memory
- summary: {{memory_summary}}
- recent notes: <redacted public template>
- recall mode: <summary_only | summary_then_raw | skip>

## Wiki
- summary: {{wiki_summary}}
- route: <selected topic or none>
- action: <promote | skip>

## Skill
- summary: {{skill_summary}}
- route: <selected skill or none>
- action: <autoload | memory_only>

## Install
- note: {{install_note}}

## Template Rules
- Keep private paths, secrets, and device-local state out of the template.
- Replace placeholders with public, reusable summaries only.
""",
    )
    return (
        _render_template(
            template,
            {
                "query": _normalize_text(query) or DEFAULT_QUERY_PLACEHOLDER,
                "workspace_id": _normalize_text(workspace_id) or DEFAULT_WORKSPACE_PLACEHOLDER,
                "profile": _normalize_text(profile) or DEFAULT_CONTEXT_PROFILE,
                "memory_summary": _normalize_text(memory_summary) or "<public memory summary>",
                "wiki_summary": _normalize_text(wiki_summary) or "<public wiki template>",
                "skill_summary": _normalize_text(skill_summary) or "<public skill template>",
                "install_note": _normalize_text(install_note) or "Use the public install chain to create the bridge layout.",
            },
        ).strip()
        + "\n"
    )


def render_wiki_page_template(title: str = "Untitled") -> str:
    template = _template_text(
        "wiki-page.template.md",
        """---
title: "{{title}}"
bucket: "wiki"
route: "wiki"
status: "template"
---
# {{title}}

## Summary
- <public summary>

## Decision / Fact
- <stable fact, rule, or decision>

## Evidence
- <link back to public source or validation artifact>

## Notes
- Keep this page public and reusable.
""",
    )
    return _render_template(template, {"title": _normalize_text(title) or "Untitled"}).strip() + "\n"


def render_skill_page_template(title: str = "Untitled") -> str:
    template = _template_text(
        "skill-page.template.md",
        """---
name: "{{title}}"
description: "Public reusable workflow template."
status: "template"
---
# {{title}}

## When to use
- <public scenario>

## Steps
- <step 1>
- <step 2>
- <step 3>

## Guardrails
- Keep the workflow public.
- Avoid user-specific paths and secrets.
""",
    )
    return _render_template(template, {"title": _normalize_text(title) or "Untitled"}).strip() + "\n"


def render_graph_page_template(title: str = "Untitled") -> str:
    template = _template_text(
        "graph-page.template.md",
        """# Personal Graph Template

## {{title}}

## Summary
- <what this item means>

## Links
- related_to: <page-id>
- derived_from: <page-id>

## Evidence
- <public note, decision, or validation artifact>

## Follow-ups
- <next public action>
""",
    )
    return _render_template(template, {"title": _normalize_text(title) or "Untitled"}).strip() + "\n"


def render_workspace_registry_template() -> str:
    template = _template_text(
        "workspace-registry.template.json",
        """{
  "version": 1,
  "primary_root": "{{workspace_root}}",
  "workspaces": [
    {
      "root": "{{workspace_root}}",
      "label": "workspace",
      "enabled": true,
      "primary": true,
      "registered_at": "{{timestamp}}",
      "updated_at": "{{timestamp}}",
      "last_seen_at": "{{timestamp}}"
    }
  ]
}
""",
    )
    return (
        _render_template(
            template,
            {
                "workspace_root": "<workspace-root>",
                "timestamp": "<timestamp>",
            },
            json_safe=True,
        ).strip()
        + "\n"
    )


def render_install_env_template(env: Mapping[str, str] | None = None) -> str:
    layout = ensure_bridge_layout(env)
    return "\n".join(
        [
            "# Generated by MaDongMei context bridge install",
            f'export CODEX_HOME="{layout["codex_home"]}"',
            f'export MADONGMEI_BRIDGE_ROOT="{layout["bridge_root"]}"',
            f'export WORKSPACE_SOURCE_ROOT="{layout["workspace_root"]}"',
            f'export WORKSPACE_SOURCE_LINK="{layout["workspace_link"]}"',
            f'export WORKSPACE_ROOT="{layout["workspace_root"]}"',
            f'export MEMORY_RUNTIME_DIR="{layout["memory_runtime_dir"]}"',
            f'export WORKSPACE_REGISTRY_FILE="{layout["registry_path"]}"',
            f'export MADONGMEI_GRAPH_DB_PATH="{layout["graph_db_path"]}"',
            f'export MADONGMEI_GRAPH_RUNTIME_DIR="{layout["graph_runtime_dir"]}"',
            f'export MADONGMEI_GRAPH_SNAPSHOT_DIR="{layout["graph_snapshot_dir"]}"',
            f'export MADONGMEI_MODEL_INSTRUCTIONS_FILE="{layout["model_instructions_file"]}"',
        ]
    ).strip() + "\n"


def render_model_instructions_template(env: Mapping[str, str] | None = None) -> str:
    layout = ensure_bridge_layout(env)
    template = _template_text(
        "model-instructions.template.md",
        """# MaDongMei Codex Memory Bridge

Use the public MaDongMei memory bridge for request-time context.

- Runtime home: `{{madongmei_home}}`
- Bridge root: `{{bridge_root}}`
- Memory runtime: `{{memory_runtime_dir}}`
- Before a task that benefits from public memory, call `memoryctl pre-hook --query "<request>"`.
- Treat returned `[MADONGMEI MEMORY]` blocks as public summaries only.
- Do not import private paths, secrets, personal notes, or device-local state.
""",
    )
    return (
        _render_template(
            template,
            {
                "madongmei_home": "${MADONGMEI_HOME}",
                "bridge_root": "${MADONGMEI_BRIDGE_ROOT}",
                "memory_runtime_dir": "${MEMORY_RUNTIME_DIR}",
            },
        ).strip()
        + "\n"
    )


def upsert_toml_key(path: Path, key: str, value: str) -> None:
    import json as _json
    import re as _re

    line = f"{key} = {_json.dumps(value)}"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = _re.compile(rf"(?m)^{_re.escape(key)}\s*=.*$")
    if pattern.search(text):
        text = pattern.sub(line, text, count=1)
    else:
        lines = text.splitlines()
        out: list[str] = []
        inserted = False
        for current in lines:
            if not inserted and current.startswith("["):
                out.append(line)
                inserted = True
            out.append(current)
        if not inserted:
            out.append(line)
        text = "\n".join(out)
    if text and not text.endswith("\n"):
        text += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@dataclass(frozen=True)
class FrameworkTemplates:
    request_context: str
    wiki_page: str
    skill_page: str
    graph_page: str
    workspace_registry: str
    install_env: str
    model_instructions: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def public_framework_templates(env: Mapping[str, str] | None = None) -> FrameworkTemplates:
    return FrameworkTemplates(
        request_context=render_request_context_template(),
        wiki_page=render_wiki_page_template(),
        skill_page=render_skill_page_template(),
        graph_page=render_graph_page_template(),
        workspace_registry=render_workspace_registry_template(),
        install_env=render_install_env_template(env),
        model_instructions=render_model_instructions_template(env),
    )


def install_bridge_scaffold(
    *,
    home: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env_map = dict(os.environ if env is None else env)
    if home is not None:
        env_map["MADONGMEI_HOME"] = str(Path(home).expanduser())
    layout = ensure_bridge_layout(env_map)
    config_path = install_config_path(env_map)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_install_env_template(env_map), encoding="utf-8")
    model_file = layout["model_instructions_file"]
    model_file.write_text(render_model_instructions_template(env_map), encoding="utf-8")
    config_toml = layout["codex_config_toml"]
    upsert_toml_key(config_toml, "model_instructions_file", str(model_file))
    return {
        "config_path": str(config_path),
        "codex_home": str(layout["codex_home"]),
        "bridge_root": str(layout["bridge_root"]),
        "workspace_root": str(layout["workspace_root"]),
        "workspace_link": str(layout["workspace_link"]),
        "memory_runtime_dir": str(layout["memory_runtime_dir"]),
        "registry_path": str(layout["registry_path"]),
        "graph_db_path": str(layout["graph_db_path"]),
        "graph_snapshot_dir": str(layout["graph_snapshot_dir"]),
        "model_instructions_file": str(model_file),
        "codex_config_toml": str(config_toml),
    }
