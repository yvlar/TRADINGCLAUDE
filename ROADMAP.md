# Roadmap — Copilote Financier IA
**Dernière mise à jour : 2026-05-28 — Sprint 122 complété**
**Auteur : Yves Larivière**

---

## État courant du projet

| Champ | Valeur |
|-------|--------|
| **Version** | 10.9.0 |
| **Phase active** | Phase 3 — Pipeline de synthèse |
| **Sprint actif** | Sprint 123 — Code-splitting des routes + lazy-load recharts |
| **Dernier sprint complété** | Sprint 122 — Export analyse individuelle en PDF enrichi ✅ |

### Ce qui fonctionne aujourd'hui

#### API FastAPI (localhost:8000)
- `GET /healthz` — vérifie le processus, PostgreSQL et Qdrant
- `POST /analyze` — 16 skills tier2 + cache Redis + cache composite_score < 24h (Sprint 65 — circuit court DB)
- `POST /screen` — screener multi-tickers (max 20, asyncio.gather + Semaphore) ; `ScreenEntry.analyzed_at` = date ISO de l'analyse sous-jacente (cache ou fraîche), None pour les échecs (Sprint 109)
- `DELETE /cache/{ticker}` — invalidation cache admin
- `GET /history?ticker=BNS` — historique paginé par cursor ; `?q=ACHAT` pour recherche cross-ticker (Sprint 73)
- `GET /metrics?days=30` — coûts cumulés, taux de cache, top tickers, `skills_cost` (coût USD réparti par skill) + `cache_by_workflow` (taux de cache par workflow) (Sprint 107) + `daily_cost` (coût USD total par jour, clé YYYY-MM-DD) (Sprint 112)
- `GET /metrics/skill-analyses?skill=&days=30` — drill-down : analyses ayant utilisé un skill donné sur la période (ticker / workflow / coût / date), filtre jsonb `skills_used @> [skill]`, 422 si `skill` absent (Sprint 112)
- `GET /telemetry/summary|costs|cache|latency` — métriques observabilité (Sprint 18)
- `GET /performance/{ticker}` — rendement rétrospectif par analyse (Sprint 39)
- `POST /auth/register` — inscription email/mot de passe, cookies JWT httpOnly + CSRF (Sprint Login)
- `POST /auth/login` — authentification cookie, rate limiting Redis 5/15 min (Sprint Login)
- `POST /auth/logout` — blacklist JWT jti + invalidation refresh token (Sprint Login)
- `POST /auth/refresh` — rotation refresh token avec détection de vol par famille (Sprint Login)
- `GET /auth/me` — profil utilisateur authentifié via cookie access_token (Sprint Login)
- `GET /alerts?limit=50` — historique des alertes Celery (ESG + composite + prix) (Sprint 99)
- `GET /semantic-search?q=&k=5` — recherche sémantique RAG dans `investment_knowledge` ; `rag_enabled=false` + `results=[]` si `OPENAI_API_KEY` absente (Sprint 106)
- `POST /auth/forgot-password` — token réinitialisation itsdangerous 1h (anti-énumération) (Sprint Login)
- `POST /auth/reset-password` — réinitialisation mot de passe avec token signé (Sprint Login)
- `POST /admin/keys` — créer une clé API (admin only) (Sprint 62)
- `GET /admin/keys` — lister toutes les clés (admin only) (Sprint 62)
- `DELETE /admin/keys/{id}` — révoquer une clé (admin only) (Sprint 62)
- `DELETE /history/{analysis_id}` — supprimer une analyse individuelle (admin only, 204/404/422) (Sprint 95)
- `GET /ticker-report/{ticker}?days=90` — rapport PDF multi-pages par ticker (Sprint 63) ; **paramètre `analysis_id` optionnel (Sprint 122)** : cible une analyse précise (404 si absente/ticker différent), reconstruction multi-skills (16 outputs tier2, skill corrompu ignoré) + PDF enrichi (verdicts skill par skill, ratios clés, annotation, score ESG) ; sans `analysis_id` = comportement inchangé (rétrocompatible)
- Celery beat — `run_scheduled_screener` dimanche 11h00 UTC (Sprint 64) — screener watchlist complet + webhook FORT
- RAG Qdrant activé si `OPENAI_API_KEY` présente (collection `investment_knowledge`)
- Langfuse activé si `LANGFUSE_SECRET_KEY` présente
- Retry exponentiel sur erreurs 429/529 (`app/utils/retry.py`)
- Prompt caching activé sur tous les system prompts

