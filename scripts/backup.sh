#!/bin/bash
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# DB backup
docker compose exec -T postgres pg_dump -U ${POSTGRES_USER:-manytracker} ${POSTGRES_DB:-manytracker} | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Media backup
tar czf "$BACKUP_DIR/media_$TIMESTAMP.tar.gz" -C . media/

# Keep only last 14 days
find $BACKUP_DIR -name "*.gz" -mtime +14 -delete

echo "Backup complete: $TIMESTAMP"
