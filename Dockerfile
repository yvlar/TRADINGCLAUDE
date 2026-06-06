FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
# Migrations versionnées (E2) appliquées par l'entrypoint avant le démarrage uvicorn.
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/
COPY infra/docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
