# Sprint 125 — Durcissement sécurité auth & fail-safe (P0)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.12.0 — Sprint 126 complété)

**Origine de ce sprint** — La revue expert FinTech du 2026-05-29 (`docs/revue-expert-fintech.md`) a relevé des correctifs P0 de sécurité auth. Ils passent **devant** les autres travaux et restent le Sprint actif. Le sprint Annotations, déjà réalisé, a été **livré comme Sprint 126** (renuméroté pour ne pas revendiquer le slot 125 sécurité). Toutes les références ci-dessous ont été vérifiées par `grep`.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.12.0, Sprint 126 ✅
3. `docs/revue-expert-fintech.md` — §5 (architecture/sécurité) : contexte et justification des 4 correctifs
4. `.claude/rules/securite.md` — secrets via `.env`, jamais de fuite dans les logs/erreurs (cœur du sprint)
5. `.claude/rules/tests-pyramide.md` — niveau unitaire (service auth) + intégration (réponse 500) obligatoires ; fixture `client`, patch des dépendances

---

## TÂCHE — Sprint 125 : Durcissement sécurité auth & fail-safe (P0)

**Objectif** : éliminer quatre faiblesses de sécurité identifiées par la revue, toutes localisées dans la couche auth/middleware, sans changer le comportement fonctionnel pour un déploiement correctement configuré. Aucune migration DB, aucun changement de prompt de skill (evals non concernées).

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Repli sur secret JWT codé en dur** — `app/services/auth_token_service.py:32-35`
   ```python
   self._secret = os.environ.get("JWT_SECRET_KEY", "")
   if not self._secret:
       logger.warning("JWT_SECRET_KEY absent — utilisation d'un secret temporaire (dev uniquement)")
       self._secret = "dev-secret-change-in-production"
   ```
   En production sans `JWT_SECRET_KEY`, tous les tokens HS256 sont signés avec un secret public → **bypass d'authentification complet**.

