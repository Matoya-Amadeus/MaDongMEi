#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
TMP_HOME="$(mktemp -d "${TMPDIR:-/tmp}/madongmei-smoke.XXXXXX")"
trap 'rm -rf "$TMP_HOME"' EXIT

export CODEX_HOME="$TMP_HOME/.codex"
export MADONGMEI_WIKI_DIR="$TMP_HOME/wiki"
export MADONGMEI_SKILL_DIR="$TMP_HOME/skills/public-autopilot"
"$ROOT/bootstrap.sh" --home "$TMP_HOME" >/dev/null
export MADONGMEI_HOME="$TMP_HOME"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

"$ROOT/scripts/install_context_bridge.sh" --home "$TMP_HOME" >/dev/null
"$ROOT/memoryctl" pre-hook --query "smoke context" --json >/dev/null
"$ROOT/memoryctl" context template --query "smoke context" --workspace-id smoke --json >/dev/null
"$ROOT/memoryctl" context templates --json >/dev/null
"$ROOT/memoryctl" workspace status --json >/dev/null
"$ROOT/memoryctl" graph template --title "smoke graph" --json >/dev/null
"$ROOT/memoryctl" graph doctor --json >/dev/null
"$ROOT/memoryctl" mcp-serve --manifest --json >/dev/null

"$ROOT/memoryctl" autopilot --dry-run --title "smoke wiki" "The canonical public rule is to keep installation decisions in the wiki." --tag smoke --json >/dev/null
"$ROOT/memoryctl" autopilot --title "smoke skill" "Please run ./bootstrap.sh and validate the clean install workflow." --tag smoke --json >/dev/null
"$ROOT/memoryctl" capture --title "smoke" "memoryctl works" --tag smoke >/dev/null
"$ROOT/memoryctl" search smoke --json >/dev/null
"$ROOT/memoryctl" recall smoke >/dev/null
"$ROOT/memoryctl" review --json >/dev/null
"$ROOT/memoryctl" weekly-review --json >/dev/null
"$ROOT/memoryctl" doctor --json >/dev/null
"$ROOT/memoryctl" cycle "smoke public cycle" --json >/dev/null
"$ROOT/memoryctl" compact --json >/dev/null
"$ROOT/memoryctl" health --readonly --json >/dev/null
"$ROOT/memoryctl" verify-step all --json >/dev/null
"$ROOT/memoryctl" eval --format json >/dev/null
"$ROOT/memoryctl" regression-gate --format json >/dev/null
"$ROOT/memoryctl" personal-capture --title "smoke personal" --content "public graph alias" --tags public,graph --json >/dev/null
"$ROOT/memoryctl" personal-search public --json >/dev/null
"$ROOT/memoryctl" personal-slo --json >/dev/null
"$ROOT/memoryctl" codex-ref-doctor --json >/dev/null

"$ROOT/memoryctl" reindex --json >/dev/null
"$ROOT/memoryctl" ingest --bucket facts --topic smoke-public --claim "public claim" --source-family open_source --authority-level secondary --source-ref templates/llmwiki-row.template.jsonl --collected-at 2026-04-29T00:00:00Z --freshness-days 30 --json >/dev/null
"$ROOT/memoryctl" graph-query public --json >/dev/null
"$ROOT/memoryctl" eval-ab --format json >/dev/null
"$ROOT/memoryctl" eval-dashboard --format json >/dev/null
"$ROOT/memoryctl" baseline-snapshot --json >/dev/null
"$ROOT/memoryctl" phase-gate --json >/dev/null
"$ROOT/memoryctl" switch-gate --json >/dev/null
"$ROOT/memoryctl" capture-stm --text "short public memory" --json >/dev/null
"$ROOT/memoryctl" prune-expired --json >/dev/null
"$ROOT/memoryctl" workspace-list --format json >/dev/null
"$ROOT/memoryctl" orchestrate capture "smoke orchestrated note" --json >/dev/null
"$ROOT/memoryctl" trajectory-warmup --json >/dev/null
"$ROOT/memoryctl" "ris""k""-check" --json >/dev/null
"$ROOT/memoryctl" suggest --json >/dev/null
"$ROOT/memoryctl" trajectory-report --format json >/dev/null
"$ROOT/memoryctl" capture-acceptance --task smoke --summary "public acceptance" --json >/dev/null
"$ROOT/memoryctl" capture-regression --task smoke --summary "public regression" --json >/dev/null

printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"ping"}' | "$ROOT/memoryctl" mcp-serve >/dev/null

export_file="$TMP_HOME/export.jsonl"
"$ROOT/memoryctl" export-jsonl --output "$export_file" >/dev/null
test -s "$export_file"

IMPORT_HOME="$(mktemp -d "${TMPDIR:-/tmp}/madongmei-smoke-import.XXXXXX")"
trap 'rm -rf "$TMP_HOME" "$IMPORT_HOME"' EXIT
"$ROOT/bootstrap.sh" --home "$IMPORT_HOME" >/dev/null
export MADONGMEI_HOME="$IMPORT_HOME"
"$ROOT/memoryctl" import-jsonl "$export_file" --replace >/dev/null
"$ROOT/memoryctl" search smoke --json >/dev/null

printf 'smoke: pass\n'
