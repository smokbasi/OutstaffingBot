# OutstaffingBot

> **Онбординг Dev2:** [docs/ONBOARDING_DEV2.md](docs/ONBOARDING_DEV2.md)

Telegram-бот + Mini App для подбора временного персонала (аутстаффинг).

## Быстрый старт (локально)

### 1. Окружение

```powershell
cd "c:\Users\Nikita\Desktop\AI MS\OutstaffingBot"
copy .env.example .env
# Отредактируйте .env — минимум BOT_TOKEN для живого бота
```

### 2. Инфраструктура (PostgreSQL 16 + Redis 7)

```powershell
docker compose up -d
```

### 3. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
cd ..
python scripts\seed_categories.py
python scripts\seed_metro.py
```

### 4. API

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка: http://localhost:8000/health → `{"status":"ok"}`

### 5. Bot

```powershell
cd backend
python -m app.bot.main
```

Без `BOT_TOKEN` — dry-run (логирует предупреждение, polling не стартует).

### 6. Mini App

```powershell
cd mini-app
npm install
npm run dev
```

Откройте http://localhost:5173 (полный initData — через WebApp-кнопку бота).

## Структура

```
OutstaffingBot/
├── docker-compose.yml
├── .env.example
├── backend/          # FastAPI + aiogram + SQLAlchemy
├── mini-app/         # React + Vite + TypeScript
├── scripts/          # seed_categories.py, seed_metro.py
└── docs/             # PLAN, TASKS, workflow
```

## Deployment (dev/staging VPS)

Если локальный Docker/WSL недоступен или работаете вдвоём — **ранний деплой на staging VPS** рекомендуется уже с Phase 0.5.

```bash
# На Ubuntu 24.04 VPS (после git clone)
sudo ./scripts/deploy/bootstrap-server.sh   # GIT_REPO=... при первом запуске
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

Полный чеклист, Git для двух разработчиков, CI/CD: **[docs/SERVER_AND_TEAM.md](docs/SERVER_AND_TEAM.md)**.

## Документация

- [ONBOARDING_DEV2.md](docs/ONBOARDING_DEV2.md) — онбординг второго разработчика
- [TASKS.md](docs/TASKS.md) — чеклист фаз (в т.ч. Phase 0.5 — dev server)
- [SERVER_AND_TEAM.md](docs/SERVER_AND_TEAM.md) — staging VPS, команда, деплой
- [PLAN.md](docs/PLAN.md) — архитектура и схема БД
- [DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) — процесс разработки
- [GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) — ветки, PR, два разработчика
