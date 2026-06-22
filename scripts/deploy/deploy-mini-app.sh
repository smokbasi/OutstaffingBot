#!/usr/bin/env bash
# Build mini-app and sync dist to server (run locally from repo root).
# Usage: ./scripts/deploy/deploy-mini-app.sh [deploy@89.125.25.99]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REMOTE="${1:-deploy@89.125.25.99}"
REMOTE_DIR="/opt/outstaffingbot/mini-app/dist"

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

echo "==> Verify assets on server"
ssh "$REMOTE" "curl -sS -o /dev/null -w 'html:%{http_code}\n' https://www.outstaffingbot.online/ && ls -la $REMOTE_DIR/assets/ | tail -3"

echo "==> Done. Restart bot if MINI_APP_URL changed: docker compose restart bot"
