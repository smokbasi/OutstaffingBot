# Процесс разработки OutstaffingBot: Karpathy + ECC

Практическое руководство для соло-разработчика и малой команды: **как писать код** (Karpathy) и **когда включать агентную оркестрацию** (ECC).

📋 **Задачи (единый чеклист):** [docs/TASKS.md](./TASKS.md)

**Связанные документы:**

| Документ | Назначение |
|----------|------------|
| [TASKS.md](./TASKS.md) | **Единый чеклист** задач Phase 0–10 |
| [PLAN.md](./PLAN.md) | Архитектура, фазы 0–10, фичи |
| [ECC_STRATEGY.md](./ECC_STRATEGY.md) | Что установлено, tier roadmap, fault tolerance |
| [GIT_WORKFLOW.md](./GIT_WORKFLOW.md) | Ветки, коммиты, PR |
| `.cursor/rules/karpathy-guidelines.mdc` | Поведенческие правила агента (alwaysApply) |
| `.cursor/rules/git-workflow.mdc` | Git-правила для агентов (alwaysApply) |

---

## A. Философия: Karpathy + ECC вместе

### Karpathy — **КАК** писать код

Правила из `karpathy-guidelines.mdc` применяются **всегда**, независимо от ECC:

| Принцип | Практика |
|---------|----------|
| Think before coding | Явно назвать допущения; при неясности — спросить, не угадывать |
| Simplicity first | Минимум кода; без спекулятивных абстракций и «на будущее» |
| Surgical changes | Одна задача = один concern; не трогать соседний код |
| Goal-driven execution | Критерии успеха до кода: «тест X падает → зелёный → PR» |

**Karpathy ограничивает объём работы агента.** Даже при полной ECC-оркестрации итоговый diff должен быть маленьким и обоснованным.

### ECC — **КОГДА** включать workflow, skills, agents, hooks

ECC не заменяет мышление разработчика — он стандартизирует **ритуалы качества**:

- **Skills** — паттерны домена (`python-patterns`, `postgres-patterns`)
- **Agents** — специализированный review/planning (`ecc-architect`, `ecc-python-reviewer`)
- **Commands** — slash-команды (`/plan`, `/code-review`, `/security-scan`)
- **Hooks** — автоматика сессии (форматирование, секреты, память)
- **Orchestration** — multi-agent pipeline (сейчас **не установлен**, см. §D)

### Как они дополняют друг друга

```
Karpathy  →  размер и форма изменений (мало, точно, проверяемо)
ECC       →  выбор инструмента по типу задачи (solo vs orchestrated)
```

**Правило синтеза:** сначала классифицировать задачу (таблица §C), затем применить Karpathy к каждому шагу. Оркестрация не отменяет surgical diffs — она координирует **несколько** surgical diffs по разным областям.

---

## B. Ежедневный workflow (solo / малая команда)

### Пошаговый цикл

```mermaid
flowchart LR
    T[Задача] --> C{ECC нужен?}
    C -->|Нет| B[feature/fix branch]
    C -->|Да| P[/plan или architect]
    P --> B
    B --> A[Agent session]
    A --> V[verify + review]
    V --> G[commit по запросу]
    G --> PR[PR + CI]
```

| Шаг | Действие | Karpathy | ECC |
|-----|----------|----------|-----|
| 1. Открыть задачу | Issue / пункт PLAN.md / свой backlog | Сформулировать критерий готовности | §C: нужна ли оркестрация? |
| 2. Контекст | Прочитать затронутые файлы **до** правок | Не предполагать структуру | `continuous-learning-v2` instincts (авто) |
| 3. Ветка | `git checkout -b feature/...` или `fix/...` | Одна ветка = одна задача | `git-workflow.mdc` |
| 4. План (если нужен) | `/plan` или Task → `ecc-planner` | План с verify-шагами | Phase kickoff для фич 3+ файлов |
| 5. Реализация | Cursor Agent (основной) | Surgical diff | Skill по домену (явно или авто) |
| 6. Проверка | `pytest`, `ruff`, `docker compose up` | Loop until green | `verification-loop` skill |
| 7. Review | `/code-review` или `ecc-python-reviewer` | Только свой diff | После каждого нетривиального изменения |
| 8. Commit / PR | Только по явному запросу | Маленький осмысленный коммит | Hooks блокируют `--no-verify` |

