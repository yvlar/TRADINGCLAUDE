# Sprint 127 — Déterminisme LLM + validation numérique des bornes

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.13.0 — Sprint 125 complété)

**Origine de ce sprint** — Suite de la revue expert FinTech (`docs/revue-expert-fintech.md` §3, §1). Le Sprint 125 a fermé les correctifs P0 de sécurité auth. Sprint 127 attaque la **reproductibilité** : les analyses sont aujourd'hui non déterministes (température LLM par défaut) et aucun garde-fou numérique ne borne les scores produits par le modèle.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.13.0, Sprint 125 ✅
3. `.claude/rules/api-skills-tier2.md` — schemas Pydantic font foi, `model_validator`/`field_validator` v2, `_parse_claude_json` → `model_validate` (cœur du sprint : c'est là qu'on ajoute les validateurs de plausibilité)
4. `.claude/rules/donnees-financieres.md` — validation `None`/div0 et **valeurs aberrantes** (« signaler si un ratio semble hors plage » — exactement ce que les nouveaux validateurs encodent)

---

## TÂCHE — Sprint 127 : Déterminisme LLM + validation numérique des bornes

**Objectif** : (1) rendre les analyses reproductibles en fixant `temperature=0` sur les appels Claude ; (2) ajouter des validateurs Pydantic de **plausibilité** post-LLM sur les scores clés, pour qu'un chiffre aberrant produit par le modèle soit rejeté plutôt que persisté. Sprint backend pur — aucune migration DB.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Aucune température fixée** — `grep "temperature" app/` est **vide** cette session → les appels utilisent le défaut Anthropic (1.0), d'où la non-reproductibilité. Point d'insertion central unique : `app/utils/retry.py:34`
   ```python
   return await client.messages.create(timeout=timeout_s, **kwargs)
   ```
   Tous les skills passent par `call_claude_with_retry` (`app/utils/retry.py:16`).
2. **Patron de validateur déjà en place** (modèle à généraliser, VÉRIFIÉ) — `app/skills/tier2/stock_valuation/schemas.py:98-116` : `@model_validator(mode="after") def valider_output` borne déjà l'ordre des fourchettes et la cohérence de la matrice. C'est le gabarit à répliquer pour les scores.
3. **Scores aujourd'hui non bornés en plausibilité** (VÉRIFIÉ) — `app/skills/tier2/earnings_quality/schemas.py` : `MScoreDetail` (l.72, `m_score`), `ZScoreDetail` (l.85, `z_score`), `FScoreDetail` (l.97, `f_score` déjà `Field(ge=0, le=9)`), `CScoreDetail` (l.109, `c_score` déjà `Field(ge=0, le=6)`), `SloanDetail` (l.115). F/C ont des bornes entières ; M/Z (floats) n'ont aucune borne de plausibilité.

### Spécification

1. **`temperature=0` central** : passer `temperature=0` à `client.messages.create` dans `app/utils/retry.py:34` (un seul point, couvre tous les skills). Le rendre **surchargeable** : ne pas écraser un `temperature` déjà fourni dans `**kwargs` (`kwargs.setdefault("temperature", 0)`), pour qu'un skill puisse exceptionnellement diverger. Vérifier qu'aucun appelant ne passe déjà `temperature` (grep vide → aucun conflit).
2. **Validateurs de plausibilité** (`@model_validator(mode="after")`, style `stock_valuation`) sur les floats non bornés, en **avertissant sans casser une analyse légitime** — préférer borner les valeurs *impossibles* (NaN/inf, signes incohérents) plutôt que des plages discutables :
   - `earnings_quality` : `z_score` et `m_score` finis (rejeter NaN/inf) ; bornes larges documentées (ex. Z hors `[-50, 50]`, M hors `[-20, 20]` → suspect). Décider seuils en lisant `.claude/skills/earnings-quality-fraud-detection/references/`.
   - Généraliser le réflexe : tout `float | None` de score/ratio exposé doit au minimum rejeter NaN/inf.
