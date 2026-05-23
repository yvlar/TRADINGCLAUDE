# Sprint CI / Dependabot — Maintenance qualite code

**Sprint independant — a utiliser quand CI devient rouge ou quand des PRs Dependabot s'accumulent.**
**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

# ROLE

Tu es un developpeur full-stack senior specialiste React + FastAPI **ET ingenieur DevOps**.
Tu maitrises Python 3.11, TypeScript strict, mypy, ruff, ESLint, pytest, vitest,
et la gestion des dependances npm/pip avec leurs breaking changes entre versions majeures.

---

# LECTURE OBLIGATOIRE AVANT TOUTE ACTION

1. `CLAUDE.md` — index slim (pointe vers `.claude/rules/`)
2. `ROADMAP.md` — version courante, sprint actif
3. `.github/workflows/ci.yml` — 4 jobs CI (test-backend, test-frontend, lint, typecheck)
4. `pyproject.toml` — configuration ruff + mypy (ignores, overrides par module)
5. `frontend/.eslintrc.cjs` — configuration ESLint + @typescript-eslint
6. `frontend/tsconfig.json` — options TypeScript strict
7. `.github/dependabot.yml` — groupes et regles d'ignore react-ecosystem

---

# ETAT DE REFERENCE CI (apres sprint 98 + hotfixes)

| Job CI | Etat | Commande locale |
|--------|------|-----------------|
| test-backend | ✅ 1383 verts | `pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q` |
| test-frontend | ✅ 205 verts | `cd frontend && npm test` |
| lint | ✅ ruff + ESLint | `ruff check app/ tests/` + `cd frontend && npm run lint` |
| typecheck | ✅ mypy + tsc | `mypy app/ --ignore-missing-imports` + `cd frontend && npm run typecheck` |

**Packages integres (a ne pas regresser) :**
- Python : asyncpg>=0.31, fastapi>=0.136.1, langfuse>=4.6.1, fakeredis>=2.35.1, respx>=0.23.1, pytest-playwright>=0.8.0
- npm : typescript ^6.0.3, @typescript-eslint/{plugin,parser} ^8.59.4, jsdom ^29.1.1

---

# TACHE — SPRINT CI / DEPENDABOT

## Etape 0 — Recuperer l'etat actuel

```bash
# Lire les branches Dependabot disponibles
git fetch TRADINGCLAUDE
git branch -r | grep dependabot

# Voir les commits en retard sur le remote
git log --oneline TRADINGCLAUDE/master..master
git log --oneline master..TRADINGCLAUDE/master

# Verifier l'etat CI actuel
.\scripts\ci-simulate.ps1          # simulation locale 4 jobs
```

## Etape 1 — Diagnostiquer les echecs CI

Pour chaque job en echec, identifier la categorie :

| Categorie | Symptome | Action |
|-----------|----------|--------|
| **Flaky test** | Passe en local, echoue en CI de facon intermittente | Encapsuler les assertions dans `waitFor()` ; remplacer `vi.clearAllMocks()` par `vi.resetAllMocks()` si queue `once` contaminee |
| **Erreur mypy** | `"X" has no attribute "Y"` sur un module tiers | Ajouter le module dans `[[tool.mypy.overrides]] ignore_errors = true` dans `pyproject.toml` |
| **Erreur ruff** | Import non utilise (F401), import non trie (I001) | Lancer `ruff check --fix app/ tests/` |
| **Erreur ESLint** | `no-explicit-any`, `no-empty-object-type` | Corriger le type ou ajouter une regle d'exception dans `.eslintrc.cjs` |
| **Erreur tsc** | Option deprecie, type manquant | Ajouter `"ignoreDeprecations"` dans `tsconfig.json` ou corriger le type |
| **Incompatibilite package** | Breaking change apres mise a jour | Voir etape 2 |

## Etape 2 — Traiter les PRs Dependabot

### Protocole de recuperation

```bash
git fetch TRADINGCLAUDE
git branch -r | grep dependabot
```

### Grille de risque

| Risque | Critere | Action recommandee |
|--------|---------|-------------------|
| **Faible** | Bump patch ou minor dans la meme major (ex : asyncpg 0.29→0.31) | Mettre a jour requirements.txt / package.json directement, sans test supplementaire |
| **Moyen** | Bump major avec deprecation d'option ou nouveau lint | Appliquer, corriger les 1-3 erreurs resultantes, committer |
| **Eleve** | Bump major avec réécriture d'API ou nouveau systeme de config | Verifier la compatibilite, adapter le code (voir items differés ci-dessous) |
| **A ignorer** | Conflit de peer dependency intentionnel | Ajouter une regle `ignore` dans `.github/dependabot.yml` |

### Verification avant de mettre a jour un package npm

```bash
# Appliquer et verifier d'un coup
cd frontend
npm install
npm run typecheck   # tsc --noEmit
npm run lint        # eslint src
npm test            # vitest run
```

