# Деплой OutstaffingBot — zero-downtime

> **Аудитория:** разработчики и AI-агенты (Cursor). **Обязательно** при любом деплое на VPS.  
> **Сервер:** `89.125.25.99`, каталог `/opt/outstaffingbot`  
> **Стек:** Docker Compose (postgres, redis, api, bot, worker) + nginx static mini-app

---

## Кратко для команды (RU)

**Проблема старого деплоя:** `docker compose up -d --build` и `deploy-staging.sh` пересоздавали **все** сервисы после долгой сборки образов (~3 мин). Бот и API были недоступны на всё время build + restart.

**Новый принцип:**

1. **Старые контейнеры работают до последней секунды** — сборка образов идёт параллельно с live-трафиком.
2. **Подмена по одному сервису** — `docker compose up -d --no-deps --force-recreate api` (~секунды простоя только на API).
3. **Postgres/Redis не трогаем** при обычном деплое (данные в volumes отдельно от кода).
4. **Mini App** — atomic swap каталога `dist` (~1–2 с), без рестарта контейнеров.
5. **Только .env изменился** — `deploy-env-only.sh` (recreate без rebuild).

**Запрещено:** `docker compose down`, `up -d --build` на весь stack, удаление live `dist` до готовности staging, `scp` прямо в live `dist`.

**Одна команда (деплой приложения из git):**

```bash
# С dev-машины (после commit + push):
./scripts/deploy/deploy-from-git.sh

# Уже на сервере:
cd /opt/outstaffingbot && ./scripts/deploy/deploy-zero-downtime.sh

# Только git pull (docs/rules/scripts, без recreate контейнеров):
./scripts/deploy/deploy-from-git.sh --git-only
```

**Скрипты:** см. таблицу ниже.

---

## Автоматический коммит → деплой (политика агентов)

После запрошенного изменения агент **сам** делает `commit → push → deploy из git`. Не ждать второго «закоммить/задеплой», кроме явного `только локально` / `без деплоя`.

| Уровень | Когда | Команда |
|---------|-------|---------|
| **Фиксация в git** | любое изменение | `commit` + `push` (**обязательно**) |
| **Sync сервера** | docs / `scripts/deploy` / файлы в `/opt/outstaffingbot` без runtime | `./scripts/deploy/deploy-from-git.sh --git-only` |
| **Деплой приложения** | api / bot / worker / mini-app | `./scripts/deploy/deploy-from-git.sh` или partial / mini-app |

Cursor rules (`.cursor/rules`): минимум — commit + push. Full docker rebuild для docs/rules-only **не нужен**.

Подробнее: [GIT_WORKFLOW.md](./GIT_WORKFLOW.md), `.cursor/rules/git-workflow.mdc`.

---

## Why old deploy caused downtime

| Old pattern | Problem |
|-------------|---------|
| `docker compose build` then `docker compose up -d` (all services) | After a long build, **all** containers recreate; bot stops for entire build window |
| `docker compose up -d --build --remove-orphans` (`pull-and-restart.sh`) | Rebuild + restart everything at once |
| Migrations **after** full `up -d` | Wrong order; api swap should follow migrations on running postgres |
| No `--no-deps` | Compose may restart dependency chain (postgres/redis) |

**Root cause:** treat deploy as «stop everything → build → start everything» instead of «build in parallel → swap one component».

---

## Architecture: component-level deploy

Python/FastAPI code runs **inside Docker images**. You cannot hot-swap a single `.py` file on a running container without rebuild. What **is** supported:

| Change | Deploy method | Downtime |
|--------|---------------|----------|
| Mini App UI (static) | `deploy-mini-app-only.sh` | ~1–2 s (nginx static swap) |
| API only | `deploy-api.sh` | ~seconds on API |
| Bot handlers only | `deploy-bot.sh` | ~seconds on bot (webhook reconnects) |
| Worker / ARQ | `deploy-worker.sh` | background jobs pause briefly |
| DB schema | migrations + `deploy-api.sh` or full zero-downtime | postgres stays up |
| `.env` only | `deploy-env-only.sh` | per-service recreate, no build |
| Full backend release | `deploy-zero-downtime.sh` | build: **zero**; swaps: seconds each |

---

## Deploy scripts

