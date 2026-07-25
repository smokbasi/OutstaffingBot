 Автоматический commit → merge → deploy для агентов

Чтобы Cursor-агент **не забывал** после каждого запрошенного изменения делать **commit → merge/rebase → deploy из git**, поставь always-on правило.

## Установка (для коллеги / другого клона)

1. Скопируй файл правила в свой проект:

   ```
   .cursor/rules/auto-commit-deploy.mdc
   ```

   Источник в этом репо: тот же путь.

2. Убедись, что в frontmatter есть:

   ```yaml
   alwaysApply: true
   ```

3. Перезапусти Cursor **или** открой **новый чат** агента (чтобы подтянуть rules).

4. Проверь, что деплой-скрипт на месте:

   ```bash
   ./scripts/deploy/deploy-from-git.sh --help
   ```

   Документация деплоя: [DEPLOYMENT.md](./DEPLOYMENT.md). Git: [GIT_WORKFLOW.md](./GIT_WORKFLOW.md).

## Что делает правило

| Шаг | Поведение агента |
|-----|------------------|
| После любой запрошенной правки | Сам коммитит (conventional commits) |
| Интеграция в `main` | PR squash merge **или** rebase/merge на `main` — как в git-workflow проекта |
| Деплой | Из git (SHA), не из dirty tree |
| Docs/rules only | Commit + push обязательны; app-rebuild можно пропустить (`--git-only`) |
| Runtime (api/bot/worker/mini-app) | Полный/partial deploy через `deploy-from-git.sh` |

Явный отказ пользователя: `только локально`, `без деплоя`, `не коммить` — тогда цикл останавливается.

## Связанные правила в этом репо

| Файл | Роль |
|------|------|
| `.cursor/rules/auto-commit-deploy.mdc` | **Портативное HARD-правило** (это копируют коллеге) |
| `.cursor/rules/git-workflow.mdc` | Полный git-workflow проекта |
| `.cursor/rules/deploy-zero-downtime.mdc` | Zero-downtime + одна команда |
| `.cursor/rules/project-workflow.mdc` | Общий workflow сессии |

## Одна команда деплоя

```bash
./scripts/deploy/deploy-from-git.sh              # app
./scripts/deploy/deploy-from-git.sh --git-only    # только git sync на сервере
```
