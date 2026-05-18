# Workflow de fin de sprint

<!-- Rule universelle : chargée à chaque session. -->

## Quand cette règle s'applique

À la fin de chaque sprint, dès que les livrables sont validés.  
**Ces mises à jour sont automatiques — ne pas demander confirmation à Yves.**

Un sprint n'est **pas terminé** tant que ces deux fichiers n'ont pas été mis à jour.

## Règles

### 1. Mettre à jour `ROADMAP.md`

- Passer le sprint complété de 🔜 → ✅
- Mettre à jour le champ **Sprint actif** (numéro du sprint suivant)
- Mettre à jour **Dernier sprint complété** (numéro + nom + ✅)
- Incrémenter la **version** (semver : patch pour petits ajouts, minor pour nouvelles fonctionnalités, major pour changements d'architecture)
- Ajouter le sprint suivant dans la roadmap si absent

### 2. Réécrire `prompt-mise-a-jour-roadmap.md`

Réécrire intégralement pour le sprint suivant — ce fichier est la carte d'embarquement de la prochaine session Claude Code :

| Section | Contenu attendu |
|---|---|
| **Titre** | Numéro et nom du sprint suivant |
| **État du projet** | Résumé de ce qui fonctionne maintenant (version, fonctionnalités actives) |
| **LECTURE OBLIGATOIRE** | Fichiers critiques à lire avant de commencer (CLAUDE.md, ROADMAP.md, architecture) |
| **TÂCHE** | Spécification détaillée et complète du sprint suivant |
| **SPRINTS SUGGÉRÉS** | 3-5 sprints non encore planifiés (voir format ci-dessous) |
| **Template** | Instruction de démarrage pour la prochaine session |

### Format de la section SPRINTS SUGGÉRÉS

```markdown
## SPRINTS SUGGÉRÉS (non planifiés)

### Sprint N+1 — Nom court
**Objectif** : description en une phrase de ce que ce sprint livre.
**Complexité** : Faible / Moyenne / Élevée
**Justification** : pourquoi maintenant, quelle valeur apporte ce sprint au projet.

### Sprint N+2 — ...
```

Proposer 3-5 sprints distincts, non redondants, qui font avancer le projet vers Phase 3 complète.

### Rappel

`ROADMAP.md` et `prompt-mise-a-jour-roadmap.md` sont la source de vérité pour la prochaine session. Sans leur mise à jour, la session suivante commence avec un contexte obsolète et perd le fil du projet.
