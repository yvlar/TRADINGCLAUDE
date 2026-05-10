# Backup PostgreSQL — Instructions

## Script

`infra/backup/backup_postgres.sh` effectue un `pg_dump` de la base `copilote`,
compresse le résultat en `.sql.gz` et supprime les fichiers de plus de 7 jours.

## Configuration requise

La variable `BACKUP_DIR` doit être définie avant l'exécution :

```bash
export BACKUP_DIR=/backups
```

Ou dans `.env` :
```
BACKUP_DIR=/backups
```

## Exécution manuelle

```bash
BACKUP_DIR=/backups bash infra/backup/backup_postgres.sh
# → /backups/copilote_YYYYMMDD_HHMMSS.sql.gz créé
```

## Planification via cron système

Ajouter dans la crontab du serveur homelab (`crontab -e`) :

```cron
0 3 * * * BACKUP_DIR=/backups bash /chemin/vers/infra/backup/backup_postgres.sh >> /var/log/copilote-backup.log 2>&1
```

Cela déclenche le backup chaque nuit à 03h00 (heure locale du serveur).

## Restauration

```bash
# Décompresser et restaurer
gunzip -c /backups/copilote_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i postgres psql -U copilote -d copilote
```
