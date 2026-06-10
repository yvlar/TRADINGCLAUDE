# Sprint 201 — E5 : test d'intégration de la bascule de plan Stripe (webhook → quotas)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.87.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (200) a ajouté `tests/meta/test_no_direct_asyncpg_in_workers.py` : meta-test AST verrouillant l'invariant « aucun worker ne crée de connexion asyncpg hors du chokepoint `create_runtime_pool` » (8 formes de contournement détectées, immunité commentaires/docstrings). État courant complet (version, endpoints, fonctionnalités, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint BACKEND/OPS seul, test pur** (zéro `app/` modifié, zéro frontend, pas d'eval) : prouver que la bascule de plan déclenchée par un webhook Stripe est **visible par `QuotaService` sans redémarrage**. La moitié webhook → `tenants.plan` est DÉJÀ couverte en intégration ; la moitié `tenants.plan` → `QuotaService._resolve_limits` ne l'est pas — c'est le chaînon manquant de la boucle de facturation E5.

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.87.0)
2. `.claude/rules/tests-pyramide.md` (niveau **intégration** ; marqueur `@pytest.mark.integration` ; vraie DB requise).
3. `.claude/rules/conventions-python.md` (type hints partout, docstrings FR du WHY, imports groupés).
4. **Code de référence à re-vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - `tests/integration/test_stripe_billing_webhook.py:81` — test existant `test_webhook_signe_passe_le_tenant_a_pro_et_forge_rejete` : webhook signé → `tenants.plan='pro'` + rejet d'une signature forgée, sous vraie DB migrée (`alembic upgrade head`) et rôle NOSUPERUSER. **Patron et point d'extension naturel** — vérifié S200.
   - `app/services/stripe_service.py` — `handle_event` (`:247`, claim+mutation dans une transaction), libellé `"customer.subscription.updated"` (`:41`), `UPDATE tenants SET plan = $1 WHERE id = $2::uuid` (`:315`) — vérifiés `grep` S200.
   - `app/services/quota_service.py` — `_resolve_limits` (`:89`) lit le plan par `SELECT pl.plan, pl.max_analyses_per_month, …` (`:93`) `JOIN plan_limits pl ON pl.plan = t.plan` (`:95`) — **lecture DB à chaque appel, pas de cache de plan** ; vérifié S200.
   - `tests/services/test_stripe_service.py` — unités `handle_event` mockées (aucune mention de `QuotaService` — gap confirmé S200) ; `tests/services/test_quota_service.py` — unités quota.

---

## TÂCHE — Sprint 201 : prouver webhook Stripe → bascule de plan → quotas, sans redémarrage

**Objectif** : S172/S173 ont livré la facturation Stripe ; le test d'intégration S174+ prouve webhook → `tenants.plan`. Mais **aucun test ne prouve la promesse produit complète** : après `customer.subscription.updated` (free→pro), un appel `QuotaService` du même process voit la **nouvelle** limite (`max_analyses_per_month` du plan pro) — et symétriquement au downgrade (`customer.subscription.deleted` → repli free). Si un futur refactor introduisait un cache de plan en mémoire dans `QuotaService` ou `_resolve_limits`, la bascule resterait invisible jusqu'au redémarrage : régression silencieuse de facturation qu'aucun test actuel ne détecterait.

### Spécification

1. **Étendre `tests/integration/test_stripe_billing_webhook.py`** (ou fichier frère `test_stripe_plan_to_quota.py` dans `tests/integration/` — au choix selon la lisibilité, même patron de fixtures).
2. **Test obligatoire (upgrade)** : tenant en plan `free` → poster l'événement signé `customer.subscription.updated` (plan pro) via le même chemin que le test existant → asserter (a) `tenants.plan = 'pro'` (parité existante) ET (b) `QuotaService._resolve_limits(tenant_id)` (ou `read_status()`) retourne les limites du plan **pro** (`max_analyses_per_month` de `plan_limits` pro), **sans recréer le service ni le pool** — le même process voit la bascule.
3. **Test obligatoire (downgrade)** : depuis l'état pro, poster `customer.subscription.deleted` → asserter le repli `tenants.plan = 'free'` ET les limites free vues par `QuotaService`.
4. **Contraintes** : Redis du compteur mensuel mocké ou neutralisé si `read_status` l'exige (le sprint prouve la résolution de **plan**, pas le compteur) ; aucun appel réseau Stripe réel (événement construit + signé localement comme dans le test existant) ; marqueur `@pytest.mark.integration` ; type hints partout, docstrings FR du WHY.

