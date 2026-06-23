#!/usr/bin/env bash
# Fail if mini-app sources or dist contain classic UTF-8→CP866 mojibake markers.
# Usage: ./scripts/deploy/verify-mini-app-encoding.sh [path-to-mini-app]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MINI_APP="${1:-$ROOT/mini-app}"
MOJIBAKE_RE='╨|╤|тАУ|тАФ|тАж|тЖР|┬╖'

echo "==> Check mini-app sources for mojibake"
if grep -rqE "$MOJIBAKE_RE" "$MINI_APP/src/" 2>/dev/null; then
  echo "FAIL: mojibake in mini-app/src (save files as UTF-8, not CP1251/CP866):" >&2
  grep -rlE "$MOJIBAKE_RE" "$MINI_APP/src/" >&2
  exit 1
fi

if [[ -d "$MINI_APP/dist/assets" ]]; then
  echo "==> Check mini-app dist for mojibake"
  if grep -rqE "$MOJIBAKE_RE" "$MINI_APP/dist/assets/"*.js 2>/dev/null; then
    echo "FAIL: mojibake in dist/assets — rebuild after fixing sources." >&2
    exit 1
  fi
fi

echo "OK: no mojibake markers in $MINI_APP"
