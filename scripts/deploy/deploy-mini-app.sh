#!/usr/bin/env bash
# Build mini-app and sync dist to server (run locally from repo root).
# Usage: ./scripts/deploy/deploy-mini-app.sh [deploy@89.125.25.99]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REMOTE="${1:-deploy@89.125.25.99}"
REMOTE_DIR="/opt/outstaffingbot/mini-app/dist"
REMOTE_STAGING="${REMOTE_DIR}.staging"
REMOTE_HOST="${REMOTE#*@}"

echo "==> Verify source encoding (no mojibake)"
"$ROOT/scripts/deploy/verify-mini-app-encoding.sh"

echo "==> Build mini-app"
cd "$ROOT/mini-app"
npm ci
npm run build

echo "==> Upload verify script"
ssh "$REMOTE" "mkdir -p /opt/outstaffingbot/scripts/deploy"
rsync -avz "$ROOT/scripts/deploy/verify-mini-app-static.sh" "$REMOTE:/opt/outstaffingbot/scripts/deploy/"

echo "==> Sync dist -> $REMOTE:$REMOTE_STAGING (atomic swap after verify)"
ssh "$REMOTE" "rm -rf $REMOTE_STAGING && mkdir -p $REMOTE_STAGING"
rsync -avz "$ROOT/mini-app/dist/" "$REMOTE:$REMOTE_STAGING/"

echo "==> Fix permissions on staging (www-data must traverse dist)"
ssh "$REMOTE" "chmod 755 $REMOTE_STAGING && find $REMOTE_STAGING -type d -exec chmod 755 {} + && find $REMOTE_STAGING -type f -exec chmod 644 {} + && chmod -R a+rX $REMOTE_STAGING"

echo "==> Verify staging (www-data read + HTTP 200)"
ssh "root@${REMOTE_HOST}" "bash /opt/outstaffingbot/scripts/deploy/verify-mini-app-static.sh --fix-perms $REMOTE_STAGING"

echo "==> Atomic swap staging -> live dist"
ssh "$REMOTE" "rm -rf ${REMOTE_DIR}.old && mv $REMOTE_DIR ${REMOTE_DIR}.old && mv $REMOTE_STAGING $REMOTE_DIR && rm -rf ${REMOTE_DIR}.old"

echo "==> Verify live dist"
ssh "root@${REMOTE_HOST}" "bash /opt/outstaffingbot/scripts/deploy/verify-mini-app-static.sh --fix-perms $REMOTE_DIR"

echo "==> Verify UTF-8 in local dist (no mojibake markers)"
if grep -rqE $'\xef\xbf\xbd|\xef\x80|\xd0\x92\xd0' "$ROOT/mini-app/dist/assets/"*.js 2>/dev/null; then
  echo "WARN: dist JS may contain mojibake; check encoding." >&2
fi
if ! grep -q 'charset="UTF-8"' "$ROOT/mini-app/dist/index.html"; then
  echo "FAIL: dist/index.html missing UTF-8 charset meta." >&2
  exit 1
fi

echo "==> Verify index.html has no ?v= on asset URLs (breaks lazy chunk imports)"
if grep -qE '(src|href)="/assets/[^"]*\?v=' "$ROOT/mini-app/dist/index.html"; then
  echo "FAIL: index.html must not add ?v= to /assets/* — lazy chunks import bare filenames." >&2
  exit 1
fi

echo "==> Done. Bump MINI_APP_URL page query only (e.g. ?v=5), not asset URLs."
echo "    Restart bot if MINI_APP_URL changed: docker compose restart bot"