# Безопасность на общем VPS

> **Для кого:** команда OutstaffingBot + владелец сервера.  
> **Контекст:** один VPS (`89.125.25.99`) уже обслуживает **vspomni_bot** (Telegram-бот + Mini App dashboard), **3X-UI** (VPN/proxy, 27+ клиентов) и конфиги **вне git**. OutstaffingBot добавляется **изолированно**.  
> **Связанные документы:** [SERVER_ACCESS.md](./SERVER_ACCESS.md), [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md).

---

## 1. Что уже на сервере (не трогать без бэкапа)

### vspomni_bot (соседний проект)

| Компонент | Путь / сервис | Порты (публичные / localhost) |
|-----------|---------------|-------------------------------|
| Prod bot | `/opt/vspomni_bot`, systemd `vspomni` | — |
| Dashboard Mini App | systemd `vspomni-dashboard` | `127.0.0.1:8088` → nginx `:8443` |
| Control API | env `VSPOMNI_CONTROL_PORT` | `127.0.0.1:8765` |
| Env / секреты | `/srv/vspomni/vspomni.env`, `/etc/vspomni/vspomni.env` | **не в git** |
| Test bot (если есть) | `/opt/vspomni_bot_test` | отдельный токен |
| Деплой | `deploy/linux/pull-and-restart.sh` | только `/opt/vspomni_bot` |

### 3X-UI / VPN

| Компонент | Путь | Порты |
|-----------|------|-------|
| 3x-ui binary | `/usr/local/x-ui/` | panel `127.0.0.1:25855` |
| x-ui systemd | `systemctl x-ui` | — |
| Docker xray | контейнер `3x-ui` | зависит от inbound |
| nginx SNI split | `/etc/nginx/sites-enabled/` | `:443`, `:80` |
| VPN Reality / WS | inbounds в x-ui DB | `:443`, `:433`, `:8444`, `:8446`, `:8448`, `:8449` |
| Подписки | nginx `vspomni-sub` | `:2096` |
| Sub internal | x-ui setting | `127.0.0.1:20961` |
| Учётные данные панели | `/root/x-ui-panel-access.txt` | **не в git** |
| Бэкап клиентов | `deploy/linux/XUI_CLIENTS_27_BACKUP.md` (в git vspomni) | — |

### Запрещённые зоны для OutstaffingBot

```
/usr/local/x-ui/
/etc/x-ui/
/root/x-ui-panel-access.txt
/opt/vspomni_bot/
/opt/vspomni_bot_test/
/srv/vspomni/
/etc/vspomni/
/etc/nginx/sites-enabled/3x-ui*
/etc/nginx/sites-enabled/vspomni*
```

**Правило:** деплой OutstaffingBot **не** вызывает `systemctl restart x-ui`, **не** правит nginx vspomni, **не** запускает `ufw reset`.

---

## 2. Изоляция OutstaffingBot

### A. Файловая система

```
/opt/outstaffingbot/          # git clone OutstaffingBot
├── .env                      # chmod 600, владелец deploy
├── docker-compose.yml
├── docker-compose.staging.yml
└── ...

/var/lib/docker/volumes/      # префикс outstaffingbot_* (compose project name)
```

### B. Docker

| Мера | Реализация |
|------|------------|
| Отдельный compose project | `COMPOSE_PROJECT_NAME=outstaffingbot` или `-p outstaffingbot` |
| Своя сеть | `outstaffing_internal` (см. `docker-compose.staging.yml`) |
| Без default bridge для БД | postgres/redis **без** `0.0.0.0:5432` |
| Имена контейнеров | `outstaffing-postgres`, `outstaffing-redis`, … |
| Не делить volumes | отдельные `postgres_data`, `redis_data` |

```bash
# Запуск (только из /opt/outstaffingbot)
cd /opt/outstaffingbot
docker compose -p outstaffingbot \
  -f docker-compose.yml -f docker-compose.staging.yml up -d
```

