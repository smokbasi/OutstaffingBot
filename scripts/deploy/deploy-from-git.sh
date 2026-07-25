!/usr/bin/env bash
# One-command deploy FROM GIT (committed SHA on BRANCH).
#
# - From a developer machine: SSH → server git sync → optional zero-downtime.
# - On the server (APP_DIR exists): same steps without SSH.
#
# Usage:
#   ./scripts/deploy/deploy-from-git.sh              # git sync + zero-downtime
#   ./scripts/deploy/deploy-from-git.sh --git-only    # git sync only (docs/rules/scripts)
#   BRANCH=main REMOTE=root@89.125.25.99 ./scripts/deploy/deploy-from-git.sh
#
# Env:
#   APP_DIR   default /opt/outstaffingbot
#   BRANCH    default main
#   REMOTE    default root@89.125.25.99
#
# NEVER for routine: SKIP_GIT=1, dirty-tree deploy, docker compose down / up -d --build
# See docs/DEPLOYMENT.md
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/outstaffingbot}"
BRANCH="${BRANCH:-main}"
REMOTE="${REMOTE:-root@89.125.25.99}"
GIT_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --git-only|-g) GIT_ONLY=1 ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg (use --git-only)" >&2
      exit 1
      ;;
  esac
done

run_on_server() {
  set -euo pipefail
  cd "$APP_DIR"
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-outstaffingbot}"
  export BRANCH
  if [[ "$GIT_ONLY" == "1" ]]; then
    echo "==> git fetch && checkout $BRANCH (git-only, no container recreate)"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
    echo "==> Server HEAD: $(git rev-parse --short HEAD) ($(git log -1 --oneline))"
    echo "==> git-only sync done"
  else
    exec ./scripts/deploy/deploy-zero-downtime.sh
  fi
}

if [[ -d "$APP_DIR/.git" && -x "$APP_DIR/scripts/deploy/deploy-zero-downtime.sh" ]] \
  || [[ -d "$APP_DIR/.git" && -f "$APP_DIR/scripts/deploy/deploy-zero-downtime.sh" ]]; then
  # Already on the server (or APP_DIR is the deploy checkout).
  run_on_server
  exit 0
fi

# Developer machine → SSH
MODE_LABEL="app"
[[ "$GIT_ONLY" == "1" ]] && MODE_LABEL="git-only"
echo "==> SSH $REMOTE → $APP_DIR (mode=$MODE_LABEL, branch=$BRANCH)"

# Export flags into the remote bash environment via inline script.
ssh "$REMOTE" \
  "export APP_DIR=$(printf %q "$APP_DIR"); export BRANCH=$(printf %q "$BRANCH"); export GIT_ONLY=$(printf %q "$GIT_ONLY"); export COMPOSE_PROJECT_NAME=outstaffingbot; bash -s" <<'EOS'
set -euo pipefail
cd "$APP_DIR"
if [[ "$GIT_ONLY" == "1" ]]; then
  echo "==> git fetch && checkout $BRANCH (git-only, no container recreate)"
  git fetch origin
  git checkout "$BRANCH"
  git pull origin "$BRANCH"
  echo "==> Server HEAD: $(git rev-parse --short HEAD) ($(git log -1 --oneline))"
  echo "==> git-only sync done"
else
  ./scripts/deploy/deploy-zero-downtime.sh
fi
EOS

echo "==> deploy-from-git finished"
