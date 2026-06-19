# Audit — Dimension UI/UX

> Produit par l'agent `audit-uiux`. Constats sourcés `fichier:ligne`. Hypothèses vérifiées dans [`00-synthese-hypotheses.md`](00-synthese-hypotheses.md).

## Résumé exécutif

Le frontend est de très bonne facture : TypeScript strict (objectif zéro `any` tenu via un `types/index.ts` centralisé), **86 fichiers de tests Vitest**, streaming SSE propre (générateur async + `AbortController`), états loading/error/empty complets, et sécurité côté client soignée (CSRF double-submit, purge du cache react-query au logout pour éviter les fuites cross-tenant). L'accessibilité de base est présente (HTML sémantique, `aria-label`, `role="alert"`, et `aria-sort` sur les en-têtes triables). Après vérification, les améliorations réelles se réduisent au **polish** : la modale `CommandPalette` sans focus trap/`aria-modal`, et les erreurs d'export via `alert()` bloquant. Deux constats initiaux ont été **infirmés** : l'overflow des tables est en fait **uniforme** (composant `ui/table.tsx` partagé) et `aria-sort` **est déjà présent** — voir [`00-synthese-hypotheses.md`](00-synthese-hypotheses.md).

**Note globale : A.** (révisée à la hausse après retrait de 2 faux positifs).

## Forces

- Type-safety stricte : zéro `any`, types miroir du backend dans `frontend/src/types/index.ts`.
- Streaming SSE robuste : `frontend/src/api/analyze.ts` (`streamAnalyze`) + annulation par `AbortController` dans `AnalyzePage`.
- Sécurité client : `frontend/src/api/client.ts` (CSRF double-submit, cookies httpOnly, Bearer optionnel) ; `queryClient.clear()` au logout (`AuthContext`).
- États complets : skeletons (`SkeletonTable`/`SkeletonCard`), erreurs inline `role="alert"`, empty states explicites.
- 86 tests Vitest (`frontend/src/__tests__/`) avec mocks réseau et polyfills Radix/cmdk.

## Faiblesses observées

| ID | Sévérité | Constat | fichier:ligne | Impact utilisateur | Verdict vérif. |
|----|----------|---------|---------------|--------------------|----------------|
| ~~Q~~ | ~~Moyenne~~ → **Néant** | ~~Débordement des tables incohérent selon la table~~ — **INFIRMÉ** : l'overflow est **uniforme** via le composant partagé | `frontend/src/components/ui/table.tsx:6` (`<div className="w-full overflow-auto">`) ; les 3 tables passent par `<Table>` | Faux positif : comportement homogène, pas d'incohérence | **INFIRMÉE** |
| R | Moyenne | Erreurs d'export CSV/XLSX via `alert()` bloquant plutôt qu'un composant inline | `frontend/src/pages/ScreenerPage.tsx:49,65` | UX dégradée, incohérente avec le reste (erreurs inline) | CONFIRMÉE |
| S | Moyenne | `CommandPalette` (Ctrl+K) : pas de focus trap ni `aria-modal`/`role="dialog"`, focus non restauré à la fermeture | `frontend/src/components/CommandPalette.tsx:99` (overlay sans rôle ARIA) | Navigation clavier/lecteur d'écran imparfaite | CONFIRMÉE |
| ~~T~~ | ~~Basse~~ → **Néant** | ~~En-têtes triables sans `aria-sort`~~ — **INFIRMÉ** : `aria-sort` est présent | `frontend/src/components/ScreenerTable.tsx:158` (`<TableHead aria-sort={ariaSort}>`) | Faux positif : tri déjà annoncé aux lecteurs d'écran | **INFIRMÉE** |
| U | Basse | Strings FR codées en dur (pas d'i18n) + quelques défauts en dur (tickers `BNS, TD, RY`, workflow `value_graham`) | `frontend/src/pages/ScreenerPage.tsx`, `WatchlistPage.tsx` | Mono-langue ; **choix de design assumé**, pas un bug | — |

## Améliorations priorisées

| ID | Action | Effort | Valeur |
|----|--------|--------|--------|
| R | Remplacer `alert()` par un composant d'erreur inline (réutiliser le pattern QuotaBanner) | Faible | Moyenne |
| S | Ajouter focus trap + `aria-modal`/`role="dialog"` + restauration de focus à `CommandPalette` | Moyen | Moyenne |
| U | Si multi-langue prévu : introduire react-i18next ; sinon extraire les défauts en constantes | Moyen | Basse |

> Les améliorations ex-Q (`overflow-x-auto`) et ex-T (`aria-sort`) sont **retirées** : déjà en place (cf. verdicts INFIRMÉE).

## Hypothèses à vérifier

- **H-Q** : certaines tables de données ont `overflow-x-auto` et d'autres non — le problème de débordement mobile est **partiel**, pas généralisé.
- **H-R** : `frontend/src/pages/ScreenerPage.tsx` utilise `alert()` pour signaler des erreurs d'export.
- **H-S** : `frontend/src/components/CommandPalette.tsx` ne contient ni `aria-modal` ni mécanisme de focus trap.
- **H-T** : aucun `aria-sort` n'est présent sur les en-têtes de `ScreenerTable.tsx`.