### Cursor Agent vs Composer vs Subagents

| Инструмент | Когда | Пример OutstaffingBot |
|------------|-------|------------------------|
| **Cursor Agent** (чат Agent mode) | Основной режим: 1 задача, 1–5 файлов, итерации с verify | FSM handler, Alembic migration, API route |
| **Composer** | Быстрые правки в 1–2 файлах без полного agent loop | Текст кнопки, rename, typo |
| **Subagents (Task)** | Параллельные **независимые** области или специализированный review | `ecc-architect` + coder; `ecc-python-reviewer` после кода |
| **ECC Commands** (`/plan`, `/security-scan`) | Структурированный ритуал с gates | Phase kickoff, pre-deploy audit |

**Не смешивать:** два subagent'а, правящих один файл, или Agent + Composer на одном файле одновременно.

---

## C. Agent orchestration — WHEN YES / WHEN NO

### Матрица решений

| Тип задачи | Оркестрация? | Почему | ECC tool |
|------------|:------------:|--------|----------|
| Опечатка в README | **НЕТ** | 1 строка, Karpathy: прямой fix | Composer / direct agent |
| Single bug fix (1 файл) | **НЕТ** | Минимальный diff; тест → fix | `tdd-workflow` + direct agent |
| Новый FSM handler (1 файл) | **НЕТ** | Локальная логика; читать соседние handlers | `python-patterns` skill |
| Новый API endpoint + schema | **НЕТ** | 2–3 файла, один слой | `fastapi-patterns` + `ecc-fastapi-reviewer` |
| Database migration + models | **MAYBE** | Схема + migration + тесты; solo если один developer | `postgres-patterns`, `ecc-database-reviewer` |
| Phase 0: scaffold monorepo | **ДА** | backend + mini-app + docker + ECC | `/plan` + manual subagents |
| Worker registration (bot+API+UI) | **ДА** | 3 слоя, единый domain | architect → implement → reviewers (§F) |
| Matching service + SQL + cache | **MAYBE** | Perf + SQL сложность; solo + `performance-optimizer` если узко | `postgres-patterns`, `redis-patterns`* |
| Security audit перед deploy | **ДА** | Специализированные проверки | `/security-scan` + `ecc-security-reviewer` |
| Full feature (bot+API+mini-app) | **ДА** | Параллельные области | manual multi-agent (§D) |
| Рефакторинг service layer | **MAYBE** | Зависит от охвата; <5 файлов — solo | `/plan` + `verification-loop` |
| Production deploy (Phase 8) | **ДА** | Infra + security + health checks | `security-scan` + deploy checklist |
| Mini App UI polish (CSS only) | **НЕТ** | Один слой; не звать backend reviewer | `frontend-patterns` |
| ARQ worker + notifications | **MAYBE** | Фоновые задачи + idempotency | `tdd-workflow` + `error-handling` |
| Admin moderation commands | **НЕТ** | Несколько handlers, один домен | `python-patterns` |
| Incident / prod debug | **MAYBE** | Длинная сессия → `strategic-compact`* | explore agent + logs |
| Документация PLAN/ECC | **НЕТ** | Текст, surgical edits | direct agent |
| E2E Mini App journey (Phase 5+) | **ДА** | Критический user flow | `ecc-e2e-runner`* + `e2e-testing`* |
| Конфликт смен (business logic) | **НЕТ** | Domain rule в 1–2 service files | `tdd-workflow` (тест на overlap) |
| Git rebase / conflict resolve | **НЕТ** | Ручная работа | `git-workflow.mdc` |
| Установка ECC capability | **НЕТ** | Одна команда install | `configure-ecc` skill |

\* Skills из Tier 2–3 — установить позже по [ECC_STRATEGY.md](./ECC_STRATEGY.md).

### Быстрые эвристики

1. **≤ 3 файла, один слой** → solo Agent, без оркестрации.
2. **Bot + API + Mini App** → оркестрация (разные папки, параллельные subagents).
3. **Есть `/plan` gate** → пользователь подтвердил план → можно multi-step.
4. **Сомневаешься** → начни solo; эскалируй в оркестрацию только если scope вырос.

