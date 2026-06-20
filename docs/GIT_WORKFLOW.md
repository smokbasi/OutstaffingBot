# Git Workflow — OutstaffingBot

> **Проект:** greenfield monorepo — Telegram-бот (aiogram) + Mini App (React/Vite) + FastAPI backend.  
> **Аудитория:** разработчики и AI-агенты (Cursor). Следуйте этому документу **при каждой** работе с репозиторием.

---

## 1. Базовые принципы

| Параметр | Значение |
|----------|----------|
| Базовая ветка | `main` |
| Стратегия слияния PR | **Squash merge** — один коммит на PR в `main`, чистая история |
| Формат коммитов | **Bilingual Conventional Commits**: тип на английском, описание на русском |
| Remote | GitHub (используйте `gh` CLI для PR) |

После инициализации репозитория (`git init`) первый коммит создаёт ветку `main`. Если remote уже использует `master`, переименуйте локально: `git branch -M main`.

---

## 2. Именование веток

```
<prefix>/<краткое-описание-через-дефис>
```

| Префикс | Когда использовать | Пример |
|---------|-------------------|--------|
| `feature/` | Новая функциональность | `feature/worker-registration-fsm` |
| `fix/` | Исправление бага | `fix/initdata-validation` |
| `docs/` | Только документация | `docs/git-workflow` |
| `chore/` | Инфра, зависимости, конфиг | `chore/docker-compose-postgres` |

**Правила:**
- Только лatinица, цифры и дефисы
- Коротко и по смыслу задачи
- **Одна ветка = одна задача** (особенно при параллельной работе агентов)

---

## 3. Формат сообщений коммитов

```
<type>(<scope>): <краткое описание на русском>

[необязательное тело — что и зачем изменено]
```

### Типы (`type`)

| Тип | Назначение |
|-----|------------|
| `feat` | Новая функциональность |
| `fix` | Исправление бага |
| `docs` | Документация |
| `chore` | Рутина, зависимости, CI |
| `refactor` | Рефакторинг без изменения поведения |
| `test` | Тесты |
| `ci` | GitHub Actions, пайплайны |

### Scope (`scope`) — опционально

Примеры для monorepo: `bot`, `api`, `miniapp`, `worker`, `infra`, `db`.

### Примеры

```
feat(bot): добавить FSM регистрации работника
fix(api): исправить валидацию initData Telegram
docs: описать Git workflow для команды
chore(infra): добавить Docker Compose для postgres и redis
```

---

## 4. Что НЕ коммитить

| Категория | Примеры | Почему |
|-----------|---------|--------|
| Секреты | `.env`, `.env.local`, токены бота, API keys, `credentials.json` | Утечка данных |
| Зависимости | `node_modules/`, `.venv/`, `venv/` | Восстанавливаются из lock-файлов |
| Кэш Python | `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/` | Артефакты сборки |
| Сборки | `dist/`, `build/`, `*.egg-info/` | Генерируются заново |
| ECC agent memory (локально) | `%USERPROFILE%\.cursor\ecc\`, дампы instincts, чувствительные логи сессий | Могут содержать контекст и секреты |
| IDE / OS | `.DS_Store`, `Thumbs.db`, `*.swp` | Личные артефакты |
| Логи | `*.log`, `logs/` | Шум в истории |

Проверяйте перед коммитом: `git status` и `git diff`. Если секрет попал в историю — **не force-push в main**; обратитесь к коллеге для ротации ключей и очистки истории через отдельную процедуру.

---

## 5. Ежедневный workflow

```
pull → branch → work → commit → push → PR → review → squash merge
```

### Шаг за шагом

```powershell
# 1. Актуализировать main
git checkout main
git pull origin main

# 2. Создать ветку задачи
git checkout -b feature/my-task

# 3. Работа, периодические коммиты
# ... правки в backend/, miniapp/, bot/ ...

# 4. Перед push — rebase на актуальный main (снижает конфликты)
git fetch origin
git rebase origin/main

# 5. Push и PR
git push -u origin feature/my-task
gh pr create --base main --title "feat(bot): описание" --body "..."
```

---

## 6. Pull Request workflow

### Создание PR (gh CLI)

```powershell
gh pr create --base main `
  --title "feat(bot): FSM регистрации работника" `
  --body @"
## Summary
- Добавлен FSM для регистрации работника
- Обновлены handlers в bot/

