# Prompt d'implémentation 04 — UX & accessibilité frontend

> **Origine** : audit `docs/audits/04-uiux.md` (**S**, **R**) ; hypothèses **H-S / H-R** confirmées dans `docs/audits/00-synthese-hypotheses.md`.
> **Priorité** : P2. **Domaine** : frontend. **Effort** : faible-moyen, 1 session.

---

## Contexte

Deux correctifs UX/accessibilité ciblés : (1) la palette de commandes (`Ctrl+K`) s'ouvre comme une
modale mais sans `role="dialog"`/`aria-modal` ni piège de focus (navigation clavier et lecteurs
d'écran imparfaits) ; (2) les erreurs d'export du screener s'affichent via `alert()` bloquant, en
rupture avec le reste de l'app qui gère les erreurs en inline.

## LECTURE OBLIGATOIRE (avant de coder)

1. `CLAUDE.md` et `ROADMAP.md`.
2. `.claude/rules/conventions-frontend.md` — React 18, TypeScript strict (zéro `any`), structure composants.

## Périmètre

- **Inclus** : accessibilité de `CommandPalette`, remplacement des `alert()` d'export par de l'inline.
- **Exclu** : ne pas introduire de librairie de focus-trap lourde si un petit hook maison suffit ; ne
  pas refondre le design des composants.

## Tâche détaillée

### H-S — `frontend/src/components/CommandPalette.tsx` : modale accessible

- État actuel : overlay `fixed inset-0` (`:99`) sans rôle ARIA ; seul `Escape` est géré (`:115`) ;
  `useRef` (`:39`) ne sert qu'au debounce.
- Ajouter sur le conteneur de dialogue : `role="dialog"` + `aria-modal="true"` + un `aria-label`.
- **Focus trap** : à l'ouverture, placer le focus sur le champ de recherche ; piéger `Tab`/`Shift+Tab`
  entre les éléments focusables du dialogue ; à la fermeture, **restaurer le focus** sur l'élément
  déclencheur (mémoriser `document.activeElement` à l'ouverture). Un petit `useEffect` + ref suffit.
- Conserver le comportement `Escape` et le portail existants.

### H-R — `frontend/src/pages/ScreenerPage.tsx` : erreurs inline

- Lignes **49** et **65** : deux `alert(...)` pour erreurs d'export (CSV/XLSX et PDF). Les remplacer par
  un état d'erreur inline (`useState`) rendu en `role="alert"`, dans l'esprit du pattern `QuotaBanner`
  / des messages d'erreur inline déjà présents ailleurs (ex. `pdfMessage`).
- Vérifier `frontend/src/pages/AdminPage.tsx` pour des `alert()` analogues ; les aligner si rapides
  (sinon les noter pour un lot ultérieur — ne pas élargir le périmètre).

## Tests & vérification

- `frontend/src/__tests__/CommandPalette.test.tsx` : focus initial sur le champ, `aria-modal` présent,
  focus restauré à la fermeture.
- `frontend/src/__tests__/ScreenerPage.test.tsx` : une erreur d'export rend un message inline
  (`role="alert"`), plus aucun appel à `window.alert`.
- `cd frontend && npm run typecheck` → 0 erreur ; `npm test` vert.

## Critères d'acceptation

- [ ] `CommandPalette` expose `role="dialog"` + `aria-modal`, piège le focus, le restaure à la fermeture.
- [ ] Plus aucun `alert()` dans `ScreenerPage.tsx` ; erreurs d'export en inline `role="alert"`.
- [ ] `npm run typecheck` 0 erreur, `npm test` vert, zéro `any` ajouté.

## Branche & commit

- Branche : `claude/impl-ux-accessibilite` (depuis `dev`). PR **base `dev`**. Push à confirmer.
