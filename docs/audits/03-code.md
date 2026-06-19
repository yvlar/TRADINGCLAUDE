# Audit — Dimension Code

> Produit par l'agent `audit-code`. Constats sourcés `fichier:ligne`. Hypothèses vérifiées dans [`00-synthese-hypotheses.md`](00-synthese-hypotheses.md).

## Résumé exécutif

La qualité de code est élevée et homogène : contrat `SkillBase` clair, Pydantic v2 partout, retry/backoff centralisé (429/529), gestion d'erreurs avec correlation IDs sanitisés, et une **pyramide de tests fournie** (~237 fichiers pytest couvrant api/services/skills/orchestrator/workers, plus e2e Playwright). Les conventions bilingues FR/EN sont respectées. Deux axes de dette ressortent après vérification : le **type-checking n'est pas bloquant** (mypy `strict=false`, modules entiers `ignore_errors`) et un **repli de tarif silencieux** pour un modèle Claude inconnu.

> ⚠️ **Correction post-vérification (voir [`00-synthese-hypotheses.md`](00-synthese-hypotheses.md))** : deux constats initiaux ont été **infirmés/atténués** par l'agent vérificateur. (1) La « lacune d'isolation RLS cross-tenant » (H-L) est **FAUSSE** — le test `tests/integration/test_rls_isolation.py::test_matrice_isolation_cross_tenant` couvre explicitement « tenant A ne lit/écrit pas les données de B » sur 6 tables, plus ~15 tests `*_rls.py`. (2) Le `except Exception` de `price_alert_service.py` (H-N) **n'avale pas** l'erreur : il émet la stacktrace via `logger.exception` (ERROR) ; seule subsiste l'absence de correlation ID côté workers.

**Note globale : A− / B+** (révisée à la hausse après retrait du faux positif RLS).

## Forces

- Contrat skill propre : `app/skills/base.py` (SkillBase, `get_system_prompt()` avec `cache_control`, `get_citations()` RAG).
- Retry exponentiel avec jitter sur 529 : `app/utils/retry.py` ; température 0 par défaut (reproductibilité).
- Sanitisation d'erreurs centralisée avec correlation IDs : `app/utils/error_sanitization.py` (aucune trace brute exposée au client).
- Pyramide de tests substantielle : `tests/` (api/ services/ skills/ orchestrator/ workers/ db/ integration/ e2e/ load/ evals/) ; appels Claude systématiquement mockés (`call_claude_with_retry`).
- Pydantic v2 idiomatique (`@field_validator`, `@computed_field`, `ConfigDict`).

## Faiblesses observées

| ID | Sévérité | Constat | fichier:ligne | Impact | Verdict vérif. |
|----|----------|---------|---------------|--------|----------------|
| ~~L~~ | ~~Haute~~ → **Néant** | ~~Couverture d'isolation RLS cross-tenant mince~~ — **INFIRMÉ** : couverture présente | `tests/integration/test_rls_isolation.py:126` (`test_matrice_isolation_cross_tenant`, 6 tables) + ~15 `*_rls.py` | Faux positif retiré | **INFIRMÉE** |
| M | Moyenne | `mypy strict=false` + `disable_error_code` + 11 modules `ignore_errors=true` → type-check non bloquant en CI | `pyproject.toml:27,30` + override `ignore_errors=true` | Erreurs de typage s'accumulent silencieusement ; dérive de contrats | CONFIRMÉE |
| N | Basse (révisée) | `except Exception` sans correlation ID dans des services de fond — **mais log ERROR via `logger.exception`, pas avalé** | `app/services/price_alert_service.py:71-72` | Traçabilité worker→requête imparfaite (pas une perte d'erreur) | PARTIELLE |
| O | Moyenne | Modèle Claude inconnu → repli silencieux sur le tarif `claude-sonnet-4-6` (pas d'erreur) | `app/utils/costs.py:29` | Faute de frappe sur `CLAUDE_MODEL` → coût mal estimé sans alerte | CONFIRMÉE |
| P | Basse | `loop.run_in_executor(None, …)` pour yfinance (lib synchrone) en pool de threads | `app/skills/tier1/yahoo_finance.py` | Acceptable mais non idéal en charge ; documenté | — |

## Améliorations priorisées

| ID | Action | Effort | Valeur |
|----|--------|--------|--------|
| M | Activer `mypy strict=true` graduellement par module ; retirer les `ignore_errors` un à un | Élevé | Haute |
| O | Lever `ValueError` si le modèle n'est pas dans `PRICING` (échouer franchement plutôt que sous-estimer) | Faible | Moyenne |
| N | Propager un correlation ID dans les tâches Celery (workers) pour corréler log worker ↔ requête | Faible | Basse |

> L'amélioration RLS (ex-L) est **retirée** : la couverture existe déjà (cf. verdict INFIRMÉE).

## Hypothèses à vérifier

- **H-L** : le répertoire `tests/db/` contient très peu de fichiers et n'inclut pas de test explicite « tenant A ne lit pas les données de tenant B ».
- **H-M** : `pyproject.toml` configure `mypy strict=false` avec `disable_error_code` et au moins un bloc `ignore_errors=true`.
- **H-N** : `app/services/price_alert_service.py` contient un `except Exception` qui avale l'erreur sans correlation ID.
- **H-O** : `app/utils/costs.py:29` fait `PRICING.get(model, PRICING["claude-sonnet-4-6"])` — repli silencieux sur le tarif sonnet pour tout modèle inconnu.
