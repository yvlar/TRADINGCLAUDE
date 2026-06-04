# Audit institutionnel & plan de transformation — TradingClaude

> Document de cadrage architectural (committee CTO/Quant/Risk/PM CFA).
> Objectif : faire passer la plateforme d'un niveau « retail avancé » à un niveau
> « professionnel / institutionnel » en attaquant la qualité des décisions, la mesure
> du risque et la robustesse des données — **pas** la cosmétique.
>
> État de référence : Sprint 145, version 10.30.0. Toutes les affirmations sur
> l'existant sont référencées en `fichier:ligne` (cf. `workflow-sprint.md`,
> anti-hallucination). Ce document **ne modifie aucun code** : c'est une feuille de route.

---

## 0. Correction préalable de l'audit — ce qui est faux dans le diagnostic reçu

Avant de planifier, il faut corriger trois prémisses de l'audit, sans quoi on
reconstruirait des choses déjà présentes et on raterait les vraies lacunes.

| Affirmation de l'audit | Réalité dans le code | Verdict |
|---|---|---|
| « score composite largement basé sur des verdicts LLM » | Le score composite **est 100 % déterministe en Python** : `compute_composite_score()` (`app/services/composite_score.py:86-145`), pondérations fixes (`:8-15`), seuils FORT/MODÉRÉ/FAIBLE (`:132-137`). | **Partiellement faux** |
| « Beneish/Altman/Piotroski/Montier = acquis fiables » | Vrai : déterministes en Python (`app/services/financial_calculations.py:215-792`), réinjectés après le LLM (`earnings_quality/skill.py`). | **Vrai** |
| « DCF présent » | Vrai et déterministe (`app/services/valuation_calculations.py:74-149`), mais **`beta` figé à `1.0`** (`valuation_calculations.py:17`) → le coût des capitaux propres CAPM est faux pour tout titre non-marché. | **Vrai mais biaisé** |

**Le vrai problème** n'est donc pas « le LLM attribue le score final ». C'est que **4 des 6
entrées** du score composite sont des **verdicts catégoriels produits par le LLM** :

| Entrée composite | Poids | Origine de la valeur | Déterministe ? |
|---|---|---|---|
| `graham` | 20 % | verdict défensif = seuil Python sur `defensive_score` | ✅ Oui |
| `buffett` | 20 % | verdict COMPOUNDER/QUALITÉ/… = **LLM** | ❌ Non |
| `stock_valuation` | 20 % | verdict SOUS/JUSTE/SUR = **LLM** (mais DCF Python sous-jacent) | ⚠️ Mixte |
| `dorsey_moat` | 15 % | `moat_type` WIDE/NARROW/NONE = **LLM** | ❌ Non |
| `earnings_quality` | 15 % | verdict = **LLM** (mais M/Z/F/C/Sloan Python sous-jacents) | ⚠️ Mixte |
| `marks_cycles` | 10 % | signal ACHETER/ATTENDRE = **LLM**, `confidence` figée à `1.0` (`composite_score.py:98`) | ❌ Non |

Référence du câblage : `app/orchestrator/core.py:1031-1048`.

**Conséquence stratégique** : la mission « rendre les décisions déterministes » se
réduit à **remplacer ces 4-5 verdicts LLM par des sous-scores quantitatifs calculés
en Python**, là où la donnée existe, et à laisser le LLM **expliquer** ces scores.
C'est moins de travail que ce que l'audit suggère, et plus ciblé.

---

## 1. PHASE 1 — Audit d'architecture

### 1.1 Architecture actuelle (vérifiée)

