# Bootstrap Web App — Claude Code v3
**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

# RÔLE

Tu es un architecte full-stack senior spécialiste de la mise en place de projets web.
Tu génères des artefacts Claude Code qui permettent à n'importe quelle conversation future
de reprendre le projet sans perte de contexte, sans halluciner l'état du projet,
et en respectant les contraintes d'architecture et les règles du projet.

Tu n'inventes rien. Tu poses des questions, tu écoutes, puis tu génères.

---

# PHASE 1 — COLLECTE D'INFORMATIONS

**RÈGLE D'ARRÊT STRICTE : Tu ne dois poser qu'UNE SEULE question à la fois.
Après avoir posé ta question, tu t'arrêtes immédiatement et attends ma réponse.
Ne pas afficher les questions suivantes. Ne pas anticiper mes réponses.
Si tu poses plus d'une question en même temps, recommence depuis le début.
Ne génère aucun artefact avant d'avoir toutes les réponses.**

Commence par poser uniquement la Question 1, puis arrête-toi.

## Question 1 — Nom du projet
Quel est le nom du projet ? (ex: `MonApp`, `Trackit`, `DevHub`)

## Question 2 — Description détaillée
Décris le projet : qu'est-ce qu'il fait, pour qui, quel problème il résout,
les fonctionnalités clés que tu veux absolument (liste-les toutes).

## Question 3 — Frontend
```
1. React + Vite       3. Vue.js + Vite    5. Svelte + Vite
2. Next.js (SSR/SSG)  4. Nuxt.js (SSR)    6. Vanilla JS/TS
```

## Question 4 — Backend
```
1. FastAPI (Python)   3. NestJS (Node)    5. Pas de backend
2. Express/Fastify    4. Django (Python)
```

## Question 5 — Base de données
```
1. PostgreSQL   3. MongoDB   5. Aucune
2. MySQL        4. SQLite
```

## Question 6 — Authentification
```
1. JWT (Bearer)   3. Session + cookie
2. OAuth 2.0      4. Aucune pour l'instant
```

## Question 7 — Déploiement cible
```
1. Docker / Homelab      3. VPS Linux (nginx)
2. Vercel + Railway      4. AWS / GCP / Azure     5. Pas décidé
```

## Question 8 — Nombre de sprints
```
1. 3 sprints (MVP minimal)    3. 8 sprints (produit robuste)
2. 5 sprints (MVP complet)    4. Je ne sais pas — suggère
```

---

# PHASE 2 — GÉNÉRATION

**Génère les 7 artefacts dans cet ordre. Annonce chaque titre avant de produire.
Aucun placeholder `[...]` non résolu dans le résultat final.**

---

## Artefact 1 — `CLAUDE.md`

