#!/usr/bin/env bash
# OutstaffingBot — git pull + rebuild/restart (только /opt/outstaffingbot).
# Аналог vspomni deploy/linux/pull-and-restart.sh
# Запуск на сервере от deploy:
#   cd /opt/outstaffingbot && ./deploy/linux/pull-and-restart.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/outstaffingbot}"
BRANCH="${BRANCH:-main}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-outstaffingbot}"

cd "$APP_DIR"

echo "==> git pull origin $BRANCH"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "==> docker compose up --build"
export COMPOSE_PROJECT_NAME
docker compose -p "$COMPOSE_PROJECT_NAME" \
  -f docker-compose.yml -f docker-compose.staging.yml up -d --build --remove-orphans

if docker compose -p "$COMPOSE_PROJECT_NAME" \
  -f docker-compose.yml -f docker-compose.staging.yml ps --status running api &>/dev/null; then
  echo "==> alembic upgrade head"
  docker compose -p "$COMPOSE_PROJECT_NAME" \
    -f docker-compose.yml -f docker-compose.staging.yml exec -T api alembic upgrade head
fi

if systemctl is-enabled outstaffingbot-bot &>/dev/null; then
  echo "==> systemd units enabled (containers also use restart: always)"
fi

echo "==> Done. docker compose ps:"
docker compose -p "$COMPOSE_PROJECT_NAME" \
  -f docker-compose.yml -f docker-compose.staging.yml ps