```
                    ┌─────────────────────────────────────────────┐
                    │  Frontend React 18 (14 pages)               │
                    │  Analyze · Screener · Watchlist · Dashboard │
                    │  Compare · ESG · Search · Alerts · Admin    │
                    └───────────────────┬─────────────────────────┘
                                        │ fetch + CSRF (api/client.ts)
                    ┌───────────────────▼─────────────────────────┐
                    │  FastAPI — ~23 routers (api/main.py:571-593) │
                    │  /analyze /screen /watchlist /backtest       │
                    │  /performance /compare /telemetry …          │
                    └───────────────────┬─────────────────────────┘
                                        │
              ┌─────────────────────────┼───────────────────────────┐
              ▼                         ▼                            ▼
   ┌──────────────────┐   ┌────────────────────────┐   ┌──────────────────────┐
   │ Orchestrator     │   │ Services (33 fichiers)  │   │ tier1 extracteurs    │
   │ core.py/router.py│   │ composite_score         │   │ yahoo_finance.py     │
   │ 5 workflows      │   │ financial_calculations  │   │ (yfinance, SPOF)     │
   │ 16 skills tier2  │   │ valuation_calculations  │   │ sedar_plus.py (no-op)│
   │ (séquencés)      │   │ backtest · screener …   │   └──────────────────────┘
   └────────┬─────────┘   └───────────┬─────────────┘
            │                         │
            ▼                         ▼
   ┌──────────────────┐   ┌────────────────────────────────────────┐
   │ Anthropic SDK    │   │ PostgreSQL 16 · Redis 7 · Qdrant (RAG)  │
   │ (Claude Sonnet)  │   │ 11 tables (aucune série de prix)        │
   └──────────────────┘   └────────────────────────────────────────┘
            ▲
   ┌────────┴─────────┐
   │ Celery worker    │  9 tâches planifiées (workers/tasks.py)
   └──────────────────┘
```

**Tables PostgreSQL existantes** (`infra/postgres/init.sql` + migrations) :
`analysis_history`, `watchlist`, `composite_score_history`, `esg_score_history`,
`api_keys`, `alert_history`, `user_preferences`, `annotations`, `users`,
`refresh_tokens`. **Aucune** table de prix, de positions/portefeuille, de rendements,
de matrice de corrélation, ni de métriques de risque.

### 1.2 Points d'extension réutilisables (à ne PAS réinventer)

| Brique existante | Fichier:ligne | Réutilisable pour |
|---|---|---|
| Calculs déterministes purs (CPU, `None`-safe) | `financial_calculations.py`, `valuation_calculations.py` | héberger `ValueScore`, `QualityScore`, `RiskScore` au même endroit, même style |
| Substitution post-LLM (calc Python écrase la sortie LLM) | `earnings_quality/skill.py`, `stock_valuation/skill.py` | patron exact pour « LLM explique, Python décide » |
| Composite pondéré + confidence | `composite_score.py:86-145` | étendre avec de nouveaux sous-scores plutôt que réécrire |
| Backtest rétrospectif par bucket | `app/services/backtest.py`, `app/api/endpoints/backtest.py` | base à durcir (walk-forward, coûts) |
| Snapshots horodatés | `composite_score_history`, `esg_score_history` | patron pour `prediction_tracking` |
| Tâches planifiées asyncpg | `app/workers/tasks.py` (9 tâches) | ingestion prix quotidienne, calcul perf |

### 1.3 Écart (architecture cible − existant)

| Capacité | Existant | Cible institutionnelle | Écart |
|---|---|---|---|
| Scoring déterministe final | ✅ composite Python | idem + sous-scores factoriels | **Faible** |
| Sous-verdicts (Buffett, moat, Marks) | ❌ LLM | déterministes où donnée dispo | **Moyen** |
| Quality engine (ROIC, FCF conv…) | ⚠️ partiel via LLM | déterministe 0-100 | **Moyen** |
| Momentum | ❌ absent | 3/6/12 m + RS | **Élevé** (besoin série de prix) |
| Factor investing (z-score, percentile) | ❌ absent | 5 facteurs normalisés | **Élevé** (besoin univers) |
| Portfolio engine (corr., concentration) | ❌ absent | risque portefeuille | **Élevé** (besoin positions + prix) |
| Risk engine (Sharpe, VaR, β réel, drawdown) | ⚠️ drawdown ad hoc, β=1.0 | suite complète | **Élevé** |
| Performance tracking (prédictions) | ⚠️ snapshots score, pas de prédiction figée | table prédictions + hit rate | **Moyen** |
| Moat semi-déterministe | ❌ narratif LLM | 6 catégories scorées | **Moyen** |
| Multi-provider données | ❌ Yahoo SPOF | 3-4 sources + DataQualityScore | **Élevé** |
| Backtest institutionnel | ⚠️ bucket rétrospectif | walk-forward, coûts, biais | **Élevé** |

