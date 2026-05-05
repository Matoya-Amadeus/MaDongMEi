#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export CODEX_HOME="${CODEX_HOME:-${HOME%/}/.codex}"

"$ROOT/tests/run_smoke.sh"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py'
"$ROOT/scripts/config_schema_gate.py" --json >/dev/null
"$ROOT/scripts/llmwiki_route_map.py" --check --json >/dev/null
"$ROOT/scripts/llmwiki_source_ref_gate.py" --json >/dev/null
"$ROOT/scripts/llmwiki_citation_gate.py" --json >/dev/null
"$ROOT/scripts/llmwiki_conflict_report.py" --json >/dev/null

"$ROOT/scripts/gate_matrix.py" report --mode quality_gate --json >/dev/null
"$ROOT/scripts/gate_matrix.py" report --mode push_readiness --json >/dev/null
"$ROOT/scripts/docs_reality_check.sh" --json >/dev/null
"$ROOT/scripts/check_cross_repo_refs.sh" --json >/dev/null
"$ROOT/scripts/preflight_paths.sh" --json >/dev/null
"$ROOT/scripts/cross_device_lint.sh" --json >/dev/null
"$ROOT/scripts/git_truth_snapshot.sh" --json >/dev/null
"$ROOT/scripts/local_ignored_artifact_report.py" --json >/dev/null
python3 "$ROOT/scripts/madongmei_code_scorecard.py" --json --no-record >/dev/null
python3 "$ROOT/scripts/request_route_real_prompt_suite.py" >/dev/null
"$ROOT/scripts/audit_index.py" --json >/dev/null
"$ROOT/scripts/task_protocol_validate.py" --tas""k""-type code --json >/dev/null
"$ROOT/scripts/style_lock_gate.py" --json >/dev/null
"$ROOT/scripts/push_readiness.sh" --strict --tas""k""-type code --json >/dev/null
"$ROOT/scripts/release_strict_gate.sh" --json >/dev/null

printf 'install_validation_matrix: pass\n'