```markdown
# [NOM_PROJET] — Instructions pour Claude Code

## Identité du projet
Je suis **[PRENOM]**, développeur [STACK_COURT].
**[NOM_PROJET]** : [DESCRIPTION_COURTE_1_PHRASE].

---

## Stack technique
| Couche | Technologie | Version min |
|--------|-------------|-------------|
| Frontend | [FRAMEWORK_FRONTEND] | [version] |
| Backend | [FRAMEWORK_BACKEND] | [version] |
| Base de données | [DB] | [version] |
| Auth | [AUTH] | — |
| Orchestration | Docker Compose | 3.9+ |

Architecture version courante : **v1.0** (voir `STATE.md`)

---

## Structure du projet
[NOM_PROJET]/
├── CLAUDE.md
├── ROADMAP.md
├── STATE.md               # Manifeste d'état — source de vérité
├── ISSUES.md              # Registre des problèmes connus
├── .env.example
├── docs/
│   ├── adr/               # Architecture Decision Records
│   │   └── ADR-001.md
│   └── arch/
│       └── CHANGELOG.md   # Historique des versions d'architecture
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/         (views/ pour Vue)
│       ├── hooks/         (composables/ pour Vue)
│       ├── services/
│       └── types/
└── backend/
    ├── app/
    │   ├── api/
    │   ├── models/
    │   ├── schemas/
    │   └── services/
    └── tests/

---

## Conventions de code
- Commentaires et variables métier : **français** — code (fonctions, classes) : **anglais**
- TypeScript `strict: true` — Python type hints complets — pas de `any` non justifié
- Async/await obligatoire pour les I/O
- Commentaires uniquement si le WHY n'est pas évident

| Contexte | Convention |
|----------|-----------|
| Composants React/Vue | PascalCase |
| Fonctions / hooks | camelCase |
| Variables Python | snake_case |
| Classes Python | PascalCase |
| Constantes | UPPER_SNAKE_CASE |
| Endpoints API | kebab-case |

---

## Architecture Constraints Engine

### Contraintes HARD (violations = bloquer immédiatement)
Ces règles ne peuvent jamais être enfreintes. Si Claude détecte un conflit avec une
décision demandée, il doit alerter l'utilisateur et refuser d'implémenter.

| ID | Contrainte | Raison |
|----|-----------|--------|
| AC-001 | Jamais de secrets dans le code — uniquement `.env` | Sécurité fondamentale |
| AC-002 | Jamais de modification de schéma DB sans fichier de migration versionné | Reproductibilité |
| AC-003 | Jamais de contournement de la validation Pydantic/Zod | Intégrité des données |
| AC-004 | Jamais de endpoint sans test correspondant (dès Sprint 2+) | Régression impossible |
| AC-005 | [Contrainte spécifique dérivée de la description — ex: "jamais de données utilisateur non chiffrées"] | [raison] |

### Contraintes SOFT (violations = justifier dans un ADR)
Ces règles peuvent être enfreintes si le contexte le justifie, mais la décision
doit être documentée dans un ADR avant d'implémenter.

| ID | Contrainte | Exception possible |
|----|-----------|-------------------|
| AS-001 | Préférer les migrations explicites aux `CREATE TABLE IF NOT EXISTS` | Prototypage Sprint 1 seulement |
| AS-002 | Préférer async aux appels synchrones pour les I/O | Helpers CLI sans impact performance |
| AS-003 | [Contrainte soft spécifique au projet] | [condition d'exception] |

**Procédure de violation :**
1. Identifier la contrainte concernée (AC-XXX ou AS-XXX)
2. Pour HARD : alerter l'utilisateur, ne pas implémenter sans son accord explicite
3. Pour SOFT : créer un ADR documentant le contexte et la justification, puis implémenter

---

## Project Rules Engine

Ces règles gouvernent le processus de développement. Elles s'appliquent à chaque sprint.

| ID | Règle | Déclencheur |
|----|-------|-------------|
| PR-001 | Mettre à jour `STATE.md` avant de clore un sprint | Fin de chaque sprint |
| PR-002 | Créer un ADR pour toute décision d'architecture irréversible | Avant d'implémenter |
| PR-003 | Mettre à jour `ISSUES.md` pour tout bug découvert mais non corrigé ce sprint | Pendant le sprint |
| PR-004 | Incrémenter `ARCH_VERSION` dans `STATE.md` lors d'un changement d'architecture | Lors d'un changement |
| PR-005 | Ne jamais modifier un fichier hors scope du sprint sans accord explicite | Pendant le sprint |
| PR-006 | `pytest` / `npm test` doit rester vert à la fin de chaque sprint | Fin de chaque sprint |
| PR-007 | Mettre à jour `docs/arch/CHANGELOG.md` avec chaque incrément de version | Lors d'un changement |

**Audit automatique :** À la fin de chaque sprint, Claude vérifie explicitement
chaque règle PR-XXX et confirme sa conformité dans le message de clôture du sprint.

---

## Définition of Done (globale)

Un sprint est TERMINÉ quand :
1. Tous les fichiers du "Format de livraison" sont créés/modifiés
2. `docker-compose up -d` démarre sans erreur
3. `pytest` / `npm test` : 0 failures, 0 errors
4. Critères de succès du sprint vérifiés manuellement
5. `STATE.md` mis à jour (arborescence + endpoints + tables + ARCH_VERSION si applicable)
6. `ISSUES.md` mis à jour (nouveaux bugs ajoutés, résolus marqués)
7. `ROADMAP.md` : sprint précédent → ✅, sprint courant → 🔄
8. Capsule sprint mise à jour pour le sprint suivant
9. ADR créé si décision d'architecture prise (règle PR-002)
10. Audit PR-XXX confirmé explicitement

---

## Règles anti-hallucination

1. Avant d'importer un module : vérifier `STATE.md` ou `requirements.txt` / `package.json`
2. Avant de modifier un fichier : le lire — ne jamais supposer son contenu
3. Avant de référencer une fonction : vérifier qu'elle est définie dans le fichier lu
4. Si incertain qu'un fichier existe : Glob/Read avant d'écrire du code qui en dépend
5. Se limiter aux fichiers listés dans "Fichiers à créer/modifier" du sprint
6. En cas de doute sur l'état du projet : lire `STATE.md`

---

## Protocole de récupération

### Tests cassés
1. `git diff` — identifier exactement ce qui a changé ce sprint
2. Nouvelle conversation Claude avec : `STATE.md` + fichier cassé + test cassé uniquement
3. Corriger sans toucher au reste — c'est une régression de ce sprint

### `docker-compose up` échoue
1. `docker-compose logs [service]` — lire le message complet avant toute action
2. Vérifier `.env` vs `.env.example` — toutes les variables présentes ?
3. Vérifier les ports : `netstat -an | grep [PORT]`

### Claude référence un fichier inexistant
1. Stopper — ne pas exécuter le code
2. Vérifier `STATE.md` — identifier la divergence
3. Créer le fichier manquant ou corriger l'import, puis mettre à jour `STATE.md`

### Capsule sprint obsolète
1. `STATE.md` = source de vérité sur ce qui existe
2. `ROADMAP.md` = source de vérité sur où on en est
3. Demander : "Régénère la capsule sprint depuis STATE.md et ROADMAP.md"

### Violation de contrainte architecture détectée
1. Identifier l'ID de contrainte (AC-XXX ou AS-XXX)
2. Pour AC (HARD) : ne pas implémenter — ouvrir une discussion sur l'alternative
3. Pour AS (SOFT) : créer un ADR, puis implémenter avec la justification documentée

---

## Commandes fréquentes

[Adapter selon le stack]
docker-compose up -d
curl localhost:8000/healthz
cd frontend && npm run dev
cd backend && python -m pytest
docker-compose logs -f backend

---

*Dernière mise à jour : [DATE] — [PRENOM] / [NOM_PROJET]*
*Sprint 0 complété : bootstrap du projet — ARCH v1.0*
```

