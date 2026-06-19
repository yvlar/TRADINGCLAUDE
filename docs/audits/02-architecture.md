# Audit — Dimension Architecture

> Produit par l'agent `audit-architecture`. Constats sourcés `fichier:ligne`. Hypothèses vérifiées dans [`00-synthese-hypotheses.md`](00-synthese-hypotheses.md).

## Résumé exécutif

L'architecture backend est mûre et bien pensée pour un SaaS multi-tenant. Les patterns async sont propres (asyncpg, httpx, redis — aucun appel bloquant détecté), la pile de middlewares (Bearer/JWT, CSRF double-submit, rate-limit, contexte tenant) est cohérente, et surtout **l'isolation Row-Level Security est centralisée** : la création du pool (`app/db/pool.py`) lie ensemble la résolution du DSN `app_runtime` (rôle NOBYPASSRLS) et l'application du contexte tenant, ce qui rend difficile de contourner l'isolation par accident. Les migrations sont versionnées (Alembic), la séparation des rôles DB (`copilote` pour les migrations, `app_runtime` pour le runtime) est correcte. Les faiblesses sont des **angles morts de résilience et d'observabilité** plutôt que des défauts structurels.

**Note globale : A− / B+.**

## Forces

- RLS centralisée et invariante : `app/db/pool.py` + `app/db/tenant_context.py` (ContextVar → GUC `app.tenant_id`).
- Séparation des rôles DB : migrations sous `copilote` (superuser), runtime sous `app_runtime` (NOSUPERUSER/NOBYPASSRLS) provisionné à l'entrypoint.
- Sécurité fail-closed en prod (secrets manquants → fail-fast), fail-open en dev, piloté par `APP_ENV`.
- Async/await partout pour l'I/O ; pas de `time.sleep()` ni de driver synchrone dans `app/`.
- Workers Celery isolés : chaque tâche crée son propre pool, Beat planifie sans chevauchement horaire.
- Dégradation gracieuse : Qdrant, Langfuse et Redis sont optionnels ; l'API répond même si l'un manque.

## Faiblesses observées

| ID | Sévérité | Constat | fichier:ligne | Impact |
|----|----------|---------|---------------|--------|
| G | Moyenne | `qdrant` n'a pas de `healthcheck` dans docker-compose ; l'API peut démarrer avant que Qdrant soit prêt | `docker-compose.yml` (service `qdrant` ≈ l.61-67, aucun bloc `healthcheck`) | RAG silencieusement indisponible au boot ; mitigé par try/except mais perte de citations |
| H | Moyenne | Les erreurs Langfuse sont avalées/loggées à bas niveau | `app/services/observability.py` (bloc try/except du tracer) | Pannes d'observabilité invisibles en prod |
| I | Moyenne | Skew possible du compteur de quota Redis si `increment()` échoue silencieusement (Redis down) | `app/services/quota_service.py` | Usage réel > compteur ; mitigé car la facturation Stripe lit `usage_events` (DB durable), pas Redis |
| J | Basse | Pas de validation de schéma de configuration : une faute de frappe dans une variable `.env` échoue silencieusement | `.env.example` / chargement config | Mauvaise config non détectée au boot |
| ~~K~~ | ~~Basse~~ → **Néant** | ~~`APP_DATABASE_URL` retombe silencieusement sur `DATABASE_URL`~~ — **INFIRMÉ** : le repli est **dev-only**, et **fail-closed (`RuntimeError`) hors dev** | `app/db/security_config.py:29-38` (repli gardé par `is_dev_environment()`), `app/db/pool.py:23-24` | Faux positif : c'est un invariant de sécurité, pas un défaut | **INFIRMÉE** |

## Améliorations priorisées

| ID | Action | Effort | Valeur |
|----|--------|--------|--------|
| G | Ajouter un `healthcheck` HTTP à `qdrant` + `depends_on: condition: service_healthy` | Faible | Moyenne |
| H | Logger les échecs Langfuse au niveau WARNING (pas DEBUG) + compteur d'erreurs | Faible | Moyenne |
| I | Tâche quotidienne de réconciliation compteur Redis ↔ agrégat `usage_events` | Moyen | Moyenne |
| J | Centraliser la config dans un `pydantic.BaseSettings` (validation fail-fast au boot) | Moyen | Haute |

> L'amélioration ex-K est **retirée** : le repli `APP_DATABASE_URL`→`DATABASE_URL` est déjà fail-closed hors dev (cf. verdict INFIRMÉE). À conserver tel quel.

## Hypothèses à vérifier

- **H-G** : le service `qdrant` de `docker-compose.yml` n'a aucun bloc `healthcheck`.
- **H-H** : les erreurs du tracer Langfuse dans `app/services/observability.py` sont attrapées et loggées sans niveau d'alerte (DEBUG/silence).
- **H-K** : `app/db/pool.py` fait retomber le DSN runtime sur `DATABASE_URL` quand `APP_DATABASE_URL` est absent.
