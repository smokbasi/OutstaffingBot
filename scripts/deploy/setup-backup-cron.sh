#!/usr/bin/env bash
# Install daily pg_dump cron for deploy user (run once on VPS as root or deploy).
# Usage: sudo ./scripts/deploy/setup-backup-cron.sh
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="${APP_DIR:-/opt/outstaffingbot}"
CRON_LINE="15 3 * * * cd $APP_DIR && $APP_DIR/scripts/deploy/backup-postgres.sh >> /var/log/outstaffingbot-backup.log 2>&1"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run with sudo to install cron for $DEPLOY_USER" >&2
  exit 1
fi

mkdir -p /var/backups/outstaffingbot
chown "$DEPLOY_USER:$DEPLOY_USER" /var/backups/outstaffingbot
chmod 700 /var/backups/outstaffingbot

touch /var/log/outstaffingbot-backup.log
chown "$DEPLOY_USER:$DEPLOY_USER" /var/log/outstaffingbot-backup.log

chmod +x "$APP_DIR/scripts/deploy/backup-postgres.sh"

(crontab -u "$DEPLOY_USER" -l 2>/dev/null | grep -v 'backup-postgres.sh'; echo "$CRON_LINE") \
  | crontab -u "$DEPLOY_USER" -

echo "==> Cron installed for $DEPLOY_USER:"
crontab -u "$DEPLOY_USER" -l | grep backup-postgres.sh
