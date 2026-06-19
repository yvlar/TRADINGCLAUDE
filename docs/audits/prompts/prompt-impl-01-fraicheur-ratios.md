# Prompt d'implémentation 01 — Validation de fraîcheur des ratios

> **Origine** : audit `docs/audits/01-investissement.md` (faiblesse **A**) + hypothèse **H-A** confirmée dans `docs/audits/00-synthese-hypotheses.md`.
> **Priorité** : P1. **Domaine** : backend + frontend. **Effort** : moyen, 1 session.

---

## Contexte

Les ratios financiers portent une date de récupération (`ratios_fetched_at`), mais **aucun chemin de
code ne la compare à `now()`** : un utilisateur peut analyser des données périmées (saisie manuelle ou
cache long) sans le savoir. Objectif : détecter et **surfacer** un avertissement de fraîcheur
(> 30 jours = avertissement ; > 90 jours = flag fort), sans bloquer l'analyse par défaut.

## LECTURE OBLIGATOIRE (avant de coder)

1. `CLAUDE.md` et `ROADMAP.md` (état courant, conventions).
2. `.claude/rules/donnees-financieres.md` — traçabilité source + date obligatoire, validation None.
3. `.claude/rules/variables-financieres.md` — nommage snake_case/camelCase miroir backend↔frontend.

## Périmètre

- **Inclus** : un utilitaire de fraîcheur, sa propagation dans `AnalyzeResponse`, son affichage front.
- **Exclu** : ne PAS ajouter de champ dans les schémas de ratios (`GrahamRatios`, etc.) — les dates y
  existent déjà. Ne PAS bloquer l'analyse par défaut (le blocage > 90 j est un flag, pas un rejet HTTP,
  sauf si tu ajoutes un paramètre opt-in `strict_freshness` — optionnel).

## Tâche détaillée

### 1. Utilitaire backend — `app/utils/ratios_freshness.py` (à créer)

- Fonction `check_ratios_age(fetched_at: datetime | None, *, label: str) -> str | None` :
  - `None` si `fetched_at` absent (pas de bruit — cohérent avec l'« honnêteté None » du projet).
  - calcul `now = datetime.now(timezone.utc)` ; `age = now - fetched_at`.
  - `> 90 j` → message fort (ex. `"{label} : données vieilles de {n} j (>90 j) — fiabilité réduite"`).
  - `> 30 j` → avertissement (ex. `"{label} : données vieilles de {n} j (>30 j)"`).
  - sinon `None`.
- Type hints complets, docstring FR une ligne. Seuils en constantes module (`SEUIL_AVERTISSEMENT_J = 30`, `SEUIL_FORT_J = 90`).

### 2. Propagation dans `AnalyzeResponse` — `app/orchestrator/core.py`

- `AnalyzeResponse` est défini lignes **242-306** (6 champs de traçabilité `ratios_*`, **aucun champ `warnings`**).
- Ajouter un champ optionnel : `ratios_freshness_warnings: list[str] = Field(default_factory=list)`.
- Le peupler à la construction de la réponse (injection ~ligne **1155**, à côté de `**_request_ratios_traces(request)`). Réutiliser `_request_ratios_traces` (`core.py:309-328`) et le helper `_ratios_trace` de `app/services/ratios_recon.py:22-48` pour récupérer les `fetched_at` des trois familles (Graham, Earnings, Valuation).
- Appeler `check_ratios_age` pour chaque famille présente ; concaténer les messages non-`None`.

### 3. Frontend — affichage

- Type miroir : ajouter `ratios_freshness_warnings?: string[] | null` à `AnalyzeResponse` dans `frontend/src/types/index.ts:449-484`.
- Composant : créer `frontend/src/components/RatiosFreshnessWarning.tsx`, calqué sur le pattern de `frontend/src/components/RatiosSourceNote.tsx` (retourne `null` si liste vide). Style « avertissement » (réutiliser les classes destructive/warning déjà présentes ; s'inspirer de `VerdictDisclaimer.tsx`).
- Le brancher dans `frontend/src/components/AnalysisResult.tsx` (près des `RatiosSourceNote` existants).

## Tests à ajouter

- Backend : `tests/utils/test_ratios_freshness.py` (cas None / <30 j / 30-90 j / >90 j) + un test d'orchestrateur vérifiant que `ratios_freshness_warnings` est peuplé quand une date est ancienne (`tests/orchestrator/`).
- Frontend : `frontend/src/__tests__/RatiosFreshnessWarning.test.tsx` (rendu si messages, rien si vide).

## Critères d'acceptation

- [ ] `python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` vert.
- [ ] `cd frontend && npm run typecheck` → 0 erreur ; `npm test` vert.
- [ ] Une analyse avec ratios datés de >30 j fait apparaître un avertissement ; <30 j → rien.
- [ ] Aucun champ ajouté dans les schémas de ratios ; `ratios_fetched_at=None` → aucun avertissement (pas de faux positif).

## Branche & commit

- Branche : `claude/impl-fraicheur-ratios` (depuis `dev`).
- Commit FR structuré ; PR **base `dev`** (cf. `.claude/rules/workflow-sprint.md`). Push à confirmer.
