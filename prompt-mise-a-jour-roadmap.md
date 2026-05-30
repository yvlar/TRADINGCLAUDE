# Sprint 128 — Calculs financiers déterministes en Python (le pivot)

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.14.0 — Sprint 127 complété)

**Origine de ce sprint** — Suite de la revue expert FinTech (`docs/revue-expert-fintech.md` §1), défaut existentiel. Le Sprint 127 a fixé `temperature=0` (reproductibilité) et ajouté des garde-fous de plausibilité (rejet NaN/inf + bornes larges) sur les scores `earnings_quality`. Mais les scores phares (Altman Z, Beneish M, Piotroski F, Montier C, Sloan, Graham Number, ossature DCF) sont **toujours produits par le LLM**, donc ni numériquement fiables ni auditables. Sprint 128 rapatrie ces calculs en Python : le LLM **commente** des chiffres calculés au lieu de les produire.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.14.0, Sprint 127 ✅
3. `.claude/rules/donnees-financieres.md` — validation `None`/div0, valeurs aberrantes, traçabilité source+date (cœur du sprint : c'est la discipline de calcul financier qu'on encode en Python)
4. `.claude/rules/base-connaissances-skills.md` — protocole obligatoire : lire les `SKILL.md` + `references/*.md` AVANT de coder les formules (les seuils et formules font foi : `.claude/skills/earnings-quality-fraud-detection/references/{altman-z-score,beneish-m-score,piotroski-f-score,montier-c-score,sloan-accruals}.md`)
5. `.claude/rules/api-skills-tier2.md` — schemas Pydantic font foi, pattern `execute()`, recâblage des skills

---

## TÂCHE — Sprint 128 : Calculs financiers déterministes en Python

**Objectif** : créer un module de calcul Python déterministe pour les scores aujourd'hui délégués au LLM, et recâbler les skills pour qu'ils reçoivent les scores **calculés** (le LLM interprète/commente, il ne les produit plus). Réduit la non-fiabilité numérique et rend chaque score auditable.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Scores remplis par le LLM** (EXISTANT, à recâbler) — `app/skills/tier2/earnings_quality/schemas.py` : `MScoreDetail`:78 (`m_score`:87), `ZScoreDetail`:99 (`z_score`:101), `FScoreDetail`:119 (`f_score`:121), `CScoreDetail`:131 (`c_score`:133), `SloanDetail`:137 (`accrual_ratio`:138). Le Sprint 127 borne déjà ces valeurs (NaN/inf + plausibilité) — Sprint 128 les **produit** au lieu de les borner.
2. **Inputs bruts déjà extraits** (EXISTANT) — `app/skills/tier1/yahoo_finance.py` : `extract`:156 (Graham), `extract_earnings_quality`:234 (les 2 exercices nécessaires au M/Z/F/C/Sloan), `extract_valuation`:370 (DCF). `EarningsQualityRatios` (`app/skills/tier2/earnings_quality/schemas.py:14`) porte déjà les champs T/T-1 nécessaires aux formules.
3. **Matrice DCF produite par le LLM** (EXISTANT) — `app/skills/tier2/stock_valuation/schemas.py` : `SensitivityMatrix`:78 (`wacc_range`:79), `matrice_sensibilite`:91 ; validateur d'ordre/cohérence déjà en place (l.98).
4. **Graham Number — n'existe nulle part en Python** (À CRÉER, vérifié : `grep "graham_number" app/` **vide** cette session) : produit aujourd'hui par le prompt graham. Formule canonique `√(22.5 × EPS × BVPS)` (cf. `.claude/rules/variables-financieres.md`, ligne `graham_number`).

### Spécification