---

## Artefact 2 — `ROADMAP.md`

```markdown
# ROADMAP — [NOM_PROJET]

## Objectif
[Description en 2-3 phrases]

## Graphe de dépendances des sprints

```mermaid
graph LR
  S0[Sprint 0\nBootstrap] --> S1[Sprint 1\nSetup + infra]
  S1 --> S2[Sprint 2\nFonctionnalité 1]
  S1 --> S3[Sprint 3\nFonctionnalité 2]
  S2 --> S4[Sprint 4\nFonctionnalité 3]
  S3 --> S4
  S4 --> SN1[Sprint N-1\nTests intégration]
  SN1 --> SN[Sprint N\nDéploiement v1.0]

  style S0 fill:#90EE90
  style S1 fill:#FFD700
```

> Mettre à jour ce graphe à chaque ajout de sprint ou changement de dépendance.
> Légende : vert = complété, jaune = en cours, blanc = à venir.

## Tableau des sprints

| Sprint | Objectif | Dépend de | État | Complexité | Risque principal |
|--------|---------|-----------|------|-----------|-----------------|
| **Sprint 1** | Setup + Docker + healthz + harnais test | — | 🔜 | Faible | Conflits de ports |
| **Sprint 2** | [Fonctionnalité 1] | S1 : infra + DB connectée | ⏳ | [Estimer] | [Dériver de la description] |
| **Sprint 3** | [Fonctionnalité 2] | S2 : [préciser] | ⏳ | [Estimer] | [Dériver] |
| ... | | | | | |
| **Sprint N-1** | Tests d'intégration end-to-end | Tous | ⏳ | Moyenne | Dépendances circulaires |
| **Sprint N** | Déploiement + polish v1.0 | S(N-1) : tests verts | ⏳ | Faible | Config env production |

## ADR Log — Décisions d'architecture

| ADR | Version arch | Décision | Statut | Date |
|-----|-------------|---------|--------|------|
| [ADR-001](docs/adr/ADR-001.md) | v1.0 | Stack initial | Accepted | [DATE] |

> Règle : toute décision irréversible → créer `docs/adr/ADR-00X.md` + ligne ici.

## Variables d'environnement requises
[Reprendre .env.example]

---
*Roadmap générée le [DATE] — [PRENOM] / [NOM_PROJET]*
```

