#!/bin/bash
# Backup FordLogger PostgreSQL database
# Usage: ./backup.sh [output_dir]
# Creates a timestamped SQL dump

set -euo pipefail

OUTPUT_DIR="${1:-.}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${OUTPUT_DIR}/fordlogger_backup_${TIMESTAMP}.sql.gz"

docker exec fordlogger-db-1 pg_dump -U fordlogger fordlogger | gzip > "$BACKUP_FILE"

echo "Backup saved to: $BACKUP_FILE"
echo "Restore with: gunzip -c $BACKUP_FILE | docker exec -i fordlogger-db-1 psql -U fordlogger fordlogger"
