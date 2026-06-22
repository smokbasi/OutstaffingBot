# GitHub CLI (`gh`) — настройка для разработки и агентов

## Установка (macOS)

- **Homebrew:** `brew install gh`
- **Без Homebrew:** бинарник [релизов cli/cli](https://github.com/cli/cli/releases) в `~/.local/bin/gh` (в проекте PATH уже настроен через `~/.zshrc`).

Проверка: `gh --version`.

## Аутентификация

Интерактивно (рекомендуется на машине разработчика):

```bash
gh auth login
# GitHub.com → HTTPS или SSH → Login with a web browser (или token)
gh auth status
```

**PAT (для CI и неинтерактивных сессий агента):**

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** (fine-grained или classic).
2. Права: **`repo`**, **`read:org`**; при использовании Projects — **`project`**.
3. Не сохраняйте токен в репозитории, `.env` проекта или коммитах.

```bash
# Вариант A: stdin (файл только локально, не в git)
gh auth login --hostname github.com --with-token < /path/to/token.txt

# Вариант B: переменная окружения в профиле shell (только локально)
export GH_TOKEN='ghp_...'
gh auth status
```

Токен в keychain после `gh auth login` хранит сам `gh`; для агентов Cursor часто нужен `GH_TOKEN` или предварительный `gh auth login` в том же пользовательском окружении.

## Проверка доступа к репозиторию

```bash
gh auth status
gh pr list --repo smokbasi/OutstaffingBot
gh issue list --repo smokbasi/OutstaffingBot
```

## Связанные документы

- Git-процесс и PR: [`docs/GIT_WORKFLOW.md`](GIT_WORKFLOW.md)
- Админ Mini App и бота: `ADMIN_TELEGRAM_IDS` в `/opt/outstaffingbot/.env` (через запятую, см. `.env.server.example`)