3. Ne **pas** déplacer le calcul des scores en Python (c'est le Sprint 128 suggéré) — ici on borne ce que le LLM renvoie, on ne le recalcule pas.

### Tests obligatoires (pyramide)
- **Unitaire** (`tests/skills/` ou `tests/services/`) : un payload avec `z_score = float('inf')` / `m_score = float('nan')` → `ValidationError` ; un payload nominal → OK (pas de régression des fixtures existantes).
- **Unitaire** (`tests/utils/`) : `call_claude_with_retry` mocké → vérifier que `messages.create` est appelé avec `temperature=0` par défaut ET qu'un `temperature` explicite dans kwargs n'est pas écrasé.
- Aucune régression de la suite skills/orchestrateur existante.

### ⚠️ Evals concernées
`temperature=0` change le comportement de **tous** les skills. La suite `pytest` (Claude mocké) restera verte sans rien prouver sur la qualité réelle. Si une clé Anthropic est disponible, lancer les `evals` ciblées (`tests/evals/`) sur 1-2 skills pour constater que les verdicts restent cohérents à température nulle. Sinon, **le dire explicitement** dans la note d'environnement plutôt que de prétendre les avoir passées.

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). Commandes :
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend
- Stack Docker non démarrée → tests sur mocks. Sprint sans frontend ni migration.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 128 — Calculs financiers déterministes en Python (le pivot)
**Objectif** : calculer en Python les scores aujourd'hui délégués au LLM (Altman Z, Beneish M, Piotroski F, Montier C, accruals Sloan, Graham Number, ossature DCF) ; le LLM **commente** des chiffres calculés au lieu de les produire.
**Complexité** : Élevée
**Justification** : défaut existentiel relevé par la revue (§1) — sans cela, les scores phares n'ont ni fiabilité numérique ni auditabilité.
**Référence** : EXISTANT (vérifié cette session) — schemas où le LLM remplit ces scores : `app/skills/tier2/earnings_quality/schemas.py` (`MScoreDetail`:72, `ZScoreDetail`:85, `FScoreDetail`:97, `CScoreDetail`:109, `SloanDetail`:115) ; matrice DCF `app/skills/tier2/stock_valuation/schemas.py` (`SensitivityMatrix` `wacc_range`:79, `matrice_sensibilite`:91). Inputs bruts : `app/skills/tier1/yahoo_finance.py` (`extract`:156, `extract_earnings_quality`:234, `extract_valuation`:370). À CRÉER — **Graham Number n'existe nulle part en Python** (`grep "graham_number" app/` vide cette session) : produit aujourd'hui par le prompt, à rapatrier. Module de calcul déterministe + recâblage des skills.

### Sprint 129 — Conformité : disclaimers & avertissement de risque
**Objectif** : afficher « recherche éducative — pas un conseil financier » + avertissement de risque dans l'UI (résultats, pied de page) et dans les rapports PDF.
**Complexité** : Faible
**Justification** : le système émet des verdicts d'achat/vente explicites sans aucun disclaimer (revue §6) — exposition réglementaire (AMF/SEC/MiFID) si diffusé.
**Référence** : EXISTANT (vérifié cette session) — **aucun** disclaimer (`grep -i "disclaimer\|conseil financier" app/ frontend/src/` vide) ; verdicts émis dans les schemas (ex. `app/skills/tier2/fisher_scuttlebutt/schemas.py:32` et validateur :49 — `ACHAT_FORT|ACHAT|CONSERVER|EVITER`) ; génération PDF `app/services/pdf_report_service.py` (fichier présent). À CRÉER — composant disclaimer (`frontend/src/components/`) + bloc dans le PDF.

### Sprint 130 — Données : honnêteté du label + repli multi-sources
**Objectif** : corriger l'étiquette `eps_growth_10y` (en réalité ~4 ans) et ajouter un repli/seconde source quand `yfinance` échoue.
**Complexité** : Moyenne
**Justification** : source unique gratuite et retardée = SPOF + biais silencieux dans les seuils Graham (revue §2, §5).
**Référence** : EXISTANT (vérifié cette session) — calcul ~4 ans `app/skills/tier1/yahoo_finance.py:18-21` (docstring `_compute_eps_growth` : « horizon max disponible, ~4 ans ») ; label trompeur `app/skills/tier2/graham_analysis/schemas.py:19` (`eps_growth_10y: float = Field(...)`, validateur :42) ; SEDAR+ non fonctionnel `app/skills/tier1/sedar_plus.py:32` (`extract` retourne `None` à :40/:53/:55/:58). À CRÉER — renommage cohérent du champ + couche de repli données.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.13.0), .claude/rules/api-skills-tier2.md et
donnees-financieres.md avant de commencer.
Sprint actif : 127 — Déterminisme LLM + validation numérique : (1) temperature=0
central dans app/utils/retry.py (surchargeable via kwargs.setdefault), (2) validateurs
Pydantic de plausibilité (rejet NaN/inf + bornes larges) sur les scores float non bornés
(z_score, m_score d'earnings_quality), sur le modèle de stock_valuation/schemas.py:98.
Tests unitaires (ValidationError sur inf/nan + temperature=0 vérifiée) obligatoires.
Sprint backend pur, sans migration. temperature=0 touche tous les skills → lancer les
evals ciblées si clé Anthropic dispo, sinon le dire explicitement.
```