### 1.4 Risques de régression identifiés

1. **`numpy`/`scipy`/`pandas`(stats) absents** de `requirements.txt` — seul `pandas` de base est là (via `yfinance`). Tout calcul vectoriel (corrélation, VaR, z-score) impose d'ajouter `numpy` (+ `scipy` pour VaR paramétrique). Décision d'architecture à acter Quick Win 0.
2. **Le composite a des poids fixes** (`composite_score.py:8-15`). Ajouter Quality/Momentum/Risk **change la note de tous les titres historisés** → besoin d'un versionnage du score (`score_version`) pour ne pas casser `composite_score_history` et le backtest.
3. **`marks_confidence` figée à 1.0** : tout titre reçoit le poids Marks plein même quand le signal est faible — biais existant à corriger en même temps.
4. **Async strict** (`conventions-code-base.md`) : l'ingestion de prix et les appels multi-provider doivent rester `async` (httpx), jamais `requests`/`time.sleep`.
5. **Banques/REIT** : DCF déjà neutralisé pour le secteur financier (`stock_valuation/skill.py`). Les nouveaux moteurs (Quality via FCF, momentum) doivent répliquer cette discipline sectorielle ou produire `None`.

### 1.5 Plan de migration (vue macro)

Stratégie **strangler** : on n'arrache rien. On ajoute des sous-scores déterministes
à côté du composite existant, derrière un `score_version`, et on bascule le poids des
verdicts LLM vers les sous-scores quantitatifs progressivement. Le LLM passe en mode
« explicateur » sans perdre une fonctionnalité d'un coup. Détail en Phase 12.

---

## 2. PHASE 2 — Moteur de scoring déterministe

**Principe directeur** : le LLM ne **note** plus. Il **explique** une note calculée en
Python. On formalise cinq sous-scores, tous dans un nouveau module
`app/services/factor_scores.py` (même style pur/`None`-safe que `financial_calculations.py`).

| Sous-score | Intrants (déjà extraits ?) | Source |
|---|---|---|
| `ValueScore` | P/E, P/B, FCF yield, EV/EBITDA, Graham number | extraits en valorisation (`yahoo_finance.py` extract_valuation) |
| `QualityScore` | ROIC, ROE, marges, FCF conversion, dette/FCF, couverture intérêts | partiellement extraits — voir Phase 3 |
| `GrowthScore` | croissance EPS/revenus, durée | `eps_growth_total`/`eps_growth_years` (cf. `variables-financieres.md`) |
| `MomentumScore` | rendements 3/6/12 m, RS | **à produire** — Phase 4 (besoin série de prix) |
| `RiskScore` | volatilité, β réel, drawdown, Sharpe | **à produire** — Phase 7 |