| Script | Where to run | Purpose |
|--------|--------------|---------|
| **`scripts/deploy/deploy-from-git.sh`** | **Dev machine или Server** | **Одна команда:** SSH (если нужно) → git sync → zero-downtime. `--git-only` — только pull |
| `scripts/deploy/deploy-zero-downtime.sh` | **Server** | Full backend: git pull → build → migrate → swap api → worker → bot |
| `scripts/deploy/deploy-staging.sh` | **Server** | Alias → `deploy-zero-downtime.sh` |
| `scripts/deploy/deploy-api.sh` | **Server** | API + migrations only |
| `scripts/deploy/deploy-bot.sh` | **Server** | Bot only |
| `scripts/deploy/deploy-worker.sh` | **Server** | Worker only |
| `scripts/deploy/deploy-env-only.sh` | **Server** | Reload `.env` without rebuild |
| `scripts/deploy/deploy-mini-app.sh` | **Dev machine** | Build + atomic dist swap on server |
| `scripts/deploy/deploy-mini-app-only.sh` | **Dev machine** | Alias → `deploy-mini-app.sh` |
| `deploy/linux/pull-and-restart.sh` | **Server** | Alias → `deploy-zero-downtime.sh` |

Shared library: `scripts/deploy/lib/common.sh` (health check, compose helpers).

### Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `APP_DIR` | `/opt/outstaffingbot` | Repo on server |
| `BRANCH` | `main` | Git branch to deploy |
| `COMPOSE_PROJECT_NAME` | `outstaffingbot` | Docker project name |
| `NO_CACHE` | `0` | Set `1` for `docker compose build --no-cache` |
| `SKIP_GIT` | `0` | Skip `git pull` on server. **FORBIDDEN for routine OutstaffingBot app deploys** — см. § «Деплой только из git». Допустимо только ops-сценарий: код уже на диске на известном коммите, повторный rebuild без pull |
| `SKIP_MIGRATIONS` | `0` | Set `1` to skip alembic |
| `HEALTH_URL` | `http://127.0.0.1:8000/health` | API health probe |

---

## Full deploy order (zero-downtime)

```
1. postgres + redis up (if down)     ← never restarted on routine deploy
2. git pull
3. docker compose build api bot worker   ← OLD containers still serve
4. alembic upgrade head (one-off run --rm --no-deps api)
5. swap api      → wait /health
6. swap worker
7. swap bot      → webhook re-register if WEBHOOK_URL set
8. (optional) mini-app atomic swap from dev machine — independent step
```

**On server:**

```bash
cd /opt/outstaffingbot
COMPOSE_PROJECT_NAME=outstaffingbot ./scripts/deploy/deploy-zero-downtime.sh
```

**Mini App (from dev machine, after merge to main):**

```bash
./scripts/deploy/deploy-mini-app-only.sh deploy@89.125.25.99
```

If WebView cache bust needed: edit `MINI_APP_URL` query in `.env`, then on server:

```bash
./scripts/deploy/deploy-env-only.sh bot
```

---

## Mini App: atomic static swap

Pattern (already in `deploy-mini-app.sh`):

1. Build locally (`npm ci && npm run build`)
2. `rsync` → `mini-app/dist.staging` (never touch live `dist`)
3. Verify staging (`verify-mini-app-static.sh` as www-data + HTTP 200)
4. `mv dist dist.old && mv dist.staging dist` (~1–2 s)
5. Verify live dist

**FORBIDDEN:**

- `rm -rf mini-app/dist` while users may load the app
- `scp` / `rsync` directly into live `dist` without staging
- Adding `?v=` to `/assets/*` in `index.html` (breaks lazy chunks)

---

## Деплой только из git (HARD)

Деплой приложения — **только** с committed (и обычно pushed) SHA. Агент перед деплоем **сам** коммитит и пушит (auto commit-deploy).

**Запрещено:**

- деплой с uncommitted локальными правками (в т.ч. mini-app — дерево должно совпадать с коммитом)
- `SKIP_GIT=1` для routine deploy app-кода
- правки исходников на сервере как source of truth
- деплой dirty tree «как main»

**Обязательно:** commit → push → `./scripts/deploy/deploy-from-git.sh` (или `--git-only` для docs/scripts).

См. также [GIT_WORKFLOW.md](./GIT_WORKFLOW.md) § «Автоматический коммит → деплой».

---

## Pre-deploy checklist

