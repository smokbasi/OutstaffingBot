# OutstaffingBot Backend

Python 3.12 — aiogram 3 + FastAPI + SQLAlchemy 2 async.

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy ..\.env.example ..\.env
```

## Database

```powershell
# from repo root
docker compose up -d
cd backend
alembic upgrade head
python ..\scripts\seed_categories.py
python ..\scripts\seed_metro.py
```

## Run API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run Bot

Set `BOT_TOKEN` in `.env`, then:

```powershell
python -m app.bot.main
```

Without `BOT_TOKEN` the bot starts in dry-run mode (logs only, no polling).