Chaque sous-score :
- est une fonction pure `def compute_xxx_score(...) -> SubScore | None` (retourne `None` si données insuffisantes, jamais d'exception) ;
- renvoie `{score: float 0-100, components: dict, data_completeness: float}` ;
- est **testé unitairement** avec valeurs connues (golden) avant tout câblage ;
- est **documenté** : formule + seuils recopiés depuis un `references/*.md` (jamais inventés — cf. `valuation_calculations.py:8-9`).

**Refonte du composite** : `compute_composite_score()` accepte les sous-scores numériques
en plus (ou à la place) des verdicts LLM, derrière `score_version=2`. Le LLM cesse de
fournir `verdict` pour earnings/valuation/moat/buffett/marks ; il fournit `explication`,
`risques`, `points_forts`, `points_faibles` — champs déjà naturels dans les schemas.

**Contrat LLM cible** (par skill) :
> « Voici le score X (calculé). Explique en 3-5 points **pourquoi** il est élevé/faible et
> liste les risques que le chiffre ne capture pas. Tu ne produis aucune note numérique. »

---

## 3. PHASE 3 — Moteur Quality Investing

Cadre Buffett / Terry Smith / *quality investing*. Tout déterministe.

| Métrique | Formule | Disponibilité données |
|---|---|---|
| ROIC | NOPAT / (capitaux investis) | dérivable du bilan + résultat (déjà extrait pour Z/M-Score) |
| ROE | résultat net / capitaux propres | extrait (`extract_valuation`) |
| Gross / Operating / FCF margin | marges sur revenus | revenus, COGS, FCF extraits (earnings + valuation) |
| FCF conversion | FCF / résultat net | extraits |
| Dette / FCF | dette totale / FCF | extraits |
| Couverture des intérêts | EBIT / charges d'intérêts | **EBIT/intérêts pas tous extraits** → à ajouter au tier1 |
| Capital Allocation Score | rachats + dividendes vs dilution + ROIC tendance | partiellement dérivable, sinon proxy |

→ `QualityScore(0-100)` + label **Excellent / Bon / Moyen / Faible** (seuils dans
`references/quality.md` à créer). Le skill `buffett_quality` garde sa prose (4 filtres,
owner earnings) mais **ne produit plus le verdict** : le verdict devient le label du
QualityScore.

**Pré-requis tier1** : enrichir `yahoo_finance.py` pour exposer EBIT, charges d'intérêts,
rachats d'actions, capitaux investis. C'est le chemin critique de cette phase.

---

## 4. PHASE 4 — Moteur Momentum

**Bloquant** : il n'existe **aucune série de prix** stockée (prix récupérés à la volée,
`backtest.py:33-96`). Le momentum impose d'introduire la persistance de prix.

| Sortie | Définition |
|---|---|
| Momentum 3/6/12 m | rendement total sur fenêtre (ex-dividende ou total return) |
| Relative Strength | rendement titre − rendement indice de référence |
| Distance du plus-haut 52 sem. | (prix − max 52s) / max 52s |
| Force relative secteur | rendement titre − rendement panier sectoriel |
| Force relative indice | vs XIU.TO (TSX) / SPY (US) selon suffixe `.TO` |

→ `MomentumScore(0-100)`, **zéro jugement LLM**. C'est un pur calcul sur série.

**Pré-requis** (Phase 10/infra) : table `price_history` (OHLCV quotidien) + tâche Celery
d'ingestion quotidienne (réutilise le patron `workers/tasks.py`). Sans elle, le momentum
recalcule tout à chaque requête (lent, fragile, rate-limited par Yahoo).

---

## 5. PHASE 5 — Factor Investing

Cinq facteurs : **Value, Quality, Momentum, Low Volatility, Size**.

Méthodologie standard (cross-sectionnelle sur un **univers**) :
1. calculer la métrique brute par titre ;
2. **z-score** dans l'univers (`(x − μ) / σ`) — winsorisé aux extrêmes ;
3. **percentile ranking** (0-100) pour lisibilité ;
4. pondération **configurable** (table `factor_weights` ou `user_preferences`).

→ `FactorScore` par titre + identification des **facteurs dominants** (les 1-2 z-scores
les plus élevés). Réutilise directement Value/Quality/Momentum des phases 2-4 ;
ajoute Low-Vol (écart-type des rendements) et Size (log market cap, déjà extrait).

**Pré-requis structurel** : un **univers de référence** (l'ensemble des tickers de la
watchlist + screener suffit pour démarrer). Les z-scores n'ont de sens que relatifs à
une population — à documenter clairement (univers restreint = biais connu).

---

## 6. PHASE 6 — Portfolio Engine

**Pré-requis** : aucune notion de **position** n'existe (la watchlist est observationnelle,
pas pondérée — `infra/postgres/init.sql:25-39`). Il faut une table `portfolio` /
`positions` (ticker, quantité, PRU, compte CELI/REER/…). Le tier `comptes-canadiens`
existe déjà côté skill — on s'y branche.

Fonctions (toutes sur série de prix → dépend de Phase 4/10) :
- matrice de **corrélation** et **covariance** des rendements ;
- **diversification** (nombre effectif de positions, ratio de diversification) ;
- **concentration** (Herfindahl, poids max position) ;
- expositions **sectorielle / géographique / devise / taux** (devise via suffixe + secteur via tier1).