### Tests / validation
- **Backend** : `pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `ruff check app/ tests/` (+ `mypy app/ --ignore-missing-imports` — aucun `app/` touché → inchangé).
- **Pas de frontend, pas d'eval**.
- **Preuve d'acceptation observable** : le test upgrade **échoue** si on simule un cache de plan (ex. mémoïser temporairement le résultat de `_resolve_limits` avant la bascule, ou réécrire `tenants.plan` à `free` juste avant l'assertion quota) — vérifier en injectant la régression factice puis en la retirant (restauration byte-identique).
- **⚠️ Pas de PostgreSQL dans le conteneur web** : les tests `tests/integration/` y sont **skippés** (comme la matrice RLS) — le gate réel est le CI. Constater localement la collection + le skip propre, et dire explicitement que la preuve verte complète vient du CI.

### Note environnement conteneur web
`pytest`/`ruff` tournent depuis `.venv` (préparé par le hook `SessionStart`). Si des imports manquent (`stripe` a manqué en S196/S199/S200), relancer `.venv/bin/pip install -r requirements.txt`.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — voir plan directeur §7-§8)

### Sprint 202 — Frontend : carte « Quota mensuel » sur la page Facturation
**Objectif** : afficher l'état courant du quota mensuel d'analyses (plan, `used`/`limit`/`remaining`, `reset_at`) dans une carte de la page `/facturation`, en réutilisant le client `getQuota()` existant.
**Complexité** : Faible.
**Justification** : `GET /quota` existe (S184) et alimente le `QuotaBadge` du header, mais la page Facturation — lieu naturel de gestion d'abonnement — n'affiche pas l'état du quota. Additif pur, aucun backend à créer.
**Référence** : `GET /quota` → `app/api/endpoints/quota.py` (`get_quota` `:19`) — vérifié `grep` S200 ; client typé `frontend/src/api/quota.ts` (`getQuota()` `:5`, type `QuotaStatus` importé `:2`) — vérifié S200 ; `frontend/src/pages/BillingPage.tsx` (page cible existante, vérifié S200) ; la carte est **à créer**.

### Sprint 203 — Ops : test d'isolation RLS `usage_events` sur le chemin orchestrateur métré
**Objectif** : prouver que `_emit_usage_events` (orchestrateur) ne peut pas écrire un événement `usage_events` sous un tenant B depuis un contexte tenant A — gap couvert par la RLS PostgreSQL mais sans test d'intégration ciblé sur le chemin d'émission.
**Complexité** : Moyenne.
**Justification** : `usage_events` est la table de facturation (S166) ; une fuite cross-tenant serait une anomalie de facturation silencieuse. Les tests RLS S163-S165 couvrent la policy, pas l'émission depuis l'orchestrateur sous un tenant scopé.
**Référence** : `app/orchestrator/core.py` — `_emit_usage_events` (`:462`, sites d'appel `:1098` et `:1677`) — vérifié `grep` S200 ; `app/db/tenant_context.py` — `tenant_scope` (`:65`) — vérifié S200 ; le test est **à créer**.

### Sprint 204 — Frontend : page d'administration des tenants (super-admin)
**Objectif** : page `/admin/tenants` listant les tenants (nom, plan, `stripe_customer_id` tronqué, date de création) via un endpoint `GET /admin/tenants` à créer, accessible admin uniquement.
**Complexité** : Moyenne.
**Justification** : aucune UI n'expose la liste des tenants — l'administrateur doit inspecter la DB. Utile pour l'onboarding B2B et le support.
**Référence** : `app/api/endpoints/admin.py` — `_require_admin` (`:58`) — vérifié `grep` S200 ; `app/services/user_service.py` — `UserService` (`:22`) — vérifié S200 ; la route et la page sont **à créer**.

### Sprint 205 — Ops : étendre le garde anti-contournement asyncpg à `app/` entier (allowlist)
**Objectif** : généraliser le meta-test S200 de `app/workers/` à tout `app/`, avec allowlist explicite des deux usages légitimes — le chokepoint lui-même et le provisioning admin.
**Complexité** : Faible.
**Justification** : S200 verrouille les workers ; un endpoint ou service pourrait encore créer un pool direct (contournant garde insecure-creds + hook RLS). L'allowlist rend l'invariant global vérifiable sans faux positif. Alternative à évaluer en session : règle lint `ruff` banned-api (couverture équivalente, per-file-ignores) — trancher AVANT d'implémenter.
**Référence** : scan AST réutilisable `tests/meta/test_no_direct_asyncpg_in_workers.py` (`_scan_violations`) — livré S200 ; usages légitimes à allowlister : `app/db/pool.py:25` (`asyncpg.create_pool` du chokepoint) et `app/db/provision_app_runtime.py:47` (`asyncpg.connect(admin_url)`, provisioning admin) — vérifiés `grep` S200 ; l'extension est **à créer**.

---

## Template de démarrage

```
Tu es un développeur Python senior (backend/ops) sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.87.0),
.claude/rules/tests-pyramide.md, .claude/rules/conventions-python.md.
Sprint actif : 201 — E5 : test d'intégration de la bascule de plan Stripe (webhook → quotas).
COMMENCE PAR RE-GREP : tests/integration/test_stripe_billing_webhook.py (test existant :81, patron),
stripe_service.handle_event (:247), UPDATE tenants SET plan (:315), quota_service._resolve_limits (:89).
LIVRABLE : 2 tests d'intégration (upgrade free→pro, downgrade pro→free) prouvant que QuotaService
voit la bascule de plan SANS redémarrage, dans le même process que le webhook.
GATES : pytest (hors e2e/evals) + ruff. Pas de frontend, pas d'eval. Pas de PG dans le conteneur
web → collection + skip propre localement, preuve verte au CI.
PREUVE : injecter une régression factice (cache de plan simulé) → test rouge → retirer.
```
