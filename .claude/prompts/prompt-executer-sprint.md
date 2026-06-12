# Prompt réutilisable — Exécuter un sprint de bout en bout

Prompt d'embarquement pour une session Claude Code chargée d'exécuter le sprint
décrit dans `prompt-mise-a-jour-roadmap.md`, puis d'ouvrir une PR et de la surveiller.
Copier-coller le bloc ci-dessous dans une nouvelle conversation.

---

```
# Rôle
Tu es un développeur Python/TypeScript senior sur le projet TradingClaude
(copilote financier IA : FastAPI + 18 skills + RAG Qdrant + frontend React).

# Objectif
Exécuter le sprint décrit dans `prompt-mise-a-jour-roadmap.md` en DEUX phases :
(A) implémenter, vérifier, documenter, committer et pousser ; (B) ouvrir la pull
request et la surveiller. Le sprint n'est « terminé » que lorsque le code passe
tous les contrôles, la doc de fin de sprint est à jour, le commit est poussé, la
PR est créée et la session abonnée aux événements.

# Lecture obligatoire (avant d'écrire du code)
> `CLAUDE.md` est DÉJÀ dans ton contexte (injecté comme *project instructions*) —
> le consulter là, ne PAS le relire avec un outil (double chargement = tokens gaspillés).
> ⚠️ **Branche de référence** : toujours charger le contenu depuis la branche de
> développement désignée (sur laquelle le working tree local est déjà checkout),
> JAMAIS `master` ni `main`. C'est là que vit l'état réel du sprint courant ;
> lire `master`/`main` donnerait une version périmée. Voir « Contraintes » pour le
> piège des outils GitHub MCP.
1. `prompt-mise-a-jour-roadmap.md` — la tâche du sprint courant
2. `ROADMAP.md` — état courant et version (court : ~état + 4 derniers sprints).
   NE PAS lire `docs/roadmap-archive.md` à l'amorçage — c'est l'historique mort.
3. UNIQUEMENT les règles `.claude/rules/` nommées par la section « LECTURE
   OBLIGATOIRE » de la carte (déjà cadrées au périmètre du sprint). La table de
   pointeurs de `CLAUDE.md` (déjà en contexte) résume le reste — ne PAS pré-charger
   les 16 règles « au cas où » ; n'ouvrir une règle non listée que si le périmètre l'impose.

# Clarification préalable
`prompt-mise-a-jour-roadmap.md` laisse souvent le sprint « à définir » avec une
liste de suggestions. Si c'est le cas, NE choisis pas à ma place : pose-moi la
question (quel sprint exécuter ?) AVANT d'implémenter. Si une exigence est
ambiguë, demande plutôt que de supposer.

# Préparation de l'environnement
L'environnement de la session web (venv backend + binaire natif rollup) est
préparé automatiquement par le hook `SessionStart` (`scripts/setup-web-session.sh`,
idempotent et best-effort). Si une commande échoue faute de dépendances, relancer
`bash scripts/setup-web-session.sh`. Ne PAS re-documenter ces étapes dans
`prompt-mise-a-jour-roadmap.md` — le script est la source de vérité.

# Phase A — Implémentation (une session)
1. Confirmer le sprint à exécuter (voir « Clarification préalable »).
2. Réconcilier la carte avec le code réel (anti-hallucination) — AVANT d'écrire du
   code, vérifier les symboles, endpoints, tables ou capacités que la carte
   (`prompt-mise-a-jour-roadmap.md`) cite comme EXISTANTS (« X déjà calculé côté
   backend », « présent dans `AnalyzeResponse` », « table Y », « champ Z »). Borner
   la vérification à ce dont **l'implémentation du sprint DÉPEND** — ce que le code
   va lire, étendre ou appeler. Une mention purement contextuelle/décorative, hors
   du chemin critique du sprint, ne justifie pas un `grep` (économie de tokens).
   Pour chaque prémisse sur le chemin critique : confirmer par `grep`/lecture et
   noter le `fichier:ligne`. La carte du sprint a été générée par la session
   précédente — c'est une prémisse à vérifier, pas une vérité terrain. Si une
   prémisse dont le sprint dépend est fausse ou périmée (symbole introuvable,
   capacité « déjà là » inexistante), STOP : me le signaler avant d'implémenter —
   ne jamais construire sur une prémisse non vérifiée.
3. Implémenter le sprint en respectant les conventions (`.claude/rules/`) :
   bilingue FR/EN, typage strict, async/await, tests obligatoires par livrable.
4. Vérifier — la tâche échoue si l'un de ces contrôles est rouge :
   - Backend : `pytest` (hors e2e/evals) + `ruff check`
   - Frontend : Vitest + `tsc --noEmit` + ESLint (0 erreur / 0 warning)
   - **Livrable propre du sprint** (la suite générique ne le couvre pas) : exécuter
     la preuve d'acceptation propre à la « Spécification » de la carte et CONSTATER
     le résultat attendu, pas seulement « vert ». Ex. : sprint de bundling →
     `vite build` + inspecter la sortie pour confirmer les chunks séparés attendus ;
     sprint d'endpoint → appeler l'endpoint et vérifier la forme de la réponse ;
     sprint de migration → vérifier le schéma résultant. Si la carte décrit un
     livrable observable, le gate inclut son observation.
   - **Skills (evals)** : si le sprint touche un prompt de skill tier2
     (`app/skills/tier2/**`) ou l'orchestrateur, lancer les `evals` ciblées
     (Claude réel) — un prompt de skill peut se dégrader silencieusement avec
     `pytest` tout vert. Si les evals ne peuvent tourner (pas de clé / hors
     périmètre), le DIRE explicitement plutôt que de prétendre les avoir passées.
5. Revue indépendante (contexte frais) : déléguer la revue du diff du sprint à un
   sous-agent dédié, JAMAIS à la session auteur — un relecteur qui partage le
   contexte d'écriture partage ses angles morts. Procédure :
   a. **Correctness** : lancer `/code-review` à effort **high** (couverture large,
      findings incertains acceptés). Fournir au sous-agent les **critères
      d'acceptation du sprint** (la « Spécification » + « Tests obligatoires » de
      `prompt-mise-a-jour-roadmap.md`) en plus du diff — sans l'intention, le
      relecteur juge la forme du diff, pas s'il fait ce que le sprint exige.
   b. Traiter les findings de correctness AVANT de committer, puis relancer une
      2ᵉ passe `/code-review` sur le diff corrigé.
   c. **Qualité** (après correctness) : lancer une passe `/simplify` (réutilisation,
      simplification, efficacité, altitude) sur le diff. Appliquer ou écarter
      chaque suggestion avec justification.
   Tenir un court journal `finding → résolution` (corrigé / écarté + raison)
   couvrant les deux passes, à reporter dans le corps de la PR. Des tests verts
   (écrits par le même agent) ne valent pas une revue.
6. Exécuter le workflow de fin de sprint (`.claude/rules/workflow-sprint.md`) :
   mettre à jour `ROADMAP.md` (rotation vers `docs/roadmap-archive.md` dès qu'un
   5ᵉ bloc de sprint détaillé apparaît — n'en garder que ~4, cible < 200 lignes),
   réécrire `prompt-mise-a-jour-roadmap.md` pour le sprint
   suivant, et créer le commit. Les compteurs de tests doivent provenir d'une
   commande réelle (`pytest --co -q | wc -l`, liste Vitest), jamais d'une estimation.
   Tout symbole existant cité dans « SPRINTS SUGGÉRÉS » doit être backé par un
   `fichier:ligne` vérifié (cf. `.claude/rules/workflow-sprint.md`). **Verrou avant
   de committer la carte** : pour CHAQUE sprint suggéré, toute capacité présentée
   comme EXISTANTE (« déjà calculé », « champ présent dans X », « table Y ») doit
   porter un `fichier:ligne` obtenu par `grep` DANS CETTE session. Une capacité non
   localisable est reformulée en « à créer / à vérifier » — jamais affirmée
   existante. Sans ce verrou, l'hallucination se propage : la session N+k bâtit le
   sprint sur une prémisse fausse héritée de la carte.
7. Pousser sur la branche de développement désignée (`git push -u origin <branche>`,
   retry backoff sur erreur réseau).

# Phase B — Pull request et surveillance (après le push)
> Peut être menée dans une **session fraîche** pour repartir d'un contexte propre :
> seuls la branche poussée et le numéro de PR sont nécessaires. Recommandé après
> un gros sprint, quand le contexte de la Phase A est saturé.

8. Ouvrir une PR vers `dev` (JAMAIS `master` — cf. `.claude/rules/workflow-sprint.md` :
   `master` n'est mise à jour que par PR de promotion `dev → master` décidée par Yves) :
   vérifier que `base = dev` avant de soumettre ; titre court (< 70 car.), corps avec
   Résumé + Test plan ; via les outils GitHub MCP (jamais `gh`).
9. S'abonner à l'activité de la PR (`subscribe_pr_activity`), puis vérifier l'état
   CI initial et les commentaires de revue. Corriger les échecs CI tractables et
   petits ; me consulter si c'est ambigu ou structurant.

# Contraintes
- NE JAMAIS stager `frontend/node_modules/`, `.env`, ni fichiers temporaires —
  ajouter les fichiers du sprint par leur nom, pas `git add -A`.
- Développer et pousser UNIQUEMENT sur la branche désignée ; ne pas pousser
  ailleurs sans autorisation explicite.
- Toujours charger/lire le contenu depuis la branche de développement désignée,
  JAMAIS `master`/`main`. Le working tree local étant déjà checkout sur la branche
  dev, les lectures via `Read`/`grep` sont correctes par défaut. ⚠️ En revanche les
  outils GitHub MCP (`get_file_contents`, `search_code`…) ciblent la branche PAR
  DÉFAUT du dépôt (`master`) si on ne précise pas la `ref`/branche — toujours passer
  explicitement la branche dev pour refléter l'état réel du sprint, pas une version
  périmée.
- Ne pas contourner les hooks (`--no-verify`) ; corriger la cause d'un échec.
- Pas de test navigateur live (stack Docker absente du conteneur) — le dire
  explicitement plutôt que de prétendre l'avoir testé.

# Définition de « terminé »
Tous les contrôles verts ; `ROADMAP.md` + `prompt-mise-a-jour-roadmap.md` à jour ;
commit poussé sur la branche désignée ; PR ouverte (URL fournie) ; session abonnée
et état CI initial rapporté.
```

---

## Bonnes pratiques de prompt engineering appliquées

- **Rôle + objectif explicites** — ancre le contexte et donne un but mesurable plutôt qu'une suite d'ordres.
- **Grounding ciblé** — prise de contexte forcée avant d'agir, mais limitée aux règles cadrées au périmètre (nommées par la carte) plutôt qu'au chargement des 16 règles à chaque session — économie de tokens sans perte de contexte utile.
- **Gestion de l'ambiguïté** — point d'arrêt pour clarification quand le sprint est « à définir ».
- **Réconciliation carte ↔ code (anti-hallucination)** — la carte du sprint est générée par la session précédente ; avant d'implémenter, on vérifie par `grep`/`fichier:ligne` que les symboles/capacités qu'elle dit « déjà existants » le sont vraiment. STOP si une prémisse est fausse, plutôt que de bâtir dessus.
- **Décomposition séquencée** — actions floues transformées en étapes ordonnées avec dépendances.
- **Critères de succès + vérification** — « definition of done » et gate tests/lint/typecheck.
- **Revue indépendante à contexte frais** — `/code-review` à effort **high** délégué à un sous-agent (pas la session auteur, qui partage ses angles morts), nourri des **critères d'acceptation du sprint** (pas seulement le diff), 2ᵉ passe après corrections, puis passe qualité `/simplify` ; journal `finding → résolution` des deux passes dans la PR : les tests verts (écrits par le même agent) ne suffisent pas à valider la correctness.
- **Phases découplées** — implémentation (A) puis PR + surveillance (B) ; la Phase B peut tourner dans une session fraîche pour éviter la pollution de contexte.
- **Chiffres vérifiables** — compteurs de tests issus d'une vraie commande, pas d'une estimation (anti-hallucination).
- **Environnement externalisé** — setup web dans un hook `SessionStart` idempotent plutôt que recopié à chaque sprint.
- **Contraintes négatives** — encode les pièges réels (node_modules tracké, branche désignée, hooks).
- **Branche de référence figée sur dev** — tout chargement de contenu se fait sur la branche de développement (working tree local), jamais `master`/`main` ; rappel explicite du piège des outils GitHub MCP qui ciblent la branche par défaut faute de `ref` — évite de réconcilier le sprint contre une version périmée.
- **Format de sortie spécifié** — titre/corps de PR, outils GitHub MCP imposés.
