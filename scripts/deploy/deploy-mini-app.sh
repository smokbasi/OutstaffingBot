#!/usr/bin/env bash
# Build mini-app and sync dist to server (run locally from repo root).
# Usage: ./scripts/deploy/deploy-mini-app.sh [deploy@89.125.25.99]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REMOTE="${1:-deploy@89.125.25.99}"
REMOTE_DIR="/opt/outstaffingbot/mini-app/dist"

echo "==> Verify source encoding (no mojibake)"
"$ROOT/scripts/deploy/verify-mini-app-encoding.sh"

echo "==> Build mini-app"
cd "$ROOT/mini-app"
npm ci
npm run build

echo "==> Sync dist -> $REMOTE:$REMOTE_DIR"
ssh "$REMOTE" "mkdir -p $REMOTE_DIR"
rsync -avz --delete "$ROOT/mini-app/dist/" "$REMOTE:$REMOTE_DIR/"

# nginx worker runs as www-data — dist must be traversable (o+x on dirs, o+r on files).
echo "==> Fix static file permissions for nginx (www-data)"
ssh "$REMOTE" "chmod 755 $REMOTE_DIR && find $REMOTE_DIR -type d -exec chmod 755 {} + && find $REMOTE_DIR -type f -exec chmod 644 {} +"

echo "==> Verify UTF-8 in local dist (no mojibake markers)"
if grep -rqE '╨|╤|тАУ|тАФ|тАж|тЖР|┬╖' "$ROOT/mini-app/dist/assets/"*.js 2>/dev/null; then
  echo "FAIL: dist JS contains mojibake (CP866/CP1251 misread UTF-8). Rebuild from UTF-8 sources." >&2
  exit 1
fi
if ! grep -q 'charset="UTF-8"' "$ROOT/mini-app/dist/index.html"; then
  echo "FAIL: dist/index.html missing UTF-8 charset meta." >&2
  exit 1
fi

echo "==> Verify assets on server"
ssh "$REMOTE" "curl -sS -o /dev/null -w 'html:%{http_code}\n' https://www.outstaffingbot.online/ && ls -la $REMOTE_DIR/assets/ | tail -3"

echo "==> Verify Cyrillic on live site (bundle must contain Откликнуться, not mojibake)"
REMOTE_JS="$(ssh "$REMOTE" "grep -l 'VacancyDetailPage' $REMOTE_DIR/assets/*.js 2>/dev/null | head -1")"
if [[ -z "$REMOTE_JS" ]]; then
  echo "WARN: VacancyDetailPage chunk not found on server; skip Cyrillic grep." >&2
else
  if ssh "$REMOTE" "grep -qE '╨|тАУ' '$REMOTE_JS'"; then
    echo "FAIL: deployed JS still contains mojibake in $REMOTE_JS" >&2
    exit 1
  fi
  if ! ssh "$REMOTE" "grep -q 'Откликнуться' '$REMOTE_JS'"; then
    echo "FAIL: deployed JS missing expected Cyrillic string Откликнуться" >&2
    exit 1
  fi
  echo "OK: Cyrillic strings verified in $(basename "$REMOTE_JS")"
fi

echo "==> Done. Restart bot if MINI_APP_URL changed: docker compose restart bot"