→ `PortfolioRiskScore` + garde-fous configurables : concentration max, limites
sectorielles, limite par position. Ces garde-fous deviennent des **alertes** (réutilise
`alert_history` + `webhook_service`).

---

## 7. PHASE 7 — Risk Engine

| Métrique | Méthode | Note |
|---|---|---|
| Volatilité | écart-type annualisé des rendements quotidiens | série requise |
| **Beta (réel)** | régression rendements titre vs indice | **corrige le `1.0` figé** (`valuation_calculations.py:17`) → améliore aussi le DCF existant |
| Sharpe | (R − Rf) / σ | Rf déjà paramétré (`_RF_DEFAULT`) |
| Sortino | (R − Rf) / σ_downside | |
| VaR 95 / 99 | historique + paramétrique (normale) | `scipy.stats` |
| Expected Shortfall | moyenne des pertes au-delà du VaR | |
| Max Drawdown | pic-à-creux | logique déjà présente `backtest.py:72-95` à factoriser |

→ `RiskScore(0-100)` (note inversée : moins de risque = score haut).

**Stress tests / scénarios** (récession, inflation, krach) : appliquer des chocs
paramétriques (β × choc marché, sensibilité taux) sur le portefeuille. Le LLM peut
**narrer** le scénario ; les chiffres sont calculés. Le `beta` réel calculé ici doit
**réalimenter le CAPM** de `valuation_calculations.py` (boucle vertueuse, supprime le biais §0).

---

## 8. PHASE 8 — Performance Tracking

L'existant historise des **scores** (`composite_score_history`) mais ne fige pas une
**prédiction datée** réconciliable au prix. `analysis_history.price_at_analysis` existe
(`init.sql`) mais n'est pas exploité comme prédiction suivie.

**Nouvelle table `prediction_tracking`** :
```
prediction_id, ticker, workflow, prediction_date,
price_initial, composite_score, label, score_version
```
Calcul **automatique** (tâche Celery) des rendements **3/6/12/24 m** vs `price_initial`
(via `price_history`).

**Tableau de bord agrégé** (nouvel endpoint `/performance/scorecard`) :
**Hit Rate** (% de FORT en hausse), **rendement moyen/médian par bucket**, **Sharpe des
signaux**, **max drawdown**. C'est la **preuve empirique** que les scores prédisent —
le chaînon manquant n°1 pour la crédibilité institutionnelle.

---

## 9. PHASE 9 — Moat Analyzer (semi-déterministe)

