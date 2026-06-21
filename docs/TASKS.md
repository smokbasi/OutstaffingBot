# Задачи OutstaffingBot

> **Онбординг Dev2:** [ONBOARDING_DEV2.md](./ONBOARDING_DEV2.md)  
> **Единый чеклист** всех фаз разработки. Детали архитектуры — в [PLAN.md](./PLAN.md), как выполнять каждую фазу — в [DEVELOPMENT_WORKFLOW.md § E](./DEVELOPMENT_WORKFLOW.md#e-workflow-по-фазам-planmd).

## Как пользоваться этим файлом

1. **Открывайте этот файл первым**, когда ищете «что делать дальше» — здесь все checkbox-задачи Phase 0–10 в одном месте.
2. **Текущая фаза** — та, где есть незакрытые пункты. Сейчас это **Phase 2**.
3. **Отмечайте прогресс** — меняйте `[ ]` на `[x]` по мере выполнения (и синхронизируйте с [PLAN.md § F](./PLAN.md#f-roadmap--фазы-реализации), если правите roadmap там).
4. **Перед началом фазы** — прочитайте строку для этой фазы в [DEVELOPMENT_WORKFLOW.md § E](./DEVELOPMENT_WORKFLOW.md#e-workflow-по-фазам-planmd): solo vs оркестрация, skills, verification.
5. **Для ECC/setup** — дополнительный чеклист Phase 0 в [ECC_STRATEGY.md § 9](./ECC_STRATEGY.md#9-чеклист-phase-0-ecc).

---

## Текущая фаза: Phase 2 — Employer + Job Requests

**Следующий шаг:** API CRUD jobs + shift_slots (backend), затем FSM (бот) и Mini App форма заявки.

**Verification Phase 0:** локально (Docker Desktop) **или** на dev/staging VPS — см. [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md).

---

### Phase 0.5 — Dev Server & Git Team (3–5 дней) [P0]

> **Зачем:** обойти проблемы Docker/WSL на Windows; общая среда для двух разработчиков. Подробно: [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md).

- [x] Public GitHub repo + push `main` — https://github.com/smokbasi/OutstaffingBot
- [x] Dev2 добавлен как collaborator
- [x] VPS (2 vCPU, 4 GB, Ubuntu 24.04) — shared `89.125.25.99` (vspomni) — Hetzner / Timeweb / Selectel
- [x] `scripts/deploy/bootstrap-server.sh` на сервере
- [x] Server `.env` на `/opt/outstaffingbot` (POSTGRES/WEBHOOK_SECRET сгенерированы; **BOT_TOKEN задан** на staging)
- [x] SSH-ключ `id_vspomni` → пользователь `deploy`
- [x] SSH pubkey Dev2 на сервере (`/home/deploy/.ssh/authorized_keys`, проверено)
- [x] `docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d` на `/opt/outstaffingbot` (`COMPOSE_PROJECT_NAME=outstaffingbot`)
- [x] Миграции + seed на staging
- [x] Bot `/start` на staging (polling; webhook — позже с доменом)
- [ ] Договорённость: PR review (1 approve), кто деплоит
- [ ] (Опционально) поддомен + TLS для webhook / Mini App
- [ ] (Опционально) GitHub Actions CI зелёный на PR

**Verification:** оба разработчика клонировали repo; staging отвечает `/start`; изменения из PR видны после deploy.

---

### Phase 0 — Foundation (1–2 недели) [P0]

- [x] Git init, структура monorepo
- [x] ECC install (`developer` + `security`) — orchestration **опционально** позже; workflow: [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)
- [x] Docker Compose: postgres, redis
- [x] SQLAlchemy models + Alembic migrations
- [x] Seed: metro, categories
- [x] FastAPI skeleton + health check
- [x] aiogram skeleton + /start + главное меню
- [x] **Ручная проверка:** `docker compose up` + migrations apply + bot `/start` (staging: docker + bot `/start` OK)

#### Phase 0 — ECC setup (дополнительно, из ECC_STRATEGY)

- [ ] Удалить Ruflo MCP из Cursor Settings (если был)
- [x] `npx ecc-install --profile developer --target cursor`
- [x] `ECC_AGENT_DATA_HOME=%USERPROFILE%\.cursor\ecc`
- [x] Сохранить Karpathy guidelines и `git-workflow` rules (не из ECC)
- [x] `node scripts/ecc.js doctor` (WARNING drift — OK) — без ошибок
- [ ] Не коммитить `.cursor/ecc-agent-data.json` с секретами (если появится)

**Как выполнять:** оркестрация (scaffold) — `/plan`, `ecc-architect`, `postgres-patterns`. См. [DEVELOPMENT_WORKFLOW § E, Phase 0](./DEVELOPMENT_WORKFLOW.md#e-workflow-по-фазам-planmd).

---

### Phase 1 — Worker Core (2 недели) [P0]

- [x] FSM регистрация работника (бот)
- [x] API: GET/PUT worker profile, experiences
- [x] Mini App: страница профиля (просмотр + редактирование)
- [x] initData auth middleware

**Verification:** профиль создаётся в боте → виден в Mini App → редактируется в Mini App.

**Как выполнять:** оркестрация (3 слоя) — `tdd-workflow`, `fastapi-patterns`, `security-review` с Phase 2 для auth.

---

### Phase 2 — Employer + Job Requests (2 недели) [P0]

> **В работе:** backend API CRUD jobs + shift_slots (ветка `feature/phase-2-employer-jobs`).

- [ ] FSM создание заявки (бот)
- [ ] API: CRUD jobs, shift_slots
- [ ] Mini App: форма создания заявки
- [ ] Статусы draft/active/cancelled

**Verification:** employer создаёт заявку через Mini App → видна в боте.

**Как выполнять:** оркестрация + `security-review`, `ecc-security-reviewer`.

---

### Phase 3 — Matching + Search (1–2 недели) [P0]

- [ ] Matching service + SQL queries
- [ ] Manual search filters (бот + API + Mini App)
- [ ] Список вакансий с пагинацией

**Verification:** worker с категорией «официант» видит только релевантные вакансии.

**Как выполнять:** solo + maybe perf — `postgres-patterns`, `performance-optimizer`.

---

### Phase 4 — Applications + Conflict Prevention (1 неделя) [P0]

- [ ] Apply / cancel application
- [ ] Shift overlap check
- [ ] UX ошибки конфликта

**Verification:** нельзя принять 2 пересекающиеся смены без отмены.

**Как выполнять:** solo — `tdd-workflow` (overlap tests).

---

### Phase 5 — Notifications + Background Jobs (1–2 недели) [P1]

- [ ] ARQ worker setup
- [ ] Push при новой заявке
- [ ] Worker preferences (категории, ставка, metro)
- [ ] Global notification toggle

**Verification:** новая заявка → push matching workers within 30s.

**Как выполнять:** maybe оркестрация — `error-handling`, ARQ patterns.

---

### Phase 6 — Group Posting (1 неделя) [P1]

- [ ] Admin: register telegram groups
- [ ] Auto-post formatted messages
- [ ] Edit on close

**Verification:** заявка появляется в тестовой группе с кнопкой отклика.

**Как выполнять:** solo — `python-patterns`.

---

### Phase 7 — Mini App Polish (2 недели) [P1]

- [ ] Полный UI/UX всех экранов
- [ ] Deep links, haptic, theme
- [ ] Employer inbox (accept/reject applications)

**Verification:** полный user journey без бота (только Mini App).

**Как выполнять:** solo (UI) — `frontend-patterns`, `ecc-react-reviewer`.

---

### Phase 8 — Production Deploy (1 неделя) [P1]

- [ ] VPS setup, nginx, TLS
- [ ] Webhook mode
- [ ] systemd/Docker production config
- [ ] Backup, logging, Sentry

**Verification:** production URL, SSL, uptime 24h.

**Как выполнять:** оркестрация — `/security-scan`, `deployment-patterns`.

---

### Phase 9 — Admin + Moderation (1 неделя) [P2]

- [ ] Admin commands
- [ ] Employer verification
- [ ] Audit log

**Как выполнять:** solo — admin handlers изолированно.

---

### Phase 10 — Enhancements [P3]

- [ ] PostGIS geo matching
- [ ] Employer push (новые подходящие работники)
- [ ] Рейтинги / отзывы
- [ ] Multi-city support
- [ ] Analytics dashboard

**Как выполнять:** по фиче — `/plan` per enhancement, отдельная ветка на каждое улучшение.

---

## Быстрая навигация

| Документ | Что там |
|----------|---------|
| **[TASKS.md](./TASKS.md)** (этот файл) | **Единый чеклист задач** Phase 0–10 |
| [PLAN.md § F](./PLAN.md#f-roadmap--фазы-реализации) | Roadmap с verification и контекстом фаз |
| [PLAN.md § C](./PLAN.md#c-детальные-разделы-по-фичам) | Детальные разделы по фичам (код, схемы) |
| [DEVELOPMENT_WORKFLOW.md § E](./DEVELOPMENT_WORKFLOW.md#e-workflow-по-фазам-planmd) | Как выполнять каждую фазу (solo vs orchestration) |
| [DEVELOPMENT_WORKFLOW.md § C](./DEVELOPMENT_WORKFLOW.md#c-agent-orchestration--when-yes--when-no) | Когда нужна multi-agent оркестрация |
| [ECC_STRATEGY.md § 9](./ECC_STRATEGY.md#9-чеклист-phase-0-ecc) | Чеклист установки ECC (Phase 0) |
| [GIT_WORKFLOW.md § 12](./GIT_WORKFLOW.md#12-чеклист-перед-pr) | Чеклист перед PR (git-процесс) |
| [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md) | Dev/staging VPS, Git для 2 разработчиков, деплой |
| [ONBOARDING_DEV2.md](./ONBOARDING_DEV2.md) | Онбординг второго разработчика |

---

## Где задачи были раньше (до TASKS.md)

Задачи **не отсутствовали**, но были **разбросаны**:

| Место | Содержание |
|-------|------------|
| `PLAN.md` § F (стр. ~991–1107) | Основной roadmap с checkbox — **в конце** 1100+ строк документа |
| `PLAN.md` § C.1 | Шаги Phase 0 (команды scaffold), без полного чеклиста |
| `DEVELOPMENT_WORKFLOW.md` § E | Таблица *как* работать по фазам, **без** checkbox-задач |
| `ECC_STRATEGY.md` § 9 | Отдельный ECC-чеклист Phase 0 |
| `GIT_WORKFLOW.md` | Чеклисты git/PR, не roadmap фич |

Отдельного `TASKS.md` или issue-board не было — отсюда ощущение, что «задач нет».
