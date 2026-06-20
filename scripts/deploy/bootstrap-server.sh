#!/usr/bin/env bash
# OutstaffingBot — первичная настройка Ubuntu 24.04 VPS (dev/staging)
# Запуск: curl -sO .../bootstrap-server.sh && chmod +x bootstrap-server.sh && sudo ./bootstrap-server.sh
#
# Переменные окружения (опционально):
#   DEPLOY_USER=deploy
#   APP_DIR=/opt/outstaffingbot
#   GIT_REPO=https://github.com/YOUR_ORG/OutstaffingBot.git

set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="${APP_DIR:-/opt/outstaffingbot}"
GIT_REPO="${GIT_REPO:-}"

echo "==> OutstaffingBot bootstrap (staging)"
echo "    DEPLOY_USER=$DEPLOY_USER"
echo "    APP_DIR=$APP_DIR"

if [[ "${SHARED_VPS:-}" == "1" ]] || [[ -d /opt/vspomni_bot ]] || [[ -d /usr/local/x-ui ]]; then
  echo ""
  echo "WARN: Обнаружен shared VPS (vspomni / 3x-ui)."
  echo "      НЕ запускайте этот скрипт целиком — UFW и пути могут сломать VPN/bot."
  echo "      См. docs/SERVER_SECURITY.md и docs/SERVER_ACCESS.md (ручная настройка deploy user)."
  echo "      Для принудительного запуска: SHARED_VPS=0 sudo ./bootstrap-server.sh"
  echo ""
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Запустите скрипт с sudo." >&2
  exit 1
fi

echo "==> Обновление системы"
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq git curl ca-certificates ufw

echo "==> Установка Docker"
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable docker
systemctl start docker

echo "==> Пользователь $DEPLOY_USER"
if ! id "$DEPLOY_USER" &>/dev/null; then
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER"

echo "==> Директория приложения $APP_DIR"
mkdir -p "$APP_DIR"
chown "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"

if [[ -n "$GIT_REPO" ]] && [[ ! -d "$APP_DIR/.git" ]]; then
  echo "==> Клонирование $GIT_REPO"
  sudo -u "$DEPLOY_USER" git clone "$GIT_REPO" "$APP_DIR"
elif [[ -z "$GIT_REPO" ]]; then
  echo "==> GIT_REPO не задан — клонируйте репозиторий вручную:"
  echo "    sudo -u $DEPLOY_USER git clone https://github.com/YOUR_ORG/OutstaffingBot.git $APP_DIR"
fi

if [[ -f "$APP_DIR/.env.example" ]]; then
  if [[ ! -f "$APP_DIR/.env" ]]; then
    echo "==> Создание .env из .env.example"
    sudo -u "$DEPLOY_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    chown "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR/.env"
    echo "    Отредактируйте $APP_DIR/.env (BOT_TOKEN, пароли БД)"
  fi
fi

echo "==> Firewall (SSH + HTTP/S)"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable || true

echo "==> Docker Compose (infra)"
if [[ -f "$APP_DIR/docker-compose.yml" ]]; then
  cd "$APP_DIR"
  sudo -u "$DEPLOY_USER" docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
  sudo -u "$DEPLOY_USER" docker compose ps
else
  echo "    docker-compose.yml не найден — выполните git clone и запустите compose вручную"
fi

cat <<'EOF'

==> Bootstrap завершён. Следующие шаги:

1. Добавьте SSH-ключи обоих разработчиков:
     /home/deploy/.ssh/authorized_keys

2. Отредактируйте .env на сервере:
     nano /opt/outstaffingbot/.env

3. Миграции и seed (после установки Python backend на сервере или через api-контейнер):
     cd /opt/outstaffingbot/backend && alembic upgrade head
     python ../scripts/seed_categories.py && python ../scripts/seed_metro.py

4. Деплой обновлений:
     cd /opt/outstaffingbot && git pull && docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d

Подробнее: docs/SERVER_AND_TEAM.md, docs/SERVER_ACCESS.md, docs/SERVER_SECURITY.md

EOF
