# Sprint 129 — Conformité : disclaimers & avertissement de risque

**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

## État du projet (v10.15.0 — Sprint 128 complété)

**Origine de ce sprint** — Suite de la file issue de la revue expert FinTech (`docs/revue-expert-fintech.md` §6). Le Sprint 128 a rapatrié les scores financiers phares en Python (déterministes, auditables). Le système émet désormais des verdicts d'achat/vente explicites, fiables… mais **sans aucun disclaimer** : exposition réglementaire (AMF/SEC/MiFID) si diffusé. Sprint 129 ajoute l'avertissement « recherche éducative — pas un conseil financier » dans l'UI et les rapports PDF.

> **État courant complet** (version, fonctionnalités actives, endpoints, pages, compteurs de tests) : **`ROADMAP.md`** — source unique. Cette carte y renvoie, elle ne le duplique pas (cf. `.claude/rules/workflow-sprint.md`).

---

## LECTURE OBLIGATOIRE AVANT DE COMMENCER

1. `CLAUDE.md` — index du projet (pointeurs vers `.claude/rules/`)
2. `ROADMAP.md` — état courant v10.15.0, Sprint 128 ✅
3. `.claude/rules/conventions-frontend.md` — React 18, TS strict, test composant obligatoire (cœur du sprint : composant disclaimer + tests)
4. `.claude/rules/securite.md` — pas de secret/donnée sensible exposée (le disclaimer touche les surfaces publiques : UI résultats, pied de page, PDF)

---

## TÂCHE — Sprint 129 : Conformité réglementaire (disclaimers)

**Objectif** : afficher un avertissement clair « Ce système produit de la recherche éducative — pas un conseil financier. Investir comporte un risque de perte en capital. » à chaque endroit où un verdict actionnable est présenté : résultats d'analyse, pied de page global, et rapports PDF générés.

### Point de départ exact (vérifié cette session — `fichier:ligne`)

1. **Aucun disclaimer aujourd'hui** (vérifié : `grep -rni "disclaimer|conseil financier|recherche éducative" app/ frontend/src/` **vide** cette session) — À CRÉER intégralement.
2. **Verdicts actionnables émis** (EXISTANT) — ex. `app/skills/tier2/fisher_scuttlebutt/schemas.py:32` (`verdict: ACHAT_FORT|ACHAT|CONSERVER|EVITER`, validateur :49). Tous les skills tier2 émettent un verdict du même type — c'est ce qui crée l'exposition réglementaire.
3. **Génération PDF** (EXISTANT) — `app/services/pdf_report_service.py` : `_build_verdicts_rows`:144, `_table_verdicts`:182 (table des verdicts par skill). Le bloc disclaimer s'insère dans le `story` ReportLab, après la table des verdicts.

### Spécification

1. **Frontend — composant `Disclaimer`** (`frontend/src/components/Disclaimer.tsx`, nouveau) : bandeau réutilisable (variante `inline` pour les résultats, variante `footer` discrète). Texte FR. `data-testid="disclaimer"`. Affiché dans `AnalysisResult.tsx` (haut ou bas du bloc résultats) et dans le shell global (pied de page de `App.tsx`).
2. **PDF — bloc disclaimer** : ajouter au `story` de `pdf_report_service.py` (et, si le périmètre tient, aux rapports screener/watchlist/mensuel qui réutilisent le même service) un paragraphe d'avertissement avant/après la table des verdicts. Style discret mais lisible.
3. **Texte centralisé** : une seule source de vérité pour le texte (constante TS partagée + constante Python) afin d'éviter la dérive de formulation entre UI et PDF.

### Tests obligatoires (pyramide)
- **Composant** (`frontend/src/__tests__/Disclaimer.test.tsx`) : rend le texte attendu + présence dans `AnalysisResult` (happy path) ; variante footer.
- **Unitaire/intégration backend** : un test sur `pdf_report_service` vérifiant que le `story` (ou les `Paragraph`) contient le texte du disclaimer pour un rapport ticker.
- Aucune régression Vitest / pytest.

### ⚠️ Evals concernées
**Aucune** — sprint d'affichage pur, aucun prompt de skill ni l'orchestrateur n'est modifié. (Le dire dans la note d'environnement.)

