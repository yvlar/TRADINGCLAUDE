# Sprint 189 — E5-S8 : bornes de quota visibles à l'erreur 429 (UX d'upgrade)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.75.0 — transformation B2B/SaaS, phase P0→P1)

Le dernier sprint (188, Refactor) a extrait `for_each_tenant()` (`app/workers/tenant_iteration.py`) : le squelette « énumère les tenants → boucle → `tenant_scope(tenant_id)` → try/except best-effort log-and-continue », dupliqué 5× dans `app/workers/tasks.py`, est désormais un helper async unique (callback async, agrégation à l'appelant) — plus de divergence silencieuse possible (un chemin qui oublierait le scope RLS ou avorterait au 1er échec). État courant complet (version, endpoints, fonctionnalités actives, compteurs de tests) : **`ROADMAP.md`** (source unique — ne pas le recopier ici).

> **Sprint MIXTE backend (petit) + frontend (cœur)** : transformer le mur de quota (`429`) en point de conversion. Aujourd'hui le `429` ne porte qu'un `detail` texte (`app/utils/quota_http.py:12`) et le `QuotaBanner` (`frontend/src/components/QuotaBanner.tsx:13`) n'affiche que ce message brut, sans lien vers `/facturation` ni contexte (plan courant, borne atteinte, restant). GATES : backend `pytest` + `ruff` + `mypy app/ --ignore-missing-imports` ; frontend `npm test` (Vitest) + `npm run typecheck` (0 erreur) + ESLint (0/0). ⚠️ Le venv web peut manquer des deps → `.venv/bin/pip install -r requirements.txt && .venv/bin/pip install mypy` si un import échoue (`stripe`, `mypy` notamment). **Pas d'eval** (UX d'erreur + enrichissement de corps `429` — aucun prompt de skill ni l'orchestrateur de skills touché).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` (déjà injecté) · `ROADMAP.md` (v10.75.0)
2. `.claude/rules/conventions-frontend.md` (React 18, TS strict zéro `any`, `data-testid`, test composant happy+erreur — c'est le cœur du sprint) **et** `.claude/rules/tests-pyramide.md` (le `429` enrichi exige un test d'intégration d'endpoint ; le `QuotaBanner` enrichi exige un test composant). Accessoirement `.claude/rules/api-architecture.md` si tu enrichis le corps `429` côté backend (assainissement des réponses d'erreur, cf. Sprint 125 — ne jamais fuiter `str(exc)`).
3. **Code de référence à vérifier en début de session (anti-hallucination — les n° de ligne DÉRIVENT, re-grep obligatoire)** :
   - **L'exception métier** : `QuotaExceededError` (`app/services/quota_service.py:64`, vérifié cette session) porte **déjà** `plan: str`, `used: int`, `limit: int`, `retry_after_s: int | None` — la donnée structurée existe à la source, elle est juste **aplatie en texte** au mapping HTTP. Levée à `quota_service.py:130` (analyses/mois, `retry_after_s` temporel) et `:201` (taille screener, `retry_after_s=None`).
   - **Le mapping `429` (à enrichir)** : `quota_exceeded_http(err)` (`app/utils/quota_http.py:9`, vérifié) construit `HTTPException(status_code=429, detail=err.message, headers={"Retry-After": …})`. Le `detail` est un **string** → l'enrichir en `dict` structuré (`{message, plan, used, limit, remaining}`) pour que le front affiche plus qu'une phrase. Appelé à 3 sites : `app/api/endpoints/analyze_stream.py:80`, `app/api/endpoints/screen.py:91`, et le SSE generator (cf. `analyze_stream.py:85` threadé) — **un seul point à changer** (le helper), les 3 appelants en héritent.
   - **Le composant front (à enrichir)** : `QuotaBanner` (`frontend/src/components/QuotaBanner.tsx:13`, vérifié) ne prend qu'une prop `message: string` ; `isQuotaError(err)` (`:4`) teste `err instanceof ApiError && err.status === 429`. Consommé par `frontend/src/pages/AnalyzePage.tsx`, `ScreenerPage.tsx`, `BillingPage.tsx` (vérifié `grep -rln QuotaBanner`). ⚠️ Vérifier comment `ApiError` (`frontend/src/api/client.ts`) expose le corps `detail` (string aujourd'hui ; après enrichissement, un objet) — **le contrat de parsing d'erreur du client est sur le chemin critique** : si `ApiError` ne porte pas le corps JSON structuré, le sprint doit d'abord l'y exposer (à VÉRIFIER avant d'écrire le composant).

---

## TÂCHE — Sprint 189 : E5-S8, bornes de quota visibles à l'erreur 429

**Objectif** : quand `/analyze-stream` ou `/screen` renvoie `429` (quota dépassé), afficher côté frontend un message d'upgrade **ciblé** (plan courant, borne atteinte, restant=0, lien vers `/facturation`) plutôt qu'une phrase générique — transformer le blocage en incitation à l'upgrade **au moment du mur**, complément du badge S184 (visibilité continue).

### Spécification

1. **Backend — enrichir le corps `429`** (`app/utils/quota_http.py`) : remplacer `detail=err.message` (string) par un `detail` **structuré** (`dict`) portant `message`, `plan`, `used`, `limit`, et `remaining` (= `max(0, limit − used)`). Conserver le header `Retry-After` (borne temporelle). **Ne pas fuiter** d'info sensible (cohérent Sprint 125 — uniquement les champs de quota déjà destinés au client). Les 3 sites appelants héritent du changement (un seul helper à toucher).
2. **Frontend — `ApiError` porte le corps structuré** : VÉRIFIER d'abord que `ApiError` (`frontend/src/api/client.ts`) expose le `detail` JSON ; si non, l'y ajouter (typé, zéro `any`) — prérequis pour que `QuotaBanner` lise plan/borne/restant.
3. **Frontend — enrichir `QuotaBanner`** : afficher le plan courant, la borne atteinte (`used/limit`), et un **lien/bouton vers `/facturation`** (CTA d'upgrade) en plus du message. `data-testid` sur le lien. Rétrocompat : si le corps n'est pas structuré (vieux cache, autre 429), retomber proprement sur le message seul (pas de crash).
4. **Garder les 3 pages consommatrices vertes** (AnalyzePage, ScreenerPage, BillingPage) — l'enrichissement est additif (nouvelle prop optionnelle ou objet), pas une rupture de signature.

### Tests / validation
- **Backend** : test d'intégration sur le `429` enrichi — corps `detail` porte `plan/used/limit/remaining` cohérents, `Retry-After` présent pour la borne temporelle / absent pour la borne screener (`retry_after_s=None`).
- **Frontend** : test composant `QuotaBanner` — happy path (plan + borne + lien `/facturation` rendus, `data-testid` cliquable) + cas dégradé (corps non structuré → message seul, pas de crash).
- Gates : backend `pytest` + `ruff` + `mypy` ; frontend Vitest + `tsc --noEmit` + ESLint. **Pas d'eval**.
- **Preuve d'acceptation observable** : un `429` sur `/analyze-stream` renvoie un corps JSON `{detail: {message, plan, used, limit, remaining}}` ; le `QuotaBanner` rendu affiche « plan FREE · M/M analyses » + un lien `/facturation`.

---

## SPRINTS SUGGÉRÉS (suite E5/Ops — facturation/SaaS, voir plan directeur §7-§8)

### Sprint 190 — E5-S9 : nettoyage du cache react-query à la déconnexion (hygiène cross-tenant)
**Objectif** : vider le cache react-query (`queryClient.clear()`) lors du `logout` pour qu'une re-connexion sous un autre tenant sur la même session SPA ne serve jamais de données périmées du tenant précédent (`usage`, `usage-reporting`, etc.).
**Complexité** : Faible.
**Justification** : finding cross-tenant de la revue S184 — généralisé. S184 a scopé `['quota', tenantId]` par tenant au cas par cas ; les clés `['usage']`/`['usage-reporting']` restent non scopées et non purgées au logout. Une purge unique au logout couvre tout le cache d'un coup.
**Référence** : `logout` défini dans `frontend/src/contexts/AuthContext.tsx:56` (vérifié cette session, `useCallback`) — il n'importe **pas** `useQueryClient`. Le `QueryClient` global est instancié dans `frontend/src/main.tsx:7` et fourni via `QueryClientProvider` à `frontend/src/main.tsx:21` (vérifié). L'injection de `useQueryClient` dans `AuthProvider` + l'appel de purge au logout sont **à créer**.

### Sprint 191 — Ops : `FORCE RLS` vérifié par test sur les 7 tables (verrou anti-régression)
**Objectif** : asserter en CI que les 7 tables RLS portent bien `relforcerowsecurity = true` (`pg_class`), pour qu'une future migration qui ajoute une table RLS sans `FORCE` (ou qui le retire) échoue immédiatement.
**Complexité** : Faible.
**Justification** : §2.3 d'OWASP repose sur `FORCE` ; aujourd'hui c'est prouvé indirectement (la matrice d'isolation échouerait), jamais asserté directement. Un test ciblé rend l'invariant explicite et auto-documenté.
**Référence** : `docs/revue-owasp-rls-2026-06.md` (vérifié présent) ; les 7 tables RLS sont énumérées dans `tests/integration/test_revoke_public_rls.py:30` (« 7 tables RLS », vérifié cette session). Le test d'assertion `relforcerowsecurity` est **à créer** (peut tourner sous le rôle `copilote` ou en lecture catalogue, pas besoin de NOSUPERUSER).

### Sprint 192 — Ops : garde `require_secure_db_url` uniformisé sur tous les pools runtime
**Objectif** : faire passer les **9 pools workers** par le même garde insecure-creds que le boot API, en l'absorbant dans `create_runtime_pool()` (ou un appel câblé dans le helper) — aujourd'hui seuls les pools API le portent.
**Complexité** : Faible.
**Justification** : finding d'altitude **différé** des revues S187 — laisser le garde API-only laisse un special-case permanent. Le rendre uniforme ferme un gap : un worker qui boote en prod avec des creds par défaut devrait échouer comme l'API. **Assumé comme changement de comportement** (d'où un sprint dédié avec tests de boot workers, pas un refactor silencieux).
**Référence** : `require_secure_db_url` (`app/utils/security_config.py:41`, vérifié cette session) appelé **uniquement** à `app/api/main.py:158` (vérifié) ; `create_runtime_pool` (`app/db/pool.py:9`, livré S187, vérifié) est le home naturel. L'absorption + les tests de boot workers sont **à créer**.

### Sprint 193 — Ops : helper de test RLS partagé (réduire la duplication des harnais d'intégration)
**Objectif** : extraire le harnais répété des tests d'intégration RLS (connexion sous rôle réel `app_runtime`/NOSUPERUSER, pose du GUC tenant, skip hors PG migré) en une fixture/helper partagé.
**Complexité** : Moyenne.
**Justification** : finding **écarté** en S185 (« refactor suite-wide ») et toujours ouvert — plusieurs `tests/integration/test_*_rls.py` répètent le même setup de connexion/skip. Un helper unique réduirait le bruit et rendrait l'ajout d'un nouveau test RLS trivial. À cadrer prudemment (ne pas casser la convention de skip existante).
**Référence** : les tests d'intégration RLS existent (ex. `tests/integration/test_revoke_public_rls.py`, `test_rls_isolation.py`, `test_app_runtime_rls.py` — cités dans `ROADMAP.md`, à re-`grep` pour le harnais exact). Le helper/fixture partagé est **à créer** ; le périmètre exact (combien de fichiers convergent) est **à mesurer** avant de s'engager.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur TradingClaude. Lis CLAUDE.md, ROADMAP.md (v10.75.0),
.claude/rules/conventions-frontend.md et tests-pyramide.md.
Sprint actif : 189 — E5-S8 : bornes de quota visibles à l'erreur 429. Enrichir le corps 429 (detail
structuré : message/plan/used/limit/remaining) au point unique quota_exceeded_http (app/utils/quota_http.py:9),
les 3 appelants (analyze_stream.py:80, screen.py:91, SSE) en héritent ; puis enrichir QuotaBanner
(frontend/src/components/QuotaBanner.tsx:13) pour afficher plan + borne + lien vers /facturation,
avec repli propre si le corps n'est pas structuré.
Sites vérifiés (n° de ligne DÉRIVENT, re-grep obligatoire) : QuotaExceededError porte déjà plan/used/limit/
retry_after_s (app/services/quota_service.py:64) ; quota_exceeded_http aplatit en texte (quota_http.py:12) ;
QuotaBanner ne prend que message ; isQuotaError teste status===429 (QuotaBanner.tsx:4).
À VÉRIFIER AVANT D'ÉCRIRE LE COMPOSANT : comment ApiError (frontend/src/api/client.ts) expose le corps
detail JSON — si pas structuré, l'y exposer d'abord (chemin critique).
Branche : claude/prompt-executer-sprint-<id>. Confirmer avant git push.
GATES : backend pytest + ruff + mypy ; frontend Vitest + tsc --noEmit + ESLint. Pas d'eval.
Preuve : un 429 renvoie {detail:{message,plan,used,limit,remaining}} ; QuotaBanner rend plan+borne+lien /facturation.
```
