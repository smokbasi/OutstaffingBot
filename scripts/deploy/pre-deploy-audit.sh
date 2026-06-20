#!/usr/bin/env bash
# Read-only аудит shared VPS перед деплоем OutstaffingBot.
# Запуск на сервере: bash scripts/deploy/pre-deploy-audit.sh
# Не изменяет конфигурацию.
set -euo pipefail

echo "=== OutstaffingBot pre-deploy audit ($(date -Iseconds)) ==="
echo ""

echo "--- Listening ports ---"
ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || true
echo ""

echo "--- Docker containers ---"
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo "(docker not available)"
echo ""

echo "--- systemd: vspomni / x-ui / nginx ---"
for svc in vspomni vspomni-dashboard x-ui nginx; do
  systemctl is-active "$svc" 2>/dev/null && echo "$svc: active" || echo "$svc: inactive/missing"
done
echo ""

echo "--- Protected paths (must exist for vspomni) ---"
for p in /opt/vspomni_bot /usr/local/x-ui /etc/nginx; do
  [[ -e "$p" ]] && echo "OK  $p" || echo "MISS $p"
done
echo ""

echo "--- OutstaffingBot target ---"
[[ -d /opt/outstaffingbot ]] && echo "OK  /opt/outstaffingbot" || echo "MISS /opt/outstaffingbot (not deployed yet)"
[[ -f /opt/outstaffingbot/.env ]] && echo "OK  /opt/outstaffingbot/.env" || echo "MISS /opt/outstaffingbot/.env"
echo ""

echo "--- UFW ---"
ufw status 2>/dev/null || echo "(ufw not available)"
echo ""

echo "=== Audit complete. See docs/SERVER_SECURITY.md §10 for checklist ==="
