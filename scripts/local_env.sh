#!/usr/bin/env bash
set -euo pipefail

madongmei_repo_root() {
  local source_path="${BASH_SOURCE[0]:-$0}"
  cd -- "$(dirname -- "$source_path")/.." >/dev/null 2>&1 && pwd -P
}

madongmei_default_codex_home() {
  if [ -n "${CODEX_HOME:-}" ]; then
    printf '%s\n' "$CODEX_HOME"
  else
    printf '%s\n' "${HOME%/}/.codex"
  fi
}

madongmei_default_home() {
  if [ -n "${MADONGMEI_HOME:-}" ]; then
    printf '%s\n' "$MADONGMEI_HOME"
  elif [ -n "${XDG_STATE_HOME:-}" ]; then
    printf '%s\n' "${XDG_STATE_HOME%/}/madongmei"
  else
    printf '%s\n' "${HOME%/}/.madongmei"
  fi
}

madongmei_export_runtime_env() {
  export CODEX_HOME="${CODEX_HOME:-$(madongmei_default_codex_home)}"
  export MADONGMEI_HOME="${MADONGMEI_HOME:-$(madongmei_default_home)}"
  export MADONGMEI_DATA_DIR="${MADONGMEI_DATA_DIR:-${MADONGMEI_HOME%/}/data}"
  export MADONGMEI_LOG_DIR="${MADONGMEI_LOG_DIR:-${MADONGMEI_HOME%/}/logs}"
  export MADONGMEI_CACHE_DIR="${MADONGMEI_CACHE_DIR:-${MADONGMEI_HOME%/}/cache}"
  export MADONGMEI_DB_PATH="${MADONGMEI_DB_PATH:-${MADONGMEI_DATA_DIR%/}/memory.jsonl}"
  export MADONGMEI_BRIDGE_ROOT="${MADONGMEI_BRIDGE_ROOT:-${CODEX_HOME%/}/.madongmei-runtime}"
  export WORKSPACE_SOURCE_ROOT="${WORKSPACE_SOURCE_ROOT:-${MADONGMEI_BRIDGE_ROOT%/}/workspaces/$(basename "$(madongmei_repo_root)")}"
  export WORKSPACE_SOURCE_LINK="${WORKSPACE_SOURCE_LINK:-${WORKSPACE_SOURCE_ROOT%/}/.agent-memory}"
  export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$WORKSPACE_SOURCE_ROOT}"
  export MEMORY_RUNTIME_DIR="${MEMORY_RUNTIME_DIR:-${MADONGMEI_BRIDGE_ROOT%/}/memory}"
  export WORKSPACE_REGISTRY_FILE="${WORKSPACE_REGISTRY_FILE:-${MEMORY_RUNTIME_DIR%/}/state/workspace_registry.json}"
  export MADONGMEI_GRAPH_DIR="${MADONGMEI_GRAPH_DIR:-${MEMORY_RUNTIME_DIR%/}/graph}"
  export MADONGMEI_GRAPH_RUNTIME_DIR="${MADONGMEI_GRAPH_RUNTIME_DIR:-$MADONGMEI_GRAPH_DIR}"
  export MADONGMEI_GRAPH_DB_PATH="${MADONGMEI_GRAPH_DB_PATH:-${MADONGMEI_GRAPH_DIR%/}/personal.db}"
  export MADONGMEI_GRAPH_SNAPSHOT_DIR="${MADONGMEI_GRAPH_SNAPSHOT_DIR:-${MADONGMEI_GRAPH_DIR%/}/snapshots}"
  export MADONGMEI_WIKI_DIR="${MADONGMEI_WIKI_DIR:-$(madongmei_repo_root)/knowledge/wiki}"
  export MADONGMEI_SKILL_DIR="${MADONGMEI_SKILL_DIR:-$(madongmei_repo_root)/skills/public-autopilot}"
}