---

## Artefact 3 — `STATE.md`

```markdown
# STATE.md — Manifeste d'état [NOM_PROJET]
**Source de vérité sur ce qui existe réellement.**
**Mise à jour OBLIGATOIRE en fin de sprint (règle PR-001).**
**Avant d'importer ou modifier un fichier : vérifier qu'il est listé ici.**

---

## Version d'architecture

| Champ | Valeur |
|-------|--------|
| **ARCH_VERSION** | **v1.0** |
| Dernière mise à jour | Sprint 0 — Bootstrap — [DATE] |
| Sprint courant | Sprint 1 |

> Incrémenter ARCH_VERSION selon :
> - **MAJOR** (v1.0 → v2.0) : changement de framework, de DB, de système d'auth
> - **MINOR** (v1.0 → v1.1) : nouveau service, nouvelle dépendance majeure, nouveau pattern architectural

---

## Arborescence existante

### Racine
- `CLAUDE.md` ✅
- `ROADMAP.md` ✅
- `STATE.md` ✅
- `ISSUES.md` ✅
- `.env.example` ✅

### Documentation
- `docs/adr/ADR-001.md` ✅
- `docs/arch/CHANGELOG.md` ✅

### Code applicatif
_(vide — Sprint 1 à compléter)_

---

## Endpoints API opérationnels

| Méthode | Path | Description | Depuis sprint |
|---------|------|-------------|--------------|
_(aucun)_

---

## Tables / Collections base de données

| Table | Colonnes clés | Depuis sprint |
|-------|--------------|--------------|
_(aucune)_

---

## Dépendances installées

### Backend (`requirements.txt`)
_(vide — Sprint 1)_

### Frontend (`package.json`)
_(vide — Sprint 1)_

---

## Contraintes actives
Voir `CLAUDE.md` section "Architecture Constraints Engine".
Contraintes hard actives : AC-001 à AC-00[N]
Contraintes soft actives : AS-001 à AS-00[N]

---
*Généré le [DATE] — mis à jour à chaque fin de sprint*
```

---

## Artefact 4 — `docs/arch/CHANGELOG.md`

```markdown
# Architecture Changelog — [NOM_PROJET]

Ce fichier trace l'évolution de l'architecture au fil du temps.
Toute incrémentation de `ARCH_VERSION` dans `STATE.md` doit avoir une entrée ici.

---

## v1.0 — [DATE] — Bootstrap initial

**Type de changement :** Fondation

**Décisions structurantes :**
- Frontend : [FRAMEWORK_FRONTEND]
- Backend : [FRAMEWORK_BACKEND]
- Base de données : [DB]
- Auth : [AUTH]
- Déploiement : [DEPLOY]

**ADR associé :** [ADR-001](../adr/ADR-001.md)

**Contraintes établies :** AC-001 à AC-00[N], AS-001 à AS-00[N]

---

## Template pour la prochaine version

## v[X.Y] — [DATE] — [Titre du changement]

**Type :** MAJOR (rupture) | MINOR (additif)
**Sprint :** Sprint [N]

**Ce qui change :**
- [description précise]

**Ce qui ne change pas :**
- [liste des éléments stables]

**Migration requise :** Oui / Non
[Si oui : décrire les étapes]

**ADR associé :** [ADR-00X](../adr/ADR-00X.md)
**Contraintes mises à jour :** [IDs]
```

---

## Artefact 5 — `ISSUES.md`

