#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export CODEX_HOME="${CODEX_HOME:-${HOME%/}/.codex}"

"$ROOT/scripts/privacy_audit.sh" --json >/dev/null
"$ROOT/scripts/export_public_projection.py" --check --json >/dev/null
"$ROOT/scripts/config_schema_gate.py" --json >/dev/null
"$ROOT/scripts/docs_reality_check.sh" --json >/dev/null
"$ROOT/scripts/check_cross_repo_refs.sh" --json >/dev/null
"$ROOT/scripts/cross_device_lint.sh" --json >/dev/null
"$ROOT/install_selfcheck.sh"
"$ROOT/install_validation_matrix.sh"
"$ROOT/scripts/push_readiness.sh" --strict --tas""k""-type code --json >/dev/null
"$ROOT/scripts/release_strict_gate.sh" --json >/dev/null
"$ROOT/scripts/madongmei_doctor.py" --json >/dev/null

printf 'quality_gate: pass\n'
