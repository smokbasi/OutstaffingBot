# План реализации OutstaffingBot: Telegram-бот + Mini App

📋 **Задачи (чеклист Phase 0–10):** [docs/TASKS.md](./TASKS.md)

**Процесс разработки:** [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md) — Karpathy + ECC: когда оркестрация, ежедневный цикл, anti-patterns.

## Текущее состояние проекта

| Параметр | Статус |
|----------|--------|
| Директория `c:\Users\Nikita\Desktop\AI MS\OutstaffingBot` | **Phase 0 scaffold** — backend, mini-app, docker-compose, migrations, seeds |
| Git | Инициализирован (`git init`); первый коммит — по запросу |
| ECC (developer + security) | **Установлен** (2026-06-19) — см. [ECC_STRATEGY.md § 10](./ECC_STRATEGY.md#10-installed-on-2026-06-19) |
| ECC orchestration module | **Не установлен** (конфликт manifest с security) — ручная multi-agent оркестрация; опционально позже |
| Ruflo | **Удалён** из проекта (заменён ECC) |

**Действие перед разработкой:** [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md) → [ECC_STRATEGY.md](./ECC_STRATEGY.md) → Phase 0: `git init` → scaffold monorepo.

---

## A. Рекомендуемый технологический стек

### Backend: **Python 3.12 + aiogram 3.x + FastAPI**

| Критерий | Python (aiogram) | Node (grammY) | Выбор |
|----------|------------------|---------------|-------|
| FSM для многошаговых диалогов | aiogram FSM — зрелый, встроенный | grammY conversations — хорош | **Python** |
| REST API для Mini App | FastAPI — async, OpenAPI, валидация Pydantic | NestJS/Fastify — тоже хорош | **FastAPI** (единый язык с ботом) |
| Фоновые задачи (matching, push) | Celery / ARQ + Redis | BullMQ | **ARQ** (легче Celery для async Python) |
| ORM / миграции | SQLAlchemy 2.0 + Alembic | Prisma | **SQLAlchemy** |
| Деплой на Linux VPS | systemd + Docker — стандарт | Аналогично | Оба OK |

**Обоснование:** один язык для бота, API, matching-логики и фоновых задач; aiogram 3 нативно async; FastAPI даёт автодокументацию для Mini App; экосистема PostgreSQL/asyncpg зрелая.

### Полный стек

```
┌─────────────────────────────────────────────────────────┐
│  Telegram Bot API  │  Telegram Web App (Mini App)      │
├────────────────────┴──────────────────────────────────┤
│  aiogram 3 (polling/webhook)  │  React 18 + Vite + TS   │
├───────────────────────────────┴─────────────────────────┤
│              FastAPI (REST + Webhook endpoint)           │
├─────────────────────────────────────────────────────────┤
│     Shared Domain Layer (services, matching, auth)       │
├──────────────┬──────────────────┬───────────────────────┤
│ PostgreSQL   │ Redis            │ ARQ worker            │
│ (данные)     │ (кэш, очереди)   │ (notifications, match)│
└──────────────┴──────────────────┴───────────────────────┘
         nginx (reverse proxy, TLS, static Mini App)
         Docker Compose / systemd на VPS
```

| Компонент | Технология |
|-----------|------------|
| БД | **PostgreSQL 16** |
| Кэш / очереди | **Redis 7** |
| Mini App | **React 18 + Vite + TypeScript + TanStack Query** |
| UI Mini App | Telegram UI Kit (`@telegram-apps/sdk-react`) |
| Auth Mini App | Валидация `initData` (HMAC-SHA256) |
| Деплой | Docker Compose, nginx, Certbot (Let's Encrypt) |
| CI | GitHub Actions (lint, test, build, deploy) |
| Мониторинг | structlog + Sentry (опционально) |

---

## B. Архитектура

### B.1. Диаграмма высокого уровня

```mermaid
flowchart TB
    subgraph Clients["Клиенты"]
        TG[Telegram Bot Chat]
        MA[Mini App WebView]
        GRP[Telegram Job Groups]
    end

    subgraph Server["VPS / Docker"]
        NGINX[nginx :443]
        BOT[aiogram Bot]
        API[FastAPI REST]
        WORKER[ARQ Worker]
        DOMAIN[Domain Services]
    end

    subgraph Data["Данные"]
        PG[(PostgreSQL)]
        RD[(Redis)]
    end

    TG -->|updates| BOT
    MA -->|HTTPS + initData| NGINX --> API
    BOT --> DOMAIN
    API --> DOMAIN
    WORKER --> DOMAIN
    DOMAIN --> PG
    DOMAIN --> RD
    WORKER -->|post message| GRP
    BOT -->|notify user| TG
    WORKER -->|push vacancy| TG
```

### B.2. Структура модулей (monorepo)

```
OutstaffingBot/
├── .cursor/                    # ECC: rules, agents, skills (после install --target cursor)
├── docs/
│   ├── PLAN.md
│   ├── DEVELOPMENT_WORKFLOW.md
│   └── ECC_STRATEGY.md
├── docker-compose.yml
├── nginx/
│   └── outstaffing.conf
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   ├── app/
│   │   ├── main.py             # FastAPI entry
│   │   ├── bot/
│   │   │   ├── main.py         # aiogram dispatcher
│   │   │   ├── handlers/
│   │   │   │   ├── start.py
│   │   │   │   ├── worker/
│   │   │   │   └── employer/
│   │   │   ├── keyboards/
│   │   │   ├── middlewares/
│   │   │   └── states/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   ├── deps.py         # initData auth
│   │   │   └── schemas/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── models/
│   │   │   └── session.py
│   │   ├── services/
│   │   │   ├── user_service.py
│   │   │   ├── worker_service.py
│   │   │   ├── job_service.py
│   │   │   ├── matching_service.py
│   │   │   ├── application_service.py
│   │   │   ├── notification_service.py
│   │   │   └── group_posting_service.py
│   │   └── workers/
│   │       ├── tasks.py
│   │       └── scheduler.py
│   └── tests/
├── mini-app/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/
│   │   ├── pages/
│   │   │   ├── worker/
│   │   │   └── employer/
│   │   └── hooks/
│   └── vite.config.ts
└── scripts/
    ├── seed_metro.py
    └── seed_categories.py
```

### B.3. Принцип: единый Domain Layer

**Бот и Mini App не дублируют бизнес-логику.** Оба вызывают одни и те же `services/*`:

```
Bot Handler  ──┐
               ├──► JobService.create_request() ──► PostgreSQL
API Route    ──┘
```

### B.4. Синхронизация Bot ↔ Mini App

| Механизм | Описание |
|----------|----------|
| Единая БД | Все настройки, резюме, заявки — в PostgreSQL |
| Идентификация | `telegram_id` — первичный ключ пользователя |
| Mini App auth | `Telegram.WebApp.initData` → HMAC-проверка на backend |
| Real-time sync | Не нужен WebSocket: Mini App refetch при focus; бот — push через Telegram |
| Конфликты | Optimistic locking через `updated_at` + version column |

### B.5. Схема базы данных

```mermaid
erDiagram
    users ||--o| workers : has
    users ||--o| employers : has
    users ||--o| worker_preferences : has
    workers ||--o{ worker_experiences : has
    workers }o--|| metro_stations : prefers
    job_categories ||--o{ job_requests : categorizes
    employers ||--o{ job_requests : creates
    job_requests }o--|| metro_stations : located_at
    job_requests ||--o{ shift_slots : contains
    job_requests ||--o{ applications : receives
    workers ||--o{ applications : submits
    shift_slots ||--o{ applications : for
    users ||--o{ notifications : receives
    job_requests ||--o{ group_posts : posted_as
    telegram_groups ||--o{ group_posts : target
```

#### Таблицы и поля

**`users`**

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| telegram_id | BIGINT UNIQUE | ID в Telegram |
| username | VARCHAR | @username |
| role | ENUM | `worker`, `employer`, `both`, `admin` |
| language_code | VARCHAR(5) | ru, en |
| is_blocked | BOOLEAN | |
| created_at, updated_at | TIMESTAMPTZ | |

**`workers`**

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| first_name | VARCHAR(100) | **обяз.** |
| last_name | VARCHAR(100) | **обяз.** |
| age | SMALLINT | **обяз.** 16–70 |
| gender | ENUM | `male`, `female`, `other`, `prefer_not_say` |
| metro_station_id | INT FK | **обяз.** предпочитаемая станция |
| metro_radius_km | SMALLINT | радиус поиска (0 = только эта станция, 1–5 км) |
| min_hourly_rate | DECIMAL(10,2) | мин. ставка ₽/час |
| resume_completed | BOOLEAN | профиль заполнен |
| notifications_enabled | BOOLEAN | глобальный вкл/выкл push |
| created_at, updated_at | TIMESTAMPTZ | |

**`worker_experiences`**

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| worker_id | UUID FK | |
| category_id | INT FK → job_categories | **категория** (упрощённый matching) |
| role_title | VARCHAR(200) | свободный текст: «официант», «грузчик» |
| duration_months | SMALLINT | стаж в месяцах |
| description | TEXT | опционально: где работал |
| created_at | TIMESTAMPTZ | |

**`employers`**

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| user_id | UUID FK | |
| company_name | VARCHAR(200) | **обяз.** |
| contact_phone | VARCHAR(20) | опционально |
| contact_person | VARCHAR(200) | опционально |
| verified | BOOLEAN | модерация |
| created_at, updated_at | TIMESTAMPTZ | |

**`job_categories`** (справочник)

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| slug | VARCHAR(50) UNIQUE | `waiter`, `loader`, `cashier`… |
| name_ru | VARCHAR(100) | «Официант» |
| parent_id | INT FK | иерархия (опционально) |
| is_active | BOOLEAN | |

**`metro_stations`** (справочник Москвы/региона)

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| name | VARCHAR(100) | «Сокольники» |
| line_name | VARCHAR(100) | «Сокольническая» |
| lat, lon | DECIMAL | для расчёта расстояния |
| is_active | BOOLEAN | |

**`job_requests`**

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| employer_id | UUID FK | |
| category_id | INT FK | **обяз.** |
| title | VARCHAR(200) | **обяз.** краткое название |
| description | TEXT | **обяз.** описание работы |
| metro_station_id | INT FK | **обяз.** |
| address | VARCHAR(300) | опционально точный адрес |
| hourly_rate | DECIMAL(10,2) | **обяз.** ₽/час |
| workers_needed | SMALLINT | **обяз.** кол-во людей |
| min_experience_months | SMALLINT | опционально мин. стаж |
| required_gender | ENUM | опционально `any`, `male`, `female` |
| min_age, max_age | SMALLINT | опционально |
| dress_code | VARCHAR(200) | опционально |
| contact_info | TEXT | опционально доп. контакт |
| status | ENUM | `draft`, `active`, `filled`, `cancelled`, `expired` |
| post_to_groups | BOOLEAN | публиковать в группы |
| notify_matching_workers | BOOLEAN | push matching workers |
| created_at, updated_at, expires_at | TIMESTAMPTZ | |

**`shift_slots`** (конкретные смены — основа conflict check)

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| job_request_id | UUID FK | |
| shift_date | DATE | **обяз.** |
| start_time | TIME | **обяз.** |
| end_time | TIME | **обяз.** |
| slots_total | SMALLINT | сколько мест на эту смену |
| slots_filled | SMALLINT | занято |
| created_at | TIMESTAMPTZ | |

**`applications`**

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| worker_id | UUID FK | |
| job_request_id | UUID FK | |
| shift_slot_id | UUID FK | **обяз.** конкретная смена |
| status | ENUM | `pending`, `accepted`, `rejected`, `cancelled_by_worker`, `cancelled_by_employer` |
| applied_at | TIMESTAMPTZ | |
| cancelled_at | TIMESTAMPTZ | |
| UNIQUE(worker_id, shift_slot_id) | | один отклик на смену |

**`worker_preferences`** (фильтры + push-настройки)

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| user_id | UUID FK | |
| category_ids | INT[] | интересующие категории (пусто = все) |
| metro_station_ids | INT[] | станции (пусто = из профиля worker) |
| min_hourly_rate | DECIMAL | переопределяет worker.min_hourly_rate |
| max_distance_km | SMALLINT | |
| push_enabled | BOOLEAN | = worker.notifications_enabled (denormalized для быстрого query) |
| quiet_hours_start, quiet_hours_end | TIME | опционально |
| updated_at | TIMESTAMPTZ | |

**`notifications`**

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| user_id | UUID FK | |
| type | ENUM | `new_vacancy`, `application_status`, `shift_reminder` |
| payload | JSONB | job_request_id, etc. |
| sent_at | TIMESTAMPTZ | |
| read_at | TIMESTAMPTZ | |

**`telegram_groups`**

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| chat_id | BIGINT UNIQUE | ID группы |
| title | VARCHAR | |
| category_ids | INT[] | какие категории постить |
| is_active | BOOLEAN | |

**`group_posts`**

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| job_request_id | UUID FK | |
| group_id | INT FK | |
| message_id | BIGINT | ID сообщения в группе |
| posted_at | TIMESTAMPTZ | |

### B.6. Масштабирование и отказоустойчивость (целевая архитектура)

Целевая topology для high load — не MVP, но проектировать с Phase 0 (idempotency keys, service layer, health checks).

| Слой | MVP | Production (Phase 8+) |
|------|-----|------------------------|
| Ingress | polling (dev), 1 webhook | nginx + webhook; rate limit; `update_id` dedup в Redis |
| Workers | 1 bot process, 1 ARQ worker | N bot/webhook workers, M ARQ workers; graceful shutdown |
| PostgreSQL | single instance | primary + read replica; matching/list reads → replica |
| Redis | single node | Sentinel/Cluster; cache / queue / rate-limit разделены |
| Jobs | ARQ + retry | idempotency keys, dead-letter, circuit breaker на Telegram 429 |
| Observability | structlog | Sentry + Prometheus; alerts на queue lag и error rate |

Детали, mermaid-диаграмма и ECC Tier 3: [ECC_STRATEGY.md § 6](./ECC_STRATEGY.md#6-отказоустойчивость-продукта-не-только-агенты).

---

## C. Детальные разделы по фичам

### 1. Настройка проекта + ECC (агентный harness)

**ECC уже установлен** (`developer` + `capability:security`). Orchestration module пропущен — см. [DEVELOPMENT_WORKFLOW.md § D](./DEVELOPMENT_WORKFLOW.md#d-ecc-orchestration-practically-в-cursor).

**Шаги Phase 0 (осталось):**

```powershell
cd "c:\Users\Nikita\Desktop\AI MS\OutstaffingBot"
git init
# ECC install — выполнен; doctor: node scripts/ecc.js doctor (при обновлении ECC)
```

**Уже есть (ECC):**

- `.cursor/agents/`, `.cursor/rules/ecc/`, skills, commands, hooks (`ECC_HOOK_PROFILE=standard`)
- `ECC_AGENT_DATA_HOME=%USERPROFILE%\.cursor\ecc`

**Python backend:**

```bash
cd backend && poetry init  # или uv/pip
poetry add aiogram fastapi uvicorn sqlalchemy asyncpg alembic redis arq pydantic-settings
```

**Mini App:**

```bash
npm create vite@latest mini-app -- --template react-ts
cd mini-app && npm install @telegram-apps/sdk-react @tanstack/react-query axios
```

**`.env` (шаблон):**

```
BOT_TOKEN=
WEBHOOK_SECRET=
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/outstaffing
REDIS_URL=redis://localhost:6379/0
MINI_APP_URL=https://yourdomain.com/app
API_BASE_URL=https://yourdomain.com/api
ADMIN_TELEGRAM_IDS=123456789
```

---

### 2. База данных и модели

- Alembic migrations с нулевой ревизией → все таблицы выше
- Seed-скрипты: `metro_stations` (~200 станций МСК), `job_categories` (~30 категорий)
- Индексы:
  - `job_requests(status, category_id, metro_station_id, hourly_rate)`
  - `shift_slots(shift_date, start_time, end_time)`
  - `applications(worker_id, status)` + partial index WHERE status = 'accepted'
- PostGIS опционально для geo-matching; на MVP — расчёт по lat/lon формулой Haversine

---

### 3. Telegram-бот (FSM)

#### Главное меню

Reply-клавиатура с двумя кнопками внизу:

- **«👷 Работник»**
- **«🏢 Работодатель»**

Дополнительно: Inline «📱 Открыть приложение» (WebApp button).

#### FSM: Работник — создание мини-резюме

```
WorkerRegistration:
  first_name → last_name → age → gender →
  metro_station (inline search) →
  experience_loop:
    category (inline) → role_title → duration_months →
    «Добавить ещё?» / «Готово» →
  min_hourly_rate → confirm → save
```

#### FSM: Работодатель — создание заявки

```
JobRequestCreation:
  category → title → description →
  metro_station → hourly_rate → workers_needed →
  shift_dates (календарь inline) →
  for each date: start_time → end_time →
  optional_fields (skip/ fill) →
  post_to_groups? → confirm → publish
```

#### FSM: Работник — поиск и отклик

```
VacancySearch:
  filters (rate, metro, category) → list →
  vacancy_detail → select_shift →
  conflict_check → apply / error
```

#### Роль пользователя

- Один `telegram_id` может быть и worker, и employer (`role = both`)
- При входе — выбор роли через нижние кнопки; контекст роли хранится в FSM data

---

### 4. Алгоритм matching

**Принцип:** категории вместо NLP по свободному тексту.

#### Scoring (0–100)

| Критерий | Вес | Логика |
|----------|-----|--------|
| Категория | 40 | `job.category_id IN worker.category_ids` OR worker has experience in category |
| Метро | 30 | same station = 30; соседние линии/радиус ≤ N км = 20–25 |
| Ставка | 20 | `job.hourly_rate >= worker.min_hourly_rate` → 20, иначе 0 (фильтр) |
| Опыт | 10 | `max(worker_experience.duration_months) >= job.min_experience_months` |

**Hard filters (SQL WHERE):**

```sql
job.status = 'active'
AND job.hourly_rate >= :min_rate
AND (job.required_gender = 'any' OR job.required_gender = worker.gender)
AND worker.age BETWEEN COALESCE(job.min_age, 16) AND COALESCE(job.max_age, 70)
AND shift_slot.slots_filled < shift_slot.slots_total
```

**Push matching:** при создании `job_request` → ARQ task `match_and_notify_workers(job_id)` → SELECT workers WHERE hard filters + score ≥ 60 → INSERT notifications → send Telegram message.

---

### 5. Conflict prevention (пересечение смен)

**Правило:** работник не может иметь две активные заявки (`status IN ('pending', 'accepted')`) на пересекающиеся `shift_slots`.

**Overlap check:**

```python
def shifts_overlap(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end
```

**SQL-запрос перед apply:**

```sql
SELECT ss.* FROM applications a
JOIN shift_slots ss ON a.shift_slot_id = ss.id
WHERE a.worker_id = :worker_id
  AND a.status IN ('pending', 'accepted')
  AND ss.shift_date = :new_date
  AND ss.start_time < :new_end AND :new_start < ss.end_time
```

**UX:**

- При конфликте: «У вас уже есть смена 19.06 10:00–18:00. Отмените её, чтобы откликнуться на новую.»
- Кнопки: «Отменить предыдущую и откликнуться» / «Назад»

---

### 6. Push-уведомления / фоновые задачи

**ARQ tasks:**

| Task | Триггер |
|------|---------|
| `match_workers_for_job(job_id)` | Новая заявка employer |
| `notify_worker(user_id, payload)` | Match found |
| `post_job_to_groups(job_id)` | job.status → active, post_to_groups=true |
| `expire_old_jobs()` | Cron каждый час |
| `shift_reminder()` | Cron за 2ч до смены |

**Worker notification settings:**

- Глобальный toggle: `notifications_enabled`
- Гранулярный: `worker_preferences.category_ids`, `metro_station_ids`, `min_hourly_rate`
- Quiet hours: не слать push 23:00–08:00 (кроме urgent)

**Rate limiting Telegram:** batch send через asyncio.Semaphore(25), retry on 429.

---

### 7. Mini App frontend

**Страницы:**

| Роль | Страницы |
|------|----------|
| Worker | Profile, Experience, Preferences, Vacancy List, Vacancy Detail, My Applications, Notifications Settings |
| Employer | Company Profile, Create Job, My Jobs, Applications inbox |

**UX:**

- Telegram theme colors (`themeParams`)
- Bottom navigation: Главная / Поиск / Мои / Настройки
- Pull-to-refresh на списках
- Haptic feedback на отклик

**Deep link:** `t.me/BotName/app?startapp=vacancy_{uuid}`

---

### 8. REST API для Mini App

**Base:** `/api/v1`

| Method | Path | Описание |
|--------|------|----------|
| GET | `/me` | текущий user + roles |
| GET/PUT | `/worker/profile` | профиль работника |
| GET/POST/DELETE | `/worker/experiences` | опыт |
| GET/PUT | `/worker/preferences` | фильтры + push |
| GET | `/vacancies` | список с фильтрами |
| GET | `/vacancies/{id}` | детали |
| POST | `/applications` | отклик |
| DELETE | `/applications/{id}` | отмена |
| GET | `/applications/mine` | мои отклики |
| POST | `/employer/jobs` | создать заявку |
| GET | `/employer/jobs` | мои заявки |
| GET | `/employer/jobs/{id}/applications` | отклики |
| PATCH | `/employer/applications/{id}` | accept/reject |
| GET | `/reference/categories` | справочник |
| GET | `/reference/metro?q=` | поиск станций |

**Auth header:** `Authorization: tma {initData}`

---

### 9. Публикация в Telegram-группы

**Требования:**

- Бот — admin в группе с правом `post_messages`
- Группы в `telegram_groups`, привязка к категориям

**Формат поста:**

```
🔔 Новая вакancy: Официант
💰 350 ₽/час  |  👥 3 чел.
📍 м. Сокольники
📅 20.06 10:00–22:00, 21.06 10:00–22:00

Описание...

[Откликнуться 👷] ← WebApp button / deep link
```

**Обновление поста:** при `filled` / `cancelled` — edit message, добавить «❌ Закрыто».

---

### 10. Admin / модерация

**MVP:**

- `ADMIN_TELEGRAM_IDS` — команды `/admin stats`, `/admin block_user`, `/admin verify_employer`
- Новые employers → `verified=false` → заявки в статусе `draft` до verify (опционально)
- Логирование всех create/update в `audit_log` (JSONB)

**Phase 2:**

- Web admin panel (FastAPI + simple React)
- Жалобы на заявки

---

### 11. Деплой на сервер

> **Команда из 2 разработчиков / ранний staging без локального Docker:** см. [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md) — dev/staging VPS, Git, CI/CD Phase 0.5, чеклист «что сделать сейчас».

**Рекомендуемая конфигурация VPS:** 2 vCPU, 4 GB RAM, Ubuntu 24.04

**docker-compose.yml (сервисы):**

- `postgres`, `redis`
- `api` (FastAPI + uvicorn)
- `bot` (aiogram webhook mode)
- `worker` (ARQ)
- `nginx` (static mini-app + proxy /api + /webhook)

**Webhook vs Polling:**

- Production: **webhook** через nginx → `https://domain/webhook/{secret}`
- Dev: polling

**systemd** (альтернатива Docker): unit files для api, bot, worker

**Backup:** pg_dump cron daily

**Масштабирование и отказоустойчивость (Phase 8+):**

| Компонент | MVP (Phase 0–7) | Production (Phase 8+) |
|-----------|-----------------|------------------------|
| Telegram ingress | Polling (dev) / single webhook | Webhook + nginx rate limit; ARQ queue для outbound с backoff на 429 |
| App processes | 1 api + 1 bot + 1 worker | N webhook workers; M ARQ workers; graceful SIGTERM |
| PostgreSQL | Single instance | Primary + read replica; PgBouncer при росте conn |
| Redis | Single node | Sentinel или Cluster; разделение cache / queue / rate-limit DB |
| Jobs | ARQ basic retry | Idempotency keys, dead-letter, circuit breaker на Telegram API |
| Observability | structlog | + Sentry, Prometheus (RPS, queue depth, 429 count), alerts |
| Health | `/health` | `/health` + `/ready` (DB + Redis) |

Полная схема и ECC-компоненты для hardening: [ECC_STRATEGY.md § 6](./ECC_STRATEGY.md#6-отказоустойчивость-продукта-не-только-агенты).

---

### 12. Безопасность

| Угроза | Мера |
|--------|------|
| Подделка initData | HMAC-SHA256 с BOT_TOKEN, проверка `auth_date` ≤ 24h |
| IDOR | Все запросы фильтруются по `telegram_id` из validated initData |
| Spam заявок | Rate limit: 5 jobs/hour per employer |
| SQL injection | SQLAlchemy parameterized queries |
| Secrets | `.env`, не в git; Docker secrets |
| Webhook | Secret path token, IP whitelist optional |

---

## D. Примеры кода

### D.1. Главное меню (ReplyKeyboard)

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

def main_menu_kb(mini_app_url: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👷 Работник"),
                KeyboardButton(text="🏢 Работодатель"),
            ],
            [
                KeyboardButton(
                    text="📱 Открыть приложение",
                    web_app=WebAppInfo(url=mini_app_url),
                )
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите роль или откройте приложение",
    )
```

### D.2. FSM: регистрация работника (фрагмент)

```python
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class WorkerRegistration(StatesGroup):
    first_name = State()
    last_name = State()
    age = State()
    gender = State()
    metro = State()
    experience_category = State()
    experience_title = State()
    experience_months = State()
    min_rate = State()
    confirm = State()

@router.message(WorkerRegistration.first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await state.set_state(WorkerRegistration.last_name)
    await message.answer("Введите фамилию:")
```

### D.3. Создание job request (service layer)

```python
async def create_job_request(
    session: AsyncSession,
    employer_id: UUID,
    data: JobRequestCreate,
) -> JobRequest:
    job = JobRequest(
        employer_id=employer_id,
        category_id=data.category_id,
        title=data.title,
        description=data.description,
        metro_station_id=data.metro_station_id,
        hourly_rate=data.hourly_rate,
        workers_needed=data.workers_needed,
        status="active",
        post_to_groups=data.post_to_groups,
    )
    session.add(job)
    await session.flush()

    for slot in data.shift_slots:
        session.add(ShiftSlot(
            job_request_id=job.id,
            shift_date=slot.date,
            start_time=slot.start_time,
            end_time=slot.end_time,
            slots_total=data.workers_needed,
        ))

    await session.commit()

    await arq_pool.enqueue_job("match_workers_for_job", str(job.id))
    if data.post_to_groups:
        await arq_pool.enqueue_job("post_job_to_groups", str(job.id))

    return job
```

### D.4. Matching query

```python
async def find_matching_vacancies(
    session: AsyncSession,
    worker: Worker,
    filters: VacancyFilters,
    limit: int = 20,
) -> list[VacancyMatch]:
    worker_cats = filters.category_ids or [
        e.category_id for e in worker.experiences
    ]
    min_rate = filters.min_hourly_rate or worker.min_hourly_rate

    stmt = (
        select(JobRequest, ShiftSlot)
        .join(ShiftSlot)
        .where(
            JobRequest.status == "active",
            JobRequest.hourly_rate >= min_rate,
            JobRequest.category_id.in_(worker_cats),
            ShiftSlot.slots_filled < ShiftSlot.slots_total,
            ShiftSlot.shift_date >= date.today(),
        )
    )
    if filters.metro_station_id:
        stmt = stmt.where(JobRequest.metro_station_id == filters.metro_station_id)

    rows = (await session.execute(stmt.limit(limit))).all()
    return [VacancyMatch(job=r[0], slot=r[1]) for r in rows]
```

### D.5. Shift conflict check

```python
async def has_shift_conflict(
    session: AsyncSession,
    worker_id: UUID,
    new_slot: ShiftSlot,
) -> Application | None:
    stmt = (
        select(Application)
        .join(ShiftSlot, Application.shift_slot_id == ShiftSlot.id)
        .where(
            Application.worker_id == worker_id,
            Application.status.in_(["pending", "accepted"]),
            ShiftSlot.shift_date == new_slot.shift_date,
            ShiftSlot.start_time < new_slot.end_time,
            new_slot.start_time < ShiftSlot.end_time,
        )
    )
    return (await session.execute(stmt)).scalar_one_or_none()
```

### D.6. Mini App initData auth middleware (FastAPI)

```python
import hashlib, hmac, json
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException, Depends

def validate_init_data(init_data: str, bot_token: str) -> dict:
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, "Missing hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()
    calculated = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if calculated != received_hash:
        raise HTTPException(401, "Invalid initData")

    user = json.loads(parsed.get("user", "{}"))
    return user

async def get_current_user(
    authorization: str = Header(...),
    settings: Settings = Depends(get_settings),
):
    if not authorization.startswith("tma "):
        raise HTTPException(401, "Invalid auth scheme")
    init_data = authorization[4:]
    tg_user = validate_init_data(init_data, settings.bot_token)
    return await user_service.get_or_create_by_telegram_id(tg_user["id"])
```

### D.7. Notification dispatcher

```python
async def notify_matching_workers(ctx, job_id: str):
    async with session_factory() as session:
        job = await job_repo.get(session, UUID(job_id))
        workers = await matching_service.find_workers_for_job(session, job)

        bot = ctx["bot"]
        for worker in workers:
            if not worker.notifications_enabled:
                continue
            text = format_new_vacancy_message(job)
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📋 Подробнее",
                    web_app=WebAppInfo(url=f"{settings.mini_app_url}/vacancy/{job.id}"),
                )
            ]])
            try:
                await bot.send_message(worker.user.telegram_id, text, reply_markup=kb)
                await notification_repo.create(session, worker.user_id, "new_vacancy", {"job_id": str(job.id)})
            except TelegramForbiddenError:
                await user_repo.mark_blocked(session, worker.user_id)
        await session.commit()
```

### D.8. Posting to group

```python
async def post_job_to_groups(ctx, job_id: str):
    async with session_factory() as session:
        job = await job_repo.get_with_relations(session, UUID(job_id))
        groups = await group_repo.find_for_category(session, job.category_id)
        text = render_group_post(job)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="👷 Откликнуться",
                url=f"https://t.me/{settings.bot_username}/app?startapp=vacancy_{job.id}",
            )
        ]])

        bot = ctx["bot"]
        for group in groups:
            msg = await bot.send_message(group.chat_id, text, reply_markup=kb)
            await group_post_repo.create(session, job.id, group.id, msg.message_id)
        await session.commit()
