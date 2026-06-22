# OutstaffingBot — systemd auto-restart (Linux VPS)

Аналог `vspomni` / `vspomni-dashboard` на shared VPS (`89.125.25.99`).

## Механизм

| Компонент | vspomni | OutstaffingBot |
|-----------|---------|----------------|
| Bot | `systemd` → `python main.py`, `Restart=always` | Docker `restart: always` + `outstaffingbot-bot.service` |
| Dashboard | `systemd` → `python dashboard_main.py`, `Restart=always` | nginx static (`mini-app/dist`) + `outstaffingbot-dashboard.service` (проверка dist + `nginx -t`) |
| API | — | Docker `restart: always` + `outstaffingbot-api.service` |
| Infra | — | postgres/redis, Docker `restart: always` + `outstaffingbot-infra.service` |

Политики перезапуска (как vspomni): **`Restart=always`**, **`RestartSec=10`**, **`TimeoutStopSec=30`** (bot/api).

## Установка (один раз, root)

```bash
cd /opt/outstaffingbot
git pull
sudo APP_DIR=/opt/outstaffingbot DEPLOY_USER=deploy ./deploy/linux/install-systemd.sh
```

Требования: Docker, пользователь `deploy` в группе `docker`, `.env`, собранный `mini-app/dist`, nginx site `outstaffingbot.conf`.

## Деплой обновлений

```bash
cd /opt/outstaffingbot
./deploy/linux/pull-and-restart.sh
```

Или существующий скрипт: `scripts/deploy/deploy-staging.sh`.

## Проверка

```bash
systemctl status outstaffingbot-bot outstaffingbot-api outstaffingbot-dashboard
docker compose -p outstaffingbot -f docker-compose.yml -f docker-compose.staging.yml ps
curl -sS -o /dev/null -w '%{http_code}\n' https://www.outstaffingbot.online/
```

## Отдельный рестарт (как vspomni)

```bash
sudo systemctl restart outstaffingbot-bot      # только бот
sudo systemctl restart outstaffingbot-api       # только API
sudo systemctl restart outstaffingbot-dashboard # проверка dist + nginx -t
```

Dashboard не падает как процесс — отдаётся nginx. При падении nginx его поднимет `nginx.service` (стандарт Ubuntu).
