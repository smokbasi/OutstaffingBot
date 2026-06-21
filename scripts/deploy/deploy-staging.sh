#!/usr/bin/env bash
# Ручной деплой на staging VPS (запускать НА СЕРВЕРЕ от пользователя deploy)
# Scope: только /opt/outstaffingbot — НЕ трогает vspomni_bot, 3x-ui, nginx vspomni.
# Shared VPS: см. docs/SERVER_SECURITY.md §10 (чеклист перед деплоем)
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/outstaffingbot}"
BRANCH="${BRANCH:-main}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-outstaffingbot}"

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "FAIL: not a git repo: $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"
echo "==> OutstaffingBot deploy (project=$COMPOSE_PROJECT_NAME, dir=$APP_DIR)"
echo "==> git pull origin $BRANCH"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "==> docker compose up"
export COMPOSE_PROJECT_NAME
docker compose -p "$COMPOSE_PROJECT_NAME" \
  -f docker-compose.yml -f docker-compose.staging.yml up -d --build

# Раскомментировать когда api-контейнер будет в compose:
docker compose -p "$COMPOSE_PROJECT_NAME" \
  -f docker-compose.yml -f docker-compose.staging.yml exec -T api alembic upgrade head

echo "==> Deploy done. Проверьте: docker compose ps"
