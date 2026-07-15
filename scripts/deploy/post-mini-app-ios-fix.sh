#!/usr/bin/env bash
# После deploy-mini-app.sh: обновить cache-bust и перезапустить бота.
# Запуск на сервере (root или deploy с docker):
#   ssh deploy@89.125.25.99 'bash -s' < scripts/deploy/post-mini-app-ios-fix.sh
set -euo pipefail

APP_DIR="${OUTSTAFFING_APP_DIR:-/opt/outstaffingbot}"
ENV_FILE="$APP_DIR/.env"
NEW_VERSION="${MINI_APP_CACHE_VERSION:-25}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FAIL: $ENV_FILE not found" >&2
  exit 1
fi

if grep -q '^MINI_APP_URL=' "$ENV_FILE"; then
  sed -i -E "s|^MINI_APP_URL=.*|MINI_APP_URL=https://www.outstaffingbot.online/?v=${NEW_VERSION}|" "$ENV_FILE"
else
  echo "MINI_APP_URL=https://www.outstaffingbot.online/?v=${NEW_VERSION}" >> "$ENV_FILE"
fi

echo "==> MINI_APP_URL updated to ?v=${NEW_VERSION}"
grep '^MINI_APP_URL=' "$ENV_FILE"

cd "$APP_DIR"
docker compose restart bot
echo "==> bot restarted"
