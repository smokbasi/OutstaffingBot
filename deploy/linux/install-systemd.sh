#!/usr/bin/env bash
# OutstaffingBot — установка systemd units (auto-restart как vspomni).
# Запуск на сервере от root:
#   sudo APP_DIR=/opt/outstaffingbot DEPLOY_USER=deploy ./deploy/linux/install-systemd.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/outstaffingbot}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-outstaffingbot}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Запустите с sudo." >&2
  exit 1
fi

if [[ ! -d "$APP_DIR" ]]; then
  echo "FAIL: APP_DIR not found: $APP_DIR" >&2
  exit 1
fi

if ! id "$DEPLOY_USER" &>/dev/null; then
  echo "FAIL: user not found: $DEPLOY_USER" >&2
  exit 1
fi

render_unit() {
  local src="$1"
  local dest="$2"
  sed \
    -e "s|@OUTSTAFFING_APP_DIR@|${APP_DIR}|g" \
    -e "s|@OUTSTAFFING_USER@|${DEPLOY_USER}|g" \
    -e "s|@OUTSTAFFING_GROUP@|${DEPLOY_USER}|g" \
    -e "s|@OUTSTAFFING_COMPOSE_PROJECT@|${COMPOSE_PROJECT}|g" \
    "$src" >"$dest"
  chmod 644 "$dest"
  echo "  -> $dest"
}

echo "==> Installing OutstaffingBot systemd units"
echo "    APP_DIR=$APP_DIR"
echo "    DEPLOY_USER=$DEPLOY_USER"
echo "    COMPOSE_PROJECT=$COMPOSE_PROJECT"

for unit in outstaffingbot-infra outstaffingbot-api outstaffingbot-bot outstaffingbot-dashboard; do
  render_unit "$SCRIPT_DIR/${unit}.service" "/etc/systemd/system/${unit}.service"
done

systemctl daemon-reload

echo "==> Building containers (first start)"
sudo -u "$DEPLOY_USER" env COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT" \
  docker compose -f "$APP_DIR/docker-compose.yml" -f "$APP_DIR/docker-compose.staging.yml" \
  up -d --build postgres redis api bot

echo "==> Enabling units (boot + auto-restart on failure)"
systemctl enable outstaffingbot-infra outstaffingbot-api outstaffingbot-bot outstaffingbot-dashboard

echo "==> Starting stack"
systemctl start outstaffingbot-infra
systemctl start outstaffingbot-api
systemctl start outstaffingbot-bot
systemctl start outstaffingbot-dashboard

echo ""
echo "==> Status:"
systemctl is-active outstaffingbot-infra outstaffingbot-api outstaffingbot-bot outstaffingbot-dashboard || true
echo ""
echo "Docker containers should use restart: always (docker-compose.staging.yml)."
echo "Проверка: systemctl status outstaffingbot-bot outstaffingbot-dashboard"
