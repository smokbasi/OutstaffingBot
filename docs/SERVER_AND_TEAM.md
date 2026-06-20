# Dev-сервер и работа команды (2 разработчика)

> **Для кого:** Nikita + второй разработчик.  
> **Контекст:** Phase 0 scaffold готов; локальный Docker/WSL на Windows может не работать — **ранний деплой на dev/staging VPS** обходит эту проблему.  
> **Связанные документы:** [PLAN.md § 11](./PLAN.md#11-деплой-на-сервер), [GIT_WORKFLOW.md § 7](./GIT_WORKFLOW.md#7-параллельная-работа-два-разработчика--ai-агенты), [TASKS.md § Phase 0.5](./TASKS.md#phase-05--dev-server--git-team), [SERVER_ACCESS.md](./SERVER_ACCESS.md), [SERVER_SECURITY.md](./SERVER_SECURITY.md).

---

## A0. Общий VPS с существующими сервисами (vspomni + 3X-UI)

**Текущая ситуация:** staging/dev VPS уже обслуживает соседний проект **vspomni_bot** (`c:\Users\Nikita\Desktop\AI MS\vspomni_bot`) — Telegram-бот, Mini App dashboard, **3X-UI** (VPN). Конфиги и секреты vspomni **не в git**.

| Документ | Содержание |
|----------|------------|
| [SERVER_ACCESS.md](./SERVER_ACCESS.md) | SSH: `89.125.25.99`, ключ `~/.ssh/id_vspomni`, пользователи `root` / `deploy`, туннели |
| [SERVER_SECURITY.md](./SERVER_SECURITY.md) | Изоляция, порты, 3x-ui, firewall, чеклист перед деплоем, rollback |
| `scripts/deploy/ssh-config.example` | Шаблон `~/.ssh/config` (`outstaffing-staging`, `vspomni-prod`) |
| `.env.server.example` | Шаблон server-side `.env` (без секретов) |

**Критично перед первым деплоем OutstaffingBot на этот VPS:**

1. **Не** запускать `bootstrap-server.sh` целиком — он настраивает UFW и может конфликтовать с VPN-правилами vspomni.
2. Создать пользователя `deploy` и `/opt/outstaffingbot` вручную (см. SERVER_ACCESS.md).
3. Использовать **отдельный** Telegram staging-bot (не токен vspomni prod).
4. Docker Compose с project name `outstaffingbot` — postgres/redis без publish на `0.0.0.0`.
5. nginx: **новый** server block / поддомен — не перезаписывать конфиги vspomni.

**Занятые порты vspomni/3x-ui:** 443, 433, 2096, 8443–8449, 8765, 8088 (localhost), 25855 (localhost). OutstaffingBot API — `127.0.0.1:8000`. Подробная карта — [SERVER_SECURITY.md §5](./SERVER_SECURITY.md#5-карта-портов-и-конфликты).

---

## A. Рекомендация: да, деплоить рано — но на dev/staging, не в production

**Ответ на вопрос «может сразу поставить рабочую версию на сервер?» — да, и это разумно.**

| Почему ранний dev/staging VPS | Что это **не** значит |
|-------------------------------|------------------------|
| Обходит боль с Docker Desktop / WSL на Windows | Не production с реальными пользователями |
| Один PostgreSQL + Redis для обоих разработчиков | Не «забыть про локальную разработку» — код пишется локально |
| Общая среда для интеграционных проверок (бот + API + Mini App) | Не отказ от Git — наоборот, Git становится центром процесса |
| Webhook + HTTPS можно проверить до Phase 8 | Не нужен идеальный CI/CD с первого дня |

**Итог:** арендуйте **dev/staging VPS**, поднимите там `docker compose`, подключите **общий staging-бот** в Telegram. Локально каждый разработчик клонирует репозиторий, пишет код в Cursor, пушит в GitHub, мержит PR → деплой на staging → тест в Telegram.

---

## B. Уровни окружений

| Окружение | Назначение | Кто имеет доступ | Когда |
|-----------|------------|------------------|-------|
| **dev/staging VPS** | Общая интеграция: бот, API, БД, Mini App | Оба разработчика + тестовые Telegram-аккаунты | **Сейчас** (Phase 0.5) |
| **local** | Написание кода, unit-тесты, опционально API/bot без Docker | Каждый на своей машине | По желанию, без обязательного Docker |
| **production** | Реальные пользователи, SLA, бэкапы, мониторинг | Ограниченный доступ | Phase 8+ |

```mermaid
flowchart LR
    subgraph Devs["Разработчики"]
        A[Dev A — Cursor]
        B[Dev B — Cursor]
    end

    subgraph Git["GitHub (public)"]
        MAIN[main]
        FEAT[feature/*]
    end

    subgraph Staging["dev/staging VPS"]
        DC[Docker Compose]
        PG[(PostgreSQL)]
        RD[(Redis)]
        API[FastAPI]
        BOT[aiogram bot]
        NG[nginx]
    end

    TG[Telegram]

    A --> FEAT
    B --> FEAT
    FEAT -->|PR + merge| MAIN
    MAIN -->|deploy| DC
    DC --> PG
    DC --> RD
    DC --> API
    DC --> BOT
    DC --> NG
    TG <-->|webhook / Mini App| NG
```

---

## C. Требования к серверу

### Минимальные характеристики (из [PLAN.md § 11](./PLAN.md#11-деплой-на-сервер))

| Параметр | Значение |
|----------|----------|
| vCPU | **2** (минимум) |
| RAM | **4 GB** (минимум; при росте worker + nginx — 8 GB комфортнее) |
| Диск | 40 GB SSD |
| ОС | **Ubuntu 24.04 LTS** |
| Docker | Устанавливается **на сервере** (Linux), не на Windows разработчика |

### Домен / поддомен

| Компонент | Нужен домен? | Пример |
|-----------|--------------|--------|
| Telegram webhook | **Да** (HTTPS обязателен) | `https://staging.example.com/webhook/{secret}` |
| Mini App (WebApp) | **Да** | `https://staging.example.com/app` |
| API | **Да** (или тот же домен `/api`) | `https://staging.example.com/api/v1/...` |
| SSH / деплой | IP достаточно | `ssh deploy@89.125.25.99` — см. [SERVER_ACCESS.md](./SERVER_ACCESS.md) |

Для staging достаточно одного поддомена: `staging.yourdomain.ru` или бесплатного DNS + Let's Encrypt.

### Провайдеры (удобные для РФ)

| Провайдер | Плюсы |
|-----------|-------|
| **Hetzner** | Недорого, EU, стабильный Docker |
| **Timeweb Cloud** | RU, оплата картой РФ, поддержка на русском |
| **Selectel** | RU, предсказуемая инфраструктура |
| **VK Cloud / Yandex Cloud** | Если нужен российский cloud и compliance |

---

## D. Git для двух разработчиков

### Remote-репозиторий

1. Репозиторий на GitHub: **public** — https://github.com/smokbasi/OutstaffingBot (исходный код открыт; секреты только в `.env` на сервере/локально).
2. Второй разработчик — **collaborator** с правом `write` (feature-ветки + PR, не прямой push в `main`):

```powershell
gh repo collaborator add USERNAME --repo smokbasi/OutstaffingBot --permission write
```
3. Базовая ветка: **`main`** (стабильная, деплоится на staging после merge).

### Стратегия веток (расширение [GIT_WORKFLOW.md](./GIT_WORKFLOW.md))

| Ветка | Назначение | Кто мержит |
|-------|------------|------------|
| `main` | Стабильный код, источник деплоя на staging | Squash merge после review |
| `feature/*`, `fix/*` | Задачи разработчиков | Автор PR после approve |
| `develop` (опционально) | Если нужен auto-deploy без каждого merge в main | Договориться в команде |

**Рекомендация для двух человек:** достаточно **`main` + feature-ветки**. Ветку `develop` добавляйте только если настроите auto-deploy именно с неё.

### Code review между двумя разработчиками

| Роль | Ответственность |
|------|-----------------|
| **Owner репозитория** (Nikita) | Создание repo, секреты на сервере, первый deploy, добавление dev2 |
| **Оба разработчика** | Review PR друг друга; минимум **1 approve** перед squash merge |
| **AI-агент (Cursor)** | Не пушит в `main`; только PR по запросу |

### Секреты и `.env`

| Правило | Детали |
|---------|--------|
| `.env` **никогда** не в Git | Только `.env.example` с пустыми/placeholder значениями |
| На сервере | Один `.env` в `/opt/outstaffingbot/.env` (права `600`, владелец deploy-user) |
| Локально у каждого dev | Свой `.env` — может указывать на **remote staging DB** или локальные сервисы |
| Утечка токена | Ротация через [@BotFather](https://t.me/BotFather), обновление server `.env` |

### Telegram-боты: один shared или отдельные test-боты?

| Подход | Когда использовать |
|--------|-------------------|
| **Один staging-бот** (рекомендуется для Phase 0–7) | Общая БД, проще воспроизвести баги, один webhook URL |
| **Отдельный test-бот на dev** | Если dev2 часто ломает webhook/polling и мешает другому |
| **Личный bot token только локально** | Dry-run / unit-тесты без Telegram API |

**Практика:** на staging VPS — **один** `@YourBot_staging` с webhook. Локально — опционально свой `@YourBot_dev` с polling (если Docker есть) или подключение к staging API/DB.

---

## E. Локальная разработка без локального Docker

Если Docker Desktop / WSL не работает на Windows — **это нормально**. Код всё равно пишется локально; инфраструктура живёт на VPS.

### Вариант 1: Локальный backend → удалённая БД на staging

```powershell
# .env локально (пример — порт проброшен через SSH tunnel)
DATABASE_URL=postgresql+asyncpg://outstaffing:SECRET@127.0.0.1:5433/outstaffing
REDIS_URL=redis://127.0.0.1:6380/0
```

SSH-туннель:

```bash
ssh -L 5433:localhost:5432 -L 6380:localhost:6379 deploy@STAGING_IP
```

| Плюсы | Минусы |
|-------|--------|
| Реальные данные staging | Риск испортить общую БД — **не запускайте destructive migrations** без согласования |
| Не нужен локальный Docker | Нужен постоянный SSH-туннель |
| Быстрая отладка API/bot | Latency выше, чем localhost |

### Вариант 2: Гибрид — bot + API локально, БД/Redis на сервере (рекомендуется)

1. На VPS крутятся **postgres + redis** (и позже полный stack).
2. Локально: Python venv, `uvicorn`, `python -m app.bot.main` (polling).
3. В `.env`: `DATABASE_URL` / `REDIS_URL` через SSH-туннель **или** (менее безопасно) открытые порты только для IP dev-машин.

**Рекомендуется для Phase 1–4**, пока не починен WSL.

### Вариант 3: Полный локальный Docker

Когда Docker Desktop / WSL заработает:

```powershell
docker compose up -d
cd backend && alembic upgrade head
```

См. [README.md](../README.md).

### Вариант 4: Cursor → push → auto-deploy на staging

Минимальный цикл без локального запуска бота:

1. Пишете код в Cursor.
2. `pytest` локально (без БД — моки; или CI на GitHub).
3. PR → merge → `git pull` на сервере → `docker compose up -d --build` → тест в Telegram.

Подходит для UI (Mini App) и API, когда бот уже стабилен на сервере.

---

## F. Архитектура деплоя на VPS

```
VPS (Ubuntu 24.04)
├── /opt/outstaffingbot/          # git clone
│   ├── .env                      # секреты (не в git)
│   ├── docker-compose.yml        # postgres, redis
│   ├── docker-compose.staging.yml # overlay для сервера
│   └── ...
├── Docker Compose
│   ├── postgres:16
│   ├── redis:7
│   ├── api        (FastAPI + uvicorn)     — Phase 1+
│   ├── bot        (aiogram webhook)       — Phase 0+
│   ├── worker     (ARQ)                   — Phase 5+
│   └── nginx      (TLS, /api, /app, /webhook) — Phase 0.5+
└── Certbot (Let's Encrypt)
```

### Webhook vs Polling на staging

| Режим | Где | Когда |
|-------|-----|-------|
| **Polling** | Локально или временно на VPS без домена | Первые тесты Phase 0 |
| **Webhook** | Staging/production с HTTPS | Как только есть домен + nginx |

---

## G. Первый деплoy: пошаговый чеклист (Ubuntu server)

Выполняет **один человек** (owner). Dev2 подключается после базовой настройки.

### 1. Подготовка VPS

```bash
# На свежем Ubuntu 24.04 (от root или sudo-пользователя)
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ca-certificates

# Docker (official convenience script — или см. scripts/deploy/bootstrap-server.sh)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Перелогиниться для группы docker
```

### 2. Deploy-пользователь и SSH-ключи

```bash
sudo adduser deploy
sudo usermod -aG docker deploy
sudo mkdir -p /home/deploy/.ssh
# Добавить публичные ключи ОБОИХ разработчиков в:
# /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

### 3. Клонирование репозитория

```bash
sudo mkdir -p /opt/outstaffingbot
sudo chown deploy:deploy /opt/outstaffingbot
sudo -u deploy git clone https://github.com/YOUR_ORG/OutstaffingBot.git /opt/outstaffingbot
cd /opt/outstaffingbot
```

### 4. Конфигурация `.env` на сервере

```bash
sudo -u deploy cp .env.example .env
sudo -u deploy nano .env   # BOT_TOKEN, DATABASE_URL, WEBHOOK_*, MINI_APP_URL, API_BASE_URL
chmod 600 .env
```

Пример для staging с docker-compose (postgres/redis внутри compose):

```env
BOT_TOKEN=123456:ABC...
APP_ENV=staging
DATABASE_URL=postgresql+asyncpg://outstaffing:STRONG_PASSWORD@postgres:5432/outstaffing
REDIS_URL=redis://redis:6379/0
WEBHOOK_SECRET=random-long-string
WEBHOOK_URL=https://staging.example.com/webhook/random-long-string
MINI_APP_URL=https://staging.example.com/app
API_BASE_URL=https://staging.example.com/api
ADMIN_TELEGRAM_IDS=123456789,987654321
```

### 5. Запуск инфраструктуры

```bash
cd /opt/outstaffingbot
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
docker compose ps
```

### 6. Миграции и seed (Phase 0)

```bash
# Временно: зайти в контейнер или запустить с хоста (Python на сервере)
# Когда появится сервис api — миграции через него или one-off container:
docker compose run --rm --no-deps \
  -e DATABASE_URL=postgresql+asyncpg://outstaffing:PASS@postgres:5432/outstaffing \
  api alembic upgrade head

# Или с хоста (если установлен Python backend):
cd /opt/outstaffingbot/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
alembic upgrade head
cd .. && python scripts/seed_categories.py && python scripts/seed_metro.py
```

> **Примечание Phase 0:** сейчас в compose только postgres + redis. Bot/API запускайте вручную на сервере или добавьте сервисы по мере Phase 1. Скрипт `scripts/deploy/bootstrap-server.sh` автоматизирует шаги 1–5.

### 7. Проверка

```bash
curl http://localhost:8000/health          # когда API запущен
docker compose logs -f postgres
# Telegram: /start на staging-боте
```

### 8. TLS + webhook (когда есть домен)

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
# nginx config — см. PLAN.md, Phase 8
sudo certbot --nginx -d staging.example.com
# Переключить бота на webhook (WEBHOOK_URL в .env)
```

---

## H. Доступ для двух разработчиков

| Ресурс | Dev A (owner) | Dev B |
|--------|---------------|-------|
| GitHub repo | Admin | Write (collaborator) |
| SSH на VPS | Да (свой ключ) | Да (свой ключ) |
| Server `.env` | Редактирует | Read через `ssh deploy@...` или shared 1Password/Vault |
| Staging PostgreSQL | Shared | Shared — **миграции только через PR + deploy** |
| Telegram staging bot | Admin в BotFather | Tester |

### Миграции Alembic в команде из двух человек

1. Миграция создаётся в **feature-ветке** и мержится через PR.
2. После merge в `main` — на сервере: `git pull && alembic upgrade head`.
3. **Не** править чужие revision-файлы — только новая миграция ([GIT_WORKFLOW.md § 9](./GIT_WORKFLOW.md#9-разрешение-конфликтов)).

---

## I. CI/CD минимальный (Phase 0–1)

### GitHub Actions (`.github/workflows/ci.yml`)

На каждый **push** и **pull request** в `main`:

- `pytest` в `backend/tests`
- (опционально) `ruff` / lint

БД в CI — ephemeral postgres service (не staging VPS).

### Деплой на staging

| Phase | Способ |
|-------|--------|
| **0.5 (сейчас)** | **Ручной:** SSH → `cd /opt/outstaffingbot && git pull && docker compose ... up -d` |
| **1+** | Скрипт `scripts/deploy/deploy-staging.sh` на сервере |
| **8** | GitHub Actions deploy + secrets, blue/green, мониторинг |

Пример ручного деплоя:

```bash
ssh deploy@STAGING_IP 'cd /opt/outstaffingbot && git pull origin main && docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build'
```

---

## J. Workflow: от кода до Telegram

```mermaid
sequenceDiagram
    participant A as Dev A/B
    participant GH as GitHub
    participant VPS as Staging VPS
    participant TG as Telegram

    A->>A: git checkout -b feature/...
    A->>A: код + pytest локально
    A->>GH: git push + PR
    GH->>GH: CI pytest
    A->>GH: review + squash merge → main
    A->>VPS: ssh deploy (git pull + compose)
    VPS->>VPS: alembic upgrade head
    VPS->>TG: bot webhook / polling
    A->>TG: тест /start, Mini App
```

**Кратко:**

```
clone → branch → code (Cursor) → push → PR → review → merge main → deploy staging → test Telegram
```

---

## K. Что сделать прямо сейчас (action list)

| # | Действие | Кто | Статус |
|---|----------|-----|--------|
| 1 | Public GitHub repo `OutstaffingBot` + push `main` | Nikita | ☑ |
| 2 | `git remote add origin` + первый push `main` | Nikita | ☐ |
| 3 | Добавить **dev2** как collaborator | Nikita | ☐ |
| 4 | Арендовать **VPS** или использовать **shared VPS** с vspomni (`89.125.25.99`) — см. [SERVER_SECURITY.md](./SERVER_SECURITY.md) | Nikita | ☐ |
| 5 | Настроить `/opt/outstaffingbot` + `deploy` user (**не** full bootstrap на shared VPS) | Nikita | ☐ |
| 6 | Создать **staging-бота** в @BotFather, прописать `BOT_TOKEN` в server `.env` | Nikita | ☐ |
| 7 | (Опционально) Поддомен + Let's Encrypt для webhook | Nikita | ☐ |
| 8 | Dev2: `git clone`, `.env` локально, SSH-ключ на VPS — [SERVER_ACCESS.md](./SERVER_ACCESS.md) | Dev2 | ☐ |
| 9 | Договориться: **1 approve** на PR, кто деплоит (можно по очереди) | Оба | ☐ |
| 10 | Отметить чеклист [TASKS.md § Phase 0.5](./TASKS.md#phase-05--dev-server--git-team) | Оба | ☐ |

---

## L. FAQ

**Можно ли не ставить Docker на Windows вообще?**  
Да. Пишите код локально, инфраструктура на VPS, деплой через Git.

**Нужен ли production сейчас?**  
Нет. Staging достаточно до Phase 8.

**Кто владеет `main`?**  
Технически owner репозитория; мерж только через PR с review.

**Что если dev2 случайно удалит данные staging?**  
Shared staging = shared риск. Бэкапы `pg_dump` cron — добавить в Phase 0.5 после первого рабочего деплоя.

**Polling локально + webhook на staging — конфликт?**  
Да, один bot token — один active mode. Локально используйте **отдельный test-bot** или не запускайте локальный bot, тестируйте на staging.

---

*Последнее обновление: июнь 2026. При изменении infra — синхронизировать с PLAN.md § 11 и TASKS.md Phase 0.5.*