### C. Пользователи и SSH

| Роль | Пользователь | Доступ |
|------|--------------|--------|
| vspomni / 3x-ui | `root` | полный (owner) |
| OutstaffingBot deploy | `deploy` | docker group, `/opt/outstaffingbot` |
| Dev 1, Dev 2 | SSH keys | оба в `/home/deploy/.ssh/authorized_keys` |

- **Не** использовать общий root-пароль.
- Dev2 **не** нужен root для OutstaffingBot — достаточно `deploy`.
- sudo для `deploy` — **не** давать без необходимости.

### D. nginx (общий, но раздельные server blocks)

OutstaffingBot получает **отдельный поддомен**, например `staging-outstaffing.example.com`:

```nginx
# /etc/nginx/sites-available/outstaffing-staging.conf
# НЕ перезаписывать vspomni конфиги
server {
    listen 443 ssl http2;
    server_name staging-outstaffing.example.com;
    # ssl_certificate — certbot
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
    }
    location /app/ {
        proxy_pass http://127.0.0.1:5173/;  # или static build
    }
    location /webhook/ {
        proxy_pass http://127.0.0.1:8000/webhook/;
    }
}
```

```bash
ln -sf /etc/nginx/sites-available/outstaffing-staging.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx   # reload, не restart — меньше риск для :443 split
```

---

## 3. Защита 3X-UI

| Угроза | Мера |
|--------|------|
| Панель в интернете | Bind `127.0.0.1:25855` (см. `vspomni_bot/deploy/linux/harden-vps-vpn.sh`) |
| Доступ админа | SSH tunnel: `ssh -L 25855:127.0.0.1:25855 root@89.125.25.99` |
| Brute-force | fail2ban (уже настроен на vspomni) |
| Слабый пароль | Смена через `x-ui setting -username -password`; хранить в `/root/x-ui-panel-access.txt` |
| Публичный порт 54321 | **Не использовать** — панель только localhost |
| Бэкап | Периодически: `/usr/local/x-ui/` + `x-ui.db` → `~/backups/3x-ui/` (encrypted tar, **не git**) |

```bash
# Пример бэкапа (root, cron)
tar czf ~/backups/3x-ui/x-ui-$(date +%Y%m%d).tar.gz \
  /usr/local/x-ui/ /etc/x-ui/ 2>/dev/null || true
chmod 600 ~/backups/3x-ui/*.tar.gz
```

OutstaffingBot **никогда** не монтирует и не изменяет каталоги x-ui.

---

## 4. Защита существующего vspomni_bot

### Перед любым изменением на сервере

```bash
# Read-only аудит (можно запускать от root или deploy)
ss -tlnp                                    # кто слушает порты
docker ps -a                                # все контейнеры
systemctl is-active vspomni vspomni-dashboard x-ui nginx
ls -la /opt/vspomni_bot/.env /etc/vspomni/  # права на секреты
```

### Бэкап перед деплоем OutstaffingBot

```bash
# root
mkdir -p ~/backups/pre-outstaffing-$(date +%Y%m%d)
cp -a /opt/vspomni_bot ~/backups/pre-outstaffing-*/vspomni_bot-tree 2>/dev/null || true
cp /srv/vspomni/vspomni.env ~/backups/pre-outstaffing-*/ 2>/dev/null || true
cp /etc/vspomni/vspomni.env ~/backups/pre-outstaffing-*/ 2>/dev/null || true
nginx -T > ~/backups/pre-outstaffing-*/nginx-full.conf
docker compose -f /opt/outstaffingbot/docker-compose.yml config > /dev/null 2>&1 || true
```

### Изоляция test/prod vspomni

**Запрещено:** копировать `/opt/vspomni_bot_test` → `/opt/vspomni_bot` или env test → prod.  
Правило зафиксировано в vspomni: `.cursor/rules/test-bot-isolation.mdc`.

