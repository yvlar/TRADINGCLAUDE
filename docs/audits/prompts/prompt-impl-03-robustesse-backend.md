# Prompt d'implémentation 03 — Robustesse backend (pricing, healthcheck, observabilité)

> **Origine** : audit `docs/audits/02-architecture.md` (**G**, **H**) + `docs/audits/03-code.md` (**O**) ; hypothèses **H-O / H-G / H-H** confirmées dans `docs/audits/00-synthese-hypotheses.md`.
> **Priorité** : P2. **Domaine** : code + infra + observabilité. **Effort** : faible, 1 session.

---

## Contexte

Trois durcissements indépendants et de faible risque : (1) un modèle Claude inconnu retombe
silencieusement sur le tarif sonnet (coût mal estimé sans alerte) ; (2) Qdrant n'a pas de healthcheck
Docker (l'API peut démarrer avant qu'il soit prêt) ; (3) les échecs Langfuse sont loggés en DEBUG
(invisibles en prod).

## LECTURE OBLIGATOIRE (avant de coder)

1. `CLAUDE.md` et `ROADMAP.md`.
2. `.claude/rules/api-architecture.md` — modèle via env, `cost_usd`, stack infra (Qdrant/Langfuse optionnels).

## Périmètre

Trois changements ciblés ci-dessous. Aucun refactor élargi. Ne pas toucher à la logique des skills.

## Tâche détaillée

### H-O — `app/utils/costs.py` : échouer sur modèle inconnu

- Ligne **29** : `pricing = PRICING.get(model, PRICING["claude-sonnet-4-6"])` → remplacer par une levée
  explicite : `raise ValueError(f"Modèle inconnu pour le pricing : {model}")` si `model not in PRICING`.
- ⚠️ **Test existant à transformer** : `tests/skills/test_skill.py:62`
  `test_modele_inconnu_fallback_sur_sonnet` **asserte aujourd'hui le fallback** — il cassera. Le
  réécrire en `test_modele_inconnu_leve_valueerror` (`pytest.raises(ValueError)`).
- **Garde-fou** : vérifier que les modèles réellement utilisés sont dans `PRICING` — `CLAUDE_MODEL`
  (défaut `claude-sonnet-4-6`) et `CLAUDE_HAIKU_MODEL` (défaut `claude-haiku-4-5-20251001`) résolus dans
  `app/api/main.py:121`. Les 15 appelants tier2 passent tous `self._model` → aucun littéral à risque,
  mais confirmer par `grep`.

### H-G — `docker-compose.yml` : healthcheck Qdrant

- Le service `qdrant` (image `qdrant/qdrant:v1.9.0`) n'a **pas** de bloc `healthcheck` (contrairement à
  `postgres` qui utilise `pg_isready`).
- Ajouter un `healthcheck` (endpoint HTTP Qdrant `/healthz` ou TCP sur 6333) avec `interval`/`retries`.
- Passer la dépendance de `copilote` sur `qdrant` de `condition: service_started` à
  `condition: service_healthy`.

### H-H — `app/services/observability.py` : Langfuse en WARNING

- Lignes **99-102** : le `except Exception` spécifique au span Langfuse logge en `logger.debug(...)`.
  Remonter à `logger.warning(...)` (garder le message FR, ne pas exposer de secret). Ne pas toucher au
  `except` externe `:140-145` (déjà en `logger.exception`).

## Tests & vérification

- `python -m pytest tests/skills/test_skill.py` (nouveau test ValueError) puis suite complète
  `tests/ --ignore=tests/e2e --ignore=tests/evals` verte.
- `docker compose config` valide le YAML ; revue manuelle du healthcheck.

## Critères d'acceptation

- [ ] `calculate_cost` lève `ValueError` sur modèle absent de `PRICING` ; test mis à jour et vert.
- [ ] `qdrant` a un healthcheck ; `copilote` attend `service_healthy`.
- [ ] Échec Langfuse loggé en WARNING.
- [ ] Suite de tests verte, aucune régression.

## Branche & commit

- Branche : `claude/impl-robustesse-backend` (depuis `dev`). PR **base `dev`**. Push à confirmer.