#### Frontend React (localhost:5173) — 11 pages + auth
- SPA React 18 + TypeScript strict, Vite (proxy → :8000), Tailwind 4, shell pleine largeur `max-w-shell`, design tokens sémantiques, animations + skeletons, palette de commandes ⌘K
- **Analyze** — saisie ticker + ratios, auto-fill Yahoo Finance, streaming SSE skill par skill, badge « score depuis cache <24h »
- **Screener** — batch 2-20 tickers, tri persistant + filtres composite + colonne fraîcheur (badge frais/périmé >24h) + export CSV filtré
- **History** — historique par ticker, recherche full-text `q` cross-ticker (index GIN pg_trgm), filtre par plage de dates, suppression par analyse
- **Watchlist** — positions surveillées, analyses manuelles, seuils ESG + prix éditables inline, score composite historique, export Excel
- **Dashboard v2** — métriques live WebSocket + section détaillée (top tickers, coût par skill avec drill-down, cache par workflow, alertes/jour, tendance coût quotidien), grille responsive 12 colonnes, eval drift
- **Comparer** — 2-5 tickers multi-skills côte à côte (historique ou analyse live opt-in, streaming SSE)
- **ESG** `/esg` — scores ESG de la watchlist (tableau triable, badges ESG_FORT/MODERE/FAIBLE)
- **Alertes** `/alerts` — tableau des alertes Celery récentes
- **Recherche** `/recherche` — recherche sémantique RAG en langage naturel
- **Admin** — gestion des clés API (créer/lister/révoquer)
- **Auth** — pages register / forgot-password / reset-password, session restaurée au montage (authMe)
- **Rapports PDF** — par ticker (ou analyse précise `analysis_id`), screener, watchlist, mensuel (section ESG)
- **UI skills 100 % riche** — les 16 skills tier2 rendus en composants React structurés et typés depuis les schemas Pydantic (plus aucun JSON brut ; `SkillSection` générique retiré) — Sprints 118-121

#### Outillage & corpus
- `.claude/rules/` — 16 règles path-scoped (CLAUDE.md allégé) ; `docs/cheatsheet.md` — commandes opérationnelles ; `.gitignore` durci
- `.claude/skills/` — 16/16 skills tier2 documentés (SKILL.md + references) → corpus RAG `investment_knowledge` complet

### Skills opérationnels
18 skills en production (16 tier2 + 2 tier1). Catalogue détaillé (code API → chemin de code) : `.claude/rules/base-connaissances-skills.md` et `CLAUDE.md`.

---

## Phases complétées

### Phase 0 — Bootstrap ✅
API FastAPI + graham_analysis + PostgreSQL + prompt caching.

### Sprint 121 — Refonte UI Fisher + Damodaran + Marks + Pabrai + Fiscalité ✅

**Objectif :** Clôturer la refonte UI démarrée aux Sprints 118-120 sur les cinq derniers skills encore affichés en JSON brut générique (`SkillSection`) — créer des composants React structurés typés depuis les schemas Pydantic backend, puis retirer le composant générique devenu inutile.

**Livrables :**
- `frontend/src/types/index.ts` — ajout des types structurés `FisherPoint`, `FisherOutput`, `DamodaranOutput`, `MarksOutput`, `DhandhoPrincipe`, `PabraiOutput`, `CanadianTaxOutput` ; `AnalyzeResponse.fisher`, `.damodaran`, `.marks`, `.pabrai` et `.canadian_tax` typés précisément (plus `SkillOutput` générique)
- `frontend/src/components/FisherSection.tsx` — en-tête avec badge qualité de direction (libellé FR : exceptionnelle/bonne/adéquate/médiocre) + verdict badge (ACHAT_FORT/ACHAT/CONSERVER/EVITER) ; score Fisher /30 ; liste des 15 points (titre + commentaire + score /2 coloré) ; recommandations
- `frontend/src/components/DamodaranSection.tsx` — en-tête avec badge cohérence + verdict badge (NARRATIVE_FORTE/ACCEPTABLE/FAIBLE/INCOHERENTE) ; échelle possible→plausible→probable (niveau atteint mis en évidence, état incohérent en rouge) ; solidité de la narrative /10 ; ERP implicite en % (masqué si null) ; divergences en badges ; recommandations
- `frontend/src/components/MarksSection.tsx` — en-tête avec badge position de cycle (libellé FR : pessimisme excessif/pessimisme/neutre/optimisme/euphorie) + badge timing (ACHETER_AGRESSIF/ACHETER_PRUDEMMENT/ATTENDRE/REDUIRE/VENDRE) ; jauge du pendule −5→+5 avec marqueur et score coloré selon la logique contrariante ; second-level thinking ; recommandations
- `frontend/src/components/PabraiSection.tsx` — en-tête avec verdict badge (DHANDHO_FORT/DHANDHO_MOYEN/PAS_DHANDHO) ; asymétrie upside/downside (×, colorée) ; Kelly fractionnel en % (N/A si null) ; score heads-I-win /9 ; grille des 9 principes Dhandho (✓/✗ + commentaire) ; recommandations
- `frontend/src/components/CanadianTaxSection.tsx` — en-tête avec badge compte recommandé (libellé FR + sigle EN : CELI (TFSA)/REER (RRSP)/CELIAPP (FHSA)/non-enregistré) ; justification fiscale ; taux d'inclusion du gain en capital en % ; badge Smith Manœuvre si applicable ; retenue à la source US (masquée si null) ; recommandations
- `frontend/src/components/AnalysisResult.tsx` — branchement sur les cinq nouveaux composants ; **retrait du composant `SkillSection` générique et de l'import `SkillOutput`** (plus aucun skill en JSON brut)
- `frontend/src/__tests__/FisherSection.test.tsx`, `DamodaranSection.test.tsx`, `MarksSection.test.tsx`, `PabraiSection.test.tsx`, `CanadianTaxSection.test.tsx` — 6 tests Vitest chacun (30 au total)