### Note d'environnement (session web)
Conteneur cloné à neuf ; deps préparées par `SessionStart` → `scripts/setup-web-session.sh` (idempotent). Si le frontend manque des types (`@testing-library/jest-dom`, `vitest/globals`), lancer `cd frontend && npm install` (node_modules parfois partiel à l'amorçage).
- Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` + `.venv/bin/ruff check app/ tests/`
- Frontend : `cd frontend && npm run typecheck && npm run lint && node node_modules/vitest/vitest.mjs run`
- ⚠️ le cwd persiste entre commandes Bash — revenir à la racine avant les commandes backend.
- Stack Docker non démarrée → tests sur mocks. Pas de test navigateur live.

---

## SPRINTS SUGGÉRÉS (non planifiés) — file issue de la revue FinTech

### Sprint 130 — Données : honnêteté du label + repli multi-sources
**Objectif** : corriger l'étiquette `eps_growth_10y` (en réalité ~4 ans) et ajouter un repli/seconde source quand `yfinance` échoue.
**Complexité** : Moyenne
**Justification** : source unique gratuite et retardée = SPOF + biais silencieux dans les seuils Graham (revue §2, §5).
**Référence** : EXISTANT (vérifié cette session) — calcul `app/skills/tier1/yahoo_finance.py:18` (`_compute_eps_growth`), câblé l.202 ; label trompeur `app/skills/tier2/graham_analysis/schemas.py:20` (`eps_growth_10y`). À CRÉER — renommage cohérent du champ (backend + `frontend/src/types/index.ts`) + couche de repli données.

### Sprint 131 — Auditabilité : persistance des sous-composantes déterministes
**Objectif** : remplir EN PYTHON les sous-composantes des scores du Sprint 128 (X1-X5 du Z, les 8 indices du M) — aujourd'hui encore issues du LLM — et les persister pour qu'une analyse soit rejouable et explicable.
**Complexité** : Moyenne
**Justification** : le Sprint 128 ne rend déterministe que le score agrégé ; les `*Detail` (dsri, gmi…) restent LLM (cf. « Limites connues » du bloc Sprint 128 dans `ROADMAP.md`) — l'auditabilité n'est complète qu'avec la trace des intermédiaires.
**Référence** : DÉPEND du Sprint 128 — `app/services/financial_calculations.py` (créé). Les champs cibles existent : `MScoreDetail.dsri/gmi/...` `app/skills/tier2/earnings_quality/schemas.py:79-86`. Persistance via `analysis_history` (table EXISTANTE, `infra/postgres/init.sql:4`).

### Sprint 132 — Calculs déterministes : ossature DCF (stock_valuation)
**Objectif** : étendre l'approche Sprint 128 à la valorisation — calculer en Python l'ossature DCF (WACC, valeur actualisée, matrice de sensibilité) et laisser le LLM commenter la narrative.
**Complexité** : Élevée
**Justification** : `stock_valuation` produit encore une matrice de sensibilité entièrement LLM — même défaut de fiabilité numérique que les scores avant Sprint 128.
**Référence** : EXISTANT (vérifié cette session) — `app/skills/tier2/stock_valuation/schemas.py:78` (`SensitivityMatrix`, `wacc_range`:79), `matrice_sensibilite`:91, validateur de cohérence l.109-115. À CRÉER — fonction DCF déterministe dans `app/services/financial_calculations.py` + recâblage du skill.

---

## Template de démarrage

```
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude.
Lis CLAUDE.md, ROADMAP.md (v10.15.0), .claude/rules/conventions-frontend.md et
.claude/rules/securite.md avant de commencer.
Sprint actif : 129 — Conformité (disclaimers) : créer un composant Disclaimer réutilisable
(frontend/src/components/Disclaimer.tsx) affiché dans AnalysisResult + pied de page global,
et un bloc disclaimer dans les rapports PDF (app/services/pdf_report_service.py), avec un
texte centralisé (constante partagée TS + Python). Aucun prompt de skill modifié → evals
non concernées. Tests composant (Disclaimer) + test backend (le story PDF contient le texte)
obligatoires.
```
