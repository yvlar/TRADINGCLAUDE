# TradingClaude — Cheatsheet commandes

*Référence humaine — ne fait pas partie du système `.claude/rules/`*

---

## Infrastructure Docker

```bash
# Démarrer l'infrastructure complète (copilote, postgres, qdrant, redis, celery)
docker-compose up -d

# Vérifier que le service est opérationnel
curl localhost:8000/healthz

# Logs du service copilote (streaming)
docker-compose logs -f copilote

# Logs Celery worker
docker-compose logs -f celery

# Arrêter l'infrastructure
docker-compose down

# Reconstruire après modification du code Python
docker-compose up -d --build copilote
```

---

## API — Requêtes courantes

```bash
# Analyse complète via SSE streaming (skills progressifs)
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BNS","workflow":"compounder_buffett"}'

# Screener multi-tickers (max 20)
curl -X POST localhost:8000/screen \
  -H "Content-Type: application/json" \
  -d '{"tickers":["BNS.TO","TD.TO","RY.TO"]}'

# Screener avec filtres (Sprint 58)
curl -X POST localhost:8000/screen \
  -H "Content-Type: application/json" \
  -d '{"tickers":["BNS.TO","TD.TO"],"min_composite_score":60,"filter_workflow":"value_graham"}'

# Extraire les ratios Yahoo Finance
curl -X POST localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BNS.TO"}'

# Historique par ticker
curl "localhost:8000/history?ticker=BNS"

# Recherche full-text cross-ticker (Sprint 73)
curl "localhost:8000/history?q=ACHAT"
curl "localhost:8000/history?q=WIDE+MOAT"

# Métriques d'observabilité
curl "localhost:8000/metrics?days=30"
curl "localhost:8000/telemetry/summary"
curl "localhost:8000/telemetry/costs"
curl "localhost:8000/telemetry/cache"
curl "localhost:8000/telemetry/latency"
curl "localhost:8000/telemetry/eval-drift"

# Rapport PDF par ticker (Sprint 63)
curl "localhost:8000/ticker-report/BNS?days=90" --output BNS-report.pdf

# Rapport PDF screener (Sprint 71)
curl "localhost:8000/screener-report?tickers=BNS.TO,TD.TO&workflow=value_graham" --output screener.pdf

# Composite score history (Sprint 57)
curl "localhost:8000/composite-history/BNS"

# Performance rétrospective (Sprint 39)
curl "localhost:8000/performance/BNS"

# Invalidation cache admin
curl -X DELETE "localhost:8000/cache/BNS" \
  -H "Authorization: Bearer VOTRE_TOKEN"

# Gestion clés API (admin only — Sprint 62)
curl -X POST localhost:8000/admin/keys \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"key-test","description":"test"}'

curl "localhost:8000/admin/keys" -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## Frontend React

```bash
# Démarrer le frontend (port 5173, proxy → API localhost:8000)
cd frontend && npm run dev

# Tests composants Vitest
cd frontend && npm test

# Tests avec rapport détaillé
cd frontend && npm run test -- --reporter=verbose

# Type-check sans build
cd frontend && npx tsc --noEmit

# Build production → dist/
cd frontend && npm run build
```

---

## Tests backend

```bash
# Tous les tests sauf e2e
python -m pytest tests/ --ignore=tests/e2e

# Tests d'intégration seulement
python -m pytest tests/ -m integration --ignore=tests/e2e

# Un fichier spécifique, verbeux
python -m pytest tests/test_graham_analysis.py -v

# Tests e2e Playwright (nécessite l'infrastructure active)
python -m pytest tests/e2e/ -m e2e

# Couverture de code
python -m pytest tests/ --ignore=tests/e2e --cov=app --cov-report=term-missing
```

---

## PostgreSQL — Requêtes utiles

```bash
# Connexion directe
docker-compose exec postgres psql -U copilote -d copilote

# 10 dernières analyses
docker-compose exec postgres psql -U copilote -d copilote \
  -c "SELECT ticker, defensive_score, cost_usd, created_at FROM analysis_history ORDER BY created_at DESC LIMIT 10;"

# Coût cumulé par ticker
docker-compose exec postgres psql -U copilote -d copilote \
  -c "SELECT ticker, COUNT(*) AS analyses, SUM(cost_usd) AS cout_total_usd FROM analysis_history GROUP BY ticker ORDER BY cout_total_usd DESC;"

# Composite score history (Sprint 57)
docker-compose exec postgres psql -U copilote -d copilote \
  -c "SELECT ticker, composite_score, recorded_at FROM composite_score_history ORDER BY recorded_at DESC LIMIT 20;"

# Clés API actives (Sprint 62)
docker-compose exec postgres psql -U copilote -d copilote \
  -c "SELECT id, name, description, created_at FROM api_keys WHERE is_active = true;"
```

---

## Celery

```bash
# Voir les tâches actives
docker-compose exec copilote celery -A app.workers.celery_app inspect active

# Déclencher le screener planifié manuellement (dimanche 11h00 UTC)
docker-compose exec copilote celery -A app.workers.celery_app call workers.tasks.run_scheduled_screener

# Déclencher le check eval drift
docker-compose exec copilote celery -A app.workers.celery_app call workers.tasks.run_eval_drift_check
```

---

## RAG Qdrant

```bash
# Vérifier la collection
curl localhost:6333/collections/investment_knowledge

# Ingestion du corpus RAG (scripts/)
python scripts/ingest_rag.py

# Compter les vecteurs
curl "localhost:6333/collections/investment_knowledge/points/count"
```

---

## Outils d'analyse (hors API)

```bash
# Backtesting Python (projet distinct de l'API)
python backtests/run_backtest.py --strategy swing --ticker QQQ

# Tests du backtest
python -m pytest backtests/tests/
```
