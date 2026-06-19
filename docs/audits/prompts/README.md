# Prompts d'implémentation — priorités d'audit

Chaque fichier est un **prompt complet et autonome** pour démarrer une implémentation dans une session
Claude Code dédiée. Ils sont **divisés par domaine** (aucun chevauchement de fichiers) pour ne pas
surcharger un seul contexte. Copier le contenu d'un fichier comme message de démarrage de session.

Chaque prompt contient : référence d'audit, **LECTURE OBLIGATOIRE**, périmètre/hors-périmètre, tâche
détaillée avec `fichier:ligne` exacts, tests, critères d'acceptation, et la branche/PR cible (`dev`).

## Index

| # | Prompt | Priorité | Domaine | Hypothèses |
|---|--------|----------|---------|------------|
| 01 | [`prompt-impl-01-fraicheur-ratios.md`](prompt-impl-01-fraicheur-ratios.md) | P1 | Backend + frontend | H-A |
| 02 | [`prompt-impl-02-durcissement-mypy.md`](prompt-impl-02-durcissement-mypy.md) | P1 | Code / typage | H-M |
| 03 | [`prompt-impl-03-robustesse-backend.md`](prompt-impl-03-robustesse-backend.md) | P2 | Code + infra + obs | H-O, H-G, H-H |
| 04 | [`prompt-impl-04-ux-accessibilite.md`](prompt-impl-04-ux-accessibilite.md) | P2 | Frontend | H-S, H-R |
| 05 | [`prompt-impl-05-sedar-plus.md`](prompt-impl-05-sedar-plus.md) | P3 | Backend invest | H-B |

## Ordre suggéré

1. **03** (robustesse backend) — gain rapide, faible risque, bon échauffement.
2. **01** (fraîcheur des ratios) — valeur investisseur la plus directe.
3. **04** (UX/accessibilité) — indépendant, parallélisable avec le backend.
4. **02** (durcissement mypy) — itératif (un lot de 3-4 modules par session, à répéter).
5. **05** (SEDAR+) — décision (retrait propre recommandé) puis exécution.

Les prompts 01, 03, 04, 05 sont **indépendants** (domaines disjoints) → parallélisables. Le 02 se
répète en plusieurs lots jusqu'à vider la liste `ignore_errors` de `pyproject.toml`.

> Contexte d'audit complet : [`../00-synthese-hypotheses.md`](../00-synthese-hypotheses.md) et les
> rapports de dimension `../01`→`../04`.