1. **Module de calcul** `app/services/financial_calculations.py` (nouveau) — fonctions pures, typées, async-free (calcul CPU) :
   - `altman_z_score(...)`, `beneish_m_score(...)`, `piotroski_f_score(...)`, `montier_c_score(...)`, `sloan_accrual_ratio(...)`, `graham_number(eps, bvps)`. Chaque fonction lit ses formules/seuils dans les `references/` (NE PAS inventer les coefficients — les recopier depuis les fichiers de référence). Retour `float | None` avec `None` si une donnée requise manque (jamais d'exception sur donnée absente — cf. `donnees-financieres.md`).
   - Variantes Z (original/Z'/Z'') : choisir selon le profil ou exposer la variante en paramètre ; les banques/assureurs (`is_financial`) → `None` (modèle inapplicable, documenté dans les références).
2. **Recâblage des skills** — `earnings_quality` et `graham_analysis` (et `stock_valuation` pour l'ossature DCF si le périmètre tient) : calculer les scores AVANT l'appel Claude, les passer au prompt comme données d'entrée, et demander au LLM d'**interpréter** (pas de recalculer). Décider : soit le skill remplit les `*Detail.score` depuis le Python et le LLM ne fournit que `interpretation`/`drapeaux_rouges`, soit on conserve le schema et on substitue le score Python post-parse. Documenter le choix.
3. **Ne pas casser** les garde-fous Sprint 127 (ils restent une 2ᵉ ligne de défense) ni les bornes `f_score ge=0 le=9` / `c_score ge=0 le=6`.

### Tests obligatoires (pyramide)
- **Unitaire** (`tests/services/test_financial_calculations.py`) : chaque fonction sur un cas connu (valeur attendue calculée à la main depuis les références) + cas `None`/div0 (donnée manquante → `None`, jamais d'exception) + cas banque → `None`. Vecteur de test idéal : un titre dont le Z/M est documenté (ex. Enron M-Score > -1.78 cité dans `beneish-m-score.md`).
- **Intégration** (`tests/skills/`) : `earnings_quality.execute()` mocké → vérifier que le score retourné provient du calcul Python, pas du bloc LLM (injecter un score LLM différent et constater qu'il est ignoré/écrasé).
- Aucune régression de la suite skills/orchestrateur.

### ⚠️ Evals concernées
Le sprint change ce que le LLM reçoit et produit (il commente au lieu de calculer) → **prompts de skills modifiés**. Si une clé Anthropic est disponible, lancer les `evals` ciblées (`tests/evals/`) sur `earnings_quality` + `graham_analysis` pour constater que les verdicts restent cohérents avec des scores désormais déterministes. Sinon, **le dire explicitement** plutôt que de prétendre les avoir passées (cf. Sprint 127 : aucune clé dans le conteneur web).

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). Commandes :
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend
- Stack Docker non démarrée → tests sur mocks. Sprint backend pur, sans migration ni frontend (sauf si le recâblage modifie la forme d'un champ exposé → alors mettre à jour `frontend/src/types/index.ts` + un test composant).

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 129 — Conformité : disclaimers & avertissement de risque
**Objectif** : afficher « recherche éducative — pas un conseil financier » + avertissement de risque dans l'UI (résultats, pied de page) et dans les rapports PDF.
**Complexité** : Faible
**Justification** : le système émet des verdicts d'achat/vente explicites sans aucun disclaimer (revue §6) — exposition réglementaire (AMF/SEC/MiFID) si diffusé.
**Référence** : EXISTANT (vérifié cette session) — **aucun** disclaimer (`grep -i "disclaimer\|conseil financier" app/ frontend/src/` vide) ; verdicts émis dans les schemas (ex. `app/skills/tier2/fisher_scuttlebutt/schemas.py:32`, validateur :49 — `ACHAT_FORT|ACHAT|CONSERVER|EVITER`) ; génération PDF `app/services/pdf_report_service.py` (fichier présent). À CRÉER — composant disclaimer (`frontend/src/components/`) + bloc dans le PDF.

### Sprint 130 — Données : honnêteté du label + repli multi-sources
**Objectif** : corriger l'étiquette `eps_growth_10y` (en réalité ~4 ans) et ajouter un repli/seconde source quand `yfinance` échoue.
**Complexité** : Moyenne
**Justification** : source unique gratuite et retardée = SPOF + biais silencieux dans les seuils Graham (revue §2, §5).
**Référence** : EXISTANT (vérifié cette session) — calcul ~4 ans `app/skills/tier1/yahoo_finance.py:18` (`_compute_eps_growth`) ; label trompeur `app/skills/tier2/graham_analysis/schemas.py:19` (`eps_growth_10y`, validateur :42). À CRÉER — renommage cohérent du champ (backend + `frontend/src/types/index.ts`) + couche de repli données.

### Sprint 131 — Auditabilité : persistance des intermédiaires de calcul
**Objectif** : persister les variables intermédiaires des scores déterministes du Sprint 128 (X1-X5 du Z, les 8 ratios du M, etc.) pour qu'une analyse soit rejouable et explicable a posteriori.
**Complexité** : Moyenne
**Justification** : sans les intermédiaires, un score calculé reste une boîte noire pour l'utilisateur — l'auditabilité promise par le Sprint 128 n'est complète qu'avec la trace.
**Référence** : DÉPEND du Sprint 128 (module `app/services/financial_calculations.py` à créer). Les `*Detail` d'`earnings_quality` portent déjà les sous-composantes (`MScoreDetail.dsri/gmi/...` `app/skills/tier2/earnings_quality/schemas.py:79-86`) — À VÉRIFIER après Sprint 128 si elles sont remplies par le Python. Persistance via `analysis_history` (table EXISTANTE).

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.14.0), .claude/rules/donnees-financieres.md,
base-connaissances-skills.md et api-skills-tier2.md avant de commencer.
Sprint actif : 128 — Calculs financiers déterministes en Python : créer
app/services/financial_calculations.py (Altman Z, Beneish M, Piotroski F, Montier C,
Sloan, Graham Number) avec formules/seuils RECOPIÉS depuis .claude/skills/.../references/,
puis recâbler earnings_quality + graham_analysis pour que le LLM COMMENTE des scores
calculés en Python (il ne les produit plus). Gestion None/div0/banques → None sans exception.
Tests unitaires (cas connu calculé à la main + None + banque) + intégration (score Python
prime sur le bloc LLM) obligatoires. Prompts de skills modifiés → lancer les evals ciblées
si clé Anthropic dispo, sinon le dire explicitement.
```