## Test plan
- [ ] /start → пройти регистрацию
- [ ] Профиль сохраняется в PostgreSQL
"@
```

### Описание PR — обязательно для параллельной работы

Указывайте:
- **Что** изменено и **зачем**
- Затронутые модули (`backend/`, `miniapp/`, `bot/`)
- Чеклист проверки (Test plan)
- Связанные задачи / Phase из `docs/PLAN.md`

### Review и merge

1. CI должен пройти (когда настроен)
2. Минимум один approve от второго разработчика (когда команда > 1)
3. **Squash merge** в `main` через GitHub UI или:

```powershell
gh pr merge <номер> --squash --delete-branch
```

Squash сохраняет линейную историю `main`: один логический коммит на PR.

---

## 7. Работа двух разработчиков

Краткие правила для команды из двух человек (+ AI-агенты). **Полный гайд:** [SERVER_AND_TEAM.md](./SERVER_AND_TEAM.md) — staging VPS, секреты, локальная разработка без Docker, деплой.

| Правило | Детали |
|---------|--------|
| Remote | Public GitHub (`smokbasi/OutstaffingBot`); второй разработчик — collaborator с `write`; базовая ветка `main` |
| Review | Минимум **1 approve** второго разработчика перед squash merge |
| Owner `main` | Технически owner repo; мерж только через PR, не прямой push |
| Одна задача — одна ветка | Не работайте в чужой feature-ветке без договорённости |
| Держите ветку короткой | Мержите PR за 1–3 дня |
| Rebase перед push | `git fetch origin && git rebase origin/main` |
| Секреты | `.env` только локально и на сервере; в git — `.env.example` |
| Staging deploy | После merge в `main` — `git pull` на VPS (см. SERVER_AND_TEAM.md § G) |
| Агенты не пушат в main | Только через PR; force-push в main **запрещён** |
| Миграции Alembic | Новая revision в PR; не редактировать чужие migration-файлы |


### Добавить второго разработчика (collaborator)

```powershell
gh repo collaborator add USERNAME --repo smokbasi/OutstaffingBot --permission write
```

Замените `USERNAME` на GitHub login dev2. Прямой push в `main` не используем — только PR + squash merge (см. выше).

### (Опционально) Защита ветки `main`

GitHub → **Settings → Branches → Add branch protection rule** для `main`:

- Require a pull request before merging (минимум 1 approval)
- Do not allow bypassing the above settings
- Restrict direct pushes (только через PR)

### Параллельная работа + AI-агенты

| Правило | Детали |
|---------|--------|
| Коммуникация через PR | Scope + Test plan; координация при пересечении файлов |
| Конфликтующие зоны | `backend/services/`, shared models, миграции — согласовывать |

---

## 8. Правила для AI-агентов (Cursor)

### Запрещено всегда

- Force push в `main` / `master`
- `git push --force` на shared-ветки без явного запроса пользователя
- `--no-verify` / пропуск pre-commit hooks
- Изменение `git config` (локального или глобального)
- Коммит без явного запроса пользователя (или без явного пункта в задаче «создать коммит»)

### Amend — только при выполнении ВСЕХ условий

1. Пользователь **явно** попросил amend, **или** hook изменил файлы после успешного коммита
2. Последний коммит создан **в текущей сессии** этим агентом
3. Коммит **ещё не запушен** на remote

### Перед каждым коммитом

```powershell
git status
git diff
git diff --staged   # если файлы уже добавлены
```

### Коммит с сообщением (PowerShell)

```powershell
git add path/to/files

git commit -m @"
feat(bot): добавить команду /start

Реализовано главное меню согласно Phase 0 PLAN.md.
"@
```

Альтернатива — однострочный коммит:

```powershell
git commit -m "feat(bot): добавить команду /start"
```

### Push и PR — только по запросу

Агент создаёт коммит, если задача это включает. Push и PR — только когда пользователь явно просит.

---

## 9. Разрешение конфликтов

```powershell
# При rebase или merge
git status                    # файлы с конфликтами
# ... отредактировать файлы, убрать маркеры <<<< ==== >>>> ...
git add <resolved-files>
git rebase --continue         # или git merge --continue
```

**Советы для OutstaffingBot:**
- Миграции Alembic: не редактируйте чужие revision-файлы — создайте новую миграцию
- `pyproject.toml` / `package.json`: объединяйте зависимости обеих сторон
- При сомнении — спросите автора другого PR

Отмена rebase: `git rebase --abort`

---

## 10. Релизы и теги (будущее)

Когда проект выйдет в production:

```powershell
# После squash merge релизного PR в main
git checkout main
git pull origin main
git tag -a v0.1.0 -m "Первый MVP: регистрация работника"
git push origin v0.1.0
```

Semver: `vMAJOR.MINOR.PATCH`. Релизные notes — через `gh release create`.

---

## 11. Чеклист перед коммитом / PR

- [ ] `git status` — нет лишних файлов (`.env`, `__pycache__`, `node_modules`)
- [ ] `git diff` — изменения соответствуют задаче
- [ ] Сообщение коммита в формате Conventional Commits
- [ ] Ветка актуальна относительно `main` (rebase выполнен)
- [ ] Локально проверена ключевая функциональность
- [ ] PR описание содержит Summary + Test plan
- [ ] Секреты не попали в diff

---

## 12. Шпаргалка команд

```powershell
# Статус и история
git status
git log --oneline -10
git branch -a

# Ветки
git checkout main
git pull origin main
git checkout -b feature/my-feature

# Коммит
git add .
git diff --staged
git commit -m "feat(scope): описание"

# Синхронизация
git fetch origin
git rebase origin/main
git push -u origin feature/my-feature

# PR
gh pr list
gh pr create --base main --title "..." --body "..."
gh pr view --web
gh pr merge 42 --squash --delete-branch

# Отмена локальных изменений (осторожно!)
git restore <file>
git restore --staged <file>
```

---

## 13. Первоначальная настройка репозитория (Phase 0)

Когда проект ещё без Git (текущее состояние greenfield):

```powershell
cd "c:\Users\Nikita\Desktop\AI MS\OutstaffingBot"
git init
git branch -M main
git add .
git commit -m "chore: начальная структура проекта OutstaffingBot"
git remote add origin https://github.com/smokbasi/OutstaffingBot.git
git push -u origin main
```

Подробный план разработки — в [`docs/PLAN.md`](PLAN.md).

---

*Последнее обновление: июнь 2026. При изменении процесса — обновляйте этот файл и `.cursor/rules/git-workflow.mdc`.*