---

## D. ECC orchestration practically в Cursor

### Текущее состояние установки (2026-06-19)

Из `.cursor/ecc-install-state.json`:

| Параметр | Значение |
|----------|----------|
| Profile | `developer` + `capability:security` |
| Установлено | rules, agents, commands, hooks, python/ts/react, database, workflow-quality, security |
| **Пропущено** | `orchestration` module (конфликт manifest с `capability:security`) |
| Hooks | `ECC_HOOK_PROFILE=standard` |
| Память | `ECC_AGENT_DATA_HOME=%USERPROFILE%\.cursor\ecc` |

**Следствие:** команды `/orch-*` есть в `.cursor/commands/`, но skills `orch-pipeline`, `orch-add-feature` **не установлены**. Используй **ручную оркестрацию** (ниже).

### Режим A — Сейчас (без orchestration module)

**Ручной multi-agent pipeline:**

```
1. /plan «<фича>»  →  ждать confirm
2. Task(ecc-architect)  →  design note (readonly)
3. Agent session  →  implement по слоям (backend → api → mini-app)
4. Task(ecc-python-reviewer)  →  backend diff
5. Task(ecc-fastapi-reviewer)  →  API diff (если менялся)
6. verification-loop  →  pytest, ruff, build mini-app
7. /code-review  →  финальный проход
8. commit / PR  →  только по запросу пользователя
```

**Параллельные subagents** — только на **разных директориях**:

- Agent A: `backend/app/bot/handlers/worker/`
- Agent B: `backend/app/api/routes/`
- Agent C: `mini-app/src/pages/profile/`

Координация через общий `/plan` artifact или описание в PR.

### Режим B — Опционально позже (orchestration module)

Когда понадобится автоматический gated pipeline (`orch-pipeline`, worktrees, tmux):

```powershell
# Вариант 1: security отдельным профилем (переустановка)
# Сначала backup .cursor/rules/karpathy-guidelines.mdc, git-workflow.mdc
npx ecc-install --profile developer --target cursor
# Без --with capability:security, чтобы вошёл orchestration

# Вариант 2: точечно после снятия конфликта в ECC manifest
npx ecc-install --target cursor --modules orchestration
```

**Когда ставить:** Phase 3–5, при регулярной параллельной разработке bot + API + Mini App **или** 2+ разработчиков. До Phase 2 ручной pipeline достаточен.

### Команды ECC для OutstaffingBot

| Команда | Фаза | Назначение |
|---------|------|------------|
| `/plan` | 0+ | План с confirm gate перед кодом |
| `/code-review` | всегда | Review локального diff или PR |
| `/security-scan` | 2, 8 | AgentShield + remediation plan |
| `/build-fix` | всегда | Починка сборки после ошибок |
| `/python-review` | 1+ | Python-specific review |
| `/fastapi-review` | 1+ | API layer review |
| `/react-review` | 7+ | Mini App components |
| `/test-coverage` | 1+ | Покрытие тестами |
| `/quality-gate` | pre-PR | Агрегированные gates |
| `/instinct-status` | anytime | Статус continuous-learning instincts |
| `/evolve` | periodic | Эволюция instincts → skills |
| `/ecc-guide` | onboarding | Справка по ECC |
| `/orch-add-feature` | 3+* | *Требует orchestration module |
| `/orch-build-mvp` | 0* | *Требует orchestration module |
| `/multi-plan` | 3+* | *Multi-area planning |

### Agents — когда вызывать

| Agent | Когда | Не вызывать |
|-------|-------|-------------|
| `ecc-planner` | Фича 5+ файлов, неясные зависимости | Typo, 1 handler |
| `ecc-architect` | Новый модуль, схема БД, service boundaries | CSS tweak |
| `ecc-python-reviewer` | После backend/bot изменений | До написания кода |
| `ecc-fastapi-reviewer` | После API/routes/deps | Bot-only change |
| `ecc-database-reviewer` | Migrations, индексы, N+1 | Seed data script |
| `ecc-security-reviewer` | Auth, initData, secrets, pre-deploy | Документация |
| `ecc-tdd-guide` | Новая бизнес-логика с тестами | Config-only |
| `ecc-build-error-resolver` | Build/pytest падает | Зелёная сборка |
| `ecc-react-reviewer` | Mini App UI Phase 7 | Backend-only |
| `ecc-e2e-runner` | Phase 5+ critical flows | Unit-testable logic |

