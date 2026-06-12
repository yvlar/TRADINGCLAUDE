# Autonomie et confirmations obligatoires

<!-- Rule universelle : chargée à chaque session. -->

## Quand cette règle s'applique

À chaque action pendant l'exécution d'un sprint — pour déterminer si une confirmation de Yves est nécessaire avant d'agir.

## Règles

### Actions libres — aucune confirmation requise

Durant l'exécution d'un sprint, Claude Code peut effectuer ces actions directement sans demander :

- **Modifier des fichiers existants** — tout fichier Python, TypeScript, Markdown, JSON, YAML du projet
- **Créer de nouveaux fichiers** — modules, schemas, tests, prompts, services, composants React
- **Exécuter des tests** — `pytest`, `vitest`, et toute commande de test du projet
- **Exécuter des commandes bash** — linting, formatage, vérifications statiques, inspection de fichiers, lecture de logs

### Confirmation obligatoire avant d'agir

Ces actions requièrent une confirmation explicite de Yves **avant** toute exécution :

| Action | Exemple | Raison |
|---|---|---|
| `git push` | `git push -u origin dev` | Affecte le dépôt distant partagé |
| Ouvrir / fusionner une PR | PR de sprint vers `dev`, PR de promotion `dev → master` | Affecte le dépôt distant partagé |
| `docker-compose down` | `docker-compose down` | Coupe l'infrastructure en cours d'exécution |
| Suppression de fichiers | `rm fichier.py`, `del fichier.ts` | Irréversible — pas de corbeille |
| Modification de `.env` | Ajouter/modifier une variable secrète | Impact direct sur tous les services |
| Opérations DB destructives | `DROP TABLE`, `DELETE FROM table` sans clause `WHERE` | Destruction irréversible de données |

> **Stratégie de branches** : `dev` = intégration (cible de toutes les PR de sprint), `master` = stable (mise à jour seulement via PR de promotion `dev → master`). Détails : [`workflow-sprint.md`](workflow-sprint.md).

### Exception — session de sprint autonome

Une session lancée via `.claude/prompts/prompt-executer-sprint.md` (exécution d'un sprint de bout en bout) est **pré-autorisée**, sans re-confirmation, pour exactement deux actions :

- `git push` vers la **branche de développement désignée** de la session (et uniquement elle)
- Ouverture de la **PR de sprint vers `dev`** (`base = dev`, jamais `master`)

Cette exception couvre la « Définition de terminé » du prompt d'exécution — rien de plus. Fusionner une PR, pousser vers une autre branche, ou toute autre action de la table ci-dessus reste à confirmation obligatoire.

### Principe de décision

- Action **locale et réversible** (via git, rebuild, ou recréation) → agir directement
- Action **distante, irréversible, ou affectant un système partagé** → demander confirmation d'abord

En cas de doute : demander plutôt qu'agir. Le coût d'une pause est faible ; le coût d'une action irréversible non voulue est élevé.
