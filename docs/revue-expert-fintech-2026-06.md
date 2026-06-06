# Revue Expert FinTech — TradingClaude

**Date** : 2026-06-05  **Branche** : `dev`  **Version analysée** : v10.39.0 (ROADMAP — sprint 153)
**Méthode** : lecture de code ancrée (`fichier:ligne`), 4 axes (moteur IA, qualité financière, UX/UI, architecture/sécurité), affirmations à fort enjeu vérifiées manuellement.
**Posture** : consultant senior FinTech, due diligence pré-investissement — critique, sans complaisance.

> Comparateurs implicites du marché moderne : TradingView, Bloomberg, Robinhood, Wealthsimple,
> Interactive Brokers, Seeking Alpha, Yahoo Finance — et la nouvelle vague d'assistants de
> recherche IA (BloombergGPT, AlphaSense, Public/Alpha, Perplexity Finance).

---

## Résumé exécutif

TradingClaude est un **copilote de recherche fondamentale value**, pas une application de trading. C'est un **moteur d'analyse multi-frameworks (16 cadres + 2 extracteurs)** piloté par l'API Claude, avec une ingénierie de **déterminisme financier remarquable** : les scores chiffrés (Altman Z, Beneish M, Piotroski F, Montier C, Sloan, Nombre de Graham, DCF/WACC) sont calculés en Python et **substitués** au LLM, qui n'interprète plus que la narrative. La base de code est mature (~19,5k LOC backend, ~18,4k LOC frontend, ~206 fichiers de tests, CI verte, auth de niveau production).

**Mais** la lecture FinTech moderne révèle un écart majeur entre la **qualité du moteur** et la **maturité produit** : pas de monétisation, **pas d'isolation multi-utilisateur** (mono-tenant), source de données unique fragile (yfinance), périmètre étroit (zéro analyse technique, macro/sectoriel embryonnaire, zéro donnée alternative), mobile sous-optimisé, et plusieurs garde-fous de sécurité conditionnels.

| Axe | Note /10 | Lecture |
|---|---|---|
| **Robustesse d'ingénierie** | 7.5 | Tests, déterminisme, auth, observabilité — sérieux |
| **Profondeur analytique financière** | 6.5 | 16 cadres + 5 scores déterministes excellents ; ROIC/bêta/macro/secteur lacunaires |
| **Moteur IA / fiabilité** | 7.0 | Tool-use forcé + T=0 + substitution = best-in-class anti-hallucination chiffrée ; narratives non vérifiées |
| **UX/UI** | 6.5 | Design system soigné ; pas d'onboarding, mobile faible, surcharge cognitive |
| **Sécurité / conformité** | 6.0 | Auth forte ; bypass conditionnels, pas de chiffrement at-rest, disclaimer mince |
| **Maturité produit / business** | 4.0 | Aucune monétisation, mono-tenant, marché de niche |
| **NOTE GLOBALE (produit investissable)** | **≈ 5.5 / 10** | Excellent actif technique dans un produit non monétisé, mono-tenant, de niche |

**Niveau** : *prototype de recherche personnel exceptionnellement abouti* — au-dessus d'un side-project, en dessous d'un produit commercial. **Potentiel réel** : élevé en tant que **moteur sous-jacent** (B2B API, white-label conseiller, génération de rapports), faible en l'état comme application retail concurrente de Wealthsimple/Robinhood.

---

## 0. Cadrage — ce que TradingClaude *est* réellement

