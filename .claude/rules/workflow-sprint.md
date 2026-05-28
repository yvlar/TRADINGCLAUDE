# Workflow de fin de sprint

<!-- Rule universelle : chargée à chaque session. -->

## Quand cette règle s'applique

À la fin de chaque sprint, dès que les livrables sont validés.  
**Ces mises à jour sont automatiques — ne pas demander confirmation à Yves.**

Un sprint n'est **pas terminé** tant que ces trois étapes n'ont pas été complétées.

## Règles

### 1. Mettre à jour `ROADMAP.md`

- Passer le sprint complété de 🔜 → ✅
- Mettre à jour le champ **Sprint actif** (numéro du sprint suivant)
- Mettre à jour **Dernier sprint complété** (numéro + nom + ✅)
- Incrémenter la **version** (semver : patch pour petits ajouts, minor pour nouvelles fonctionnalités, major pour changements d'architecture)
- Ajouter le sprint suivant dans la roadmap si absent
- **Rotation vers l'archive** : `ROADMAP.md` ne garde que l'état courant + les
  ~4 derniers sprints détaillés. Dès qu'un 5ᵉ bloc apparaît, **déplacer** le plus
  ancien vers `docs/roadmap-archive.md` (couper-coller, jamais recopier de mémoire).
  Cible : `ROADMAP.md` < 200 lignes (rechargé à chaque session — chaque ligne
  superflue est un coût de tokens récurrent). Ne jamais lire l'archive à l'amorçage.
- **Compteurs de tests vérifiables** : avant d'écrire « N CI verts » / « N Vitest »,
  les obtenir par une **commande réelle**, jamais par estimation ni recopie :
  - Backend : `.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals --co -q | tail -1`
  - Frontend : `cd frontend && node node_modules/vitest/vitest.mjs list | wc -l`
  Si un chiffre n'a pas été mesuré dans la session, l'omettre plutôt que l'inventer.

### 2. Réécrire `prompt-mise-a-jour-roadmap.md`

Réécrire intégralement pour le sprint suivant — ce fichier est la carte d'embarquement de la prochaine session Claude Code :

| Section | Contenu attendu |
|---|---|
| **Titre** | Numéro et nom du sprint suivant |
| **État du projet** | 2-3 lignes MAX : version + la nouveauté du dernier sprint. NE PAS recopier la liste « Fonctionnalités actives » ni les compteurs de tests — pointer vers la section correspondante de `ROADMAP.md` (source unique). La carte ne duplique pas l'état, elle y renvoie. |
| **LECTURE OBLIGATOIRE** | CLAUDE.md + ROADMAP.md, puis nommer explicitement les **1-2 règles `.claude/rules/`** réellement cadrées au périmètre du prochain sprint (pas une liste générique de toutes les règles) — c'est cette liste que la session exécutante chargera. |
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

### 3. Créer un commit git

Après les deux mises à jour documentaires, créer un commit qui inclut **tous les fichiers modifiés et nouveaux du sprint** :

```bash
# Stager les fichiers du projet (jamais node_modules, .env, fichiers temp)
git add app/ frontend/src/ tests/ infra/ scripts/ docs/ ROADMAP.md CLAUDE.md \
        prompt-mise-a-jour-roadmap.md requirements.txt .env.example \
        .claude/rules/ .claude/prompts/ .claude/settings.json .claude/settings.local.json

# Commiter avec message structuré
git commit -m "feat(sprintNN): <nom du sprint> — vX.Y.Z

<description courte des livrables principaux>
<tests : +N CI verts, +N Vitest verts — chiffres MESURÉS, voir étape 1>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

**Cette étape est automatique — ne pas demander confirmation à Yves.**  
Ne jamais inclure : `frontend/node_modules/`, `.env`, `frontend/vite.config.ts.timestamp-*`, `test_write.txt`.

### Rappel

`ROADMAP.md`, `prompt-mise-a-jour-roadmap.md` et le commit git sont la source de vérité pour la prochaine session. Sans ces trois étapes, la session suivante commence avec un contexte obsolète et du travail non sauvegardé.
