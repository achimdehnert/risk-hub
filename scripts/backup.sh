#!/bin/bash
# risk-hub database + media backup
# Runs daily via cron: 0 2 * * * /home/deploy/projects/risk-hub/scripts/backup.sh
set -euo pipefail

BACKUP_DIR="/opt/backups/risk-hub"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=14

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# PostgreSQL dump via Docker
docker exec risk_hub_db pg_dump \
  -U risk_hub \
  -d risk_hub \
  -Fc \
  > "$BACKUP_DIR/risk_hub_${TIMESTAMP}.dump"

echo "[$(date)] DB backup: risk_hub_${TIMESTAMP}.dump ($(du -sh "$BACKUP_DIR/risk_hub_${TIMESTAMP}.dump" | cut -f1))"

# Media files backup
if docker volume inspect risk_hub_media &>/dev/null; then
  docker run --rm \
    -v risk_hub_media:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf "/backup/media_${TIMESTAMP}.tar.gz" -C /data .
  echo "[$(date)] Media backup: media_${TIMESTAMP}.tar.gz ($(du -sh "$BACKUP_DIR/media_${TIMESTAMP}.tar.gz" | cut -f1))"
fi

# Cleanup old backups
find "$BACKUP_DIR" -name "*.dump" -mtime +${KEEP_DAYS} -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +${KEEP_DAYS} -delete

echo "[$(date)] Cleanup: removed backups older than ${KEEP_DAYS} days"
echo "[$(date)] Backup complete. Available:"
ls -lh "$BACKUP_DIR" | tail -10