- [ ] PR merged to `main`; CI green
- [ ] **Все deployable-изменения закоммичены и запушены** (не деплоить uncommitted код)
- [ ] Shared VPS: read [SERVER_SECURITY.md §10](./SERVER_SECURITY.md) (do not touch vspomni / 3x-ui)
- [ ] New migration? Coordinate if destructive
- [ ] `./scripts/deploy/pre-deploy-audit.sh` on server (optional)
- [ ] Rollback commit hash noted
- [ ] **Не использовать `SKIP_GIT=1`** для routine deploy

---

## Health checks

Deploy scripts wait for API health:

```bash
curl -sf http://127.0.0.1:8000/health
```

On failure, script exits non-zero; old image may still run if swap failed mid-way — check `docker compose ps` and logs.

Bot (webhook mode): after bot swap, check logs for webhook registration.

---

## Rollback

### Backend (api / bot / worker)

```bash
cd /opt/outstaffingbot
git log -3 --oneline                    # pick good commit
git checkout <GOOD_COMMIT>
NO_CACHE=1 ./scripts/deploy/deploy-zero-downtime.sh
# or partial:
./scripts/deploy/deploy-api.sh
./scripts/deploy/deploy-bot.sh
```

### Mini App

```bash
# On server — restore previous dist from git (if tracked) or backup:
cd /opt/outstaffingbot
git checkout <GOOD_COMMIT> -- mini-app/dist
# or redeploy previous build from dev machine
```

### Database

Migrations are forward-only. Roll back **code** to match schema; do not `downgrade` on production without team agreement. Postgres data lives in Docker volume `outstaffingbot_postgres_data` — unaffected by code deploy.

### Emergency: never do this on shared VPS

```bash
# FORBIDDEN routine rollback:
docker compose down
docker compose up -d --build
```

---

## FORBIDDEN commands (routine deploy)

| Command | Why |
|---------|-----|
| `docker compose down` | Stops bot, api, postgres, redis — full outage |
| `docker compose up -d --build` (whole stack) | Rebuilds and restarts everything |
| `docker compose restart` (whole stack) | Unnecessary multi-service downtime |
| Stop bot before `docker compose build` completes | Bot offline for entire build |
| `rm -rf mini-app/dist` before staging ready | Broken static site |
| `scp` into live `dist` | Partial files served mid-upload |

---

## REQUIRED practices

| Practice | How |
|----------|-----|
| Build while old runs | `docker compose build <service>` before any `up` |
| Rolling swap | `docker compose up -d --no-deps --force-recreate <service>` |
| Migrations before api swap | `compose run --rm --no-deps api alembic upgrade head` |
| Health check after api swap | automatic in scripts |
| Atomic mini-app | staging → verify → `mv` swap |
| Document rollback commit | before deploy |

---

## Shared VPS notes

- Scope: **only** `/opt/outstaffingbot`
- Do **not** restart `vspomni`, `x-ui`, or foreign nginx configs
- See [SERVER_SECURITY.md](./SERVER_SECURITY.md), [SERVER_ACCESS.md](./SERVER_ACCESS.md)

---

## Verify deploy pattern (smoke test)

On server, while deploy runs in another session:

```bash
# Terminal 1 — watch bot container uptime
watch -n2 'docker compose -p outstaffingbot ps bot api'

# Terminal 2 — deploy
cd /opt/outstaffingbot && ./scripts/deploy/deploy-zero-downtime.sh
```

Bot container should show **continuous uptime through build phase**; recreate happens only at the final bot swap step.

Telegram: send `/start` before, during (build phase), and after deploy.

---

## Troubleshooting

### `bash\r: No such file or directory` on Linux

Scripts edited on Windows must use **LF** line endings. Repo enforces via `.gitattributes` (`*.sh text eol=lf`). After clone on Windows, re-save or run before scp:

```powershell
# PowerShell — fix before upload
(Get-Content scripts/deploy/deploy-zero-downtime.sh -Raw) -replace "`r`n","`n" | Set-Content -NoNewline scripts/deploy/deploy-zero-downtime.sh
```

---

## Related docs

| Document | Section |
|----------|---------|
| [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md) | § Deploy |
| [GIT_WORKFLOW.md](./GIT_WORKFLOW.md) | § После merge |
| [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md) | § Staging deploy |
| [SERVER_SECURITY.md](./SERVER_SECURITY.md) | §11–12 |
| `.cursor/rules/deploy-zero-downtime.mdc` | Agent rules (alwaysApply) |

---

*Created 2026-07-03. Replaces ad-hoc `docker compose up -d --build` as the default staging deploy.*