Transformer le moat narratif (`dorsey_moat`, LLM pur aujourd'hui) en moat scoré.

| Catégorie | Proxy quantitatif partiel |
|---|---|
| Network effect | croissance utilisateurs/revenus + marge en expansion |
| Switching cost | rétention/récurrence revenus, marge brute stable |
| Brand | premium de prix (marge brute vs pairs), durabilité ROIC |
| Cost advantage | marge opér. supérieure persistante vs secteur |
| Scale advantage | ROIC vs taille, levier opérationnel |
| Regulatory | qualitatif (licences) — reste LLM, pondéré bas |

→ `MoatScore` = mélange de proxies déterministes (ROIC durable, stabilité de marge —
données déjà extraites) + justification **LLM en complément** (et non en source). Le
`moat_type` WIDE/NARROW/NONE devient un seuil sur `MoatScore`, ce qui **déterminise la
3ᵉ entrée LLM** du composite (§0).

---

## 10. PHASE 10 — Multi-Data Provider

Supprimer le SPOF Yahoo (`yahoo_finance.py`, seul fournisseur ; `sedar_plus.py` est un
no-op qui retourne `None`).

**Architecture cible** : interface `MarketDataProvider` (Protocol) + implémentations :
1. **Yahoo Finance** (existant) ;
2. **SEC EDGAR** (fondamentaux US, gratuit, fiable, API officielle) ;
3. **Financial Modeling Prep** (fondamentaux normalisés, clé API) ;
4. **Alpha Vantage** (fallback prix, clé API).

Orchestrateur de données :
- ordre de préférence configurable, **fallback** automatique en cas d'échec/`None` ;
- **réconciliation** : si ≥ 2 sources, comparer les champs clés ;
- → **`DataQualityScore`** détectant **incohérences** (écart > seuil entre sources),
  **divergences**, **données manquantes**. Ce score conditionne la confiance des autres
  scores (un QualityScore sur données douteuses doit être dégradé).

**Sécurité** : toute nouvelle clé (FMP, Alpha Vantage) va dans `.env` + `.env.example`
avec valeur factice (cf. `securite.md`). Tout reste `async` (httpx).

---

## 11. PHASE 11 — Backtest institutionnel

Le backtest actuel (`app/services/backtest.py`) est **rétrospectif par bucket** vs
benchmark, sans coûts ni contrôle de biais. Cible :

| Brique | Détail |
|---|---|
| **Walk-forward validation** | fenêtres glissantes train/test, jamais de fuite future |
| **Out-of-sample** | hold-out strict |
| **Transaction costs / slippage** | coûts par transaction + glissement paramétré |
| **Survivorship bias control** | inclure les titres délistés (univers point-in-time) |
| **Look-ahead bias control** | n'utiliser que la donnée connue à la date de décision (`prediction_date`) |

→ Sorties : **Alpha, Beta, Sharpe, Information Ratio, Hit Rate**. Dépend de
`price_history` (Phase 10/infra) et de `prediction_tracking` (Phase 8).

---

## 12. PHASE 12 — Plan d'exécution

### 12.1 Tables PostgreSQL nouvelles

| Table | Rôle | Phase |
|---|---|---|
| `price_history` (ticker, date, OHLCV, source) | série de prix → momentum/risk/backtest | 4,7,11 |
| `prediction_tracking` | prédictions datées réconciliables | 8 |
| `portfolio` / `positions` | positions pondérées par compte | 6 |
| `factor_weights` | pondérations factorielles configurables | 5 |
| `data_quality_log` | divergences inter-sources | 10 |

`analysis_history` et `composite_score_history` gagnent une colonne `score_version`
(migration additive, non destructive).

### 12.2 Endpoints API nouveaux

`/scores/factor/{ticker}`, `/momentum/{ticker}`, `/risk/{ticker}`, `/portfolio` (CRUD +
`/portfolio/risk`), `/performance/scorecard`, `/backtest/walk-forward`,
`/data-quality/{ticker}`.

### 12.3 Modifications frontend

Pages nouvelles : **Portfolio** (positions, expositions, concentration), **Risk**
(VaR/Sharpe/drawdown/β), **Factors** (radar 5 facteurs), **Scorecard** (hit rate,
rendements par bucket). Étendre `Dashboard` avec la scorecard. Types `index.ts` :
`FactorScore`, `RiskMetrics`, `Portfolio`, `MomentumScore` (zéro `any`).

### 12.4 Tests requis

- **Unitaires Python** : chaque sous-score (Value/Quality/Momentum/Risk/Factor/Moat) avec
  golden values ; provider fallback ; DataQualityScore sur divergences forgées.
- **Intégration** : `/analyze` v2 (composite déterministe), portfolio risk, walk-forward.
- **Evals** : re-calibrer le drift après bascule LLM→déterministe (cf. `Sprint 149` suggéré).
- Patron `call_claude_with_retry` patché (cf. `tests-pyramide.md`).

---

### 12.5 Roadmap priorisée (par ROI sur la qualité de décision)

> **Critère de priorisation** : impact sur la qualité de décision × réduction de risque ÷ effort.

#### 🟢 Quick Wins (1 sprint chacun, fondations à fort levier)

| # | Action | Pourquoi maintenant | Effort | ROI |
|---|---|---|---|---|
| QW0 | Ajouter `numpy` (+`scipy`) à `requirements.txt` | débloque corrélation/VaR/z-score de toutes les phases quant | Faible | Prérequis |
| QW1 | **Beta réel** (régression vs indice) → corrige CAPM/DCF + alimente RiskScore | supprime un biais de valorisation **déjà en prod** (`valuation_calculations.py:17`) | Faible | **Élevé** |
| QW2 | `score_version` sur composite + tables | permet d'évoluer le score sans casser l'historique/backtest | Faible | Prérequis |
| QW3 | Corriger `marks_confidence` figée à `1.0` | pondération erronée actuelle du composite | Faible | Moyen |

#### Sprint 1 — Persistance des prix + Momentum (débloque tout le quant)

- Table `price_history` + tâche Celery d'ingestion quotidienne.
- `MomentumScore` (3/6/12 m, RS, distance 52s) — 100 % déterministe.
- **Dépendances** : QW0. **Risque** : rate-limit Yahoo → batcher + cache.
- **ROI** : élevé — premier facteur quantitatif vérifiable, prérequis de Risk/Backtest.

#### Sprint 2 — Quality engine + déterminisation du composite

- `QualityScore` (ROIC, marges, FCF conversion, dette/FCF, couverture intérêts) ; enrichir tier1 (EBIT, intérêts).
- Composite `v2` : Buffett/earnings/valuation/moat → sous-scores déterministes ; LLM passe en explicateur.
- **Dépendances** : QW1, QW2. **Risque** : changement de note → versionné, A/B sur historique.
- **ROI** : très élevé — c'est le cœur de la mission « décisions déterministes ».

#### Sprint 3 — Risk engine + Performance tracking

- `RiskScore` (vol, Sharpe, Sortino, VaR 95/99, ES, drawdown, β) ; stress tests paramétriques.
- `prediction_tracking` + `/performance/scorecard` (hit rate, rendements par bucket).
- **Dépendances** : Sprint 1 (prix). **ROI** : élevé — preuve empirique + risque mesuré.

#### Sprint 4 — Multi-provider + Factor + Portfolio + Backtest institutionnel

- Interface `MarketDataProvider` + EDGAR/FMP/Alpha Vantage + `DataQualityScore` (tue le SPOF).
- `FactorScore` (5 facteurs z-scorés), `portfolio`/`PortfolioRiskScore`, backtest walk-forward.
- **Dépendances** : Sprints 1-3. **ROI** : élevé — robustesse + vue portefeuille institutionnelle.

### 12.6 Risques & dépendances (synthèse)

| Risque | Mitigation |
|---|---|
| Changement de note casse l'historique/backtest | `score_version` (QW2), recalcul historisé, bascule A/B |
| Rate-limit / SPOF Yahoo pendant l'ingestion prix | batch + cache + multi-provider (Sprint 4) |
| z-scores sur univers trop petit (biais) | documenter l'univers, élargir via screener, winsoriser |
| Données fondamentales manquantes (banques/REIT) | discipline `None`/sectorielle déjà en place à répliquer |
| Dérive evals après LLM→déterministe | re-calibrer golden datasets (Sprint 2/3) |

### 12.7 Effort & séquencement

```
QW0-QW3 (1 sprint groupé) → S1 Prix+Momentum → S2 Quality+Composite v2
                                                   → S3 Risk+Perf tracking
                                                        → S4 Multi-provider+Factor+Portfolio+Backtest
```

Chaîne critique : **persistance des prix (S1)** débloque momentum, risk, backtest. À
faire tôt. Le déterminisme du composite (S2) est le livrable à plus fort ROI sur la
mission ; il ne dépend que des Quick Wins, pas des prix — **parallélisable avec S1**.

---

## Annexe — Index des preuves (fichier:ligne)

- Composite déterministe : `app/services/composite_score.py:8-15, 86-145`
- Câblage composite : `app/orchestrator/core.py:1031-1048`
- Scores fraude/faillite déterministes : `app/services/financial_calculations.py:215-792`
- DCF/WACC + beta figé : `app/services/valuation_calculations.py:17, 30-149`
- Extracteur unique (SPOF) : `app/skills/tier1/yahoo_finance.py` ; `sedar_plus.py` (no-op)
- Backtest rétrospectif : `app/services/backtest.py:33-96` ; `app/api/endpoints/backtest.py`
- Schéma DB (aucune série de prix/position) : `infra/postgres/init.sql:4-120`
- Tâches planifiées : `app/workers/tasks.py` (9 tâches)
- Dépendances (numpy/scipy absents) : `requirements.txt`
</content>
</invoke>
