#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TMP_HOME="$(mktemp -d "${TMPDIR:-/tmp}/madongmei-selfcheck.XXXXXX")"
trap 'rm -rf "$TMP_HOME"' EXIT

export CODEX_HOME="$TMP_HOME/.codex"
export MADONGMEI_WIKI_DIR="$TMP_HOME/wiki"
export MADONGMEI_SKILL_DIR="$TMP_HOME/skills/public-autopilot"
"$ROOT/bootstrap.sh" --home "$TMP_HOME" >/dev/null
# shellcheck source=/dev/null
source "$TMP_HOME/config.env"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

bridge_json="$("$ROOT/scripts/install_context_bridge.sh" --home "$TMP_HOME" --json)"
printf '%s\n' "$bridge_json" | python3 -c 'import json, pathlib, sys; payload = json.load(sys.stdin); assert payload["config_path"].endswith("context-bridge.env"); assert payload["bridge_root"]; assert payload["workspace_root"]; assert payload["graph_snapshot_dir"]; assert pathlib.Path(payload["model_instructions_file"]).exists(); assert pathlib.Path(payload["codex_config_toml"]).exists()'

prehook_json="$("$ROOT/memoryctl" pre-hook --query "Keep the bridge install chain public." --json)"
printf '%s\n' "$prehook_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); assert payload["schema_version"] == 1; assert payload["public"] is True; assert "[MADONGMEI MEMORY]" in payload["block"]; assert payload["codex_context"]["repo"] == "MaDongMei"; assert payload["tool_route"]["auto_execute"] is False; assert "route_trace" in payload'

context_json="$("$ROOT/memoryctl" context template --query "Keep the bridge install chain public." --workspace-id "selfcheck" --json)"
printf '%s\n' "$context_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); assert "Keep the bridge install chain public." in payload["template"]; assert "<redacted public template>" in payload["template"]'

context_templates_json="$("$ROOT/memoryctl" context templates --json)"
printf '%s\n' "$context_templates_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); assert "request_context" in payload and "workspace_registry" in payload and "model_instructions" in payload'

workspace_json="$("$ROOT/memoryctl" workspace status --json)"
printf '%s\n' "$workspace_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); assert payload["bridge_root"]; assert payload["workspace_registry_path"]; assert payload["graph_db_path"]; assert payload["graph_snapshot_dir"]'

workspace_list_json="$("$ROOT/memoryctl" workspace list --json)"
printf '%s\n' "$workspace_list_json" | python3 -c 'import json, sys; rows = json.load(sys.stdin); assert rows and rows[0]["primary"]'

graph_json="$("$ROOT/memoryctl" graph template --title "Framework graph" --json)"
printf '%s\n' "$graph_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); assert "Framework graph" in payload["template"]'

graph_capture_json="$("$ROOT/memoryctl" graph capture --title "selfcheck graph" --content "Framework only" --tag public --json)"
printf '%s\n' "$graph_capture_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); assert payload["ok"] is True; assert payload["page_id"]'

graph_search_json="$("$ROOT/memoryctl" graph search Framework --json)"
printf '%s\n' "$graph_search_json" | python3 -c 'import json, sys; rows = json.load(sys.stdin); assert rows and rows[0]["title"] == "selfcheck graph"'

graph_doctor_json="$("$ROOT/memoryctl" graph doctor --json)"
printf '%s\n' "$graph_doctor_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); assert payload["ok"] is True; assert payload["snapshot_root"]'

mcp_manifest_json="$("$ROOT/memoryctl" mcp-serve --manifest --json)"
printf '%s\n' "$mcp_manifest_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); tool_names = {tool["name"] for tool in payload["tools"]}; assert "context_template" in tool_names; assert "graph_snapshot" in tool_names; assert "workspace_remove" in tool_names'

printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"ping"}' | "$ROOT/memoryctl" mcp-serve >/dev/null

autopilot_json="$("$ROOT/memoryctl" autopilot --title "selfcheck autopilot" "The canonical public rule is to keep installation decisions in the wiki." --tag public --tag smoke --json)"
printf '%s\n' "$autopilot_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); assert payload["plan"]["wiki_action"] == "promote"; assert payload["wiki"]["path"]; assert payload["record"]["bucket"] in {"wiki", "decision", "faq"}'

capture_json="$("$ROOT/memoryctl" capture --title "selfcheck" "MaDongMei selfcheck note" --tag public --tag smoke --json)"
printf '%s\n' "$capture_json" | python3 -c 'import json, sys; payload = json.load(sys.stdin); assert payload["title"] == "selfcheck"; assert "public" in payload["tags"]'

