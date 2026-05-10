# Revue de projet — Copilote Financier RAG
**Rôle : Développeur Python senior, spécialiste RAG**
**Date : Mai 2026**

---

## 1. État des lieux

Le projet est en Phase 0 complète. L'infrastructure de base fonctionne :
- API FastAPI avec `/healthz` et `/analyze`
- Un skill opérationnel (`graham_analysis`) avec prompt caching
- PostgreSQL pour l'historique
- 15 skills de connaissance dans `.claude/skills/` — le futur corpus RAG
- 87 tests unitaires couvrant schemas, skill, orchestrateur et API

Le RAG n'existe pas encore. Qdrant tourne mais est vide.

---

## 2. Points à améliorer

### 2.1 Bugs et régressions silencieuses

| # | Problème | Fichier | Impact |
|---|----------|---------|--------|
| B1 | `tokens_input`, `tokens_output`, `tokens_cache_read`, `tokens_cache_creation` sont persistés à **0** en dur | `core.py:87-90` | Les données de coût dans la DB sont incomplètes — impossible d'auditer les dépenses par skill |
| B2 | `SkillBase` est défini dans `graham_analysis/skill.py` — un fichier privé à un skill | `skill.py:58` | Chaque nouveau skill devra copier-coller `SkillBase` ou créer une dépendance circulaire |
| B3 | `_calculate_cost` et `_PRICING` sont dans `skill.py` — couplage fort | `skill.py:14-45` | Le deuxième skill réimplémentera le calcul de coût, ou importera depuis un module de domaine privé |
| B4 | Le prompt impose "EXACTEMENT 8 objets" en `criteria_defensif` mais aucun code ne valide le compte | `schemas.py` + `system.md` | Si Claude retourne 7 critères, Pydantic accepte silencieusement — analyse tronquée sans erreur |
| B5 | `get_citations()` retourne `[]` sans log | `skill.py:74-76` | En Phase 1, si Qdrant est mal initialisé, on obtient toujours `[]` sans avertissement |

---

### 2.2 Architecture — dettes techniques

**Couplage SkillBase / Skills**

```
Situation actuelle :
  graham_analysis/skill.py  →  contient SkillBase + GrahamAnalysisSkill

Situation cible :
  app/skills/base.py        →  SkillBase, Citation, _calculate_cost, _PRICING
  graham_analysis/skill.py  →  importe app.skills.base, contient GrahamAnalysisSkill
```

**Tokens non persistés**

`GrahamAnalysisSkill.execute()` reçoit `response.usage` et en extrait seulement `cost_usd`.
Les 4 compteurs de tokens sont calculés mais jamais retournés au niveau de l'orchestrateur.
Solution : faire remonter un objet `UsageDetail` depuis `execute()`.

**Validation du compte de critères**

```python
# À ajouter dans schemas.py via @model_validator
@model_validator(mode="after")
def valider_comptes_criteres(self) -> "GrahamAnalysisOutput":
    if len(self.criteria_defensif) != 8:
        raise ValueError(f"criteria_defensif : attendu 8, reçu {len(self.criteria_defensif)}")
    if len(self.criteria_entreprenant) != 5:
        raise ValueError(f"criteria_entreprenant : attendu 5, reçu {len(self.criteria_entreprenant)}")
    return self
```

---

### 2.3 Observabilité — angle mort complet

Le projet n'a **aucune observabilité** sur :
- Le taux de cache hit (ratio `cache_read / input_tokens`)
- La latence des appels Claude par skill
- Le coût cumulé par ticker et par workflow
- Les erreurs de parsing JSON de la réponse Claude

Sans ces métriques, il est impossible de savoir si le prompt caching fonctionne réellement.

---

### 2.4 Solidité de l'API

- `/healthz` vérifie uniquement que le processus répond — il ne teste pas la connexion PostgreSQL, ni Qdrant, ni Redis
- Aucun timeout sur les appels `client.messages.create(...)` — une réponse lente de Claude bloque le thread
- Aucune limite de taille sur le body JSON entrant
- Aucune authentification — l'API est ouverte sur le réseau homelab

---

### 2.5 Tests — lacunes

| Test manquant | Raison |
|---------------|--------|
| Test du `@model_validator` sur le compte de critères | Bug B4 non couvert |
| Test de `_persist` avec vrais tokens (non zéro) | Bug B1 non couvert |
| Test de `get_citations` quand Qdrant est indisponible | Phase 1 |
| Test du `defensive_score` cohérent avec `criteria_defensif` | Cohérence métier |
| Test de la latence max (timeout) | Résilience |
| `asyncio.get_event_loop().run_until_complete()` dans `test_skill.py:L100` | Déprécié Python 3.10+, remplacer par `@pytest.mark.asyncio` |

---

## 3. Liste de travail — prochaines étapes

### Sprint 1 — Corrections immédiates (avant Phase 1)

```
[ ] S1-1  Créer app/skills/base.py avec SkillBase, Citation, UsageDetail
[ ] S1-2  Déplacer _calculate_cost et _PRICING dans app/utils/costs.py
[ ] S1-3  Faire remonter les tokens depuis execute() via UsageDetail
[ ] S1-4  Corriger _persist pour persister les vrais tokens
[ ] S1-5  Ajouter @model_validator dans GrahamAnalysisOutput (comptes de critères)
[ ] S1-6  Corriger le test get_citations (remplacer get_event_loop)
[ ] S1-7  Enrichir /healthz avec pg_isready + ping Qdrant
```

### Sprint 2 — Infrastructure RAG (Phase 1)