Avant la critique, poser la nature exacte du produit (sinon on le juge sur un marché qu'il ne vise pas) :

- **C'est** : un assistant de **due diligence fondamentale** (Graham/Buffett/Lynch/Greenblatt/Damodaran/Klarman/Marks/Pabrai/Fisher/Munger/Dorsey) avec détection de fraude/faillite déterministe et fiscalité canadienne. Cible : investisseur value averti (le propriétaire, Yves).
- **Ce n'est PAS** : un broker, un bot de trading, un terminal de marché temps réel, ni une plateforme multi-tenant. Le `CLAUDE.md` l'assume (« copilote financier IA de Yves Larivière »).
- **Conséquence d'audit** : comparer son UX mobile à Robinhood ou ses charts à TradingView est partiellement hors-cible. Le bon comparateur est **Seeking Alpha / AlphaSense / un analyste junior buy-side** — et sur ce terrain, le verdict change (voir §5).

Cette honnêteté de cadrage est elle-même un signal de maturité : le projet **ne se survend pas** (disclaimers présents, « recherche éducative — pas un conseil financier »).

---

## 1. Qualité de l'analyse financière

### Forces
- **16 frameworks réellement implémentés** (`app/skills/tier2/*`, `app/orchestrator/router.py:13-67`), enchaînés en 5 workflows (`value_graham`, `compounder_buffett` 10 étapes, `fast_grower_lynch`, `special_situation`, `distressed_pabrai`).
- **5 cadres de qualité des bénéfices déterministes et auditables** (`app/services/financial_calculations.py`) : Altman Z (3 variantes, termes X1-X5), Beneish M (8 indices DSRI/GMI/AQI/SGI/DEPI/SGAI/TATA/LVGI), Piotroski F (9 critères booléens), Montier C (6 signaux), Sloan accruals — avec `sum(passe) == f_score` par construction. **C'est le point fort différenciant** : la plupart des outils retail n'offrent aucun de ces signaux anti-piège.
- **Valorisation par triangulation** (`app/services/valuation_calculations.py`) : DCF Gordon 2-temps + WACC (CMPC) + matrice de sensibilité 5×5, gate sectoriel excluant financières/REIT du DCF.
- **Fiscalité canadienne** (skill `canadian_tax`) : CELI/REER/CELIAPP/REEE, dividendes éligibles, gain en capital 50 %, retenue US 15 %, Norbert's Gambit, perte apparente — **niche défendable et rare** chez les concurrents US.

### Faiblesses critiques (vérifiées)
- **ROIC jamais extrait** — `app/skills/tier1/yahoo_finance.py:494` : `roic=None` en dur. Or ROIC > 15 % est le **cœur** des cadres Buffett, Dorsey (moat) et Damodaran. Sans lui, ces trois skills régressent vers du qualitatif LLM. *Angle mort majeur sur le ratio le plus important de la philosophie « quality ».*
- **Bêta figé à 1.0** — `app/services/valuation_calculations.py:17` : `_BETA_DEFAULT = 1.0`, jamais remplacé par le bêta yfinance. Impact CAPM → WACC → DCF : ±0,5 % de WACC ≈ ±10–30 % de valeur intrinsèque. Une small-cap volatile et une utility défensive obtiennent le **même** coût des fonds propres.
- **Hypothèses macro figées présentées comme des mesures** : taux sans risque, ERP (~4,23 %), taux d'imposition (26,5 % QC) sont des constantes, non recalculées sur les conditions courantes (hausse des taux 2024-2026 non répercutée). La sortie affiche pourtant une fourchette basse/centrale/haute comme une *vérité*.
- **Détection sectorielle naïve** — matching par mot-clé (`stock_valuation`) : « real » dans « RE/MAX » désactive à tort le DCF ; faux positifs/négatifs sectoriels non testés.
- **Banques/REITs : ratios spécialisés déclarés mais non calculés** (Tier 1/CET1, Texas Ratio, FFO, NAV) → l'analyse de ces secteurs **tombe à 100 % côté LLM** = risque d'hallucination maximal là où la rigueur compte le plus.
- **Owner earnings (Buffett) non calculé en Python** — champ d'entrée seulement ; la métrique-clé de Buffett reste LLM-dépendante.
- **Calibration des seuils non revalidée** : Beneish (1999, industrielles US), Piotroski (2003, N≈2300 US) appliqués au Canada 2026 sans backtest local.
- **Biais de survie implicite** : tous les seuils sont calibrés sur des sociétés cotées survivantes.

### Angles morts (confirmés absents)
- **Zéro analyse technique** (RSI/MACD/MM/momentum/volume) — assumé par design ; correct pour du value pur, disqualifiant pour tout *timing*.
- **Macro/top-down embryonnaire** : VIX, spreads de crédit, insider, sentiment existent comme **entrées optionnelles manuelles** (`marks_cycles`), jamais auto-récupérées. Pas de cycle PMI, pas d'inflation implicite, pas de FX.
- **Peers comparables non extraits automatiquement** — le skill réclame 4-6 pairs mais l'utilisateur/LLM les fournit.
- **Zéro donnée alternative moderne** : pas de short interest, options flow, transcripts d'earnings calls, sentiment réseaux sociaux auto, données satellites/cartes de crédit. C'est l'écart le plus net vs le « FinTech moderne » du brief.

---

## 2. Moteur IA & moteur d'analyse

### Forces (ingénierie anti-hallucination de premier ordre)
- **Tool-use forcé** (`app/skills/tier2/graham_analysis/skill.py:159-160`, `tool_choice={"type":"tool",...}`) : le modèle peuple un schéma Pydantic, **éliminant l'hallucination de format JSON**.
- **Température 0 centralisée** — `app/utils/retry.py:33` : `kwargs.setdefault("temperature", 0)`. Reproductibilité maximale.
- **Substitution déterministe post-parse** (`graham/skill.py:177-179`, `earnings_quality` `_injecter_scores`) : tous les chiffres sont recalculés en Python et écrasent la sortie LLM (« prime sur toute valeur LLM, Sprint 128 »). **Le LLM interprète, il ne calcule plus.**
- **Prompt caching** activé sur tous les system prompts (`cache_control: ephemeral`), retry exponentiel 429/529 (`app/utils/retry.py`), observabilité Langfuse optionnelle, coût USD persisté par appel (`app/utils/costs.py`).
- **RAG méthodologique** (Qdrant + embeddings `text-embedding-3-small`) injecté dans les prompts (`graham/skill.py:106-112`), dégradation propre si `OPENAI_API_KEY` absente.

### Faiblesses / risques
- **Le RAG ancre la *méthode*, pas les *faits*** : il récupère les principes de Graham, pas les états financiers réels de la société. Utile pour appliquer correctement le cadre ; **n'ajoute aucune vérification factuelle** sur l'entreprise analysée.
- **Narratives non fact-checkées** : `drapeaux_rouges`, `verdict_detail`, synthèses restent libres (T=0 mais non contraintes). Un skill peut affirmer un fait grave sans justification, persisté en base comme établi. Aucune règle « faillite ⇒ Z < 1,81 ».
- **Orchestration strictement séquentielle** (`app/orchestrator/core.py`) : `compounder_buffett` = 10 appels Claude en série ≈ **5 min/ticker**. Des skills indépendants (Graham/Lynch) pourraient paralléliser. *Latence = friction produit majeure.*
- **Source de données unique** : yfinance pour tout ; SEDAR+ (`app/skills/tier1/sedar_plus.py`) est un **placeholder non fonctionnel** (retourne `None`). Aucun fallback cross-provider → yfinance down = système aveugle. Données : prix retardé ~15 min, fondamentaux trimestriels.
- **Aucun circuit-breaker de budget** intra-workflow ; les retries 529 ajoutent un coût invisible.
- **Pas de fuzzing des entrées aberrantes** (P/E = −1000, total_assets = 0) — GIGO non testé.

---

## 3. UX / UI

### Forces
- Design system cohérent : **tokens HSL sémantiques** (bull/bear/neutral), shadcn/ui, **palette de commandes ⌘K**, skeletons/animations soignés, `RatiosSourceNote`/`RatiosProvenanceNote` (source + date + repli de clé yfinance affichés — **honnêteté des données rare et excellente**).
- **Streaming SSE skill-par-skill** (`StreamingProgress`) : feedback temps réel = perception de rapidité.
- Gestion `null` vs `0` honnête côté données (jamais de `0.0` trompeur).
- 74 fichiers de tests Vitest.

### Faiblesses critiques
- **Aucun onboarding ni landing** : l'utilisateur non authentifié atterrit sur le login, puis directement face à 18 frameworks. *Conversion débutant ≈ 0.*
- **Desktop-first, pas mobile-first** : grilles 2-cols serrées < 576 px, formulaire ~10 ratios, tables sans reflow. L'usage réel « checker une action en transit » est inconfortable. (Constat partiellement inféré — à valider sur device réel.)
- **Aucun graphique de prix / chandelier** : la brique de base de toute app d'investissement est absente — l'analyse fondamentale flotte sans ancre de cours.
- **Disclaimer en pied de page seulement, pas inline sur le verdict** (`frontend/src/constants/disclaimer.ts`) — exposition réglementaire (le verdict « ACHETER » s'affiche sans avertissement adjacent).
- **Surcharge cognitive** : 16 sections + **6 taxonomies de verdict incompatibles** (Graham `CANDIDAT_SOLIDE`, Buffett `COMPOUNDER`, Dorsey `WIDE/NARROW`, Lynch 6 catégories, ESG 3 niveaux…). Un débutant ne sait pas *quelle est la vraie recommandation*. Jargon (P/E, ROIC) sans tooltips.
- **Composite score caché** (visible surtout au Dashboard, pas en tête d'analyse) ; pas de mode « simple vs expert ».
- **Pas de bascule thème clair/sombre** ; accessibilité ~60 % (bon contraste, mais pas d'`aria-live` sur le streaming, navigation clavier des tables incomplète).

---

## 4. Architecture, sécurité & infra

### Forces
- **Auth de niveau production** : Argon2 (params OWASP), JWT HS256 avec secret *fail-fast*, blacklist JTI *fail-closed*, rotation des refresh tokens avec **détection de vol par famille**, rate-limit login 5/15 min. Sérieux et au-dessus de la moyenne des MVP.
- Séparation claire (24 routers, 38 services), lifespan propre, gestion d'erreurs avec `correlation_id`, **coûts/tokens persistés** par analyse, CI (pytest + Vitest + typecheck) verte, Caddy/ACME en prod, `.env.example` complet (47 lignes).
- Pyramide de tests réelle : ~132 fichiers backend + 74 frontend, dont e2e Playwright et evals Claude réelles (hors CI).

### Risques / vulnérabilités (vérifiés)
- **🔴 Pas d'isolation multi-utilisateur** : `analysis_history` et `watchlist` n'ont **aucune colonne `user_id`** (`infra/postgres/init.sql`), et l'endpoint d'analyse ne reçoit aucun `current_user`. Deux comptes **partagent une seule watchlist et un seul historique**. L'app a une *authentification* mais pas de *cloisonnement des données*. **Bloqueur SaaS/B2B absolu** (et risque de fuite de données entre utilisateurs si jamais déployé en multi-compte).
- **🔴 Bypass CSRF conditionnel** — `app/middleware/csrf.py:64-66` : si `API_KEY` est vide, CSRF est **entièrement désactivé**. Dangereux si la prod oublie la variable. Comparaison de token non *timing-safe* (`!=` ligne 77, devrait être `hmac.compare_digest`).
- **🟠 Fallback CORS localhost** si `CORS_ORIGINS` vide (`app/api/main.py:599-612`).
- **🟠 Pas de chiffrement at-rest** (PostgreSQL/Redis) ; risque de **secrets/données sensibles dans les logs** (`exc_info` complet, payloads Claude non assainis).
- **🟠 `python-jose`** (requirements) — quasi non maintenu depuis 2023 ; migrer vers `PyJWT`. **yfinance** = scraping fragile (rupture si Yahoo change son HTML).
- **🟠 SPOF & scalabilité** : Redis sans Sentinel, pool asyncpg `max_size=10` (+ pool Celery séparé), tâches Celery **sans `time_limit`** (risque zombie), invalidation cache via `KEYS` (O(N), bloque Redis à grande échelle).
- **🟡 Hygiène** : `requirements.txt` déclare `fastapi` et `uvicorn` **deux fois** avec des contraintes divergentes (lignes 2/4 et 3/5) ; `costs.py` connaît `opus-4-7` mais pas `opus-4-8` (sous-comptage silencieux si Opus utilisé). Référence morte dans ROADMAP vers `docs/revue-expert-fintech.md` (absent). Léger décalage doc/commits (ROADMAP annonce sprint 153 / v10.39.0, dernier commit titré = sprint148).

---

## 5. Analyse concurrentielle

| Capacité | TradingClaude | Standard FinTech moderne |
|---|---|---|
| Analyse fondamentale multi-cadres | ✅ **Supérieur** (16 cadres) | Seeking Alpha ~1-2 angles |
| Détection fraude/faillite déterministe | ✅ **Rare** (5 cadres) | Quasi-absent en retail |
| Fiscalité canadienne | ✅ **Différenciateur** | Wealthsimple basique |
| Traçabilité source/coût/déterminisme | ✅ **Institutionnel** | Opaque ailleurs |
| Données temps réel / charts prix | ❌ Absent | TradingView/IBKR natif |
| Analyse technique / timing | ❌ Absent | Standard |
| Données alternatives / sentiment | ❌ Absent | Bloomberg/AlphaSense |
| Mobile-first | ❌ Faible | Robinhood/Wealthsimple excellent |
| Multi-tenant / comptes clients | ❌ Absent | Pré-requis de tout SaaS |
| Couverture marchés | TSX/NYSE/NASDAQ actions | Global multi-actifs |

**Lecture** : ne pas opposer TradingClaude à Robinhood (catégories différentes). Son vrai pair est **l'assistant de recherche IA buy-side** (AlphaSense, BloombergGPT, analyste junior). Sur *ce* terrain, la **rigueur déterministe + multi-cadres + fiscalité CA** est un avantage réel ; les manques sont l'**ampleur des données** et l'**absence de plateforme** (multi-tenant, monétisation).

---

## 6. Crédibilité pour investisseurs

**Renforce la crédibilité (institutionnel)** : déterminisme auditable, source+date affichées, sous-composantes exposées (8 indices Beneish, 9 critères Piotroski), disclaimers présents, coûts tracés.

**Érode la crédibilité (amateur)** : ROIC manquant sur des cadres « quality », bêta 1.0 et hypothèses figées vendues comme une fourchette précise (**fausse précision** — l'écueil classique du DCF), 6 verdicts contradictoires sans recommandation unique, absence de contexte de prix, analyses bancaires 100 % LLM.

**Net** : crédible pour un **investisseur value averti** qui sait lire entre les lignes ; potentiellement **trompeur pour un débutant** (précision apparente > précision réelle).

---

## 7. Business & monétisation

- **Aucune infrastructure de monétisation** : zéro Stripe/billing/abonnement/paywall (les occurrences « pricing/premium » sont du vocabulaire de *moat analysis* ; `costs.py` = coûts API internes).
- **Mono-tenant** (cf. §4) : impossible d'onboarder des clients sans refonte du modèle de données (ajout `user_id` partout, RLS, quotas).
- **Brique B2B partielle** : `api_keys` (rôles admin/reader) existe, mais **sans metering ni facturation**.
- **Économie unitaire favorable** : prompt caching + Haiku sur skills mécaniques + cache Redis 24h → coût/analyse faible (centimes), bien tracé. C'est un atout si monétisé.

**Chemins réalistes** (par effort croissant) :
1. **Outil personnel** (état actuel) — parfaitement viable comme copilote privé.
2. **API/white-label B2B** pour conseillers/family offices québécois (la niche fiscale CA + déterminisme = argument de vente) — le plus court chemin vers un revenu.
3. **Génération de rapports** (PDF mensuel/ticker/screener déjà présents) en service d'abonnement — proche.
4. **SaaS multi-tenant retail** — le plus loin : exige multi-tenance, mobile, charts, onboarding, conformité.

**Douve potentielle** : le **moteur de frameworks déterministe** + le **corpus RAG** + la **niche fiscale canadienne**. Faible douve vs un incumbent bien financé qui copierait les cadres ; la défensabilité vient de l'intégration et de la spécialisation locale, pas de la techno seule.

---

## 8. Risques importants (consolidés)

| # | Risque | Gravité | Source |
|---|---|---|---|
| R1 | Pas d'isolation par utilisateur (fuite inter-comptes si multi-user) | 🔴 Élevée | `init.sql`, endpoints sans `user_id` |
| R2 | Bypass CSRF si `API_KEY` vide en prod | 🔴 Élevée | `csrf.py:64-66` |
| R3 | Source de données unique (yfinance scraping) | 🔴 Élevée | `yahoo_finance.py`, `sedar_plus.py` placeholder |
| R4 | Hallucination résiduelle sur champs narratifs | 🟠 Moyenne | skills (champs libres) |
| R5 | Fausse précision DCF (bêta/ERP/taux figés) | 🟠 Moyenne | `valuation_calculations.py:17` |
| R6 | Pas de chiffrement at-rest / secrets dans logs | 🟠 Moyenne | infra, `error_sanitization` |
| R7 | Exposition réglementaire (ligne « conseil ») mince, pas de KYC/suitability | 🟠 Moyenne | disclaimer footer-only |
| R8 | Dépendance `python-jose` non maintenue | 🟡 Faible | `requirements.txt` |
| R9 | SPOF Redis, Celery sans timeout, pool asyncpg=10 | 🟡 Faible | infra |

---

## 9. Fonctionnalités manquantes (priorisées)

**Indispensables pour devenir un produit** : isolation multi-utilisateur (`user_id` + RLS), graphique de prix (chandelier 1-5 ans), onboarding/landing, disclaimer inline sur le verdict, optimisation mobile.
**Indispensables pour la profondeur analytique** : extraction ROIC + bêta, ratios sectoriels banques/REITs en Python, recalcul macro (taux/ERP courants), extraction auto des peers.
**Différenciateurs modernes** : sentiment/insider/short auto, transcripts d'earnings calls, score composite en tête d'analyse, mode simple/expert.
**Business** : metering + facturation (Stripe), quotas par compte, fallback données (Refinitiv/Polygon/FMP).

---

## 10. Recommandations prioritaires

**P0 (avant tout usage multi-personne ou prod ouverte)**
1. Ajouter `user_id` à `analysis_history`/`watchlist` + filtrage par compte (sinon ne pas ouvrir le multi-compte).
2. Rendre CSRF *fail-closed* (ne jamais bypasser sur `API_KEY` vide hors dev explicite) + `hmac.compare_digest`.
3. CORS *fail-fast* en prod ; assainir les logs (pas de payloads/secrets).
4. Disclaimer inline sur chaque verdict.

**P1 (profondeur & fiabilité)**
5. Extraire ROIC et bêta ; recalculer ERP/taux ; tester le DCF sur entrées aberrantes.
6. Implémenter les ratios sectoriels banques/REITs en Python (sortir l'analyse financière du 100 % LLM).
7. Fallback de données cross-provider ; circuit-breaker de budget.
8. Migrer `python-jose` → `PyJWT` ; dédupliquer `requirements.txt` ; ajouter `opus-4-8` au pricing.

**P2 (produit & marché)**
9. Onboarding + graphique de prix + mobile + mode simple/expert + score composite en tête.
10. Paralléliser les skills indépendants (réduire la latence ~5 min).
11. Décider la stratégie business : API B2B / white-label conseiller vs SaaS retail.

---

## 11. Analyse stratégique

TradingClaude a investi son capital d'ingénierie au **bon endroit pour un actif technique** (déterminisme, auditabilité, frameworks, tests) et au **mauvais endroit pour un produit commercial** (pas de monétisation, mono-tenant, pas de mobile/charts/onboarding). C'est cohérent avec son identité réelle de **copilote personnel**, mais cela signifie qu'une bascule vers un produit exige un **travail de fondation** (multi-tenance, données, distribution), pas du polish.

La **thèse stratégique la plus crédible** n'est pas « concurrencer Wealthsimple », mais **« moteur de recherche fondamentale-as-a-service »** : exposer le déterminisme multi-cadres + la fiscalité canadienne à des **conseillers/family offices** via API ou white-label. C'est là que les forces existantes (rigueur, traçabilité, coûts maîtrisés, rapports PDF) deviennent un produit, et que les faiblesses (mobile, charts, onboarding retail) cessent d'être critiques.

---

## 12. Évaluation finale

**Comme actif technique / prototype de recherche** : **8/10** — sérieux, rare, bien construit.
**Comme produit FinTech investissable aujourd'hui** : **≈ 5,5/10** — moteur excellent, enveloppe produit/business absente.

> Verdict de consultant : *« Je n'investirais pas dans la société en l'état — il n'y a pas encore de produit ni de modèle d'affaires — mais je financerais volontiers l'équipe pour transformer ce moteur en API B2B de recherche fondamentale. La technologie de déterminisme et la niche fiscale canadienne sont une vraie base ; le risque est l'exécution produit (multi-tenance, données, distribution) et la banalisation par un incumbent. »*

### SWOT condensé
- **Forces** : déterminisme auditable, 16 cadres, fiscalité CA, auth forte, tests, coûts maîtrisés.
- **Faiblesses** : mono-tenant, ROIC/bêta/macro/secteur, source unique, mobile, onboarding.
- **Opportunités** : B2B/white-label conseillers, rapports en abonnement, niche canadienne.
- **Menaces** : banalisation par incumbents IA, fragilité yfinance, exposition réglementaire, dette de scalabilité.

---

*Toutes les affirmations à fort enjeu (ROIC, bêta, multi-tenance, bypass CSRF, CORS) ont été vérifiées par lecture directe du code. Les constats UX mobile partiellement inférés sont signalés comme tels.*
