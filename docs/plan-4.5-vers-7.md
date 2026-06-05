# Plan produit — passer la note « investissable » de 4,5 à 7+

*Cible de positionnement : moteur d'analyse fondamentale B2B / API (pas grand public).*
*Réconcilié avec `docs/audit-institutionnel-2026.md` — mêmes briques, priorisation orientée note produit.*

---

## Principe directeur

Le 4,5 mesure la distance à un produit finançable. Trois leviers le déplacent :

| Levier | Gain note | Sprint |
|---|---|---|
| **Preuve empirique** (scorecard / hit rate) | **+1,5 à +2** | C |
| **Données fiables** (multi-source, DataQualityScore) | +0,5 à +1 | D |
| **Composite honnête + risque/qualité déterministes** | +0,5 à +1 | A, E |
| **Modèle économique** (API meterée B2B) | +1 | F |

Méthode : **strangler** (on ajoute à côté, on n'arrache rien), tout derrière un `score_version` pour ne pas casser l'historique ni le backtest. Chaque sprint = sa branche `claude/sprintNN-<nom>` → PR vers `dev`. Async strict, Pydantic v2, bilingue FR/EN, toute nouvelle clé dans `.env.example`.

**Chemin critique** : Sprint B (persistance des prix) débloque C, E, et le backtest. À faire tôt. La preuve (C) est le livrable à plus fort ROI sur la note.

```
A (honnêteté+durcissement) ─┐
                            ├─► B (prix) ─► C (scorecard★) ─► E (risk+quality, composite v2)
                            │                     │
                            └─────────────────────┴─► D (multi-source) ─► F (modèle B2B/API)
                                                                          (G portefeuille, optionnel)
```

---

## Sprint A — Honnêteté & durcissement (P0)

**Objectif** : retirer ce qui ferait perdre confiance un investisseur en due diligence, et corriger les biais déjà en prod.

**Livrables**
- **Composite honnête** (`composite_score.py:110-130`) : ajouter `data_completeness` (part du poids théorique réellement renseigné) au `CompositeScore` ; **plafonner/dégrader le label** quand `data_completeness < seuil` (ex. < 0,6 → label au mieux « MODÉRÉ », mention « données partielles »). Corrige **FC1**.
- **β réel** : nouvelle fonction `compute_beta(returns_titre, returns_indice)` (régression) ; alimente le CAPM de `valuation_calculations.py:17` (remplace le `1.0` figé) et le futur RiskScore. Corrige **FC5**. *(Nécessite quelques prix → version simple : fenêtre courte via yfinance en attendant la table du Sprint B.)*
- **`marks_confidence`** dérivée du signal au lieu de figée à `1.0` (`composite_score.py:98`). Corrige **FC2 (partiel)**.
- **Sécurité** : rate-limit **fail-closed** + lecture `X-Forwarded-For` (`rate_limit.py:43-46`) ; **authentifier `/report`** (`middleware/auth.py:43`) ; pool Redis partagé (supprimer le 2ᵉ pool `rate_limit.py:28`). Corrige **R2, R3, A3**.
- **Pool Celery** : remplacer `asyncio.run()` par tâche par une boucle/event-loop persistante + pool asyncpg réutilisé (`workers/tasks.py:61-73`). Corrige **A1**.
- **Hygiène** : dédupliquer `requirements.txt` (`fastapi`/`uvicorn`), ajouter `numpy` + `scipy` (débloque le quant). Corrige **A7**.

**Tests** : unitaires golden sur `data_completeness` et `compute_beta` ; intégration rate-limit fail-closed ; test auth 401 sur `/report`.
**Effort** : Faible-Moyen · **Dépendances** : aucune · **Effet note** : +0,3 (lève l'objection « le score peut mentir »).

---

## Sprint B — Persistance des prix (chemin critique)

**Objectif** : introduire la série de prix, socle de tout le quant moderne (aujourd'hui inexistante — `backtest.py:33-96` récupère les prix à la volée).

**Livrables**
- **Table `price_history`** (`ticker, date, open, high, low, close, adj_close, volume, source`), migration additive `infra/postgres/migrations/`.
- **Tâche Celery d'ingestion quotidienne** (réutilise le patron `workers/tasks.py`) : OHLCV des tickers watchlist + screener, batchée + cachée (anti rate-limit Yahoo). Backfill initial 5 ans.
- **Service `price_history_service`** : lecture async, calcul de rendements, `None`-safe.
- Refactor `backtest.py` pour lire la table au lieu de yfinance live.

**Tests** : unitaires ingestion (mock provider), intégration tâche Celery, idempotence du backfill.
**Effort** : Moyen · **Dépendances** : A (numpy) · **Risque** : rate-limit Yahoo → batch + cache + retry. **Effet note** : indirect (débloque C et E).

---

## Sprint C — Prediction tracking + Scorecard ★ (LE levier)

**Objectif** : prouver empiriquement que les scores prédisent. C'est **l'argument de vente n°1** et le plus gros gain de note.

**Livrables**
- **Table `prediction_tracking`** : `prediction_id, ticker, workflow, prediction_date, price_initial, composite_score, label, score_version`. Figée **au moment de l'analyse** (le champ `analysis_history.price_at_analysis` existe déjà mais n'est pas exploité comme prédiction suivie).
- **Tâche Celery** : calcule les rendements **3/6/12/24 m** vs `price_initial` (via `price_history`), réconciliation automatique.
- **Endpoint `GET /performance/scorecard`** : **Hit Rate** (% de FORT en hausse), **rendement moyen/médian par bucket** (FORT/MODÉRÉ/FAIBLE), **Sharpe des signaux**, **max drawdown**, échantillon (n).
- **Frontend** : page **Scorecard** (`frontend/src/pages/`) — tableau hit rate + courbe de rendement par bucket (recharts), badge « basé sur N prédictions sur M mois ». Type `ScorecardMetrics` dans `index.ts` (zéro `any`).

**Tests** : unitaires calcul de rendement/hit rate sur séries forgées ; intégration endpoint ; Vitest page.
**Effort** : Moyen · **Dépendances** : B · **Effet note** : **+1,5 à +2**. *Sans ce sprint, aucune affirmation de qualité décisionnelle n'est vérifiable.*

> **Re-priorisation vs l'audit** : l'audit place le perf-tracking en S3. Pour la note *produit*, je le remonte juste après les prix — c'est la preuve qu'un investisseur exige en premier.

---

## Sprint D — Multi-provider + DataQualityScore

**Objectif** : supprimer le SPOF Yahoo (`yahoo_finance.py` seul ; `sedar_plus.py` no-op `:55`). Corrige **FC3 / R5**.

**Livrables**
- **Interface `MarketDataProvider`** (Protocol) + implémentations : Yahoo (existant), **SEC EDGAR** (fondamentaux US, gratuit, API officielle), **Financial Modeling Prep** (fondamentaux normalisés, clé), **Alpha Vantage** (fallback prix).
- **Orchestrateur de données** : ordre de préférence configurable, **fallback** automatique, **réconciliation** des champs clés si ≥ 2 sources.
- **`DataQualityScore`** : détecte écart > seuil entre sources, divergences, données manquantes → **dégrade la confiance** des autres scores. Table `data_quality_log`.
- Clés FMP/Alpha Vantage dans `.env.example` (valeurs factices). Tout `async` (httpx).

**Tests** : unitaires fallback (provider 1 échoue → 2 prend le relais), DataQualityScore sur divergences forgées.
**Effort** : Élevé · **Dépendances** : B · **Effet note** : +0,5 à +1 (fiabilité = argument B2B clé).

---

## Sprint E — Risk + Quality engines (composite v2)

**Objectif** : déterminer ce qui est encore du verdict LLM (4/6 entrées, `core.py:1031-1048`) et donner des mesures de risque. Corrige **FC2, FC4, FC6**.

**Livrables**
- **`RiskScore`** (nouveau `factor_scores.py` ou `risk_calculations.py`) : volatilité annualisée, **β réel** (réutilise Sprint A), Sharpe, Sortino, **VaR 95/99** (scipy), Expected Shortfall, max drawdown (factorise `backtest.py:72-95`). Score 0-100 inversé.
- **`QualityScore`** : ROIC, ROE, marges (brute/op./FCF), FCF conversion, dette/FCF, **couverture d'intérêts**. Enrichir `tier1` (EBIT, charges d'intérêts, capitaux investis — chemin critique). Corrige **FC4** (ROIC enfin calculé → test ROIC > WACC).
- **Composite v2** (`score_version=2`) : Buffett / earnings / valuation / moat → **sous-scores déterministes** ; le LLM passe **explicateur** (« voici le score, explique pourquoi, liste les risques non capturés »). `marks_confidence` finalisée.
- **Gate sectoriel Montier** + neutralisation du signal mort (`financial_calculations.py:131-132, 695-699`). Corrige **FC6**.

**Tests** : unitaires golden Risk/Quality ; **re-calibrer les evals** (drift après bascule LLM→déterministe) ; intégration composite v2 A/B sur l'historique.
**Effort** : Élevé · **Dépendances** : B (prix pour Risk), A/D · **Effet note** : +0,5 à +1.

---

## Sprint F — Modèle B2B/API (monétisation)

**Objectif** : créer le chemin vers des revenus — l'élément qui manque le plus à la note produit.

**Livrables**
- **Quotas & metering par clé API** : la table `api_keys` + rôles existe déjà (`api_key_service.py`) ; ajouter compteur d'usage (analyses/mois), plafonds par plan, `429` au dépassement, endpoint `/admin/usage`.
- **Rate-limit par clé** (pas seulement par IP) ; **security headers** (X-Frame-Options, HSTS, CSP — corrige **A4**) ; **CORS strict** whitelist (corrige **A5**).
- **OpenAPI productisé** : documentation publique des endpoints `/analyze`, `/screen`, `/performance/scorecard`, `/risk/{ticker}`, exemples, SDK minimal.
- **Page tarifs / facturation** (hooks Stripe ou équivalent — au moins le schéma de plans).
- **Disclaimer renforcé & conforme AMF** (centralisé déjà en place — `constants/disclaimer.ts`), mention statut « recherche, non-conseil ».

**Tests** : intégration quota/429, headers présents, CORS rejette origine non whitelistée.
**Effort** : Moyen-Élevé · **Dépendances** : C (la scorecard est l'argument de vente), D · **Effet note** : +1 (passe de « projet » à « produit »).

---

## Sprint G — Portfolio engine (optionnel / parallèle)

**Objectif** : compléter la vue institutionnelle.

**Livrables** : table `positions` (ticker, quantité, PRU, compte CELI/REER — se branche sur le skill `canadian_tax` existant) ; `PortfolioRiskScore` (corrélation, covariance, concentration Herfindahl, expositions sectorielle/devise) ; garde-fous configurables → alertes (réutilise `alert_history` + `webhook_service`) ; pages **Portfolio** + **Risque/Facteurs**.
**Effort** : Élevé · **Dépendances** : B, E · **Effet note** : +0,5 (renforce le positionnement institutionnel).

---

## Projection de la note

| Étape cumulée | Note produit estimée | Ce qui est débloqué |
|---|---|---|
| Départ | **4,5** | — |
| + A | ~4,8 | Le score ne ment plus ; sécurité durcie |
| + B + **C** | **~6,3** | **Preuve empirique (hit rate)** — le saut décisif |
| + D | ~6,8 | Données fiables multi-sources |
| + E | ~7,2 | Risque mesuré, composite déterministe |
| + F | **~7,8** | Modèle économique B2B/API |
| + G | ~8,0 | Vue portefeuille institutionnelle |

**Cap au-delà de 8** : tant que le positionnement reste B2B/API. Aller plus haut (produit grand public) exigerait mobile/PWA + onboarding + courtage/temps réel — un changement de nature, hors de ce plan.

---

## Hors périmètre (volontairement)

- **Mobile/PWA & onboarding grand public** : nécessaires seulement pour le positionnement (c), pas (b). À garder pour une phase ultérieure si la cible change.
- **Trading/exécution d'ordres** : hors mission (l'app est explicitement un outil d'analyse, pas un bot).

---

## Risques & mitigations

| Risque | Mitigation |
|---|---|
| Changement de note casse l'historique/backtest | `score_version` (Sprint A), recalcul historisé, bascule A/B |
| Rate-limit / SPOF Yahoo pendant l'ingestion prix | batch + cache + multi-provider (D) |
| z-scores / stats sur univers trop petit | documenter l'univers, élargir via screener, winsoriser |
| Dérive des evals après LLM→déterministe | re-calibrer les golden datasets (E) |
| Conformité AMF dès la monétisation | disclaimer renforcé + statut « recherche » explicite (F), valider avec un juriste avant facturation |