---

## 5. Карта портов и конфликты

### Занято vspomni / 3x-ui (не использовать для OutstaffingBot)

| Порт | Назначение |
|------|------------|
| 22 | SSH |
| 80 | nginx HTTP |
| 443 | nginx (SNI: WS / Reality / MTProto) |
| 433 | VLESS Reality |
| 2096 | VPN subscriptions (nginx) |
| 8443 | vspomni dashboard (nginx → 8088) |
| 8444, 8446, 8448, 8449 | VPN inbounds |
| 5222 | MTProxy (если включён) |
| 8765 | vspomni Control API (localhost) |
| 8088 | vspomni dashboard (localhost) |
| 25855 | 3x-ui panel (localhost) |
| 20961 | x-ui sub (localhost) |

### Рекомендуется для OutstaffingBot

| Порт | Bind | Назначение |
|------|------|------------|
| 5432 | **только Docker internal** | postgres (не на host) |
| 6379 | **только Docker internal** | redis |
| 8000 | `127.0.0.1:8000` | FastAPI (nginx upstream) |
| 5433 | `127.0.0.1:5433` (опционально) | postgres для SSH-туннеля dev |
| 6380 | `127.0.0.1:6380` (опционально) | redis для SSH-туннеля dev |

**8000** на vspomni не занят — безопасно bind на localhost для API OutstaffingBot.

**5432 на host:** если на сервере уже есть postgres — OutstaffingBot использует **только контейнер**, без publish порта (см. staging overlay).

---

## 6. Секреты

| Тип | Где хранить | Git |
|-----|-------------|-----|
| `BOT_TOKEN`, `WEBHOOK_*` | `/opt/outstaffingbot/.env` | `.env.example`, `.env.server.example` |
| Postgres password | `.env` + compose vars | placeholder |
| vspomni tokens | `/srv/vspomni/`, `/etc/vspomni/` | **нет** |
| 3x-ui credentials | `/root/x-ui-panel-access.txt` | **нет** |
| SSH private keys | `~/.ssh/id_vspomni` (локально) | **нет** |

### Права

```bash
chmod 600 /opt/outstaffingbot/.env
chown deploy:deploy /opt/outstaffingbot/.env
```

### Опционально: зашифрованный бэкап секретов

- **sops** + age key у owner
- **ansible-vault** для небольших команд
- Простой вариант: `gpg -c vspomni.env` → хранить offline

3x-ui и vspomni env — бэкап в `~/backups/` на сервере + копия offsite (encrypted).

---

## 7. Firewall (UFW)

На vspomni уже настроен UFW (`harden-vps-vpn.sh`). **Не запускать** `bootstrap-server.sh` на shared VPS — он делает `ufw allow` без учёта VPN.

### Добавление правил для OutstaffingBot

OutstaffingBot **не требует** новых публичных портов, если:
- API за nginx на `:443` (отдельный `server_name`)
- postgres/redis без host publish

Если нужен прямой доступ к staging API (не рекомендуется):

```bash
# Только с IP разработчиков
ufw allow from DEV_IP to any port 8000 proto tcp comment 'Outstaffing API dev'
```

### Блокировка

- postgres `:5432` — **не** открывать в UFW
- redis `:6379` — **не** открывать
- 3x-ui panel — **не** открывать (только localhost + tunnel)

---

## 8. fail2ban

Уже включён для SSH и nginx (vspomni). После добавления nginx server block OutstaffingBot — fail2ban продолжит работать на общих логах `/var/log/nginx/`.

Не снижать `bantime` / `maxretry` без причины.

---

## 9. Доступ двух разработчиков

