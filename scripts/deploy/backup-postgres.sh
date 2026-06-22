#!/usr/bin/env bash
# Daily PostgreSQL backup for OutstaffingBot (run on VPS via cron).
# Usage:
#   ./scripts/deploy/backup-postgres.sh
#   BACKUP_DIR=/var/backups/outstaffingbot RETENTION_DAYS=14 ./scripts/deploy/backup-postgres.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/outstaffingbot}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/outstaffingbot}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-outstaffingbot}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE="$BACKUP_DIR/outstaffing_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

cd "$APP_DIR"
set -a
# shellcheck disable=SC1091
source .env
set +a

POSTGRES_USER="${POSTGRES_USER:-outstaffing}"
POSTGRES_DB="${POSTGRES_DB:-outstaffing}"

echo "==> pg_dump -> $ARCHIVE"
docker compose -p "$COMPOSE_PROJECT_NAME" \
  -f docker-compose.yml -f docker-compose.staging.yml \
  exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl \
  | gzip -9 > "$ARCHIVE"

chmod 600 "$ARCHIVE"
find "$BACKUP_DIR" -name 'outstaffing_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete

echo "==> Backup complete: $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1))"
