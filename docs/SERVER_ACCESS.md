# SSH-доступ к серверу (OutstaffingBot)

> **Контекст:** OutstaffingBot деплоится на **общий VPS** с существующим проектом **vspomni_bot** (соседняя папка: `Desktop/AI MS/vspomni_bot`).  
> **Связанные документы:** [SERVER_SECURITY.md](./SERVER_SECURITY.md), [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md).

---

## Сервер

| Параметр | Значение |
|----------|----------|
| IP | `89.125.25.99` |
| ОС | Ubuntu (prod VPS vspomni) |
| Существующий проект | `vspomni_bot` — `/opt/vspomni_bot`, systemd |
| OutstaffingBot | `/opt/outstaffingbot` — Docker Compose, пользователь `deploy` |

**Важно:** ключи SSH **не хранятся в репозитории**. Используйте `~/.ssh/` на своей машине.

---

## SSH-ключ

Соседний проект использует ключ:

| Параметр | Значение |
|----------|----------|
| Путь к ключу (Windows) | `%USERPROFILE%\.ssh\id_vspomni` |
| Путь к ключу (Linux/macOS) | `~/.ssh/id_vspomni` |
| Пользователь vspomni / 3x-ui | `root` |
| Пользователь OutstaffingBot (рекомендуется) | `deploy` |

Если ключа ещё нет — создайте отдельную пару для OutstaffingBot (`id_outstaffing`) или используйте существующий `id_vspomni` (только если публичный ключ уже в `authorized_keys` на сервере).

```powershell
# Windows — проверка наличия ключа (содержимое НЕ коммитить)
Test-Path "$env:USERPROFILE\.ssh\id_vspomni"
```

---

## Подключение

### Быстрый способ (без config)

```bash
# vspomni / администрирование (root) — существующий доступ
ssh -i ~/.ssh/id_vspomni root@89.125.25.99

# OutstaffingBot (после создания пользователя deploy на сервере)
ssh -i ~/.ssh/id_vspomni deploy@89.125.25.99
```

PowerShell (Windows):

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_vspomni" deploy@89.125.25.99
```

### Рекомендуемый способ — `~/.ssh/config`

Скопируйте шаблон и отредактируйте пути:

```bash
# Linux/macOS
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cp scripts/deploy/ssh-config.example ~/.ssh/config.d/outstaffing 2>/dev/null || \
  cat scripts/deploy/ssh-config.example >> ~/.ssh/config
chmod 600 ~/.ssh/config
```

Windows: файл `%USERPROFILE%\.ssh\config` (создайте папку `.ssh`, если её нет).

После настройки:

```bash
ssh outstaffing-staging          # deploy → OutstaffingBot
ssh vspomni-prod                 # root → vspomni / 3x-ui (осторожно)
```

---

## SSH-туннели

### PostgreSQL / Redis OutstaffingBot (для локальной разработки)

На staging postgres/redis **не** слушают `0.0.0.0` — только Docker internal network. Туннель с хоста:

```bash
ssh outstaffing-staging -L 5433:127.0.0.1:5433 -L 6380:127.0.0.1:6379
```

Локальный `.env`:

```env
DATABASE_URL=postgresql+asyncpg://outstaffing:PASSWORD@127.0.0.1:5433/outstaffing
REDIS_URL=redis://127.0.0.1:6380/0
```

> Порты `5433`/`6380` на хосте пробрасываются из compose только если включены в `docker-compose.staging.yml` (см. комментарии в overlay). По умолчанию — доступ только из контейнеров; для dev-туннеля включите `127.0.0.1`-bind в overlay.

### 3x-ui panel (только root, localhost на сервере)

**Не открывайте панель в интернет.** Доступ через туннель (как в vspomni):

```bash
ssh -L 25855:127.0.0.1:25855 -i ~/.ssh/id_vspomni root@89.125.25.99
# Браузер: http://127.0.0.1:25855/<webBasePath>
```

Учётные данные панели — на сервере в `/root/x-ui-panel-access.txt` (не в git).

---

## Деплой OutstaffingBot

### С локальной машины (one-liner)

```bash
ssh outstaffing-staging 'cd /opt/outstaffingbot && ./scripts/deploy/deploy-staging.sh'
```

### На сервере

```bash
sudo -u deploy bash /opt/outstaffingbot/scripts/deploy/deploy-staging.sh
```

Перед **первым** деплоем на shared VPS — прочитайте [SERVER_SECURITY.md § F](./SERVER_SECURITY.md#f-чеклист-безопасности-перед-деплоем) и выполните аудит портов.

---

## Первичная настройка пользователя `deploy` (на shared VPS)

**Не запускайте** `bootstrap-server.sh` целиком на сервере с vspomni — он сбросит UFW. Вместо этого (от `root`):

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
mkdir -p /home/deploy/.ssh
# Вставить публичные ключи разработчиков (id_vspomni.pub или id_outstaffing.pub)
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

mkdir -p /opt/outstaffingbot
chown deploy:deploy /opt/outstaffingbot
sudo -u deploy git clone https://github.com/YOUR_ORG/OutstaffingBot.git /opt/outstaffingbot
sudo -u deploy cp /opt/outstaffingbot/.env.server.example /opt/outstaffingbot/.env
chmod 600 /opt/outstaffingbot/.env
```

---

## Безопасность ключей

| Правило | Детали |
|---------|--------|
| Ключи только в `~/.ssh/` | Никогда в репозитории, `.ssh/` в проекте не создавать |
| Права | `chmod 600` на private key, `700` на `~/.ssh` |
| Два разработчика | Отдельные ключи → оба в `authorized_keys` пользователя `deploy` |
| Root | Только owner; OutstaffingBot-деплой через `deploy`, не root |
| Ротация | При утечке — удалить ключ из `authorized_keys`, сгенерировать новый |

---

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| `Permission denied (publickey)` | Проверьте `-i ~/.ssh/id_vspomni`, ключ добавлен в `authorized_keys` |
| `deploy` не в группе docker | `sudo usermod -aG docker deploy`, перелогиниться |
| Порт занят при compose up | `ss -tlnp`, см. [SERVER_SECURITY.md § совместимость](./SERVER_SECURITY.md#совместимость-с-vspomni_bot) |
| Сломался vspomni после правок | **Откат:** не трогать `/opt/vspomni_bot`, `/usr/local/x-ui`, nginx vspomni |

---

*Последнее обновление: июнь 2026.*
---

## Deploy status (2026-06-20)

| Item | Status |
|------|--------|
| Path | /opt/outstaffingbot |
| Compose project | outstaffingbot — контейнеры outstaffing-postgres, outstaffing-redis |
| User deploy | SSH с id_vspomni проверен; Docker group |
| Postgres/Redis на host | **не** опубликованы (docker-compose.staging.yml + ports: !reset []) |
| API / bot | ещё не в compose (Phase 1+); /health на :8000 недоступен |
| .env | на сервере; **нужен BOT_TOKEN** staging-бота |

Повторный деплой (после git remote): ssh deploy@89.125.25.99 'cd /opt/outstaffingbot && COMPOSE_PROJECT_NAME=outstaffingbot ./scripts/deploy/deploy-staging.sh'
