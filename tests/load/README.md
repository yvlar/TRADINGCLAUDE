# Tests de charge — Sprint 19

Tests de charge Locust pour valider la capacité de l'API avant tout déploiement public.

---

## Prérequis

```bash
pip install -r requirements-dev.txt
# locust >= 2.20.0 est inclus
```

L'API doit être démarrée et accessible :

```bash
docker-compose up -d
curl localhost:8000/healthz  # doit retourner {"status": "ok"}
```

---

## Scénarios

| Classe | Endpoint | Poids | Attente |
|--------|----------|-------|---------|
| `AnalyzeUser` | `POST /analyze` (Graham BNS) | 70 % | 1–3 s |
| `ScreenUser` | `POST /screen` (5 banques) | 20 % | 2–5 s |
| `TelemetryUser` | `GET /telemetry/summary` + `/cache` | 10 % | 5–10 s |

---

## Commandes d'exécution

### Palier 10 utilisateurs (référence de base)

```bash
locust --headless -f tests/load/locustfile.py \
  --host http://localhost:8000 \
  -u 10 -r 2 --run-time 2m \
  --csv tests/load/results_10u
```

### Palier 25 utilisateurs

```bash
locust --headless -f tests/load/locustfile.py \
  --host http://localhost:8000 \
  -u 25 -r 5 --run-time 2m \
  --csv tests/load/results_25u
```

### Palier 50 utilisateurs (stress)

```bash
locust --headless -f tests/load/locustfile.py \
  --host http://localhost:8000 \
  -u 50 -r 5 --run-time 2m \
  --csv tests/load/results_50u
```

### Interface web interactive (port 8089)

```bash
locust -f tests/load/locustfile.py --host http://localhost:8000
# Ouvrir http://localhost:8089 dans un navigateur
```

---

## Variables d'environnement Locust

```bash
export LOCUST_HOST=http://localhost:8000
export LOCUST_USERS=10
export LOCUST_SPAWN_RATE=2
export LOCUST_RUN_TIME=2m

locust --headless -f tests/load/locustfile.py \
  --csv tests/load/results_${LOCUST_USERS}u
```

---

## Critères de succès

| Utilisateurs | p95 /analyze | p95 /screen | Taux erreur |
|-------------|-------------|-------------|-------------|
| 10 | < 5 000 ms | < 15 000 ms | < 1 % |
| 25 | < 8 000 ms | < 20 000 ms | < 2 % |
| 50 | < 15 000 ms | < 30 000 ms | < 5 % |

> Ces seuils supposent que le cache Redis est actif et chaud (analyses BNS déjà en cache).
> Le premier palier à 10 utilisateurs chauffe le cache — les paliers suivants bénéficient du circuit-court.

---

## Lecture des résultats CSV

Locust génère trois fichiers CSV :

```
tests/load/results_10u_stats.csv        # Métriques agrégées par endpoint
tests/load/results_10u_stats_history.csv # Séries temporelles
tests/load/results_10u_failures.csv     # Détail des erreurs
```

Colonne clé dans `_stats.csv` : `95%` (p95 en ms), `Failure Count`, `Requests/s`.

---

## Exécution avec authentification

Si `API_KEY` est défini dans `.env`, ajouter le header dans `locustfile.py` :

```python
# Dans chaque UserClass :
def on_start(self) -> None:
    import os
    api_key = os.getenv("API_KEY", "")
    if api_key:
        self.client.headers["Authorization"] = f"Bearer {api_key}"
```

Ou utiliser la variable `LOCUST_HEADLESS_AUTH` avec un proxy.

---

## Notes

- Le rate limiting (10 req/min/IP) peut déclencher des 429 à 50+ utilisateurs si tous partagent la même IP. Augmenter `RATE_LIMIT_PER_MIN` dans `.env` pour les tests de charge.
- Locust ne nécessite pas Docker — il tourne directement depuis le host vers l'API conteneurisée.
- Les résultats CSV sont ignorés par `.gitignore` (`tests/load/results_*.csv`).
