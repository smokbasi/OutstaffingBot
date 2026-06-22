#!/usr/bin/env bash
# ╨а╤Г╤З╨╜╨╛╨╣ ╨┤╨╡╨┐╨╗╨╛╨╣ ╨╜╨░ staging VPS (╨╖╨░╨┐╤Г╤Б╨║╨░╤В╤М ╨Э╨Р ╨б╨Х╨а╨Т╨Х╨а╨Х ╨╛╤В ╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╤В╨╡╨╗╤П deploy)
# Scope: ╤В╨╛╨╗╤М╨║╨╛ /opt/outstaffingbot тАФ ╨Э╨Х ╤В╤А╨╛╨│╨░╨╡╤В vspomni_bot, 3x-ui, nginx vspomni.
# Shared VPS: ╤Б╨╝. docs/SERVER_SECURITY.md ┬з10 (╤З╨╡╨║╨╗╨╕╤Б╤В ╨┐╨╡╤А╨╡╨┤ ╨┤╨╡╨┐╨╗╨╛╨╡╨╝)
#
# Usage:
#   ./scripts/deploy/deploy-staging.sh
#   BRANCH=feature/my-branch NO_CACHE=1 ./scripts/deploy/deploy-staging.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/outstaffingbot}"
BRANCH="${BRANCH:-main}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-outstaffingbot}"
NO_CACHE="${NO_CACHE:-0}"
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.staging.yml)

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "FAIL: not a git repo: $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"
echo "==> OutstaffingBot deploy (project=$COMPOSE_PROJECT_NAME, dir=$APP_DIR, branch=$BRANCH)"

echo "==> git fetch && checkout $BRANCH"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

BUILD_ARGS=()
if [[ "$NO_CACHE" == "1" ]]; then
  BUILD_ARGS+=(--no-cache)
fi

echo "==> docker compose build api bot worker"
export COMPOSE_PROJECT_NAME
docker compose -p "$COMPOSE_PROJECT_NAME" "${COMPOSE_FILES[@]}" build "${BUILD_ARGS[@]}" api bot worker

echo "==> docker compose up -d"
docker compose -p "$COMPOSE_PROJECT_NAME" "${COMPOSE_FILES[@]}" up -d

echo "==> alembic upgrade head"
docker compose -p "$COMPOSE_PROJECT_NAME" "${COMPOSE_FILES[@]}" exec -T api alembic upgrade head

echo "==> wait for /health"
for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null; then
    break
  fi
  sleep 2
done
curl -sf http://127.0.0.1:8000/health | head -c 200
echo

if grep -q '^WEBHOOK_URL=' .env 2>/dev/null && grep -q '^WEBHOOK_SECRET=' .env 2>/dev/null; then
  echo "==> webhook mode: restart bot (register webhook with Telegram)"
  docker compose -p "$COMPOSE_PROJECT_NAME" "${COMPOSE_FILES[@]}" restart bot
  sleep 3
  docker compose -p "$COMPOSE_PROJECT_NAME" "${COMPOSE_FILES[@]}" logs --tail=20 bot
fi

echo "==> docker compose ps"
docker compose -p "$COMPOSE_PROJECT_NAME" "${COMPOSE_FILES[@]}" ps

echo "==> Deploy done"

echo "    Auto-restart (как vspomni): deploy/linux/install-systemd.sh — один раз от root"