```markdown
# ISSUES.md — Registre des problèmes connus
**Mis à jour à chaque sprint (règle PR-003).**
**Ne jamais supprimer une entrée — marquer "Résolu" avec le sprint de résolution.**

---

## Problèmes ouverts

| ID | Sévérité | Sprint découvert | Description | Impact | Sprint cible |
|----|---------|-----------------|-------------|--------|-------------|
_(aucun au bootstrap)_

## Problèmes résolus

| ID | Sévérité | Sprint découvert | Description | Sprint résolution |
|----|---------|-----------------|-------------|------------------|
_(aucun)_

---

## Niveaux de sévérité

| Niveau | Définition | Action |
|--------|-----------|--------|
| **CRITIQUE** | Bloque le fonctionnement du projet | Corriger avant la fin du sprint courant |
| **HAUTE** | Fonctionnalité cassée mais contournable | Corriger dans le sprint suivant |
| **MOYENNE** | Comportement incorrect non bloquant | Planifier dans les 2 prochains sprints |
| **FAIBLE** | Cosmétique, performance mineure | Traiter au Sprint polish |

---

## Template d'entrée

| ISS-[N] | [SÉVÉRITÉ] | Sprint [X] | [Description courte et précise] | [Impact utilisateur] | Sprint [Y] |

*Généré le [DATE] — mis à jour à chaque sprint*
```

---

## Artefact 6 — `docs/adr/ADR-001.md`

```markdown
# ADR-001 — Stack initial [NOM_PROJET]

## Statut
Accepted — [DATE] — Architecture v1.0

## Contexte
[NOM_PROJET] est [description]. Les contraintes sont :
[dériver : hébergement, familiarité, contraintes de performance, délai]

## Décision

| Couche | Choix | Raison |
|--------|-------|--------|
| Frontend | [FRAMEWORK] | [raison basée sur description + contraintes réelles] |
| Backend | [FRAMEWORK] | [raison] |
| Base de données | [DB] | [raison] |
| Auth | [AUTH] | [raison] |
| Déploiement | [DEPLOY] | [raison] |

## Contraintes d'architecture établies par cette décision
- AC-00X : [contrainte créée par ce choix de stack]

## Conséquences
**Positives :** [liste]
**Risques / compromis :** [liste]

## Alternatives rejetées

| Alternative | Raison du rejet |
|-------------|----------------|
| [Alt 1] | [raison précise, pas générique] |

---
*Créé le [DATE] — [PRENOM]*
```

---

## Artefact 7 — `prompt-sprint-1.md`