2. **Blacklist JTI non protégée** — `app/services/auth_token_service.py:59-62`
   ```python
   async def is_jti_blacklisted(self, jti: str) -> bool:
       result = await self._redis.get(f"blacklist:jti:{jti}")
   ```
   Si Redis est indisponible, le `.get()` lève une exception → soit 500 bloquant les logins, soit (selon l'appelant) un token révoqué accepté. Doit être **fail-closed** (refuser en cas de doute), contrairement au rate-limiting qui est fail-open par tolérance.

3. **Fuite de détails d'exception** — `app/api/main.py:592-596`
   ```python
   async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
       ...
       content={"error": type(exc).__name__, "detail": str(exc)},
   ```
   `str(exc)` peut exposer des contraintes DB (ex. unicité email → énumération d'utilisateurs). Voir aussi `app/api/main.py:664` (`HTTPException(500, detail=str(exc))`).

4. **CORS sur-permissif** — `app/api/main.py:578-586` : `allow_methods=["*"]` + origines `localhost` codées en dur.

### Spécification

1. **Secret JWT fail-fast** (`auth_token_service.py:32-35`) : si `JWT_SECRET_KEY` est absent, **lever `RuntimeError`** à l'initialisation plutôt que retomber sur le secret de dev. Tolérer un repli **uniquement** derrière un flag explicite (ex. `APP_ENV in {"dev","test"}`) pour ne pas casser le confort local et les tests — décider et documenter le mécanisme retenu. Ajouter `JWT_SECRET_KEY` à `.env.example` s'il n'y figure pas.
2. **JTI blacklist fail-closed** (`auth_token_service.py:59-62`) : envelopper l'appel Redis dans `try/except` ; sur erreur Redis, **considérer le token comme non fiable** (retourner `True` = blacklisté, ou propager une 503 contrôlée) — choix de sécurité à documenter en commentaire WHY. Ne jamais laisser une panne Redis ouvrir l'accès.
3. **Assainir les réponses 500** (`main.py:592-596` et `:664`) : renvoyer un message générique (`"Erreur interne"`) + un identifiant de corrélation ; **logger** le détail complet côté serveur uniquement (jamais dans le body HTTP).
4. **Durcir CORS** (`main.py:578-586`) : `allow_methods` explicite (`["GET","POST","PUT","DELETE","OPTIONS"]`) ; lire les origines depuis une variable d'env `CORS_ORIGINS` (CSV), avec repli localhost en dev. Ajouter `CORS_ORIGINS` à `.env.example`.

### Tests obligatoires (pyramide)
- **Unitaire** (`tests/services/`) : init `AuthTokenService` sans `JWT_SECRET_KEY` (hors dev) → `RuntimeError` ; `is_jti_blacklisted` quand le mock Redis lève → fail-closed (pas d'exception qui fuit, accès refusé).
- **Intégration** (`tests/api/`, fixture `client`) : une route qui lève une exception non gérée → la réponse 500 **ne contient pas** `str(exc)` (assert que le détail brut est absent du body).
- Aucune régression des tests auth existants (login/refresh/logout, blacklist nominale Redis up).

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). ⚠️ Si `frontend/node_modules` est absent, lancer `npm install` depuis `frontend/`. Commandes :
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend
- Stack Docker non démarrée → tests sur pool/Redis mockés. Sprint backend pur (pas de test navigateur). Pas de changement de prompt → evals non concernées.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 127 — Déterminisme LLM + validation numérique des bornes
**Objectif** : rendre les analyses reproductibles (`temperature=0`) et ajouter des validateurs Pydantic de plausibilité post-LLM sur les scores clés (Z-score, M-score, WACC, fourchettes).
**Complexité** : Faible
**Justification** : un outil financier doit être reproductible et garde-fou contre les chiffres LLM aberrants ; correctif à haute valeur / faible coût. (Revue §3, §1.)
**Référence** : EXISTANT (vérifié) — **aucune** occurrence de `temperature` dans `app/` (`grep` vide) → défaut 1.0 ; point d'insertion unique `app/utils/retry.py:34` (`messages.create(timeout=..., **kwargs)`) ; validateur de bornes déjà en place comme modèle à généraliser `app/skills/tier2/stock_valuation/schemas.py:98-116`. À CRÉER — `temperature=0` (central ou par skill) + validateurs `@model_validator` de plausibilité sur `earnings_quality`/`graham`/`stock_valuation`.

### Sprint 128 — Calculs financiers déterministes en Python (le pivot)
**Objectif** : calculer en Python les scores aujourd'hui délégués au LLM (Altman Z, Beneish M, Piotroski F, Montier C, accruals Sloan, Graham Number, ossature DCF) ; le LLM **commente** des chiffres calculés au lieu de les produire.
**Complexité** : Élevée
**Justification** : c'est le défaut existentiel relevé par la revue (§1) — sans cela, les scores phares n'ont pas de fiabilité numérique ni d'auditabilité.
**Référence** : EXISTANT (vérifié) — formules aujourd'hui décrites dans les prompts et remplies par le LLM : `app/skills/tier2/earnings_quality/schemas.py:72-117` (Z/M/F/C/Sloan), `app/skills/tier2/graham_analysis/schemas.py:104-109` (Graham Number), `app/skills/tier2/stock_valuation/schemas.py:78-81` (matrice DCF). Inputs bruts extraits par `app/skills/tier1/yahoo_finance.py:234-358`. À CRÉER — module de calcul déterministe + recâblage des skills pour passer les valeurs calculées en contexte.

### Sprint 129 — Conformité : disclaimers & avertissement de risque
**Objectif** : afficher « recherche éducative — pas un conseil financier » + avertissement de risque dans l'UI (résultats, pied de page) et dans les rapports PDF.
**Complexité** : Faible
**Justification** : le système émet des verdicts d'achat/vente explicites sans aucun disclaimer (revue §6) — exposition réglementaire (AMF/SEC/MiFID) si diffusé.
**Référence** : EXISTANT (vérifié) — **aucun** disclaimer dans le code (`grep` "conseil financier"/"disclaimer" vide) ; verdicts émis dans les schemas (`ACHAT_FORT`, `VENDRE`, etc., ex. `app/skills/tier2/fisher_scuttlebutt/schemas.py`) ; génération PDF `app/services/pdf_report_service.py`. À CRÉER — composant disclaimer (`frontend/src/components/`) + bloc dans le PDF.

### Sprint 130 — Données : honnêteté du label + repli multi-sources
**Objectif** : corriger l'étiquette `eps_growth_10y` (en réalité ~4 ans) et ajouter un repli/seconde source quand `yfinance` échoue.
**Complexité** : Moyenne
**Justification** : source unique gratuite et retardée = SPOF + biais silencieux dans les seuils Graham (revue §2, §5).
**Référence** : EXISTANT (vérifié) — calcul ~4 ans `app/skills/tier1/yahoo_finance.py:18`, label trompeur `app/skills/tier2/graham_analysis/schemas.py:19` ; SEDAR+ non fonctionnel `app/skills/tier1/sedar_plus.py:54-55`. À CRÉER — renommage cohérent du champ + couche de repli données.

> _Le sprint « Annotations enrichies : tags + filtres » (initialement 125, un temps suggéré en 130) a été **livré comme Sprint 126** — retiré de cette file._

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.12.0), docs/revue-expert-fintech.md (§5) et
.claude/rules/securite.md + tests-pyramide.md avant de commencer.
Sprint actif : 125 — Durcissement sécurité auth & fail-safe (P0) : (1) secret JWT
fail-fast au lieu du repli dev codé en dur, (2) blacklist JTI fail-closed si Redis tombe,
(3) réponses 500 assainies (pas de str(exc) dans le body), (4) CORS durci (méthodes
explicites + origines via env CORS_ORIGINS). Tests unitaires service auth + intégration
500 sanitisé obligatoires. Sprint backend pur, sans migration ni changement de prompt.
```
