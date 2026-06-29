# Задачи OutstaffingBot

> **Онбординг Dev2:** [ONBOARDING_DEV2.md](./ONBOARDING_DEV2.md)  
> **Единый чеклист** всех фаз разработки. Детали архитектуры — в [PLAN.md](./PLAN.md), как выполнять каждую фазу — в [DEVELOPMENT_WORKFLOW.md § E](./DEVELOPMENT_WORKFLOW.md#e-workflow-по-фазам-planmd).

## Как пользоваться этим файлом

1. **Открывайте этот файл первым**, когда ищете «что делать дальше» — здесь все checkbox-задачи Phase 0–10 в одном месте.
2. **Текущая фаза** — та, где есть незакрытые пункты. Сейчас это **Phase 7**.
3. **Отмечайте прогресс** — меняйте `[ ]` на `[x]` по мере выполнения (и синхронизируйте с [PLAN.md § F](./PLAN.md#f-roadmap--фазы-реализации), если правите roadmap там).
4. **Перед началом фазы** — прочитайте строку для этой фазы в [DEVELOPMENT_WORKFLOW.md § E](./DEVELOPMENT_WORKFLOW.md#e-workflow-по-фазам-planmd): solo vs оркестрация, skills, verification.
5. **Для ECC/setup** — дополнительный чеклист Phase 0 в [ECC_STRATEGY.md § 9](./ECC_STRATEGY.md#9-чеклист-phase-0-ecc).

---

## Текущая фаза: Phase 7 — Mini App Polish

**Следующий шаг:** UI/UX всех экранов, deep links / haptic / theme, metro search (Phase 7).

**Dev2 sync (2026-06-23):** selective port из `feature/phase-9-10` (PR #10) — reviews API, geo/haversine, employer push, контакты после accept, worker verification. PR #9, #2, #3, #10 закрыты как superseded. Dev2: rebase от main, продолжить Phase 7 metro search и 9.10–9.11 Mini App.

**Dev2 Phase 7/8:** cherry-pick в main (544d800–97aa832) — webhook/Sentry/backup, fix 500 отклика, theme/haptic; inbox и Phase 6 — отдельные коммиты Nikita.

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

- [x] FSM создание заявки (бот)
- [x] API: CRUD jobs, shift_slots
- [x] Mini App: форма создания заявки
- [x] Статусы draft/active/cancelled

**Verification:** employer создаёт заявку через Mini App → видна в боте.

**Как выполнять:** оркестрация + `security-review`, `ecc-security-reviewer`.

---

### Phase 3 — Matching + Search (1–2 недели) [P0]

- [x] Matching service + SQL queries
- [x] Manual search filters (бот + API + Mini App)
- [x] Список вакансий с пагинацией

**Verification:** worker с категорией «официант» по умолчанию видит все активные вакансии (подходящие сверху); при отключении «Показывать все вакансии» — только релевантные.

**Как выполнять:** solo + maybe perf — `postgres-patterns`, `performance-optimizer`.

---

### Phase 4 — Applications + Conflict Prevention (1 неделя) [P0]

- [x] Apply / cancel application
- [x] Shift overlap check
- [x] UX ошибки конфликта

**Verification:** нельзя принять 2 пересекающиеся смены без отмены.

**Как выполнять:** solo — `tdd-workflow` (overlap tests).

---

### Phase 5 — Notifications + Background Jobs (1–2 недели) [P1]

- [x] ARQ worker setup
- [x] Push при новой заявке
- [x] Worker preferences (категории, ставка, metro)
- [x] Global notification toggle

**Verification:** новая заявка → push matching workers within 30s.

**Как выполнять:** maybe оркестрация — `error-handling`, ARQ patterns.

---

### Phase 6 — Group Posting (1 неделя) [P1]

- [x] Admin: register telegram groups (только в группе: /register_group → «Группа привязана»)
- [x] Auto-post formatted messages
- [x] Кнопка «Откликнуться» → deep link `start=job_{id}` → бот → профиль → отклик
- [x] Edit on close
- [x] При снятии отклика — переоткрыть пост в группе (если заявка active и набор не закрыт)
- [x] При наборе нужного числа людей — автозакрытие поста в группе

**Verification:** заявка появляется в тестовой группе с кнопкой отклика; после набора людей пост закрывается; после отмены отклика — снова открывается.

**Как выполнять:** solo — `python-patterns`.

---

### Phase 7 — Mini App Polish (2 недели) [P1]

- [ ] Полный UI/UX всех экранов
- [x] Deep links (Nikita), haptic, theme (Dev2 lib/telegram)
- [x] Employer inbox (accept/reject applications)
- [ ] **Metro search (Mini App):** поиск станций по подстроке, без учёта регистра, многословные названия [P1]
  - **Проблема:** сейчас поиск в Mini App фактически работает только по первому слову и чувствителен к регистру — UX сломан.
  - **Acceptance criteria:**
    - Запрос `сокол` находит «Сокольники»; `НОВО` — «Новокузнецкая» и др. с подстрокой в названии.
    - Многословные станции: `площадь револю` → «Площадь Революции» (поиск по всей строке `name`, не только первому токену).
    - API `GET /reference/metro?q=` и Mini App (Profile, CreateJob, VacancyList, NotificationsSettings) используют одну логику; debounce и min length ≥ 2 сохранены.
    - Unit/integration-тесты на `search_metro_stations` с кейсами case-insensitive и multi-word.
  - **Слой:** backend (`worker_service.search_metro_stations`) + при необходимости фронт; см. [PLAN.md § C.8](./PLAN.md#8-rest-api-для-mini-app).

**Verification:** полный user journey без бота (только Mini App); metro autocomplete находит станции по части названия в любом регистре.

**Как выполнять:** solo (UI) — `frontend-patterns`, `ecc-react-reviewer`; metro search — `postgres-patterns`, `tdd-workflow`.

---

### Phase 8 — Production Deploy (1 неделя) [P1]

- [ ] VPS setup, nginx, TLS
- [x] Webhook mode (код в main; staging health mode=webhook)
- [ ] systemd/Docker production config
- [x] Backup scripts, logging_config, Sentry SDK (DSN в .env — при настройке)

**Verification:** production URL, SSL, uptime 24h.

**Как выполнять:** оркестрация — `/security-scan`, `deployment-patterns`.

---

### Phase 9 — Admin + Moderation (2–3 недели) [P1/P2]

> **Wordlists (открытые + кастом):** [badwords-py](https://github.com/FlacSy/BadWords) (MIT), [readme-SVG/Banned-words](https://github.com/readme-SVG/Banned-words) (Apache-2.0), Krugozor/RussianBadWords, CensureBlock, hacking-buds, kugimiya banlist + custom. **Файлы в репо:** [`backend/data/moderation/`](../backend/data/moderation/) — `stop_words_profanity.txt`, `stop_words_sex.txt`, `stop_words_drugs.txt`, `stop_words_translit.txt`, `allow_words_alcohol.txt`; пересборка: `python build_wordlists.py`. Детали — [moderation/README.md](../backend/data/moderation/README.md), нормализация — [PLAN.md § 10.1](./PLAN.md#101-content-moderation--compliance).

#### 9.1 Content Moderation — базовый pipeline [P0]

- [x] Сервис модерации: нормализация текста → проверка по объединённым wordlists → результат (ok / violation + matched term + field)
  - **Acceptance criteria:**
    - Единая точка входа для полей заявки/профиля: `description`, `contact_info`, `venue_name`, опыт работника и т.д.
    - Wordlists загружаются из [`backend/data/moderation/stop_words_*.txt`](../backend/data/moderation/); escort-список (`stop_words_sex.txt`) **остаётся** активным; alcohol-whitelist — `allow_words_alcohol.txt` (Phase 9.5).
    - Легитимная alcohol-тематика не блокируется **в любой категории** (см. 9.5).
    - Покрытие unit-тестами: чистый текст, явный мат, obfuscation, translit.

#### 9.2 Brackets / special chars — pattern rules (не слепое удаление) [P0]

- [x] Разделить **обфускацию** и **легитимные** скобки; нормализовать только для матчинга, исходный текст пользователю не портить
  - **Правила обфускации (normalize for matching):**
    - Внутри слова: `SE[X` → `sex`, `зак[лад]ка` → `закладка`, `п[и]дор` → `пidor` — удалить `[`, `]`, `{`, `}` **между буквами одного токена**.
    - Разделители внутри токена: `.`, `-`, `_`, `|` между буквами одного слова (кроме осмысленных аббревиатур) — схлопнуть для матчинга.
    - Leetspeak / homoglyphs: `@→a`, `0→o`, `$→s` и т.п. — только в moderation-normalize, не в сохранённом тексте.
  - **Легитимные (не трогать при сохранении; при матчинге — опционально strip только внешние скобки целиком):**
    - Описание: `(удобный график)`, `(опыт приветствуется)`, `(м. рядом)`.
    - Адрес / venue: `(стр. 2)`, `(корп. 3)`, `(д. 5)`, `(лит. А)`.
    - Обычные круглые скобки вокруг **целой фразы** (regex: `\([^)]{3,}\)` не разбивающая одно слово) — не считать obfuscation.
  - **Acceptance criteria:** тесты на obfuscation-кейсы блокируются; легитимные описания с адресными скобками проходят; регрессия на «зак[лад]ка в описании» — violation.

#### 9.3 Translit detection [P0]

- [x] Расширить normalization: латиница, имитирующая русский мат/наркотики
  - **Примеры для словаря/правил:** `GOVNO`, `PIDOR`, `Mephedron`, `HUY`, `BLYAT`, `suka`, `pizda` → каноническая кириллица перед wordlist-match.
  - **Acceptance criteria:** translit-варианты ловятся так же, как кириллические; false positive на латинские бренды/IT-термины минимизирован whitelist-ом контекста (имена компаний в `venue_name` — отдельный кейс в тестах).

#### 9.4 contact_info — ослабление модерации [P1]

- [x] Перед wordlist-check разбить `contact_info` на сегменты; **email** и **@telegram** сегменты не прогонять через stop_words
  - **Правила сегментации:**
    - Email: RFC-подобный паттерн `local@domain`.
    - Telegram: `@username`, `t.me/username`, `https://t.me/...`.
    - Остальной текст (телефон, произвольный комментарий) — полная модерация.
  - **Acceptance criteria:** `contact@bar.ru` и `@employer_spb` не дают ложных срабатываний; мат в свободном тексте контакта по-прежнему блокируется.

#### 9.5 Category whitelist — alcohol [P1]

- [x] Алкогольная тематика **разрешена на всей платформе** для легитимных заявок на работу — **во всех категориях**, не только bar / bartender (бар, коктейли, алкогольное меню, винный бар, сомелье и т.д.)
  - Escort / prostitution wordlist **без изменений**.
  - Убрать alcohol-related термины из block-листов (или не применять блокировку по ним): легитимные упоминания алкоголя не должны давать false positive в **любой** категории.
  - **Acceptance criteria:** заявки с формулировками «бармен, коктейли, алкогольное меню», «сомелье, винная карта» и аналогичными проходят **в любой категории**; escort-формулировки по-прежнему блокируются.

#### 9.6 Violation threshold + persistence [P0]

- [x] Счётчик нарушений на пользователя (`telegram_id`); после **N** нарушений (env `MODERATION_VIOLATION_THRESHOLD`, default 3) — статус «требует review admin»
  - Таблица/модель `moderation_violations`: `user_id`, `telegram_id`, `field`, `raw_snippet`, `matched_term`, `normalized_snippet`, `source` (bot/mini-app/api), `created_at`.
  - **Acceptance criteria:** каждое срабатывание логируется; порог N настраивается; API/бот возвращают понятное сообщение пользователю без утечки полного wordlist.

#### 9.7 Admin: violation log & user ban [P0]

- [x] Просмотр логов и блокировка по Telegram ID — команды бота (`/moderation_queue`, `/violation_log`, `/block_user`) **и** вкладка «Модерация» в Mini App admin (`/admin/moderation/*`)
  - Команды (или подменю `/admin`): список пользователей с violations ≥ N, детализация по `telegram_id`, `/admin block_user <telegram_id>`, `/admin unblock_user <telegram_id>`.
  - Admin видит примеры срабатываний (snippet + matched term + дата), принимает решение о блокировке.
  - Заблокированный пользователь: создание заявок/откликов запрещено; сообщение «аккаунт заблокирован».
  - **Acceptance criteria:** admin из whitelist видит лог; block/unblock идемпотентны; блок проверяется в middleware/service layer; audit запись в `audit_log`.

#### 9.8 Admin — базовое (из roadmap) [P2]

- [x] Admin commands (`/admin stats`, …)
- [x] Employer verification
- [x] Audit log (create/update; включая moderation actions)

#### 9.9 Жалобы и нарушения по заявкам (Complaints) [P1]

> **Контекст:** сейчас нарушения контента (`moderation_violations`) и действия админа (`audit_log`) разнесены; жалоб по заявкам (опоздание, невыход, неоплата, отсутствие работы) **нет**. Вкладка «Журнал» в Mini App admin — один плоский audit-лист ([`AdminPanelPage.tsx`](../mini-app/src/pages/AdminPanelPage.tsx)). Модели: `Application` (worker + `job_request_id` + `shift_slot_id`), `JobRequest` → `Employer.company_name`; отклики employer — `GET /employer/applications`, `GET /employer/jobs/{id}/applications`.
>
> **План реализации (архитектура):**
>
> | Слой | Решение |
> |------|---------|
> | **Data model** | Таблица `application_complaints` (или `complaints`): `id`, `application_id` (FK, NOT NULL), `job_request_id` (FK, денорм. для фильтров), `shift_slot_id` (FK), `reporter_user_id`, `reporter_role` (`worker` / `employer`), `target_user_id` (обвиняемый: user работника или user работодателя), `violation_type` enum, `description` (TEXT), `status` (`open` / `under_review` / `resolved` / `dismissed`), `admin_notes`, `resolved_at`, `resolved_by_telegram_id`, `created_at`. Индексы: `(violation_type, created_at)`, `(job_request_id)`, substring на `company_name` через join или денорм. |
> | **Violation types** | `late` (опоздание), `no_show` (невыход на смену), `no_payment` (отсутствие оплаты), `no_work` (отсутствие работы / работа не предоставлена). UI-лейблы на русском в enum-map. |
> | **Связь с заявкой** | Жалоба **всегда** на конкретный `application_id` (конкретный работник + смена + заявка). Employer выбирает заявку → список откликов → конкретный worker/application. Worker выбирает свой отклик (application) на заявку работодателя. |
> | **Правила доступа** | Worker: только свои `applications`; target = employer.user. Employer: только отклики на свои `job_requests`; target = worker.user. Заблокированные пользователи — 403. MVP: жалоба только если `application.status == accepted`; P2 — разрешить pending для `no_work`. |
> | **Дедупликация** | MVP: одна открытая жалоба `(application_id, reporter_user_id, violation_type)`; повтор — 409 с подсказкой. |
> | **Модерация текста** | **Исключение из pipeline:** текст `description` жалобы **не публичный** — видят только reporter, admin и involved parties. Стоп-слова и `content_moderation_service` применяются к **публичным** поверхностям (заявки, профили, публичные сообщения). Для complaints pipeline **полностью пропускается**: нет reject по stop-words, нет записей в `moderation_violations` для текста описания жалобы. Допустима только валидация формата (min length для worker, max length). |
> | **Audit** | `complaint.created`, `complaint.status_change` (resolve/dismiss) в `audit_log` с `entity_type=application_complaint`, `entity_id`, `application_id`, `violation_type`. |
> | **Отделение от stop-words** | Stop-word нарушения — `moderation_violations` (только публичный контент); жалобы по заявкам — `application_complaints` (приватный контент, **без** пересечения с moderation pipeline). Admin «Журнал» — разные подвкладки (см. 9.11). Вкладка «Модерация» — очередь flagged users (без изменений). |
>
> **Сбор данных (UX):**
> - **Работодатель:** нав «Пожаловаться» → список своих заявок (`title`, дата, статус) → экран заявки → список откликов (имя работника, смена, статус отклика) → форма: тип нарушения (4 radio) + необязательное описание → submit.
> - **Работник:** нав «Пожаловаться» → список своих откликов (название заявки, **company_name**, смена, статус; **без** данных других работников) → форма: тип + **обязательное** описание → submit.
> - **Admin:** подвкладка «Нарушения по заявкам» — таблица/лист с фильтрами (тип, период, поиск по `company_name`), карточка: reporter role, тип, описание, ссылки на application/job, действия resolve/dismiss + notes.
>
> **API (черновик):**
> - Worker: `GET /complaints/my-context` (eligible applications + company_name), `POST /complaints` `{ application_id, violation_type, description }`.
> - Employer: `GET /employer/complaints/jobs` (заявки с count откликов), `GET /employer/complaints/jobs/{job_id}/applications`, `POST /employer/complaints` `{ application_id, violation_type, description? }`.
> - Admin: `GET /admin/journal/stop-words?from=&to=&telegram_id=&limit=` (из `moderation_violations`), `GET /admin/audit` (как сейчас), `GET /admin/journal/application-violations?violation_type=&from=&to=&company_q=&limit=`, `GET /admin/complaints/{id}`, `PATCH /admin/complaints/{id}` `{ status, admin_notes }`.
>
> **Phasing:**
> - **MVP (9.9–9.11):** таблица + ручные жалобы в Mini App + admin журнал с фильтрами + audit; без бота.
> - **P2:** уведомление админу (push/Telegram) при новой жалобе; экспорт CSV; статистика по типам в «Статистика».
> - **P3:** автоматические сигналы (check-in опоздания, подтверждение оплаты работодателем, attendance); рейтинги (Phase 10).

- [x] **9.9.1** Миграция + модели: `ApplicationComplaint`, enums `ComplaintViolationType`, `ComplaintReporterRole`, `ComplaintStatus` [P0]
  - **Acceptance criteria:** Alembic revision; FK на `applications`, `job_requests`, `shift_slots`, `users`; уникальный partial index на открытые дубликаты; downgrade работает.

- [x] **9.9.2** `complaint_service`: создание, валидация прав, дедупликация, resolve/dismiss [P0]
  - **Acceptance criteria:** worker не может жаловаться на чужой application (404/403); employer — только на свои jobs; `description` worker min 20 символов; employer description optional; **без** вызова `content_moderation_service` / stop-words (текст жалобы приватный, не логируется в `moderation_violations`); unit-тесты на IDOR и дедуп.

- [x] **9.9.3** API worker + employer (`/complaints`, `/employer/complaints/*`) [P0]
  - **Acceptance criteria:** Pydantic schemas; `company_name` в eligible applications для worker; OpenAPI; integration-тесты happy path + forbidden; `POST` с description, содержащим stop-слова, — 201 без записи в `moderation_violations`.

- [x] **9.9.4** API admin: список/деталь/resolve жалоб по заявкам [P1]
  - **Acceptance criteria:** фильтры `violation_type`, `from`/`to` (ISO date), `company_q` (substring, case-insensitive); пагинация `limit`/`offset`; только `get_current_admin`.

- [x] **9.9.5** Audit: `complaint.created`, `complaint.status_change` [P1]
  - **Acceptance criteria:** записи в `audit_log` при create и resolve/dismiss; labels в `AdminPanelPage` AUDIT_ACTION_LABELS.

#### 9.10 Mini App — «Пожаловаться» (Worker & Employer) [P1]

> **UX (контекстный flow):** отдельная вкладка «Пожаловаться» убрана. Worker: **Отклики** → отклик (принят) → «Пожаловаться». Employer: **Заявки** → заявка → принятые работники → «Пожаловаться».

- [x] **9.10.1** Worker: «Пожаловаться» из детали принятого отклика в [`MyApplicationsPage.tsx`](../mini-app/src/pages/MyApplicationsPage.tsx) [P1]
  - **Acceptance criteria:** список откликов → drill-down → для `accepted` кнопка «Пожаловаться» → форма (4 типа + описание); success/error; haptic; описание **не** блокируется стоп-словами.

- [x] **9.10.2** Employer: «Пожаловаться» из детали заявки в [`EmployerJobsPage.tsx`](../mini-app/src/pages/EmployerJobsPage.tsx) [P1]
  - **Acceptance criteria:** список заявок → деталь заявки → принятые работники → форма жалобы; имя работника из отклика; описание **не** блокируется стоп-словами.

- [x] **9.10.3** API client [`client.ts`](../mini-app/src/api/client.ts): типы и методы complaints [P1]
  - **Acceptance criteria:** типы `ComplaintViolationType`, `ComplaintRead`; методы list/create для worker и employer.

- [x] **9.10.4** Общий компонент формы [`ComplaintForm.tsx`](../mini-app/src/components/ComplaintForm.tsx) [P1]

#### 9.11 Admin — реструктуризация вкладки «Журнал» [P1]

> Текущая вкладка «Журнал» (`audit`) заменяется на **подвкладки**: **Стоп-слова** | **Журнал действий** | **Нарушения по заявкам**. Вкладка «Модерация» (очередь flagged users) **не** переносится.

- [ ] **9.11.1** API `GET /admin/journal/stop-words` — лог `moderation_violations` [P1]
  - **Acceptance criteria:** поля: дата, telegram_id/username, field, matched_term, snippet (truncate), source; фильтры `from`/`to`, `telegram_id`; limit ≤ 100; не смешивать с complaints.

- [ ] **9.11.2** UI: подвкладки «Журнал» в [`AdminPanelPage.tsx`](../mini-app/src/pages/AdminPanelPage.tsx) [P1]
  - **Acceptance criteria:**
    - **Стоп-слова** — список из 9.11.1 (не очередь review).
    - **Журнал действий** — текущий `AuditTab` без регрессии.
    - **Нарушения по заявкам** — список complaints + фильтры: тип нарушения, дата (from/to), поиск по названию компании; карточка с resolve/dismiss; **не** смешивать с `moderation_violations` (жалобы — приватный контент, вне stop-word pipeline).
  - **Partial (2026-06):** карточки «Статистика» кликабельны — drill-down списки workers/employers/jobs/blocked; «На верификации»/«На модерации» → вкладки; «Нарушения» → список complaints (без фильтров/resolve).

- [ ] **9.11.3** (P2) Пагинация и «загрузить ещё» для всех трёх подвкладок [P2]
  - **Acceptance criteria:** offset/limit на API; кнопка «Ещё» без дублирования записей.

**Verification (9.9–9.11):** работник подаёт жалобу на принятый отклик → записи в `application_complaints` и audit; работодатель жалуется на конкретного работника по заявке; admin видит жалобу в «Нарушения по заявкам» с фильтром по компании; stop-word срабатывание на **публичном** контенте видно в «Стоп-слова», не в complaints; текст жалобы со stop-словами создаётся успешно, без записи в `moderation_violations`; IDOR-тесты проходят.

**Verification (Phase 9 целиком):** заведомо запрещённый текст блокируется с логом; после N попыток user попадает в admin-очередь; admin блокирует по ID; легитимные alcohol-формулировки проходят в любой категории; contact с @telegram не даёт false positive; `/admin_stats` показывает счётчики; `/verify_employer` верифицирует работодателя (без verify — заявка остаётся в draft); audit_log записывает block/unblock и verify; жалобы по заявкам и трёхсекционный журнал работают (9.9–9.11).

**Как выполнять:** solo — `python-patterns`, `security-review`; wordlists — отдельный модуль + `tdd-workflow`; 9.9–9.11 — оркестрация (API + Mini App), `tdd-workflow`, `security-review` на IDOR.

---

### Phase 10 — Enhancements [P3]

- [x] Geo matching (haversine по metro lat/lon, city filter, max_distance_km)
- [x] Employer push (новые подходящие работники при регистрации — ARQ `notify_employers_for_worker`)
- [x] Рейтинги / отзывы (API `/reviews`, review_service; Mini App UI — partial)
- [x] Контакты worker/employer после accept (phone, Telegram)
- [x] Worker verification (поле `workers.verified`, admin verify API)
- [ ] Multi-city support (UI + seed городов)
- [ ] Analytics dashboard

**Как выполнять:** по фиче — `/plan` per enhancement, отдельная ветка на каждое улучшение.

---

## Быстрая навигация

| Документ | Что там |
|----------|---------|
| **[TASKS.md](./TASKS.md)** (этот файл) | **Единый чеклист задач** Phase 0–10 |
| [TASKS.md § Phase 9](./TASKS.md#phase-9--admin--moderation-23-недели-p1p2) | Content Moderation, violation log, admin ban |
| [TASKS.md § 9.9–9.11](./TASKS.md#99-жалобы-и-нарушения-по-заявкам-complaints-p1) | Жалобы по заявкам, «Пожаловаться», журнал admin (3 подвкладки) |
| [PLAN.md § 10.1](./PLAN.md#101-content-moderation--compliance) | Архитектура модерации и wordlists |
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