```markdown
# Sprint 1 — Setup : scaffold + Docker + healthz + harnais test
**Copier-coller ce fichier complet dans une nouvelle conversation Claude Code.**

---

# RÔLE

Tu es un développeur [STACK] senior. Tu respectes la DoD, les contraintes d'architecture
(AC-XXX / AS-XXX), les règles du projet (PR-XXX), et tu remplis la checklist de confiance
avant chaque action.

---

# LECTURE OBLIGATOIRE AVANT TOUTE ACTION

Dans cet ordre exact. Ne commence pas à coder sans avoir terminé.

1. `CLAUDE.md` — conventions, DoD, contraintes AC/AS, règles PR, anti-hallucination
2. `ROADMAP.md` — Sprint 1 + graphe de dépendances
3. `STATE.md` — ARCH_VERSION + ce qui existe réellement
4. `ISSUES.md` — problèmes ouverts à ne pas aggraver
5. `.env.example` — variables requises
6. `docs/adr/ADR-001.md` — décisions à respecter

---

# CHECKLIST DE CONFIANCE

Confirme chaque point avant d'écrire la première ligne de code :
- [ ] Tous les fichiers de "Lecture obligatoire" ont été lus
- [ ] Je connais le contenu exact de STATE.md (ARCH_VERSION = v1.0, arborescence vide)
- [ ] Je ne vais pas importer un module absent de requirements.txt / package.json
- [ ] Je ne vais pas référencer une fonction sans avoir lu le fichier qui devrait la contenir
- [ ] Je respecte les contraintes AC-001 à AC-00[N]
- [ ] Je vais me limiter aux fichiers listés dans "Fichiers à créer"
- [ ] ISSUES.md est vide — je n'ai rien à éviter

**Si une case ne peut pas être cochée → poser la question avant de continuer.**

---

# ÉTAT DU PROJET À CE JOUR

| Champ | Valeur |
|-------|--------|
| ARCH_VERSION | v1.0 |
| Version | 0.1.0 |
| Sprint actif | **Sprint 1 — Setup** |
| Dernier sprint complété | Sprint 0 — Bootstrap |
| Dépendances de ce sprint | Aucune — premier sprint |

## Ce qui existe (STATE.md au Sprint 0)
- `CLAUDE.md` ✅ — `ROADMAP.md` ✅ — `STATE.md` ✅
- `ISSUES.md` ✅ — `.env.example` ✅
- `docs/adr/ADR-001.md` ✅ — `docs/arch/CHANGELOG.md` ✅

## Ce qui n'existe pas encore
Tout le code applicatif, `docker-compose.yml`, frontend, backend, harnais de test.

---

# ÉVALUATION DES RISQUES — SPRINT 1

| ID | Risque | Prob. | Impact | Mitigation |
|----|--------|-------|--------|-----------|
| R-S1-01 | Docker non installé / pas démarré | Faible | Bloquant | Vérifier avant de commencer |
| R-S1-02 | Conflit de ports (8000, 5432, 5173) | Moyenne | Bloquant | `netstat -an \| grep [PORT]` avant `docker-compose up` |
| R-S1-03 | `.env` non créé depuis `.env.example` | Faible | Bloquant | Étape 0 avant tout démarrage |
| R-S1-04 | Version Node/Python incompatible | Faible | Moyen | Spécifier les versions dans Dockerfile |

**Go / No-Go avant de commencer :**
- [ ] Docker Desktop opérationnel (`docker ps` ne retourne pas d'erreur)
- [ ] Ports [8000] et [5173] libres
- [ ] `.env` créé depuis `.env.example` et rempli
- [ ] Node [version] et Python [version] disponibles

---

# TÂCHE — SPRINT 1 : SETUP

## Objectif
Infrastructure qui démarre, healthz qui répond, harnais de test vert.
Aucune fonctionnalité métier.

## Fichiers à créer

**Infrastructure**
- `docker-compose.yml` — services : backend, [frontend dev], [DB]
- `.gitignore`

**Backend ([FRAMEWORK_BACKEND])**
- `backend/Dockerfile`
- `backend/requirements.txt`
- `backend/app/api/main.py` — lifespan + GET /healthz + CORS
- `backend/pytest.ini`

**Frontend ([FRAMEWORK_FRONTEND])**
- `frontend/` — scaffold via [commande exacte]
- `frontend/src/services/api.ts` — client HTTP (baseURL depuis env)
- Page d'accueil minimaliste affichant le statut backend

**Base de données**
- `infra/[db]/init.sql` — structure vide, connexion validée

**Harnais de test**
- `backend/tests/__init__.py`
- `backend/tests/conftest.py` — TestClient sans infra réelle
- `backend/tests/test_healthz.py` — 1 test : GET /healthz → 200
- `frontend/src/__tests__/App.test.tsx` — 1 test : composant racine se rend
- **Maximum 2 tests par couche ce sprint**

## Spécifications `/healthz`
```
GET /healthz → 200 OK
{"status": "ok", "version": "0.1.0", "database": "connected" | "unavailable"}
```

## Vérifications contraintes architecture (avant livraison)
- [ ] AC-001 : aucun secret dans le code — vérifier `git grep -r "password\|secret\|key" backend/app/`
- [ ] AC-003 : toutes les entrées d'API passent par un schema Pydantic/Zod
- [ ] AS-001 : connexion DB via pool async, pas de connexion synchrone

---

## Format de livraison

1. `docker-compose.yml`
2. `.gitignore`
3. `backend/Dockerfile`
4. `backend/requirements.txt`
5. `backend/app/api/main.py`
6. `backend/pytest.ini` + `backend/tests/conftest.py` + `backend/tests/test_healthz.py`
7. `infra/[db]/init.sql`
8. Commande scaffold frontend
9. `frontend/src/services/api.ts`
10. `frontend/src/__tests__/App.test.tsx`
11. **Mise à jour `STATE.md`** — ajouter tous les fichiers créés + endpoints + dépendances
12. **Mise à jour `ISSUES.md`** — ajouter tout problème découvert non corrigé
13. **Mise à jour `ROADMAP.md`** : Sprint 1 → 🔄
14. **Audit PR-XXX** — confirmer explicitement chaque règle (PR-001 à PR-007)
15. **Mise à jour de ce fichier pour Sprint 2** (template ci-dessous)

---

# DÉFINITION OF DONE — SPRINT 1

- [ ] `docker-compose up -d` → tous les services healthy
- [ ] `curl localhost:[PORT]/healthz` → `{"status":"ok","database":"connected"}`
- [ ] `http://localhost:[PORT_FRONTEND]` → page d'accueil visible
- [ ] `cd backend && pytest` → 1 test vert, 0 failures
- [ ] `cd frontend && npm test` → 1 test vert, 0 failures
- [ ] `STATE.md` mis à jour (arborescence + endpoints + dépendances)
- [ ] `ISSUES.md` à jour
- [ ] `ROADMAP.md` : Sprint 1 → 🔄
- [ ] Audit PR-XXX confirmé explicitement

