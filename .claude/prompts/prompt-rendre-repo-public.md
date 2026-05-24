# Rendre TradingClaude public sur GitHub

**Copier-coller ce fichier dans une nouvelle conversation Claude Code.**

---

## Contexte

Repo : `https://github.com/yvlar/TRADINGCLAUDE` (actuellement privé)
Remote git : `TRADINGCLAUDE` (pas `origin`)
Branche : `master`
Version : 9.5.0

Le Sprint 100 a nettoyé la structure (racine épurée, tests réorganisés, `.gitignore` renforcé).
Deux problèmes bloquants restent à régler avant de passer le repo en public.

---

## ÉTAPES — dans cet ordre exact

### ÉTAPE 1 — Invalider la clé Anthropic exposée (hors terminal)

Un commit ancien (`25271fc2 ish`) a commité le fichier `.env` avec une vraie clé :
```
ANTHROPIC_API_KEY=ANTHROPIC_KEY_REDACTED
```

**Action manuelle** : aller sur [console.anthropic.com](https://console.anthropic.com) → API Keys → supprimer cette clé → en générer une nouvelle → mettre à jour le `.env` local.

**Ne pas continuer avant d'avoir fait ça.**

---

### ÉTAPE 2 — Purger `.env` de l'historique git

Deux commits ont commité le fichier `.env` directement : `25271fc2` et `a97c373b`.

```bash
# Installer l'outil (si absent)
pip install git-filter-repo

# Supprimer .env de TOUS les commits — réécrit l'historique
git filter-repo --path .env --invert-paths --force

# Vérifier — doit retourner vide
git log --all -S "sk-ant-api03" --oneline

# Vérifier — .env absent du HEAD
git show HEAD:.env 2>/dev/null || echo "OK"
```

---

### ÉTAPE 3 — Corriger le submodule cassé `.claude/skills/`

`.claude/skills/` contient un `.git` imbriqué sans `.gitmodules`.
Sur GitHub, les SKILL.md apparaîtront comme un submodule cassé (icône ↗, contenu invisible).

```bash
# Supprimer le .git imbriqué (irréversible)
Remove-Item -Recurse -Force ".claude/skills/.git"

# Supprimer le dossier orphelin
Remove-Item -Recurse -Force ".claude/skills/investment"

# Ajouter les SKILL.md au repo principal
git add .claude/skills/
git commit -m "chore: intégrer SKILL.md dans le repo principal — retire gitlink cassé"
```

---

### ÉTAPE 4 — Force push (obligatoire après filter-repo)

`git filter-repo` réécrit l'historique → les SHA changent → le push ordinaire sera rejeté.

```bash
git push TRADINGCLAUDE master --force
```

---

### ÉTAPE 5 — Vérification finale avant publication

```bash
# Aucun secret dans le HEAD
git show HEAD:.env 2>/dev/null || echo "OK — .env absent"
git log --all -S "sk-ant-" --oneline | head -5

# CI vert en local
python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q --tb=short

# Racine propre (aucun fichier parasite)
ls
```

Contenu attendu à la racine :
`CLAUDE.md`, `CONTRIBUTING.md`, `Dockerfile`, `LICENSE`, `README.md`, `ROADMAP.md`,
`SECURITY.md`, `docker-compose.yml`, `docker-compose.prod.yml`, `pyproject.toml`,
`pytest.ini`, `prompt-mise-a-jour-roadmap.md`, `requirements*.txt`, `app/`, `docs/`,
`frontend/`, `infra/`, `scripts/`, `tests/`

---

### ÉTAPE 6 — Passer le repo en public sur GitHub

GitHub → `https://github.com/yvlar/TRADINGCLAUDE` → **Settings** → **Danger Zone**
→ **Change repository visibility** → **Make public** → confirmer.

---

## Points de contrôle post-publication

- [ ] Le CI GitHub Actions passe (4 jobs verts)
- [ ] Les SKILL.md sont navigables dans `.claude/skills/` (plus de ↗ cassé)
- [ ] `analyses/` n'apparaît pas dans l'arborescence GitHub
- [ ] `.claude/settings.local.json` n'apparaît pas
- [ ] Aucune clé dans `git log --all -S "sk-ant-" --oneline`