В Cursor: Task tool с `subagent_type` или явный запрос «запусти ecc-python-reviewer на diff».

### Skills — auto vs explicit

| Skill | Режим | Триггер |
|-------|-------|---------|
| `python-patterns` | **Explicit** при backend | FSM, services, async |
| `fastapi-patterns` | **Explicit** при API | routes, deps, schemas |
| `postgres-patterns` | **Explicit** при БД | models, migrations, indexes |
| `frontend-patterns` | **Explicit** при Mini App | React components |
| `tdd-workflow` | **Explicit** для фич/багов | После `/plan` или по запросу |
| `verification-loop` | **Explicit** pre-PR | После реализации |
| `security-review` | **Explicit** Phase 2+ | Auth, user data |
| `security-scan` | **Explicit** Phase 8 | Pre-deploy |
| `continuous-learning-v2` | **Auto** (hooks) | SessionStart/End, Pre/PostToolUse |
| `verification-loop` | По команде `/verify`* | *если настроена |

Karpathy: skill — это **контекст**, не разрешение на 500 строк. Агент читает skill и применяет **минимально достаточное**.

### Hooks (`ECC_HOOK_PROFILE=standard`)

Автоматически из `.cursor/hooks.json`:

| Hook | Что делает |
|------|------------|
| `sessionStart` | Контекст прошлой сессии, instincts |
| `sessionEnd` | Оценка паттернов → continuous-learning |
| `beforeShellExecution` | Блок `--no-verify`; напоминание про git push review |
| `afterFileEdit` | Auto-format, TS check, console.log warning |
| `beforeReadFile` | Предупреждение при чтении `.env`, ключей |
| `beforeSubmitPrompt` | Детект секретов в промпте (sk-, ghp_, AKIA) |
| `subagentStart/Stop` | Логирование subagents |
| `stop` | Audit console.log в изменённых файлах |

Профили: `minimal` (отладка), `standard` (Phase 0–7), `strict` (Phase 8+ prod).

### continuous-learning-v2 — долгосрочная память

- Instincts накапливаются **per-project** (не смешиваются с другими репо)
- Hooks наблюдают сессии → atomic behaviors с confidence
- Команды: `/instinct-status`, `/evolve`, `/promote`, `/projects`
- **Не коммитить** `%USERPROFILE%\.cursor\ecc\` и секреты из agent data

Периодически (раз в фазу): `/instinct-status` → проверить, что instincts про OutstaffingBot релевантны (aiogram FSM, initData, service layer).

---

## E. Workflow по фазам PLAN.md

Для каждой фазы: подход, ECC, Karpathy, verification.

| Phase | Название | Подход | ECC skills/agents | Karpathy | Verification |
|:-----:|----------|--------|-------------------|----------|--------------|
| **0** | Foundation | **Оркестрация** (scaffold) | `/plan`, `ecc-architect`, `postgres-patterns`, `docker`* | Не over-engineer monorepo; только skeleton | `docker compose up`, migrations, `/start` |
| **1** | Worker Core | **Оркестрация** (3 слоя) | `tdd-workflow`, `python-patterns`, `fastapi-patterns`, reviewers | FSM = один handler file за раз | Профиль в боте → виден в Mini App |
| **2** | Employer + Jobs | **Оркестрация** | + `security-review`, `ecc-security-reviewer` | Не дублировать логику bot/API | CRUD job через Mini App → бот |
| **3** | Matching | **Solo + MAYBE perf** | `postgres-patterns`, `performance-optimizer` | Matching query — surgical, с тестом | Фильтр категории работает |
| **4** | Applications | **Solo** | `tdd-workflow` (overlap tests) | Conflict check — один service | Нельзя 2 пересекающиеся смены |
| **5** | Notifications | **MAYBE** | `error-handling`, ARQ patterns* | Idempotency keys — минимально | Push за 30s |
| **6** | Group Posting | **Solo** | `python-patterns` | Один posting service | Пост в тестовой группе |
| **7** | Mini App Polish | **Solo** (UI) | `frontend-patterns`, `ecc-react-reviewer` | Не трогать backend без нужды | Full journey в Mini App |
| **8** | Production Deploy | **Оркестрация** | `/security-scan`, `deployment-patterns`* | Infra changes — отдельные PR | SSL, uptime 24h |
| **9** | Admin | **Solo** | `python-patterns` | Admin handlers — изолированно | Audit log пишется |
| **10** | Enhancements | **По фиче** | `/plan` per enhancement | Каждое улучшение — отдельная ветка | Feature-specific tests |

**Паттерн verification-before-completion** (все фазы):

```
1. [Шаг] → verify: <конкретная команда>
2. Не заявлять «готово» без зелёных тестов / ручной проверки из PLAN.md
3. `verification-loop` перед PR
```

---

## F. Multi-agent patterns для OutstaffingBot

### Пример 1: «Implement worker registration»

```
/plan «FSM регистрация работника + API profile + Mini App страница»
  ↓ confirm
