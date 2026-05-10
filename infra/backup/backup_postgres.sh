#!/bin/bash
# backup_postgres.sh — pg_dump journalier + rotation 7 jours
# Usage : bash infra/backup/backup_postgres.sh
set -euo pipefail

: "${BACKUP_DIR:?Variable BACKUP_DIR manquante}"

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/copilote_${TIMESTAMP}.sql.gz"

docker exec postgres pg_dump -U copilote copilote | gzip > "$BACKUP_FILE"
echo "Backup créé : $BACKUP_FILE"

find "$BACKUP_DIR" -name "copilote_*.sql.gz" -mtime +7 -delete
echo "Rotation effectuée — fichiers > 7 jours supprimés"
