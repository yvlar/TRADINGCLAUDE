---
paths:
  - "app/services/**"
  - "app/workers/**"
---

# Gotchas opérationnels — services et workers

## Quand cette règle s'applique

Lors de l'édition de `app/services/` (screener, cache, watchlist, etc.) ou `app/workers/` (tâches Celery).

## Règles

### Timeouts — ordre obligatoire dans `app/services/screener.py`

```python
_TIMEOUT_TICKER_S = 300   # timeout par ticker — DOIT être supérieur à CLAUDE_TIMEOUT_S
_TIMEOUT_GLOBAL_S = 600   # timeout global screener
```

`_TIMEOUT_TICKER_S` **doit être strictement supérieur** à `CLAUDE_TIMEOUT_S` (défini dans `.env`).

Symptôme si l'ordre est inversé : le ticker expire (`asyncio.TimeoutError`) avant que Claude puisse retourner une réponse, même si l'appel Claude lui-même aurait réussi.

Valeurs correctes : `_TIMEOUT_TICKER_S = 300`, `_TIMEOUT_GLOBAL_S = 600`, `CLAUDE_TIMEOUT_S ≤ 240`.

### Parallélisme screener — `max_parallel=3` pour `compounder_buffett`

Quand le screener multi-tickers (`POST /screen`) lance le workflow `compounder_buffett` en parallèle :

```python
semaphore = asyncio.Semaphore(3)  # max 3 tickers simultanés pour compounder_buffett
```

**Pourquoi 3 ?** `compounder_buffett` enchaîne 10 skills (~5 min/ticker). Avec plus de 3 tickers en parallèle simultané, le débit cumulé sature les limites de rate du modèle Claude (erreurs 429/529). Le retry exponentiel de `app/utils/retry.py` compense les pics ponctuels mais ne peut pas absorber un débit structurellement trop élevé.

Pour les workflows plus courts (`value_graham` = 5 steps), `max_parallel` peut être augmenté.

Voir `api-orchestrator.md` pour la liste complète des 10 steps de `compounder_buffett`.

---

<!-- Registre vivant — ajouter tout nouveau gotcha découvert en production :
     contexte, symptôme observé, valeur correcte. -->