**Version** : 10.8.0
**Tests** : 1 423 CI verts (inchangé — sprint frontend pur) ; 391 Vitest verts (+30 Sprint 121) ; tsc 0 erreur ; ESLint 0 ; ruff clean

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0 erreur/0 warning), Vitest composant (+30), et la suite backend complète (1 423 verts, ruff `All checks passed`).

---

### Sprint 120 — Refonte UI Lynch + Greenblatt + Munger + Klarman ✅

**Objectif :** Poursuivre le pattern des Sprints 118/119 sur le dernier lot de skills encore affichés en JSON brut générique (`SkillSection`) — créer des composants React structurés typés depuis les schemas Pydantic backend pour les quatre frameworks identifiés comme prioritaires : Lynch (catégorie + PEG), Greenblatt (rang ROC + earnings yield), Munger (biais cognitifs détectés), Klarman (marge de sécurité + downside).

**Livrables :**
- `frontend/src/types/index.ts` — ajout des types structurés `LynchCategoriesOutput`, `GreenblattOutput`, `BiaisCognitif`, `MungerOutput`, `KlarmanOutput` ; `AnalyzeResponse.lynch`, `.greenblatt`, `.munger` et `.klarman` typés précisément (plus `SkillOutput` générique)
- `frontend/src/components/LynchCategoriesSection.tsx` — en-tête avec badge catégorie (libellé FR des 6 archétypes : croissance lente/pilier/croissance rapide/cyclique/redressement/jeu d'actifs) + verdict badge (EXCELLENT/BON/MOYEN/EVITER) ; ratio PEG mis en évidence et coloré (< 1 bull, 1-2 neutral, > 2 bear, N/A si null) ; badge tenbagger potentiel ; score de qualité de croissance /5 ; recommandations
- `frontend/src/components/GreenblattSection.tsx` — en-tête avec verdict badge (TOP_DECILE/BON/MOYEN/EVITER) ; ROC et rendement des bénéfices affichés en % avec couleur seuillée ; situations spéciales en badges ; recommandations
- `frontend/src/components/MungerSection.tsx` — en-tête avec verdict comportemental badge (CONFIANCE_JUSTIFIEE/BIAIS_DETECTE/ALERTE_ROUGE) + badge lollapalooza si risque ; grille des biais cognitifs détectés (nom + badge d'impact MINEUR/MODERE/MAJEUR + description) ou message si aucun ; analyse par inversion ; recommandations
- `frontend/src/components/KlarmanSection.tsx` — en-tête avec badge type de situation qualifié (libellé FR : net-net/actifs cachés/en détresse/situation spéciale/valeur classique) + verdict badge (OPPORTUNITE_FORTE/OPPORTUNITE_MODEREE/ATTENDRE/PASSER) ; décote vs valeur intrinsèque en % (colorée selon le signe) ; barres scores marge de sécurité + préservation du capital /10 ; recommandations
- `frontend/src/components/AnalysisResult.tsx` — branchement sur `LynchCategoriesSection`, `GreenblattSection`, `MungerSection` et `KlarmanSection` (plus `SkillSection` générique pour ces quatre skills)
- `frontend/src/__tests__/LynchCategoriesSection.test.tsx` — 6 tests Vitest (catégorie + verdict + toggle fermé, PEG ouvert, PEG null → N/A, badge tenbagger présent, badge tenbagger masqué, score + recommandations)
- `frontend/src/__tests__/GreenblattSection.test.tsx` — 6 tests Vitest (verdict + toggle, ROC %, earnings yield %, situations spéciales, situations vides masquées, recommandations)
- `frontend/src/__tests__/MungerSection.test.tsx` — 6 tests Vitest (verdict + toggle, badge lollapalooza présent, badge lollapalooza masqué, biais détectés, message si aucun biais, inversion + recommandations)
- `frontend/src/__tests__/KlarmanSection.test.tsx` — 6 tests Vitest (situation + verdict + toggle, décote %, décote null masquée, deux scores /10, recommandations, libellé situation NET_NET)

**Version** : 10.7.0
**Tests** : 1 423 CI verts (inchangé — sprint frontend pur) ; 361 Vitest verts (+24 Sprint 120) ; tsc 0 erreur ; ESLint 0 ; ruff clean

**Note d'environnement :** session web — tests UI navigateur non exécutés (stack Docker Postgres/Redis/Qdrant non démarrée dans le conteneur éphémère). Couverture assurée par tsc `--noEmit` (0 erreur), ESLint (0 erreur/0 warning), Vitest composant (+24), et la suite backend complète (1 423 verts, ruff `All checks passed`).

---

### Sprint 119 — Refonte UI Dorsey Moat + Buffett Quality + Valorisation ✅

**Objectif :** Appliquer le pattern Sprint 118 aux trois skills fréquemment utilisés dans `value_graham` et `compounder_buffett` qui restaient affichés en JSON brut — créer des composants React structurés typés depuis les schemas Pydantic backend.

**Livrables :**
- `frontend/src/types/index.ts` — ajout des types structurés `MoatSource`, `DorseyMoatOutput`, `BuffettFiltre`, `BuffettQualityOutput`, `ValuationMethod`, `SensitivityMatrix`, `StockValuationOutput` ; `AnalyzeResponse.dorsey`, `.buffett` et `.valuation` typés précisément (plus `SkillOutput` générique)
- `frontend/src/components/DorseyMoatSection.tsx` — en-tête avec badge type de moat (WIDE/NARROW/NONE) + barre de confiance ; durabilité ROIC ; grille des 5 sources d'avantage concurrentiel (intangibles, coûts de transfert, effets de réseau, avantages de coûts, échelle efficiente) avec présence ✓/✗, badge d'intensité (FORTE/MODÉRÉE/FAIBLE/ABSENTE) et justification ; red flags ; recommandations
- `frontend/src/components/BuffettQualitySection.tsx` — en-tête avec verdict badge (COMPOUNDER/QUALITE_CORRECTE/REJETER) + quality score /4 + barre de confiance ; owner earnings par action mis en évidence ; 4 filtres séquentiels ✓/✗ avec score et justification ; red flags ; recommandations
- `frontend/src/components/ValuationSection.tsx` — en-tête avec verdict badge (SOUS_EVALUE/JUSTE_VALEUR/SUREVALUE) + marge de sécurité composite ± % ; fourchette basse/centrale/haute (3 colonnes, centrale mise en évidence) ; 3 méthodes de triangulation (DCF/comparables/sectoriel) avec valeur + hypothèses ; matrice de sensibilité WACC × croissance terminale ; recommandations
- `frontend/src/components/AnalysisResult.tsx` — branchement sur `DorseyMoatSection`, `BuffettQualitySection` et `ValuationSection` (plus `SkillSection` générique pour ces trois skills)
- `frontend/src/__tests__/DorseyMoatSection.test.tsx` — 6 tests Vitest (toggle, 5 sources, durabilité ROIC, drapeaux rouges, recommandations, masquage drapeaux vides)
- `frontend/src/__tests__/BuffettQualitySection.test.tsx` — 6 tests Vitest (toggle + score, 4 filtres, owner earnings, owner earnings null → N/A, drapeaux + recommandations, verdict REJETER)
- `frontend/src/__tests__/ValuationSection.test.tsx` — 6 tests Vitest (toggle + marge, fourchette, 3 méthodes, matrice de sensibilité, recommandations, marge négative SUREVALUE)

**Version** : 10.6.0
**Tests** : 1 423 CI verts (inchangé — sprint frontend pur) ; 337 Vitest verts (+18 Sprint 119) ; tsc 0 erreur ; ESLint 0 ; ruff 0

---

### Sprint 118 — Refonte UI Earnings Quality + Thèse d'investissement ✅

**Objectif :** Remplacer l'affichage JSON brut des deux skills les plus riches (Earnings Quality et Investment Thesis Builder) par des composants React structurés et visuellement exploitables.

**Livrables :**
- `frontend/src/types/index.ts` — ajout des types structurés `MScoreDetail`, `ZScoreDetail`, `FScoreCriterion`, `FScoreDetail`, `CScoreSignal`, `CScoreDetail`, `SloanDetail`, `EarningsQualityOutput`, `ThesisScenario`, `ThesisBuilderOutput` ; `AnalyzeResponse.earnings_quality` et `.thesis` typés précisément (plus `SkillOutput` générique)
- `frontend/src/components/EarningsQualitySection.tsx` — composant dédié : en-tête avec verdict badge + barre de confiance (% des 5 cadres calculables) ; grille 2 colonnes des 5 frameworks : F-Score Piotroski (9 critères ✓/✗ avec détail), C-Score Montier (6 signaux ⚠/✓ avec détail), M-Score Beneish (8 ratios + seuil -1.78), Z-Score Altman (variante + seuil 2.99/1.81), Sloan accruals (ratio % + seuil ±5%) ; red flags en badges danger ; recommandations prochaine étape ; note contextuelle institutions financières
- `frontend/src/components/ThesisSection.tsx` — composant dédié : en-tête avec verdict_final badge + position size % ; 3 cartes scénarios côte à côte (bull/base/bear) avec barres de probabilité colorées, rendement cible ±%, hypothèses clés ; kill criteria en liste ✗ ; devil's advocate en box mise en évidence ; synthèse narrative découpée en paragraphes
- `frontend/src/components/AnalysisResult.tsx` — branchement sur `EarningsQualitySection` et `ThesisSection` (plus `SkillSection` générique pour ces deux skills)
- `frontend/src/__tests__/EarningsQualitySection.test.tsx` — 6 tests Vitest (toggle fermé/ouvert, F-Score, C-Score, M-Score, Z-Score, drapeaux rouges, recommandations, M-Score null → N/A)
- `frontend/src/__tests__/ThesisSection.test.tsx` — 6 tests Vitest (toggle fermé/ouvert, 3 scénarios, rendements formatés, kill criteria, devil's advocate ciblé avec `within`, narrative paragraphes)

**Version** : 10.5.0
**Tests** : 1 423 CI verts (inchangé — sprint frontend pur) ; 319 Vitest verts (+12 Sprint 118) ; tsc 0 erreur ; ESLint 0 ; ruff non modifié

---

## Sprints antérieurs (Sprint 117 → Sprint 0)

L'historique détaillé des sprints complétés est archivé dans
[`docs/roadmap-archive.md`](docs/roadmap-archive.md) — il n'est **pas** lu à
l'amorçage d'un sprint, afin de réduire le coût en tokens. Seuls les ~4 derniers
sprints restent ici (section « Phases complétées » ci-dessus).

---

## Décisions d'architecture

Les décisions structurantes (choix d'embedding, Tool Use, multi-model routing,
streaming SSE, scoring composite, etc.) sont documentées au fil des sprints dans
[`docs/roadmap-archive.md`](docs/roadmap-archive.md) et dans `.claude/rules/`
(`api-architecture.md`, `api-orchestrator.md`).

---

## Règles de mise à jour de ce fichier

1. **Après chaque sprint** : passer le sprint de 🔜 → ✅, mettre à jour le tableau
   « État courant » (Version, Sprint actif, Dernier sprint complété) et ajouter un
   bloc détaillé en tête de « Phases complétées ».
2. **Rotation vers l'archive** : ne garder ici que les **~4 derniers sprints** en
   détail. Déplacer les blocs plus anciens vers `docs/roadmap-archive.md`. Ce
   fichier doit rester court (cible < 200 lignes) — c'est lui qui est lu à chaque
   amorçage de session.
3. **Pas de doublon** : un sprint n'apparaît qu'une seule fois. Ne jamais recopier
   l'historique de mémoire — **déplacer**, pas réécrire.
4. **Chiffres de tests vérifiables** : les compteurs (« N CI verts », « N Vitest »)
   doivent provenir d'une commande réelle, pas d'une estimation
   (voir `.claude/rules/workflow-sprint.md`).
5. **Version** : semver — incrément mineur (`X.Y.0`) par sprint livré, patch
   (`X.Y.Z`) pour un correctif isolé.

---

*Roadmap mise à jour le 2026-05-28 — historique complet dans `docs/roadmap-archive.md`.*
