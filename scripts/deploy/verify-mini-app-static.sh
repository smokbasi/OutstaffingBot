#!/usr/bin/env bash
# Verify mini-app static files are readable by nginx (www-data) and return HTTP 200.
# Usage: verify-mini-app-static.sh [--fix-perms] [DIST_DIR]
set -euo pipefail

FIX_PERMS=0
DIST_DIR="/opt/outstaffingbot/mini-app/dist"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fix-perms) FIX_PERMS=1; shift ;;
    -*) echo "Unknown option: $1" >&2; exit 2 ;;
    *) DIST_DIR="$1"; shift ;;
  esac
done

INDEX="${DIST_DIR}/index.html"
BASE_URL="${MINI_APP_VERIFY_BASE:-https://www.outstaffingbot.online}"

if [[ ! -f "$INDEX" ]]; then
  echo "FAIL: missing $INDEX" >&2
  exit 1
fi

if grep -qE '(src|href)="/assets/[^"]*\?v=' "$INDEX"; then
  echo "FAIL: $INDEX has ?v= on asset URLs — remove it (lazy chunks import bare /assets/*.js)." >&2
  exit 1
fi

if [[ "$FIX_PERMS" -eq 1 ]]; then
  chmod 755 "$DIST_DIR"
  find "$DIST_DIR" -type d -exec chmod 755 {} +
  find "$DIST_DIR" -type f -exec chmod 644 {} +
  chmod -R a+rX "$DIST_DIR"
fi

mapfile -t PATHS < <(
  grep -oE '(src|href)="(/[^"]+)"' "$INDEX" \
    | sed -E 's/^(src|href)="(\/[^"]+)"/\2/' \
    | grep -E '^/(assets/|favicon\.svg|icons\.svg)' \
    | sort -u
)

fail=0
for rel in "${PATHS[@]}"; do
  # Query strings bust CDN/WebView cache; map to on-disk paths.
  local_rel="${rel%%\?*}"
  local_path="${DIST_DIR}${local_rel}"
  if [[ ! -f "$local_path" ]]; then
    echo "FAIL: missing file $local_path (from index.html $rel)" >&2
    fail=1
    continue
  fi
  if ! runuser -u www-data -- test -r "$local_path"; then
    echo "FAIL: www-data cannot read $local_path" >&2
    fail=1
  fi
  code=$(curl -sS -o /dev/null -w "%{http_code}" "${BASE_URL}${rel}")
  if [[ "$code" != "200" ]]; then
    echo "FAIL: HTTP $code for ${BASE_URL}${rel}" >&2
    fail=1
  else
    echo "OK: $rel ($code)"
  fi
done

if [[ "$fail" -ne 0 ]]; then
  exit 1
fi

echo "All ${#PATHS[@]} static assets verified."