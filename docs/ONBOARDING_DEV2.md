# Онбординг Developer 2 — OutstaffingBot

> **Для:** Dev2 — GitHub [`streetmonster-labZ`](https://github.com/streetmonster-labZ) · `streetmonster2078@gmail.com`  
> **Обновлено:** июнь 2026

---

## 1. Добро пожаловать

**OutstaffingBot** — Telegram-бот и Mini App для подбора временного персонала (аутстаффинг): работники регистрируют профиль, работодатели создают заявки, система матчит и уведомляет. Monorepo: Python (aiogram + FastAPI + PostgreSQL) + React Mini App, деплой на shared staging VPS.

**Полезные ссылки:**

| Ресурс | URL |
|--------|-----|
| GitHub | https://github.com/smokbasi/OutstaffingBot |
| Staging-бот | [@Outstaffing_Work_BOT](https://t.me/Outstaffing_Work_BOT) |
| Домен (prod/staging) | https://www.outstaffingbot.online |
| Mini App (когда настроен nginx) | https://www.outstaffingbot.online/app |
| Чеклист задач | [TASKS.md](./TASKS.md) |

---

## 2. Первый день — чеклист

- [ ] **Принять invite** на GitHub (collaborator / admin — Nikita отправит на `streetmonster-labZ`)
- [ ] **Клонировать репозиторий**
  ```powershell
  git clone https://github.com/smokbasi/OutstaffingBot.git
  cd OutstaffingBot
  ```
- [ ] **Установить софт**
  - Python **3.12**
  - Node.js **20+**
  - Git
  - [Cursor](https://cursor.com) или VS Code (рекомендуется Cursor — в проекте настроены ECC rules/skills)
- [ ] **Docker — опционально**  
  На Windows Docker Desktop / WSL может не работать — это нормально. БД и Redis уже крутятся на staging VPS; локально можно обойтись без Docker (см. §5).
- [ ] **Скопировать `.env`**
  ```powershell
  copy .env.example .env
  ```
  Заполнить секреты — **получить у Nikita** (минимум `BOT_TOKEN`, пароль Postgres для staging, при необходимости `DATABASE_URL` / `REDIS_URL` для туннеля). **Не коммитить `.env`.**
- [ ] **SSH-ключ → отправить pubkey Nikita**
  ```powershell
  # Создать ключ (если нет) — можно id_outstaffing или свой паттерн
  ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_outstaffing" -C "streetmonster2078@gmail.com"
  Get-Content "$env:USERPROFILE\.ssh\id_outstaffing.pub"
  ```
  Отправить содержимое `.pub` Nikita — он добавит в `/home/deploy/.ssh/authorized_keys` на сервере `89.125.25.99`.
- [ ] **Проверить SSH**
  ```powershell
  ssh -i "$env:USERPROFILE\.ssh\id_outstaffing" deploy@89.125.25.99
  ```
  После настройки `~/.ssh/config` (§4): `ssh outstaffing-staging`
- [ ] **Прочитать** [TASKS.md](./TASKS.md) — текущая фаза **Phase 1**
- [ ] **Написать Nikita:** договориться про PR review и кто деплоит на staging (§9)

---

## 3. GitHub и Git

| Параметр | Значение |
|----------|----------|
| Repo | https://github.com/smokbasi/OutstaffingBot |
| Базовая ветка | `main` |
| Твой GitHub | `streetmonster-labZ` |
| Права | **Admin** на repo (feature-ветки + PR; в `main` — только через merge) |

### Ежедневный цикл (кратко)

```
pull main → feature/fix branch → commit → push → PR → review → squash merge
```

Подробно: **[GIT_WORKFLOW.md](./GIT_WORKFLOW.md)**

### Ветки

| Префикс | Пример |
|---------|--------|
| `feature/` | `feature/worker-registration-fsm` |
| `fix/` | `fix/initdata-validation` |
| `docs/` | `docs/onboarding-update` |
| `chore/` | `chore/docker-compose-postgres` |

**Одна ветка = одна задача.** Перед push: `git fetch origin && git rebase origin/main`.

### Conventional commits — примеры

```
feat(bot): добавить FSM регистрации работника
fix(api): исправить валидацию initData Telegram
docs: обновить онбординг Dev2
chore(infra): добавить overlay для staging compose
test(api): покрыть GET /workers/me
```

Формат: `<type>(<scope>): описание на русском`. Scope: `bot`, `api`, `miniapp`, `worker`, `infra`, `db`.

### Что не коммитить

- `.env`, `.env.local`, токены, ключи
- `node_modules/`, `.venv/`, `__pycache__/`
- `%USERPROFILE%\.cursor\ecc\` (agent memory)

Squash merge в `main`: `gh pr merge <номер> --squash --delete-branch`

---

## 4. SSH-доступ к серверу

| Параметр | Значение |
|----------|----------|
| IP | `89.125.25.99` |
| Пользователь OutstaffingBot | **`deploy`** (не root) |
| Путь проекта | `/opt/outstaffingbot` |
| Ключ | Свой pubkey (например `id_outstaffing`); у Nikita паттерн `id_vspomni` |

### Добавление ключа

1. Сгенерировать пару (§2).
2. Отправить **публичный** ключ Nikita.
3. Nikita добавляет строку в `/home/deploy/.ssh/authorized_keys`.

### `~/.ssh/config` (рекомендуется)

Скопируй блоки из [`scripts/deploy/ssh-config.example`](../scripts/deploy/ssh-config.example) в `%USERPROFILE%\.ssh\config`:

```ssh-config
Host outstaffing-staging
  HostName 89.125.25.99
  User deploy
  IdentityFile ~/.ssh/id_outstaffing
  IdentitiesOnly yes
```

Подключение: `ssh outstaffing-staging`

Туннель к БД (если включены порты в staging overlay):

```ssh-config
Host outstaffing-db-tunnel
  HostName 89.125.25.99
  User deploy
  IdentityFile ~/.ssh/id_outstaffing
  LocalForward 5433 127.0.0.1:5433
  LocalForward 6380 127.0.0.1:6379
```

Подробнее: **[SERVER_ACCESS.md](./SERVER_ACCESS.md)**

### Что можно трогать

| Путь / действие | OK |
|-----------------|-----|
| `/opt/outstaffingbot` | git pull, docker compose, `.env` на сервере |
| `scripts/deploy/deploy-staging.sh` | деплой только этого проекта |
| Docker project `outstaffingbot` | postgres, redis, позже api/bot |

### Что НЕ трогать

| Зона | Почему |
|------|--------|
| `/opt/vspomni_bot`, `/opt/vspomni_bot_test` | соседний prod-бот |
| `/usr/local/x-ui`, `/etc/x-ui/` | VPN / 3X-UI (27+ клиентов) |
| nginx vspomni (`/etc/nginx/sites-enabled/vspomni*`, `3x-ui*`) | общий :443 SNI |
| `scripts/deploy/bootstrap-server.sh` **целиком** на shared VPS | сбросит UFW, конфликт с VPN |
| `systemctl restart x-ui`, `ufw reset` | риск для vspomni |

Полная карта безопасности: **[SERVER_SECURITY.md](./SERVER_SECURITY.md)**

---

## 5. Локальная разработка (без Docker на Windows)

Если Docker Desktop не работает — **нормальная ситуация**. Код пишется локально; инфраструктура на VPS.

### Python backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cd ..
```

Миграции (нужен доступ к Postgres — локальный Docker **или** SSH-туннель к staging):

```powershell
cd backend
alembic upgrade head
cd ..
python scripts\seed_categories.py
python scripts\seed_metro.py
```

### API локально

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка: http://localhost:8000/health → `{"status":"ok"}`

### Bot локально

```powershell
cd backend
python -m app.bot.main
```

**Важно — один `BOT_TOKEN` = один режим (polling или webhook).**

| Вариант | Когда |
|---------|-------|
| **Shared staging-бот** `@Outstaffing_Work_BOT` | Тест на сервере после deploy; **не** запускай локальный bot с тем же токеном |
| **Свой test-бот** | Создай через [@BotFather](https://t.me/BotFather), пропиши токен в локальный `.env` — безопасно для polling |
| **Dry-run** | Пустой `BOT_TOKEN` — бот не стартует, API/тесты работают |

Рекомендация для Phase 1: **локально — свой test-bot или только API**; интеграцию с `@Outstaffing_Work_BOT` проверяй на staging.

### Mini App

```powershell
cd mini-app
npm install
npm run dev
```

http://localhost:5173 — полный `initData` только через кнопку WebApp в Telegram.

### SSH-туннель к БД на сервере (опционально)

Окно 1 — туннель:

```powershell
ssh outstaffing-db-tunnel
# или вручную:
ssh -L 5433:127.0.0.1:5433 -L 6380:127.0.0.1:6379 deploy@89.125.25.99
```

Локальный `.env` (пароль — у Nikita, **не коммитить**):

```env
DATABASE_URL=postgresql+asyncpg://outstaffing:YOUR_PASSWORD@127.0.0.1:5433/outstaffing
REDIS_URL=redis://127.0.0.1:6380/0
```

> Postgres/Redis на staging по умолчанию **не** опубликованы на `0.0.0.0`. Порты `5433`/`6380` на хосте — только если включены в `docker-compose.staging.yml`. Не запускай destructive migrations на shared БД без согласования с Nikita.

Подробнее: **[SERVER_AND_TEAM.md § E](./SERVER_AND_TEAM.md#e-локальная-разработка-без-локального-docker)**

---

## 6. Деплой на staging

После **squash merge** в `main` — обновить код на VPS.

### С локальной машины (one-liner)

```bash
ssh outstaffing-staging 'cd /opt/outstaffingbot && COMPOSE_PROJECT_NAME=outstaffingbot ./scripts/deploy/deploy-staging.sh'
```

### На сервере (от `deploy`)

```bash
cd /opt/outstaffingbot
COMPOSE_PROJECT_NAME=outstaffingbot ./scripts/deploy/deploy-staging.sh
```

### Docker Compose вручную

```bash
cd /opt/outstaffingbot
export COMPOSE_PROJECT_NAME=outstaffingbot
docker compose -p outstaffingbot \
  -f docker-compose.yml -f docker-compose.staging.yml up -d --build
docker compose -p outstaffingbot ps
docker compose -p outstaffingbot logs -f postgres
```

Миграции после merge (когда api в compose — через контейнер; сейчас — с хоста или one-off):

```bash
cd /opt/outstaffingbot/backend
source .venv/bin/activate   # если venv на сервере
alembic upgrade head
```

### Кто деплоит

**Договоритесь с Nikita** (по очереди или один owner). Минимальный процесс:

```
PR merged → кто-то один делает deploy-staging.sh → тест /start в @Outstaffing_Work_BOT
```

---

## 7. Ключевые файлы и правила

| Файл | Зачем |
|------|-------|
| [PLAN.md](./PLAN.md) | Архитектура, стек, схема БД, roadmap |
| [TASKS.md](./TASKS.md) | **Чеклист задач** — смотри текущую Phase |
| [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md) | Как работать с AI/ECC, solo vs оркестрация |
| [GIT_WORKFLOW.md](./GIT_WORKFLOW.md) | Ветки, PR, два разработчика |
| [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md) | Staging VPS, секреты, workflow команды |
| [SERVER_ACCESS.md](./SERVER_ACCESS.md) | SSH, туннели |
| [SERVER_SECURITY.md](./SERVER_SECURITY.md) | Изоляция на shared VPS |
| [ECC_STRATEGY.md](./ECC_STRATEGY.md) | AI-агенты: skills, commands (кратко — §ниже) |
| `.cursor/rules/` | Правила для Cursor-агентов (always apply) |

### Karpathy guidelines (кратко)

Правила в `.cursor/rules/karpathy-guidelines.mdc`:

- **Думай до кода** — неясно → спроси, не угадывай.
- **Простота** — минимальный diff, без «на будущее».
- **Хирургические правки** — одна задача = один concern; не рефактори соседнее.
- **Verify first** — критерий готовности до merge: тест зелёный или ручная проверка из TASKS.

**Практика:** маленькие PR (1–3 дня), не over-engineer, не дублировать логику bot/API — единый service layer (PLAN §B.3).

### ECC / AI-агенты (кратко)

В проекте установлен ECC (`developer` + `security`). Полезные команды в Cursor:

- `/plan` — план фичи перед кодом
- `/code-review` — review diff
- `/tdd`, `/verify` — тесты и проверки

Orchestration module **не установлен** — multi-agent вручную (см. DEVELOPMENT_WORKFLOW §D). Агенты **не пушат в main** и **не коммитят** без явного запроса.

---

## 8. Текущий статус проекта

### Фазы

| Phase | Статус |
|-------|--------|
| **Phase 0** — Foundation | ✅ Scaffold готов (monorepo, Docker compose, models, migrations, seeds, API skeleton, bot `/start`) |
| **Phase 0.5** — Dev server & Git team | 🟡 Частично: repo на GitHub, VPS, postgres/redis, staging bot; **ожидается** invite Dev2, договорённость review/deploy |
| **Phase 1** — Worker Core | ⏭ **Следующая:** FSM регистрация работника + API профиля + Mini App + initData auth |

**Следующий шаг:** [TASKS.md § Phase 1](./TASKS.md#phase-1--worker-core-2-недели-p0)

### Что работает на сервере (`89.125.25.99`)

| Компонент | Статус |
|-----------|--------|
| `/opt/outstaffingbot` | git clone, `.env` на сервере |
| Docker `outstaffingbot` | `outstaffing-postgres`, `outstaffing-redis` |
| Bot `@Outstaffing_Work_BOT` | `/start` на staging (polling) |
| API в compose | ещё нет (Phase 1+) — `/health` на :8000 недоступен снаружи |
| Webhook + TLS | позже (домен есть, nginx для app/api — в процессе) |

### Известные issues / pending

- [ ] Dev2 collaborator на GitHub — Nikita добавляет `streetmonster-labZ`
- [ ] Договорённость: **1 approve** на PR, кто деплоит
- [ ] DNS / nginx для `app` и `api` на `www.outstaffingbot.online` — pending (webhook и Mini App через HTTPS)
- [ ] `bootstrap-server.sh` **не** запускался целиком (shared VPS) — настройка вручную, см. SERVER_ACCESS
- [ ] GitHub Actions CI — опционально, не блокер
- [ ] Один bot token: локальный polling + staging webhook **конфликтуют** — используй отдельный test-bot локально

---

## 9. Коммуникация

| Тема | Правило |
|------|---------|
| **PR review** | Минимум **1 approve** второго разработчика перед squash merge |
| **Push в `main`** | **Запрещён** — только PR + squash merge ([GIT_WORKFLOW §7](./GIT_WORKFLOW.md#7-работа-двух-разработчиков)) |
| **Force push** | В `main` и shared-ветки — **никогда** без явной договорённости |
| **Миграции Alembic** | Только через PR; не править чужие revision-файлы |
| **Shared staging DB** | Destructive migrations / ручные правки — согласовать с Nikita |
| **Деплой** | После merge; кто деплоит — договориться (§6) |
| **Секреты** | Только лично / secure channel; не в Git, не в PR comments |

Nikita (owner): первый deploy, секреты на сервере, добавление SSH-ключей.  
Dev2: feature-ветки, PR, review PR Nikita, тест на staging после deploy.

---

## 10. Быстрые команды (copy-paste)

### Git

```powershell
git checkout main
git pull origin main
git checkout -b feature/my-task
git fetch origin
git rebase origin main
git push -u origin feature/my-task
gh pr create --base main --title "feat(bot): описание" --body "## Summary`n- ...`n`n## Test plan`n- [ ] ..."
```

### Локально (Windows, без Docker)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
# другой терминал:
python -m app.bot.main
```

```powershell
cd mini-app
npm run dev
```

```powershell
cd backend
pytest
ruff check .
```

### SSH и деплой

```powershell
ssh outstaffing-staging
```

```bash
ssh outstaffing-staging 'cd /opt/outstaffingbot && COMPOSE_PROJECT_NAME=outstaffingbot ./scripts/deploy/deploy-staging.sh'
```

```bash
ssh outstaffing-staging 'cd /opt/outstaffingbot && docker compose -p outstaffingbot ps'
```

### SSH-туннель к БД

```powershell
ssh -L 5433:127.0.0.1:5433 -L 6380:127.0.0.1:6379 deploy@89.125.25.99
```

---

## Куда идти дальше

1. Закрой чеклист §2.
2. Открой [TASKS.md](./TASKS.md) → **Phase 1**.
3. Прочитай [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md) §E (Phase 1 = оркестрация 3 слоёв).
4. Возьми задачу: `feature/worker-registration-fsm` (или согласуй с Nikita).

Вопросы — Nikita или issue/PR с тегом в описании.

*При изменении infra или процесса — обновляй этот файл и [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md).*