```

---

## E. Агентная оркестрация (ECC)

Ruflo удалён. Агентный harness — **ECC** ([github.com/affaan-m/ECC](https://github.com/affaan-m/ECC)).

| Документ | Содержание |
|----------|------------|
| [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md) | **Ежедневная работа:** Karpathy + ECC, таблица «оркестрация да/нет», multi-agent patterns, anti-patterns |
| [ECC_STRATEGY.md](./ECC_STRATEGY.md) | Установка, tier roadmap, top-10 компонентов, fault-tolerance |

**Краткий workflow (Karpathy + ECC):**

1. Классифицировать задачу → solo или orchestrated ([DEVELOPMENT_WORKFLOW.md § C](./DEVELOPMENT_WORKFLOW.md#c-agent-orchestration--when-yes--when-no))
2. Phase kickoff → `/plan` (confirm gate) → при 3 слоях: manual subagents (`ecc-architect` → implement → reviewers)
3. Реализация → surgical diffs + `tdd-workflow`, `python-patterns`, `postgres-patterns`
4. Проверка → `verification-loop`, `/code-review`
5. Security (Phase 2+) → `security-review`, `/security-scan`
6. Deploy (Phase 8) → `deployment-patterns`*, `/security-scan`
7. Память → `continuous-learning-v2` (hooks), `ECC_AGENT_DATA_HOME=~/.cursor/ecc`

\* Tier 2–3 skills — по [ECC_STRATEGY.md](./ECC_STRATEGY.md).

**Orchestration module:** не установлен (конфликт с `capability:security`). Команды `/orch-*` есть; skills `orch-pipeline` — нет. Использовать ручной pipeline из [DEVELOPMENT_WORKFLOW.md § D](./DEVELOPMENT_WORKFLOW.md#d-ecc-orchestration-practically-в-cursor). Установка orchestration — опционально Phase 3–5.

---

## E.1. Процесс разработки (кратко)

Полная версия: [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md).

| Принцип | Источник |
|---------|----------|
| Мало кода, surgical diffs, verify before done | Karpathy (`karpathy-guidelines.mdc`) |
| Выбор solo vs multi-agent по типу задачи | ECC + § C DEVELOPMENT_WORKFLOW |
| Ветки, коммиты, PR только по запросу | `git-workflow.mdc`, [GIT_WORKFLOW.md](./GIT_WORKFLOW.md) |
| Hooks, instincts, session memory | ECC `standard` profile |

**Типичный цикл:** задача → ветка → (при необходимости `/plan`) → Agent session → tests green → review → commit/PR по запросу.

---

## F. Roadmap — фазы реализации

### Phase 0: Foundation (1–2 недели) — P0

- [x] Git init, структура monorepo
- [x] ECC install (`developer` + `security`) — orchestration **опционально** позже; workflow: [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)
- [x] Docker Compose: postgres, redis
- [x] SQLAlchemy models + Alembic migrations
- [x] Seed: metro, categories
- [x] FastAPI skeleton + health check
- [x] aiogram skeleton + /start + главное меню

**Verification:** `docker compose up`, bot отвечает /start, migrations apply.

---

### Phase 1: Worker Core (2 недели) — P0

- [x] FSM регистрация работника (бот)
- [x] API: GET/PUT worker profile, experiences
- [x] Mini App: страница профиля
- [x] initData auth middleware

**Verification:** профиль создаётся в боте → виден в Mini App.

---

### Phase 2: Employer + Job Requests (2 недели) — P0

- [x] FSM создание заявки (бот)
- [x] API: CRUD jobs, shift_slots
- [x] Mini App: форма создания заявки
- [x] Статусы draft/active/cancelled

**Verification:** employer создаёт заявку через Mini App → видна в боте.

---

### Phase 3: Matching + Search (1–2 недели) — P0

- [x] Matching service + SQL queries
- [x] Manual search filters (бот + API + Mini App)
- [x] Список вакансий с пагинацией

**Verification:** worker с категорией «официант» видит только релевантные вакансии.

---

### Phase 4: Applications + Conflict Prevention (1 неделя) — P0

- [x] Apply / cancel application
- [x] Shift overlap check
- [x] UX ошибки конфликта

**Verification:** нельзя принять 2 пересекающиеся смены без отмены.

---

### Phase 5: Notifications + Background Jobs (1–2 недели) — P1

- [x] ARQ worker setup
- [x] Push при новой заявке
- [x] Worker preferences (категории, ставка, metro)
- [x] Global notification toggle

**Verification:** новая заявка → push matching workers within 30s.

---

### Phase 6: Group Posting (1 неделя) — P1

> Частично в старых образах bot/worker; в git пропущена — требует решения команды.

- [ ] Admin: register telegram groups
- [ ] Auto-post formatted messages
- [ ] Edit on close

**Verification:** заявка появляется в тестовой группе с кнопкой отклика.

---

### Phase 7: Mini App Polish (2 недели) — P1

- [x] Полный UI/UX всех экранов
- [x] Deep links, haptic, theme
- [x] Employer inbox (accept/reject applications)

**Verification:** полный user journey без бота (только Mini App).

---

### Phase 8: Production Deploy (1 неделя) — P1

- [ ] VPS setup, nginx, TLS
- [ ] Webhook mode
- [ ] systemd/Docker production config
- [ ] Backup, logging, Sentry

**Verification:** production URL, SSL, uptime 24h.

---

### Phase 9: Admin + Moderation (1 неделя) — P2

- [ ] Admin commands
- [ ] Employer verification
- [ ] Audit log

---

### Phase 10: Enhancements — P3

- [ ] PostGIS geo matching
- [ ] Employer push (новые подходящие работники)
- [ ] Рейтинги / отзывы
- [ ] Multi-city support
- [ ] Analytics dashboard

---

## Справочник: категории работ (MVP seed)

| slug | name_ru |
|------|---------|
| waiter | Официант |
| bartender | Бармен |
| cashier | Кассир |
| loader | Грузчик |
| courier | Курьер |
| promo | Промоутер |
| cleaner | Уборщик |
| cook_helper | Помощник повара |
| warehouse | Складской работник |
| event_staff | Персонал мероприятий |
| security | Охранник |
| driver | Водитель |
| other | Другое |

---

## Риски и решения

| Риск | Решение |
|------|---------|
| Telegram rate limits | ARQ queue + backoff; Redis token bucket; ECC `redis-patterns` |
| Рассинхрон bot/mini app | Единый service layer, не дублировать логику |
| Свободный текст опыта | Категории + optional description |
| Пересечение смен | DB constraint + pre-check + понятный UX |

---

## Следующий шаг

Когда будете готовы к реализации, начните с **Phase 0**: `git init` → Docker Compose + миграции. ECC harness уже установлен.

**Процесс разработки:** [`docs/DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md) — Karpathy + ECC, оркестрация, anti-patterns.

**Git workflow:** [`docs/GIT_WORKFLOW.md`](GIT_WORKFLOW.md) — обязателен для всех разработчиков и AI-агентов.