search_json="$("$ROOT/memoryctl" search selfcheck --json)"
printf '%s\n' "$search_json" | python3 -c 'import json, sys; rows = json.load(sys.stdin); assert rows and rows[0]["title"] == "selfcheck"'

"$ROOT/memoryctl" recall selfcheck >/dev/null
"$ROOT/memoryctl" review --json >/dev/null
"$ROOT/memoryctl" weekly-review --json >/dev/null
"$ROOT/memoryctl" doctor --json >/dev/null
"$ROOT/memoryctl" cycle "selfcheck public cycle" --json >/dev/null
"$ROOT/memoryctl" compact --json >/dev/null
"$ROOT/memoryctl" health --readonly --json >/dev/null
"$ROOT/memoryctl" verify-step all --json >/dev/null
"$ROOT/memoryctl" eval --format json >/dev/null
"$ROOT/memoryctl" regression-gate --format json >/dev/null
"$ROOT/memoryctl" personal-capture --title "selfcheck personal" --content "Public graph alias" --tags public,graph --json >/dev/null
"$ROOT/memoryctl" personal-search public --json >/dev/null
"$ROOT/memoryctl" personal-doctor --json >/dev/null
"$ROOT/memoryctl" personal-slo --json >/dev/null
"$ROOT/memoryctl" codex-ref-doctor --json >/dev/null

"$ROOT/memoryctl" reindex --json >/dev/null
"$ROOT/memoryctl" ingest --bucket facts --topic selfcheck-public --claim "public claim" --source-family open_source --authority-level secondary --source-ref templates/llmwiki-row.template.jsonl --collected-at 2026-04-29T00:00:00Z --freshness-days 30 --json >/dev/null
"$ROOT/memoryctl" graph-extract --json >/dev/null
"$ROOT/memoryctl" graph-build --json >/dev/null
"$ROOT/memoryctl" graph-query public --json >/dev/null
"$ROOT/memoryctl" eval-ab --format json >/dev/null
"$ROOT/memoryctl" eval-dashboard --format json >/dev/null
"$ROOT/memoryctl" baseline-snapshot --json >/dev/null
"$ROOT/memoryctl" phase4-acceptance --json >/dev/null
"$ROOT/memoryctl" phase-gate --json >/dev/null
"$ROOT/memoryctl" switch-gate --json >/dev/null
"$ROOT/memoryctl" capture-stm --text "short public memory" --json >/dev/null
"$ROOT/memoryctl" promote-mtm --json >/dev/null
"$ROOT/memoryctl" prune-expired --json >/dev/null
"$ROOT/memoryctl" workspace-list --format json >/dev/null
"$ROOT/memoryctl" workspace-register --root "$TMP_HOME/workspace" --label selfcheck --primary --json >/dev/null
"$ROOT/memoryctl" workspace-set-primary --root "$TMP_HOME/workspace" --json >/dev/null
"$ROOT/memoryctl" workspace-cleanup --json >/dev/null
"$ROOT/memoryctl" workspace-unregister --root "$TMP_HOME/workspace" --json >/dev/null
"$ROOT/memoryctl" orchestrate capture "selfcheck orchestrated note" --json >/dev/null
"$ROOT/memoryctl" trajectory-warmup --json >/dev/null
"$ROOT/memoryctl" "ris""k""-check" --json >/dev/null
"$ROOT/memoryctl" suggest --json >/dev/null
"$ROOT/memoryctl" trajectory-report --format json >/dev/null
"$ROOT/memoryctl" capture-acceptance --task selfcheck --summary "public acceptance" --json >/dev/null
"$ROOT/memoryctl" capture-regression --task selfcheck --summary "public regression" --json >/dev/null

export_file="$TMP_HOME/export.jsonl"
"$ROOT/memoryctl" export-jsonl --output "$export_file" >/dev/null
test -s "$export_file"

IMPORT_HOME="$(mktemp -d "${TMPDIR:-/tmp}/madongmei-selfcheck-import.XXXXXX")"
trap 'rm -rf "$TMP_HOME" "$IMPORT_HOME"' EXIT
"$ROOT/bootstrap.sh" --home "$IMPORT_HOME" >/dev/null
# shellcheck source=/dev/null
source "$IMPORT_HOME/config.env"
export MADONGMEI_HOME="$IMPORT_HOME"
"$ROOT/memoryctl" import-jsonl "$export_file" --replace >/dev/null
"$ROOT/memoryctl" search selfcheck --json >/dev/null

printf 'install_selfcheck: pass\n'