```
[ ] S2-1  Choisir le modèle d'embedding (text-embedding-3-small ou nomic-embed-text local)
[ ] S2-2  Créer scripts/ingest_rag.py :
           - Parcourir .claude/skills/*/SKILL.md et references/*.md
           - Chunker par section h2/h3 (regex sur "## " et "### ")
           - Embedder chaque chunk
           - Upsert dans Qdrant avec payload {skill_id, source_file, section, chunk_index}
[ ] S2-3  Initialiser la collection Qdrant au démarrage du service (app startup)
[ ] S2-4  Implémenter get_citations() dans GrahamAnalysisSkill avec client Qdrant
[ ] S2-5  Passer les citations dans le message utilisateur (context injection)
[ ] S2-6  Ajouter le logging structuré (JSON) avec taux de cache hit et latence
```

### Sprint 3 — Deuxième skill (Phase 2 amorce)

```
[ ] S3-1  Implémenter earnings_quality_skill (M-Score, Z-Score, F-Score, C-Score)
[ ] S3-2  Ajouter earnings_quality au workflow company_analysis
[ ] S3-3  Créer le système de context enrichment (résultat skill N → input skill N+1)
[ ] S3-4  Exposer GET /history?ticker=BNS pour consulter les analyses passées
```

### Sprint 4 — Observabilité (Phase 2-3)

```
[ ] S4-1  Intégrer Langfuse pour tracer chaque appel Claude (cost, latency, cache_hit)
[ ] S4-2  Créer un dashboard simple : coût total, coût par ticker, taux de cache
[ ] S4-3  Ajouter un timeout configurable sur messages.create (env CLAUDE_TIMEOUT_S)
[ ] S4-4  Ajouter retry avec backoff exponentiel pour les erreurs 529 (overloaded)
```

---

## 4. Priorité absolue avant d'écrire du RAG

Corriger **B1** et **B2** avant d'implémenter le deuxième skill.
Si `SkillBase` reste dans `graham_analysis/skill.py`, le projet accumule une dette
architecturale qui coûtera 2× plus cher à corriger après le troisième skill.

---

## 5. Prompt complet — pour les prochaines revues

```
# RÔLE

Développeur Python senior spécialiste RAG et architecture de systèmes LLM.
Tu maîtrises FastAPI, asyncpg, Qdrant, le SDK Anthropic Python (prompt caching,
structured output), et les patterns de production pour les applications IA.

# CONTEXTE

Projet : copilote financier RAG — analyse d'investissement multi-frameworks
basé sur 15 skills (Graham, Buffett, Dorsey, Damodaran, etc.).

Architecture :
- Source de vérité : architecture-copilote-financier.md (sections 3.2, 7.3, 8.2, 9.1, 10, 11.2)
- Phase active : {PHASE_ACTUELLE}
- Stack : Python 3.11, FastAPI, Anthropic SDK, asyncpg, Qdrant, PostgreSQL, Redis
- Corpus RAG : ~77 documents dans .claude/skills/ (SKILL.md + references/*.md)
- Prompt caching activé sur tous les system prompts (cache_control ephemeral)
- Langue du code : anglais | Commentaires, docstrings : français
- Tests : pytest-asyncio, aucun service réel dans les tests unitaires

Contraintes non-négociables :
- Type hints stricts (pas de Any non justifié)
- Async/await sur tout I/O
- Pydantic v2 pour tous les modèles de données
- cost_usd calculé et persisté sur chaque appel Claude
- citations = [] en Phase 0-1 jusqu'à l'activation du RAG

# TÂCHE

{DÉCRIRE LA TÂCHE PRÉCISE ICI}

Exemples de tâches typiques :
- "Implémenter le skill earnings_quality en héritant de SkillBase (app/skills/base.py)"
- "Écrire le script d'ingestion RAG pour les documents .claude/skills/"
- "Corriger le bug B1 : persister les vrais tokens dans analysis_history"
- "Ajouter le endpoint GET /history avec pagination cursor-based"

# CONTRAINTES NON-NÉGOCIABLES

- Ne pas modifier l'interface SkillBase sans mettre à jour tous les skills existants
- Ne pas introduire de dépendances hors requirements.txt sans justification explicite
- Chaque skill doit avoir son propre prompts/system.md (source de vérité du prompt)
- Le system prompt doit dépasser 1 024 tokens pour que le caching soit rentable
- Aucun print() — utiliser logging (logger = logging.getLogger(__name__))
- Ne pas committer .env ni les clés API

# CRITÈRE DE SUCCÈS UNIQUE

La séquence suivante s'exécute sans erreur et retourne un JSON valide avec
cost_usd > 0 et citations correctement peuplées (si RAG activé) :

docker-compose up -d
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BNS","ratios":{...}}'

# FORMAT DE SORTIE

Fichiers Python directement dans le repo courant, dans leur chemin définitif.
Pas de diff partiel — chaque fichier fourni est complet et autonome.
Un fichier par skill, un fichier par module utilitaire.

# MODE DE RÉPONSE

1. Lire architecture-copilote-financier.md sections concernées AVANT de coder
2. Si une décision d'architecture n'est pas dans le document → demander
3. Pas de commentaires décoratifs (# ===), pas de TODO, pas de placeholders
4. Après les fichiers, donner uniquement :
   - Liste des fichiers créés/modifiés (path + 1 ligne de description)
   - Commande de validation (curl ou pytest)
   - 1-2 points d'attention si applicable
```

---

*Revue générée le 7 mai 2026 — à réviser après chaque sprint complété.*
