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
- [x] **Playwright E2E scaffold:** mobile (Pixel 5) + desktop (Chrome), visual snapshots, mock Telegram initData + API
  - **2026-07-10:** `mini-app/e2e/` — guest landing, role picker, worker vacancy list/detail; `npm run e2e`
  - **2026-07-10:** расширенный suite `e2e/scenarios/{worker,employer,shared}/` — 48 сценариев × 3 viewport (144 passed); см. `mini-app/e2e/README.md`
  - **Runbook:** [E2E_VISUAL_TESTING_PLAN.md](./E2E_VISUAL_TESTING_PLAN.md) — локальный ПК + CI без физического телефона
- [ ] **Playwright E2E scenarios M1–M6:** CreateJob, custom verify, profile experience, employer flows (см. [CATEGORY_TAXONOMY.md § Manual QA](./CATEGORY_TAXONOMY.md#manual-qa--e2e-scenarios))
  - **2026-07-10:** Playwright покрывает M1/M3 и большую часть employer/worker UI; остаётся M2 custom+verify, M4 bot, M5 search filter, M6 matching
- [ ] **Real Telegram E2E (Maestro + Android AVD):** smoke → M1–M3 flows → API/DB/logs verify; nightly/pre-release (не blocking PR)
  - **План:** [E2E_REAL_TELEGRAM_PLAN.md](./E2E_REAL_TELEGRAM_PLAN.md) — Phase 0–5; scaffold `e2e-mobile/flows/smoke-open-miniapp.yaml`
  - **Phase 0 (инфра):** [e2e-mobile/SETUP.md](../e2e-mobile/SETUP.md) + scripts `check-prerequisites`, `install-maestro`, `start-emulator`, `run-smoke`
  - [x] Phase 0 repo artifacts: scripts, `config.yaml`, `.env.e2e.example`, `SETUP.md`, smoke flow scaffold
  - [x] Phase 0 manual: Android Studio + AVD, Telegram test account, первый успешный smoke на AVD (2026-07-11, Maestro `smoke-open-miniapp.yaml` passed)
  - [ ] WebView Debug в Telegram (опционально, для отладки Mini App)
  - **iPhone на Windows:** автоматизация невозможна (XCUITest = macOS); manual QA или Mac/Cloud в Phase 5
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

> **Wordlists:** [`backend/data/moderation/`](../backend/data/moderation/) — profanity, sex, drugs, translit, **`stop_words_slang_manual.txt`** (9.3.4), `allow_words_alcohol.txt`; пересборка `python build_wordlists.py`. **Lemma:** runtime 9.3.1, build-time 9.3.5. **Translit:** фонетика 9.3 `[x]`, visual homoglyph 9.3.2 `[x]`. Детали — [moderation/README.md](../backend/data/moderation/README.md), [PLAN.md § 10.1](./PLAN.md#101-content-moderation--compliance).

#### 9.3 Moderation pipeline — roadmap (lemma + slang + translit)

> **Оценка:** ~3–4 дня solo с тестами. **Два типа translit:** фонетический (`GOVNO`, `HUY` — 9.3) и **visual homoglyph** (`Хyй`, `Пиздa` — 9.3.2).

| Фаза | ID | Приоритет | Статус | Суть |
|------|-----|-----------|--------|------|
| 0 | [9.3.0](#930-подготовка-lemma--slang) | P0 | `[x]` | pymorphy3, `moderation_lemmatizer.py`, README |
| 1 | [9.3.1](#931-lemma-layer-runtime-pymorphy3-p0) | P0 | `[x]` | Runtime lemma в `_find_violation` |
| 2 | [9.3.4](#934-slang-wordlist-layer-manual--sources-p0) | P0 | `[x]` | `stop_words_slang_manual.txt`, exact-only |
| 3 | [9.3.5](#935-lemma-canonicalization-в-build_wordlists-p1) | P1 | `[x]` | `build_wordlists.py`: imported / slang / lemma buckets |
| 4 | [9.3.6](#936-moderation-при-create-не-только-publish-p1) | P1 | `[x]` | Moderation при `POST /employer/jobs` |
| — | [9.3.2](#932-visual-homoglyph-translit-p0) | P0 | `[x]` | Translit по **виду** буквы (отдельно от звука) |
| — | [9.3.3](#933-allow-latin-in-public-text-fields-p1) | P1 | `[x]` | Снять blanket `reject_latin`, EN-бренды |

**Порядок match (целевой):** obfuscation → **visual homoglyph** → **phonetic translit** → exact (фразы + `slang_manual`) → **lemma** → block.

**Структура файлов после гибрида:**

```
backend/data/moderation/
├── stop_words_profanity.txt      # lemma-canonical после 9.3.5
├── stop_words_drugs.txt
├── stop_words_sex.txt
├── stop_words_translit.txt       # exact only, фонетика
├── stop_words_slang_manual.txt   # NEW 9.3.4 — exact only, без lemma
├── allow_words_alcohol.txt
├── build_wordlists.py
└── _sources/
```

**Риски:**

| Риск | Решение |
|------|---------|
| False positive (`фен`, `кокс`) | `EXCLUDE_FALSE_POSITIVES` + alcohol whitelist |
| pymorphy ломает сленг | slang только в `slang_manual`, проверка до lemma |
| Размер словаря | Dedupe лемм при сборке (9.3.5) |
| Производительность | `@lru_cache` на lemma; wordlists в `frozenset` |
| Латиница в брендах | 9.3.3 + `_COMPANY_BRAND_TERMS`; мат — visual/phonetic translit |

**Источники сленга / wordlists** (пересборка `build_wordlists.py`):

| Источник | Путь / URL | Назначение |
|----------|------------|------------|
| Krugozor RussianBadWords | `_sources/krugozor_stopwords.php` | «Наркоманский жаргон», препараты, площадки |
| kugimiya «Банлист Алисы» | `_sources/kugimiya_banlist.yaml` | Regex-roots sex/drugs |
| CensureBlock ex-ussr | `_sources/censureblock_ex_ussr.txt` | Корни эскорт/мат |
| hacking-buds | `_sources/bad_terms.csv` | Prostitution/trafficking фразы |
| readme-SVG Banned-words | `_sources/ru_banned_readme_svg.txt` | Мат RU (Apache-2.0) |
| badwords-py | PyPI / `_sources/badwords_core_api.json` | RU profanity (MIT) |
| LDNOOBW (опционально) | [List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words) | CC-BY-4.0; `ru` — только с фильтрацией + review |
| pymorphy3 | PyPI | Леммы runtime (9.3.1) и build (9.3.5); **не** pymorphy2 |

**Не брать слепо:** Jigsaw / форумные списки — много false positives; только через `EXCLUDE_FALSE_POSITIVES` + ручной review.

#### 9.3.0 Подготовка (lemma + slang) [P0]

- [x] Зафиксировать контракт pipeline, не ломая текущие тесты
  - `pymorphy3` + `pymorphy3-dicts-ru` в `pyproject.toml`
  - `backend/app/services/moderation_lemmatizer.py` — lazy `MorphAnalyzer`, `@lru_cache` на `lemma(token)`
  - `backend/data/moderation/README.md` — слои и порядок проверки
  - **Verify:** `pytest tests/test_content_moderation.py` зелёный до/после изменений lemma-слоя

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

- [x] Расширить normalization: латиница, имитирующая русский мат/наркотики (**фонетический** translit)
  - **Примеры для словаря/правил:** `GOVNO`, `PIDOR`, `Mephedron`, `HUY`, `BLYAT`, `suka`, `pizda` → каноническая кириллица перед wordlist-match.
  - **Acceptance criteria:** translit-варианты ловятся так же, как кириллические; false positive на латинские бренды/IT-термины минимизирован whitelist-ом контекста (имена компаний в `venue_name` — отдельный кейс в тестах).

#### 9.3.1 Lemma layer (runtime, pymorphy3) [P0]

- [x] Лемматизация кириллических токенов перед wordlist-match (`гашиша` → `гашиш`)
  - Модуль: `app/services/moderation_lemmatizer.py`; зависимости: `pymorphy3`, `pymorphy3-dicts-ru`.
  - Файлы: `content_moderation_service.py`, `moderation_lemmatizer.py`, `test_content_moderation.py`.
  - Алгоритм `_find_violation`: после `normalize_for_matching` + alcohol mask — **exact whole-word** → для токенов с кириллицей **lemma** ∈ `block_terms`.
  - Порядок (фаза 1): exact match → lemma match.
  - **Acceptance criteria:**
    - `Разбивка гашиша` → block, term `гашиш`
    - `продажа героина` → block (lemma)
    - `бармен` + alcohol whitelist → pass
    - `косяк` → block (exact в drugs; после 9.3.4 — через `slang_manual`)
    - регрессия `test_content_moderation.py` зелёная; deploy с pymorphy3 на staging

#### 9.3.4 Slang wordlist layer (manual + sources) [P0]

- [x] **Фаза 2:** отдельный exact-match слой для жаргона, который **не лемматизируется**
  - **Файл:** `backend/data/moderation/stop_words_slang_manual.txt` — только exact match; **не** прогонять через pymorphy при сборке.
  - **Приоритет:** slang_manual + многословные фразы → lemma → profanity/drugs/sex/translit.
  - **Что класть в manual slang:**
    - Нарко-жаргон: `косяк`, `шмаль`, `заклад`, `торч`, `дозняк`, `барыга`
    - Фразы: `vip девушки`, `массаж 18`, `интим услуги`
    - EN slang (без дубля translit): `mephedrone`, `spice`, `darknet` — где нет в `stop_words_translit.txt`
    - Обфускация — уже в translit; дубли не нужны
  - **Источники** (`build_wordlists.py`): Krugozor «Наркоманский жаргон», `SLANG_MANUAL_SEED`; см. таблицу источников в [9.3 roadmap](#93-moderation-pipeline--roadmap-lemma--slang--translit).
  - **Acceptance criteria:** `косяк`, `шмаль`, `vip девушки` блокируются; `EXCLUDE_FALSE_POSITIVES` (`фен`, `кокс`) — регрессия зелёная; README обновлён.

#### 9.3.5 Lemma canonicalization + пересборка словарей [P1]

- [x] **Фаза 3:** пайплайн `build_wordlists.py` — три bucket:
  - `imported` → Krugozor, kugimiya, badwords, readme-SVG, hacking-buds, CensureBlock…
  - `slang_manual` → `stop_words_slang_manual.txt` (ручной + curated jargon)
  - `lemma_canonical` → profanity/drugs/sex: кириллица ≥4 символов → pymorphy3 → лемма, dedupe
  - **Не канонизировать:** translit, slang_manual, многословные фразы, латиница.
  - `python build_wordlists.py` → `_build_stats.txt` + stats в README.
  - **Acceptance criteria:** размер словарей уменьшается без потери покрытия; runtime lemma + exact ловят регрессии; idempotent rebuild.

#### 9.3.6 Moderation при create (не только publish) [P1]

- [x] **Фаза 4 (опционально):** `moderate_job_for_publish` в `create_job_request` и аналогах бота
  - Сейчас: проверка только при `draft → active`.
  - **Acceptance criteria:** `POST /employer/jobs` с `гашиша` в title → `400 content_rejected`; чистый черновик → `201`.

#### 9.3.2 Visual homoglyph translit [P0]

- [x] **Новый тип translit** — нормализация по **внешнему виду** буквы (латиница ≈ кириллица), **отдельно** от фонетического `_TRANSLIT_TO_CYRILLIC` (9.3)
  - **Проблема:** mixed-script обходы — `Хyй`, `Пиздa`, `Сукa`, `gоvnо` (кириллица + лат. `y`/`a`/`e`/`o`/`p`/`c`/`x`…).
  - **Правило:** map lookalikes: `a→а`, `e→е`, `o→о`, `p→р`, `c→с`, `x→х`, `y→у`, `H→Н`, `B→В`, `K→К`, `M→М`, `T→Т`; затем wordlist / lemma.
  - **Сохранить без изменений:** фонетический translit (`GOVNO`, `HUY`, `BLYAT`, `Mephedron`).
  - **Acceptance criteria:** `Хyй`, `Пиздa`, `Сукa`, `gоvnо` → violation; чистая латиница брендов (`McDonald's`, `KFC`) — не ломается после 9.3.3.

#### 9.3.3 Allow Latin in public text fields [P1]

- [x] Снять blanket `reject_latin` с полей заявок/профиля; разрешить латиницу для названий компаний и EN-терминов
  - Сейчас: `app/core/text_validation.py` + Pydantic validators блокируют любую латиницу → ложные отказы для `McDonald's`, `Burger King`, IT-названий.
  - **Замена:** валидация длины/формата + content moderation (stop-words + visual/phonetic translit); whitelist брендов (`_COMPANY_BRAND_TERMS`) расширить.
  - Mini App / bot: убрать client-side `rejectLatin` там, где дублирует backend.
  - **Acceptance criteria:** `company_name` = `ООО McDonald's` проходит; `Хyй` / `Пиздa` в title/description — `content_rejected`; регрессия alcohol whitelist и contact_info сегментов.

#### 9.3.7 Anti-bypass roadmap (аудит 44 фраз) [P0/P1]

> **Базовый аудит (2026-07):** 44 тестовые фразы — 20 BLOCK / 24 PASS. **После 9.3.7.1–9.3.7.3 (без 9.3.7.4):** 27 BLOCK / 17 PASS (`test_bypass_audit_level`). Level 1 (прямой матч) — 5/5 OK.

| Уровень | Обход | Сейчас | Приоритет | ID |
|---------|-------|--------|-----------|-----|
| 1 | Прямое слово (`хуй`, `гашиш`) | 5/5 | — | `[x]` 9.1 |
| FP | Ложное «есть» в profanity | fixed | P0 | `[x]` 9.3.7.0 |
| 2 | Пробелы внутри слова (`и щ у д е в о ч к у`) | 4/5 | **P0** | `[x]` 9.3.7.1 |
| 3 | Leet-цифры в кириллице (`д3в0чку`, `1нтимa`) | 5/5 | **P0** | `[x]` 9.3.7.2 |
| 4 | Частичная латиница / translit (`prodau metadon`, `ищу девочку для intiма`) | 7/7 | **P0** | `[x]` 9.3.7.3 |
| 5 | Сленг-эвфемизмы (кекс, ляля, ласточка, happy end, белый порошок…) | 3/12 | P1 | 9.3.7.4 |
| 6 | Комбинированный (leet + slang + mixed script) | 3/10 | P1 | `[x]` 9.3.7.5 (partial) |

##### 9.3.7.0 False positive «есть» [P0] — `[x]`

- **Проблема:** standalone `есть` в `stop_words_profanity.txt` (badwords-py) блокировал «Есть витамины».
- **Слой:** `build_wordlists.py` — `EXCLUDE_FALSE_POSITIVES` + фильтр после `canonicalize_bucket` (лемма `ести` → `есть`).
- **Verify:** `test_est_common_verb_not_blocked`, `test_profanity_still_blocked_after_est_removed`; пересборка не возвращает `есть`.

##### 9.3.7.1 Level 2 — пробелы внутри слова [P0] — `[x]`

- **Проблема:** `normalize_for_matching` схлопывает только **межсловные** `\s+`, не внутри токена (`и щ у` остаётся четырьмя токенами).
- **Слой:** `content_moderation_service.py` — `_collapse_intra_word_spaces(text)` + `_find_violation_by_glued_substrings` для склеенных токенов.
- **Acceptance (BLOCK):** `и щ у д е в о ч к у д л я и н т и м а`, `г е р о и н`, `з а к л а д к а`, `м е ф е д р о н`, `п р о д а ю к о к а и н`.
- **Acceptance (PASS):** `и щ у официанта`, `в и т а м и н ы`, `(м. рядом)`.
- **Verify:** `test_level2_*`, `test_collapse_intra_word_spaces_*`. Остаток: `к у п л ю г е р ы ч` (герыч — 9.3.7.4).

##### 9.3.7.2 Level 3 — leet в кириллице [P0] — `[x]`

- **Проблема:** `_LEET_TRANSLATION` мапит цифры в **латиницу** (`3→e`, `0→o`), а обходы типа `д3в0чку` / `м3тад0н` требуют `3→з/е`, `0→о`, `1→и/л` в кириллическом контексте.
- **Слой:** `content_moderation_service.py` — `_CYRILLIC_LEET_TRANSLATION` в `_deobfuscate_token` (токены с кириллицей + цифры/@).
- **Acceptance (BLOCK):** `д3в0чку` (в фразе), `1нтимa`, `м3тад0н`, `г3р0ин`, `к0каин`.
- **Acceptance (PASS):** `3 смены в неделю`, `опыт 10 лет`.
- **Verify:** `test_level3_*`.

##### 9.3.7.3 Level 4 — translit / mixed-script фразы [P0] — `[x]`

- **Проблема:** нет записей в `_TRANSLIT_TO_CYRILLIC` для `metadon`, `intiма`, `gashish` и др.
- **Слой:** `content_moderation_service.py` — расширен `_TRANSLIT_TO_CYRILLIC` (`metadon`, `prodau`, `intima`, `gashish`, `g3roin`, …).
- **Acceptance (BLOCK):** `prodau metadon`, `ищу девочку для intiма`, `vip devushki escort`, `zakladka v centre`, `продам gashish`.
- **Acceptance (PASS):** `McDonald's`, `IT support`, `KFC lounge bar`.
- **Verify:** `test_level4_*`.

##### 9.3.7.4 Level 5 — сленг-эвфемизмы [P1]

- **Проблема:** жаргон не в `stop_words_slang_manual.txt` / sex/drugs stems; часть есть только в источниках Krugozor, не попала в manual bucket.
- **Слой:** `build_wordlists.py` — расширить `SLANG_MANUAL_SEED`, `SEX_STEMS`/`DRUG_STEMS`; `stop_words_slang_manual.txt` (exact-only, без lemma).
- **Кандидаты (BLOCK):** `кекс` (нарк.), `ляля`/`ласточка` (эскорт), `happy end` (сейчас только `happy ending`), `белый порошок`, `снег`/`лед` (контекст нарк.), `массаж с продолжением`, `взрослые игры`.
- **Acceptance (PASS):** `кекс на день рождения` (если оставить — нужен контекстный фильтр или фразовый матч; **риск FP**), `массаж спины`, `ледовое шоу`, фамилии (`Снегур`, `Ласточкин`).

##### 9.3.7.5 Level 6 — комбинированные обходы + регрессия [P1] — `[x]` partial

- **Слой:** параметризованный `test_bypass_audit_level` (44 фразы аудита); `test_bypass_audit_summary_stats` (27/44 BLOCK без 9.3.7.4).
- **Verify:** `pytest tests/test_content_moderation.py -k bypass_audit`.
- **Остаток PASS (ожидаемо без 9.3.7.4):** кекс, ляля, ласточка, happy end, белый порошок, снег/лед, массаж с продолжением, взрослые игры, герыч (`к у п л ю г е р ы ч`).

**Порядок реализации:** 9.3.7.0 → 9.3.7.1 → 9.3.7.2 → 9.3.7.3 (P0) → 9.3.7.4 → 9.3.7.5 (P1).

**Риски / false positives:**

| Риск | Митигация |
|------|-----------|
| Склейка пробелов ломает адреса / аббревиатуры | Исключения: `(м. …)`, `стр.`, `корп.`, телефоны; unit-тесты на PASS-фразы |
| Leet ломает «3D», «H2O», номера смен | Deobfuscate только токены с кириллицей + цифры и/или `_deobfuscated_matches_block_term` |
| Сленг «снег/лед/кекс» в быту | Фразовый матч (bigram) или контекстные stems; review + `EXCLUDE_FALSE_POSITIVES` |
| Alcohol whitelist | Сохранить `_mask_alcohol_terms` до block-match; регрессия 9.5 |
| Лемматизация возвращает омонимы (`ести`→`есть`) | `EXCLUDE_FALSE_POSITIVES` + post-canonicalize filter в `build_wordlists.py` |

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

- [x] **9.11.1** API `GET /admin/journal/stop-words` — лог `moderation_violations` [P1]
  - **Acceptance criteria:** поля: дата, telegram_id/username, field, matched_term, snippet (truncate), source; фильтры `from`/`to`, `telegram_id`; limit ≤ 100; не смешивать с complaints.

- [x] **9.11.2** UI: подвкладки «Журнал» в [`AdminPanelPage.tsx`](../mini-app/src/pages/AdminPanelPage.tsx) [P1]
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

### Category Taxonomy v2 — полная реализация [P1]

> **Контекст:** гибридная таксономия **Direction A** — 8 групп, ~43 стандартные роли, поиск, «своя должность» с обязательной группой и AI-верификацией. Спецификация: [CATEGORY_TAXONOMY.md](./CATEGORY_TAXONOMY.md). Плановая таксономия: [`category_taxonomy.py`](../backend/app/reference/category_taxonomy.py). **Production DB:** иерархия `job_categories` (миграция `011_category_taxonomy`).
>
> **Статус фазы (2026-07-09):** CT2.1–CT2.7 **implemented**; CT2.6.1–2 (OpenAI key staging/prod) и CT2.8 (admin queue) — open.
>
> | Компонент | Статус |
> |-----------|--------|
> | DB: 8 групп + ~43 роли + legacy 14 slug mapping | `[x]` |
> | API: groups, search, recent, verify-custom-role | `[x]` |
> | Mini App: 2-step picker, custom verify, profile, vacancy filter | `[x]` |
> | Bot: group→role FSM, custom verify, search | `[x]` |
> | Hybrid matching (group + fuzzy + role_slug) | `[x]` |
> | Deploy backend + Mini App (zero-downtime) | `[x]` |
> | QA + docs (CT2.7) | `[x]` |
> | OpenAI key on staging/prod | `[ ]` CT2.6.1–2 |
> | Admin suggested-roles queue | `[ ]` CT2.8 optional |

**Оценка:** ~2–3 недели solo (без optional admin phase). **Порядок:** CT2.1 → CT2.2 → CT2.3 → CT2.4 → CT2.5 → CT2.6 → CT2.7; CT2.8 — опционально после CT2.6.

#### CT2.1 — БД: миграция, seed, маппинг legacy [P0]

> **Зависимости:** нет (старт фазы). Колонка `job_categories.parent_id` уже есть в модели — использовать для иерархии group → role.

- [x] **CT2.1.1** Alembic: иерархия `job_categories` — 8 групп (parent_id=NULL) + ~43 leaf-роли (parent_id→group); поля `kind` (`group`|`role`) и/или `group_slug`/`role_slug` при необходимости для API
  - **Acceptance criteria:** downgrade работает; уникальность `slug` глобально; группы и роли из `PLANNED_CATEGORY_GROUPS` покрыты.

- [x] **CT2.1.2** Seed/migration script: заполнить таксономию v2 из `category_taxonomy.py`; сохранить существующие 14 legacy slug как leaf с `legacy_slug` mapping
  - **Зависит от:** CT2.1.1
  - **Acceptance criteria:** `scripts/seed_categories.py` (или новый `seed_category_taxonomy.py`) идемпотентен; повторный запуск не дублирует записи.

- [x] **CT2.1.3** Data migration: `job_requests.category_id`, `worker_experiences.category_id`, `worker_preferences.category_ids`, `group_posting_rules.category_ids` — маппинг flat slug → новый leaf `category_id` по `legacy_slug`
  - **Зависит от:** CT2.1.2
  - **Acceptance criteria:** ни одна активная заявка/опыт не теряет категорию; отчёт миграции (mapped / unmapped / manual review); unmapped только для `other` и явно задокументированных кейсов.

- [x] **CT2.1.4** (Опционально P2) Колонки `job_requests.role_slug`, `group_slug` — денорм. для matching и audit custom titles; backfill NULL для legacy заявок
  - **Зависит от:** CT2.1.3

- [x] **CT2.1.5** Unit/integration-тесты: seed, legacy mapping, FK целостность после миграции
  - **Зависит от:** CT2.1.3
  - **Verify:** `pytest tests/test_category_taxonomy_migration.py` (новый файл).

**Verification (CT2.1):** в БД 8 групп + ~43 роли; старые 14 slug резолвятся в leaf; существующие заявки и опыт работников указывают на корректные `category_id`.

#### CT2.2 — API: справочник, поиск, recent history [P0]

> **Зависимости:** CT2.1.2 (таксономия в БД). Сейчас: `[x]` плоский `GET /reference/categories` — заменить/расширить, не ломая legacy consumers до CT2.3.

- [x] **CT2.2.0 (MVP)** `POST /employer/job-categories/verify-custom-role` — AI/fallback верификация по `group_slug` (без `group_id` до миграции)
- [x] **CT2.2.0 (MVP)** `GET /reference/categories` — плоский список legacy `job_categories`

- [x] **CT2.2.1** `GET /reference/category-groups` — 8 групп (`id`, `slug`, `name_ru`, `roles_count`)
  - **Зависит от:** CT2.1.2

- [x] **CT2.2.2** `GET /reference/category-groups/{group_slug}/roles` — роли группы; query `q` — поиск по подстроке в `name_ru` (case-insensitive, min length ≥ 2, как metro search)
  - **Зависит от:** CT2.1.2
  - **Acceptance criteria:** `офиц` → «Официант»; `БАР` → «Бармен», «Бариста»; пагинация/limit ≤ 50.

- [x] **CT2.2.3** `GET /reference/categories/search?q=` — глобальный поиск по всем ролям (возврат: `group_slug`, `group_name_ru`, `role_id`, `role_slug`, `name_ru`, `legacy_category_id?`)
  - **Зависит от:** CT2.1.2
  - **Acceptance criteria:** многословные запросы; ранжирование: exact prefix > substring; тесты на case-insensitive.

- [x] **CT2.2.4** Recent history: `GET /employer/category-selections/recent` и `GET /worker/category-selections/recent` — последние N (default 5) уникальных пар group+role / category из заявок employer или опыта worker
  - **Зависит от:** CT2.1.3
  - **Acceptance criteria:** только свои данные (auth); дедуп по `role_id`; сортировка по `last_used_at` DESC.

- [x] **CT2.2.5** Обновить `verify-custom-role`: принимать `group_id` (после миграции); `group_slug` остаётся для обратной совместимости
  - **Зависит от:** CT2.1.2
  - **Acceptance criteria:** `group_id` снимает 501; невалидный `group_id` → 400; регрессия `test_custom_role_verification.py` зелёная.

- [x] **CT2.2.6** Pydantic schemas + OpenAPI; integration-тесты search/recent/groups
  - **Зависит от:** CT2.2.1–CT2.2.5
  - **Verify:** `pytest tests/test_category_reference_api.py`.

**Verification (CT2.2):** Mini App и бот могут получить группы, роли с поиском и recent history через API; verify-custom-role работает с `group_id`.

#### CT2.3 — Mini App: 2-step group→role + custom verify [P0]

> **Зависимости:** CT2.2. Сейчас: `[x]` `CreateJobPage` — плоский `<select>` по `category_id`; `[x]` `verifyCustomRole()` в client без UI.

- [x] **CT2.3.0 (MVP)** `verifyCustomRole()` + типы в [`client.ts`](../mini-app/src/api/client.ts)
- [x] **CT2.3.0 (MVP)** `CreateJobPage` — плоский выбор категории (legacy dropdown)

- [x] **CT2.3.1** `CreateJobPage`: шаг 1 — выбор **группы** (8 карточек/кнопок); шаг 2 — **роль** из группы или «Своя должность»
  - **Зависит от:** CT2.2.1, CT2.2.2
  - **Acceptance criteria:** нельзя перейти к роли без группы; «Назад» сохраняет состояние; haptic на выбор.

- [x] **CT2.3.2** Поиск ролей в шаге 2: debounce ≥ 300 ms, min length ≥ 2, `GET .../roles?q=` или global search
  - **Зависит от:** CT2.2.2 или CT2.2.3
  - **Acceptance criteria:** UX как metro search (Phase 7); пустой результат — подсказка «Своя должность».
  - **2026-07-10:** глобальный поиск на шаге 1 (group screen) — `GET /reference/categories/search?q=`; tap «Группа · Роль» → прямой выбор без шага 2

- [x] **CT2.3.3** Блок **Recent** — последние выборы employer (`CT2.2.4`) над списком групп/ролей
  - **Зависит от:** CT2.2.4, CT2.3.1

- [x] **CT2.3.4** Flow **«Своя должность»**: поле title + кнопка «Проверить» / blur → `verifyCustomRole`; карточка результата по `status` (`approved` | `map_to_existing` | `revise` | `rejected`)
  - **Зависит от:** CT2.2.0, CT2.3.1
  - **Acceptance criteria:** `map_to_existing` — предложить выбрать стандартную роль; `revise` — показать `suggested_title`; `rejected` — блок submit; `approved` — `form.title` = custom, `category_id` из legacy mapping при наличии.

- [x] **CT2.3.5** Submit заявки: `category_id` = leaf role; `title` = custom или стандартное имя роли; валидация «verify пройден» для custom path
  - **Зависит от:** CT2.3.4

- [x] **CT2.3.6** `ProfilePage` / опыт работника: тот же 2-step picker + recent (worker context)
  - **Зависит от:** CT2.3.1–CT2.3.3
  - **Acceptance criteria:** регрессия редактирования опыта; `role_title` по-прежнему свободный текст после выбора категории-leaf.

- [x] **CT2.3.7** `VacancyListPage` / фильтры: поиск категории через taxonomy search вместо плоского списка
  - **Зависит от:** CT2.2.3

**Verification (CT2.3):** employer создаёт заявку через group → role; custom title проходит verify и сохраняется; recent ускоряет повторный выбор.

#### CT2.4 — Bot: клавиатуры group→role + поиск [P1]

> **Зависимости:** CT2.2. Сейчас: `[x]` плоские `categories_keyboard` в `job_request.py`, `worker_registration.py`, `vacancy_search.py`.

- [x] **CT2.4.0 (MVP)** FSM создание заявки — плоский выбор `job_categories` (`JobRequestCreation.category`)
- [x] **CT2.4.0 (MVP)** FSM регистрация работника — плоский выбор категории опыта
- [x] **CT2.4.0 (MVP)** Поиск вакансий — фильтр по категориям из опыта работника

- [x] **CT2.4.1** `job_request.py`: шаг «Группа» → inline keyboard 8 групп → шаг «Роль» → роли группы (пагинация по 8)
  - **Зависит от:** CT2.2.1, CT2.2.2

- [x] **CT2.4.2** Bot: «Своя должность» — текстовый ввод title → вызов `verify_custom_role` (shared service, не HTTP) → ответ по status
  - **Зависит от:** CT2.2.0, CT2.4.1

- [x] **CT2.4.3** Bot search: команда/кнопка «Найти роль» — пользователь вводит подстроку → `search` API → выбор из результатов
  - **Зависит от:** CT2.2.3

- [x] **CT2.4.4** `worker_registration.py`: 2-step group→role для опыта (аналог CT2.4.1)
  - **Зависит от:** CT2.4.1

- [x] **CT2.4.5** `vacancy_search.py`: фильтр категории через taxonomy search / группы
  - **Зависит от:** CT2.2.3, CT2.4.3

- [x] **CT2.4.6** Тесты bot handlers (mock session + taxonomy fixtures)
  - **Зависит от:** CT2.4.1–CT2.4.5

**Verification (CT2.4):** employer создаёт заявку в боте через группу и роль; custom title верифицируется; worker добавляет опыт с новым picker.

#### CT2.5 — Matching: hybrid group + fuzzy role [P0]

> **Зависимости:** CT2.1.3. Сейчас: `[x]` matching только по `category_id` (flat) в `matching_service.py`.

- [x] **CT2.5.0 (MVP)** `matching_service` — фильтр и сортировка по `job.category_id` ∩ worker experiences
- [x] **CT2.5.0 (MVP)** Push matching (`notify_matching_workers`) — по `category_id` из preferences/experiences

- [x] **CT2.5.1** Group filter: worker matches job если leaf role job принадлежит группе, в которой есть **любой** опыт worker (после миграции — по `parent_id` / `group_slug`)
  - **Зависит от:** CT2.1.3
  - **Acceptance criteria:** worker с опытом «Официант» видит заявку «Бармен» в той же группе `horeca_service` только при включённом «Показывать все вакансии»; при выключенном — strict leaf или hybrid по настройке.

- [x] **CT2.5.2** Fuzzy role title: для custom/несовпадающих leaf — `SequenceMatcher` normalized similarity между `job.title` и `worker_experience.role_title` (threshold ~0.82, как в verifier)
  - **Зависит от:** CT2.1.3
  - **Acceptance criteria:** «Старший официант зала» матчится с опытом «официант зала»; unit-тесты на threshold и normalization.

- [x] **CT2.5.3** Shortcut `map_to_existing`: заявки с верифицированным `role_slug` — match по leaf `category_id` без fuzzy
  - **Зависит от:** CT2.1.4, CT2.3.4

- [x] **CT2.5.4** Обновить push matching и employer notify: учитывать group + fuzzy; не ломать `show_all_vacancies` и `worker_preferences.category_ids`
  - **Зависит от:** CT2.5.1–CT2.5.3

- [x] **CT2.5.5** Регрессия: `test_matching_service.py`, `test_push_matching.py` — legacy flat jobs + новые taxonomy jobs
  - **Зависит от:** CT2.5.4

**Verification (CT2.5):** custom title заявка находит работников той же группы с похожим `role_title`; стандартные роли матчятся по leaf; push не рассылается лишним категориям.

#### CT2.6 — Deploy + конфигурация OpenAI [P1]

> **Зависимости:** CT2.2.0 (verify endpoint). **Деплой:** только zero-downtime по [DEPLOYMENT.md](./DEPLOYMENT.md) + `.cursor/rules/deploy-zero-downtime.mdc`.

- [x] **CT2.6.0 (MVP)** `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TIMEOUT_SECONDS` в `config.py` и `.env.example`
- [x] **CT2.6.0 (MVP)** Fallback verifier без API key (moderation + fuzzy)

- [ ] **CT2.6.1** Staging `.env`: задать `OPENAI_API_KEY` (secret, не в git); smoke `POST verify-custom-role` → `verification_mode: ai`
  - **Зависит от:** CT2.2.0
  - **2026-07-09:** на сервере `OPENAI_*` в `.env` **отсутствуют** — пользователь должен добавить ключ вручную; smoke verify → `verification_mode: fallback` (ожидаемо без ключа)

- [ ] **CT2.6.2** Production `.env`: `OPENAI_API_KEY` через `deploy-env-only.sh`; проверить timeout и rate limits
  - **Зависит от:** CT2.6.1
  - **2026-07-09:** заблокировано отсутствием ключа; defaults в контейнере: `gpt-4o-mini`, timeout `15s`

- [x] **CT2.6.3** Deploy backend (api + bot + worker) после CT2.1 миграции: `deploy-zero-downtime.sh` — migrations → rolling swap
  - **Зависит от:** CT2.1, CT2.2, CT2.5
  - **Запрещено:** `docker compose down`, full stack `--build`.
  - **2026-07-09:** alembic `011_category_taxonomy (head)`; rolling swap api → worker → bot (`SKIP_GIT=1`); ops: создан пустой `stop_words_violence.txt` на сервере (moderation preflight)

- [x] **CT2.6.4** Deploy Mini App после CT2.3: `deploy-mini-app-only.sh` (staging → verify → atomic mv)
  - **Зависит от:** CT2.3
  - **2026-07-09:** `MINI_APP_URL=…?v=23`, dist от CT2.3 (2026-07-09 14:02 UTC); локального dist новее нет — redeploy не нужен
  - **2026-07-10:** `MINI_APP_URL=…?v=24` — CategoryPicker step 1: глобальный поиск ролей (`searchCategories`) на экране выбора группы; CreateJobPage + ProfilePage

- [x] **CT2.6.5** Post-deploy checklist: `/health`; verify-custom-role AI; создать заявку group→role; worker matching на staging
  - **Зависит от:** CT2.6.3, CT2.6.4
  - **2026-07-09:** health OK; category-groups 8 групп; verify-custom-role → `fallback`/`approved` (AI после CT2.6.1); 19 заявок с `group_slug`; `find_workers_for_job` smoke OK

**Verification (CT2.6):** на staging/prod `verification_mode=ai` при валидном ключе; fallback при сбое OpenAI; миграция применена без даунтайма.

#### CT2.7 — QA и документация [P1]

> **Зависимости:** CT2.3–CT2.6. Финальная приёмка перед закрытием фазы.

- [x] **CT2.7.1** E2E сценарии (manual или Playwright): CreateJob group→standard role; CreateJob custom+verify; Profile experience; bot job create; vacancy search filter
  - **Зависит от:** CT2.3, CT2.4
  - **2026-07-09:** manual matrix M1–M6 в [CATEGORY_TAXONOMY.md § Manual QA](./CATEGORY_TAXONOMY.md#manual-qa--e2e-scenarios)

- [x] **CT2.7.2** Regression suite: полный `pytest backend/tests` + mini-app build; матрица legacy 14 slug vs новые роли
  - **Зависит от:** CT2.5.5
  - **2026-07-09:** **535 passed**, 1 skipped (full pytest, 498s); **74 passed** (CT2 subset); `npm run build` mini-app OK

- [x] **CT2.7.3** Обновить [CATEGORY_TAXONOMY.md](./CATEGORY_TAXONOMY.md) и [PLAN.md § C](./PLAN.md) — статус «implemented», схема БД, matching rules
  - **Зависит от:** CT2.1–CT2.5

- [x] **CT2.7.4** Отметить выполненные пункты CT2.* в этом файле и синхронизировать [PLAN.md § F](./PLAN.md#f-roadmap--фазы-реализации) при необходимости
  - **2026-07-09:** CT2 progress summary + PLAN § F CT2 block обновлены

**Verification (CT2.7):** все CT2 acceptance criteria пройдены; документация отражает production state.

#### CT2.8 — (Опционально) Admin: очередь suggested roles [P2]

> **Зависимости:** CT2.3.4 (custom verify). Для частых `revise` / спорных `approved` custom titles — модерация перед публикацией в справочник.

- [ ] **CT2.8.1** Таблица `suggested_role_submissions`: `employer_id`, `group_slug`, `proposed_title`, `verification_status`, `verification_mode`, `ai_reason`, `created_at`, `reviewed_at`, `admin_decision`
  - **Зависит от:** CT2.1

- [ ] **CT2.8.2** API admin: `GET /admin/suggested-roles?status=pending`, `PATCH .../approve|reject` — при approve опционально добавить в `job_categories` или synonym table
  - **Зависит от:** CT2.8.1

- [ ] **CT2.8.3** Mini App Admin: подвкладка «Предложенные должности» (или секция в «Модерация») — список, approve/reject, snippet + group
  - **Зависит от:** CT2.8.2

- [ ] **CT2.8.4** Bot admin: `/suggested_roles` — compact list + inline actions (по аналогии с `/moderation_queue`)
  - **Зависит от:** CT2.8.2

**Verification (CT2.8):** custom title с `approved` логируется; admin видит очередь и может отклонить спам-должности до повторного использования.

**Как выполнять:** CT2.1–CT2.2 — `postgres-patterns`, `database-migrations`, `tdd-workflow`; CT2.3 — `frontend-patterns`, `ecc-react-reviewer`; CT2.4 — `python-patterns`; CT2.5 — `tdd-workflow`, `postgres-patterns`; deploy — [DEPLOYMENT.md](./DEPLOYMENT.md); security — `OPENAI_API_KEY` только в `.env`, не в образе git.

---

## Быстрая навигация

| Документ | Что там |
|----------|---------|
| **[TASKS.md](./TASKS.md)** (этот файл) | **Единый чеклист задач** Phase 0–10 |
| [TASKS.md § Category Taxonomy v2](./TASKS.md#category-taxonomy-v2--полная-реализация-p1) | 8 групп, поиск ролей, custom verify, matching, миграция |
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
