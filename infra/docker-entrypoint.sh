#!/bin/sh
# Applique le schéma (Alembic) avant de démarrer le process applicatif.
# Le process API ne fait plus de DDL (E2-S2) : la migration est la seule étape de
# schéma au démarrage du conteneur. RUN_MIGRATIONS_ON_BOOT=false la désactive (ex.
# replica en lecture seule, ou pipeline de déploiement qui migre séparément ; le
# worker Celery la désactive aussi pour éviter une double migration concurrente).
set -e

if [ "${RUN_MIGRATIONS_ON_BOOT:-true}" = "true" ]; then
    echo "[entrypoint] alembic upgrade head"
    alembic upgrade head
    # La migration 0011 crée le rôle runtime `app_runtime` sans mot de passe (hygiène secrets) ;
    # on pose son mot de passe depuis APP_DATABASE_URL (no-op si absente → repli dev DATABASE_URL).
    echo "[entrypoint] provisionnement du rôle runtime app_runtime"
    python -m app.db.provision_app_runtime
else
    echo "[entrypoint] RUN_MIGRATIONS_ON_BOOT=false — migrations ignorées"
fi

exec "$@"