### Verification avant de mettre a jour un package pip

```bash
pip install -r requirements-ci.txt
mypy app/ --ignore-missing-imports
pytest tests/ --ignore=tests/e2e --ignore=tests/evals -q --tb=short
```

---

# ITEMS DIFFERES — A TRAITER DANS CE SPRINT

Ces deux migrations ont ete differees lors du sprint precedent car elles forment un ensemble coherent.
**Elles doivent etre traitees ensemble dans le meme commit.**

## Item 1 — Vite 6 + @vitejs/plugin-react 6

**Pourquoi ensemble :** `@vitejs/plugin-react@6` requiert `vite@6`. Vite 5 n'est pas compatible.

**Changements attendus dans `frontend/package.json` :**
```json
"@vitejs/plugin-react": "^6.0.2",
"vite": "^6.x.x"
```

**Points de rupture connus Vite 6 :**
- `vite.config.ts` : verifier la syntaxe `defineConfig` (identique)
- `tsconfig.node.json` : le champ `include` peut changer
- Proxy config : `server.proxy` — API inchangee

**Procedure :**
1. Mettre a jour `package.json` (plugin-react 6 + vite 6)
2. `npm install`
3. `npm run build` — corriger les erreurs eventuelles
4. `npm test` — corriger les tests brises
5. `npm run typecheck` + `npm run lint`

## Item 2 — Tailwind CSS 4

**Pourquoi differe :** Tailwind 4 remplace `tailwind.config.js` par une configuration CSS-first.
C'est une migration de surface importante mais previsible.

**Changements majeurs Tailwind 4 :**
- `tailwind.config.js` est remplace par une directive `@import "tailwindcss"` dans le CSS principal
- Le fichier `postcss.config.js` change (plugin `@tailwindcss/postcss` a la place de `tailwindcss`)
- Les classes utilitaires restent identiques pour la plupart

**Procedure :**
1. Mettre a jour `package.json` : `"tailwindcss": "^4.3.0"` + `"@tailwindcss/postcss": "^4.x.x"`
2. `npm install`
3. Remplacer dans `frontend/src/index.css` ou equivalent :
   ```css
   /* avant */
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   /* apres */
   @import "tailwindcss";
   ```
4. Supprimer ou adapter `frontend/tailwind.config.js` (theme, content paths)
5. Adapter `postcss.config.js` : remplacer `require('tailwindcss')` par `require('@tailwindcss/postcss')`
6. Lancer `npm run dev` et verifier visuellement les pages principales
7. `npm test` — corriger les snapshots CSS eventuellesClasses qui changent entre Tailwind 3 et 4 (verifier dans le code) :
   - `bg-muted`, `text-muted-foreground` : peuvent necessiter des variables CSS personnalisees
   - Classes prefixees `dark:` — syntaxe inchangee

---

# CONTRAINTES ABSOLUES (rappel)

- Ne jamais appeler `client.messages.create()` directement — utiliser `call_claude_with_retry()`
- Les tests CI standard ne consomment aucun token Claude reel
- `pyproject.toml` : toute nouvelle erreur mypy pre-existante → ajouter dans `[[tool.mypy.overrides]]` avec commentaire expliquant pourquoi
- `frontend/.eslintrc.cjs` : toute nouvelle regle d'exception doit etre dans `rules` avec `'off'` ou `'warn'` justifie
- Jamais committer `frontend/node_modules/`, `.env`, `frontend/vite.config.ts.timestamp-*`, `test_write.txt`
- Apres chaque correction : relancer le job CI simule correspondant pour confirmer
- `vi.clearAllMocks()` dans `beforeEach` ne reinitialise pas la queue `mockReturnValueOnce` — utiliser `vi.resetAllMocks()` si des tests partagent un mock avec des valeurs `once` non consommees
- Toujours synchroniser les versions majeures `@typescript-eslint/eslint-plugin` et `@typescript-eslint/parser` (doivent etre identiques)
- `@types/react-dom` reste en v18 (regle ignore dans `dependabot.yml`) — ne pas accepter les PRs v19

---

# COMMIT DE FIN DE SPRINT

```bash
git add requirements.txt requirements-ci.txt requirements-dev.txt \
        frontend/package.json frontend/package-lock.json \
        frontend/tsconfig.json frontend/tsconfig.node.json \
        frontend/src/ \
        pyproject.toml .github/

git commit -m "chore(ci): maintenance CI + integration Dependabot — vX.Y.Z

<liste des packages mis a jour>
<corrections code apportees>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

_Template maintenance CI/Dependabot — TradingClaude_
_Derniere mise a jour : 2026-05-23_
_Packages integres : typescript 6, typescript-eslint 8, jsdom 29, asyncpg 0.31, fastapi 0.136, langfuse 4.6, fakeredis 2.35, respx 0.23, pytest-playwright 0.8_
_Items differés : Vite 6 + plugin-react 6, Tailwind 4_
