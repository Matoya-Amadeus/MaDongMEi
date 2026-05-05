#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
HOME_OVERRIDE=""
JSON_OUTPUT=0

while [ $# -gt 0 ]; do
  case "$1" in
    --home)
      HOME_OVERRIDE="${2:-}"
      shift 2
      ;;
    --json)
      JSON_OUTPUT=1
      shift
      ;;
    --help|-h)
      cat <<'EOF'
Usage: ./scripts/install_context_bridge.sh [--home PATH] [--json]
EOF
      exit 0
      ;;
    *)
      echo "install_context_bridge: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

# shellcheck source=/dev/null
source "$ROOT/scripts/local_env.sh"
if [ -n "$HOME_OVERRIDE" ]; then
  export MADONGMEI_HOME="$HOME_OVERRIDE"
fi
madongmei_export_runtime_env

"$ROOT/bootstrap.sh" --home "$MADONGMEI_HOME" >/dev/null
# shellcheck source=/dev/null
source "$MADONGMEI_HOME/config.env"

if [ "$JSON_OUTPUT" -eq 1 ]; then
  "$ROOT/memoryctl" context install --json
else
  "$ROOT/memoryctl" context install
fi