| Практика | Детали |
|----------|--------|
| Отдельные SSH keys | `id_outstaffing` или общий `id_vspomni` — оба pubkey в `authorized_keys` |
| GitHub | Private repo, 1 approve на PR |
| Server `.env` | Owner редактирует; dev2 — read через SSH или 1Password |
| Root | Только owner (vspomni / 3x-ui) |
| Deploy OutstaffingBot | `deploy` user, скрипт scoped to `/opt/outstaffingbot` |
| Миграции БД | Только через PR + deploy, не вручную на shared DB без согласования |

---

## 10. F. Чеклист безопасности перед деплоем

- [ ] Выполнен аудит портов: `ss -tlnp`
- [ ] Бэкап vspomni `.env` и nginx config
- [ ] Бэкап 3x-ui (`~/backups/3x-ui/`)
- [ ] Создан пользователь `deploy`, ключи добавлены
- [ ] `/opt/outstaffingbot/.env` создан из `.env.server.example`, chmod 600
- [ ] Compose project name `outstaffingbot` — не пересекается с `3x-ui`
- [ ] postgres/redis **без** publish на `0.0.0.0`
- [ ] nginx: **новый** server block, `nginx -t` OK
- [ ] **Не** тронуты `/usr/local/x-ui`, `/opt/vspomni_bot`
- [ ] Отдельный Telegram staging-bot (не prod vspomni token)
- [ ] UFW: новые правила только если необходимо
- [ ] Rollback plan записан (см. ниже)

---

## 11. Безопасный деплой OutstaffingBot

Скрипт `scripts/deploy/deploy-staging.sh`:
- работает только в `$APP_DIR` (default `/opt/outstaffingbot`)
- не вызывает systemctl vspomni/x-ui
- idempotent: `git pull` + `docker compose up -d`

```bash
# От deploy
cd /opt/outstaffingbot
COMPOSE_PROJECT_NAME=outstaffingbot \
  ./scripts/deploy/deploy-staging.sh
```

---

## 12. Rollback

### OutstaffingBot сломался

```bash
cd /opt/outstaffingbot
git checkout HEAD~1   # или конкретный commit
docker compose -p outstaffingbot \
  -f docker-compose.yml -f docker-compose.staging.yml up -d --build
```

### Случайно затронули vspomni

```bash
systemctl restart vspomni vspomni-dashboard
# восстановить .env из ~/backups/pre-outstaffing-*/
# восстановить nginx из бэкапа nginx-full.conf
nginx -t && systemctl reload nginx
```

### Случайно затронули 3x-ui

```bash
systemctl restart x-ui
# восстановить из ~/backups/3x-ui/
# **не** переустанавливать x-ui без бэкапа DB
```

---

## 13. Совместимость с vspomni_bot

| Аспект | vspomni | OutstaffingBot | Конфликт? |
|--------|---------|----------------|-----------|
| Runtime | systemd + Python | Docker Compose | Нет |
| БД | SQLite / Google Sheets | PostgreSQL 16 (container) | Нет |
| Mini App | :8443 nginx | отдельный subdomain :443 | Нет (разные server_name) |
| Bot token | @Avto_ychot_MSBOT | отдельный staging bot | **Да, если один token** — использовать разные |
| :443 | nginx SNI multiplex | новый `server_name` на том же :443 | OK при отдельном server block |
| RAM/CPU | bot + dashboard + xray | + postgres + redis + api | Мониторить `free -h`, при 4GB — осторожно |

**Рекомендация:** мониторинг ресурсов после первого деплоя:

```bash
docker stats --no-stream
free -h
systemctl status vspomni vspomni-dashboard x-ui
```

---

## 14. Что не класть в git

- `.env`, `.env.local`, `.env.production`
- `server.env`, `*.pem`, `id_*` (private keys)
- дампы `x-ui.db`, `vspomni.env`
- `/root/x-ui-panel-access.txt`
- содержимое `~/backups/` с секретами

В git **можно:** `.env.example`, `.env.server.example`, `ssh-config.example`, документация без секретов.

---

*Последнее обновление: июнь 2026. При изменении портов vspomni — синхронизировать §5.*