ecc-architect (readonly)
  → service layer: WorkerService.create_or_update
  → bot FSM states в bot/states/worker.py
  ↓
Agent 1: backend/app/bot/handlers/worker/registration.py
Agent 2: backend/app/api/routes/workers.py + schemas
Agent 3: mini-app/src/pages/Profile.tsx
  ↓ (последовательно или параллельно — разные папки)
ecc-python-reviewer  →  bot + services
ecc-fastapi-reviewer  →  API only
  ↓
verification-loop: pytest + manual initData test
/code-review
```

**НЕ вызывать** отдельного агента для CSS, если правки в рамках существующих компонентов.

### Пример 2: «Deploy to production» (Phase 8)

```
/plan «production deploy checklist»
  ↓
security-scan (AgentShield)
ecc-security-reviewer (initData, secrets, IDOR)
  ↓
Implement: nginx, webhook, docker-compose.prod
  ↓
verification-loop:
  - curl /health, /ready
  - SSL check
  - 24h smoke
```

### Пример 3: «Fix shift overlap bug» — solo, без оркестрации

```
1. Написать failing test: test_overlap_rejected
2. Surgical fix в application_service.py
3. ecc-python-reviewer
4. commit по запросу
```

---

## G. Anti-patterns

| Anti-pattern | Почему плохо | Что делать |
|--------------|--------------|------------|
| Оркестрация 3-line fix | Overhead > value | Composer / direct agent |
| `npx ecc-install --profile full` | Bloat, нерелевантные skills | `developer` + точечные `--with` |
| Игнор Karpathy → 500-line PR | Review hell, скрытые баги | Разбить на PR; surgical per concern |
| Параллельные agents на одном файле | Merge conflicts, дубли | Один agent на файл/папку |
| `/orch-add-feature` без orchestration module | Skill не найден | Ручной pipeline §D |
| Commit без запроса пользователя | Нарушение git-workflow | Ждать явного «закоммить» |
| `--no-verify` | Обход quality gates | Hooks блокируют |
| Дублировать bot/API логику | Рассинхрон | Единый service layer (PLAN §B.3) |
| Security только в Phase 8 | Auth/initData с Phase 1 | `security-review` с Phase 2 |
| План без confirm gate | Scope creep | `/plan` → wait for yes |

---

## Быстрая шпаргалка (1 экран)

```
Задача → ≤3 файла? → Agent solo + skill
       → bot+API+UI? → /plan → architect → parallel agents → reviewers
       → deploy?     → security-scan orchestration

Всегда: Karpathy (мало, точно, verify)
Никогда: full ECC, parallel same file, commit без запроса
Память: continuous-learning-v2 (авто)
Детали install: ECC_STRATEGY.md
Git: GIT_WORKFLOW.md
```

---

*Документ создан 2026-06-20. Отражает установку ECC без orchestration module; обновлять при изменении `.cursor/ecc-install-state.json`.*