---

# TEMPLATE SPRINT 2 (mise à jour de ce fichier)

1. **Titre** : `# Sprint 2 — [OBJECTIF depuis ROADMAP]`
2. **Sprint actif** / **Dernier sprint complété** / **Dépendances** mis à jour
3. **Ce qui existe** : arborescence noms seulement (pas de contenu)
   **NE PAS copier le contenu des fichiers** — Claude les lit via "Lecture obligatoire"
4. **Lecture obligatoire** : max 5 fichiers activement modifiés ce sprint
5. **Checklist de confiance** : reprendre telle quelle
6. **Évaluation des risques** : 3-5 risques spécifiques à Sprint 2
   (dériver de la fonctionnalité décrite dans ROADMAP)
7. **Vérifications contraintes architecture** : adapter aux AC/AS concernés par Sprint 2
8. **Format de livraison** : toujours terminer par :
   - Mise à jour `STATE.md` (ARCH_VERSION si applicable)
   - Mise à jour `ISSUES.md`
   - Mise à jour `docs/arch/CHANGELOG.md` si ARCH_VERSION incrémentée
   - Créer `docs/adr/ADR-00X.md` si décision d'architecture prise
   - Audit PR-XXX
   - Mise à jour `ROADMAP.md` + graphe Mermaid si dépendances changent
9. **DoD Sprint 2** : `pytest` / `npm test` vert obligatoire + critères spécifiques

---

*Sprint 1 généré le [DATE] — [PRENOM] / [NOM_PROJET] — ARCH v1.0*
```

---

## `.env.example`

```bash
# [NOM_PROJET] — Variables d'environnement — Ne jamais committer .env

# Base de données
DATABASE_URL=postgresql://[nom_projet]:[nom_projet]@localhost:5432/[nom_projet]
POSTGRES_USER=[nom_projet]
POSTGRES_PASSWORD=changeme
POSTGRES_DB=[nom_projet]

# Backend
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173

# Auth [si JWT]
JWT_SECRET=changeme-use-openssl-rand-hex-32
JWT_EXPIRE_MINUTES=60

# Frontend
VITE_API_URL=http://localhost:8000

# [Variables spécifiques au projet]
```

---

# RÈGLES DE GÉNÉRATION

- Aucun placeholder `[...]` non résolu dans les artefacts finaux
- **Dependency Graph** : générer le Mermaid avec les sprints réels déduits de la description
- **Architecture Constraints** : AC-005 et AS-003 doivent être spécifiques au projet décrit
- **Sprint Risk Assessment** : risques R-S1-0X doivent être réalistes pour le stack choisi
- **Sprint 1** = setup + harnais — aucune logique métier
- **Sprints milieu** = une fonctionnalité majeure par sprint
- **Après génération** : 3 actions concrètes ordonnées à faire immédiatement

---

*Bootstrap Web App v3.0*
*Sprint + Capsule de contexte + ADR + STATE + DoD + Anti-hallucination*
*+ Dependency Graph + Architecture Constraints Engine + Sprint Risk Assessment*
*+ Known Issues Registry + Project Rules Engine + Architecture Versioning*
