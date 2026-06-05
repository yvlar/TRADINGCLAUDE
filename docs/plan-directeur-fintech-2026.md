# Plan Directeur FinTech — TradingClaude → Plateforme B2B/SaaS

**Date** : 2026-06-05 · **Base** : branche `dev`, v10.39.0 · **Référence d'audit** : `revue-expert-fintech-2026-06.md` (revue interne — gardée locale par convention `.gitignore: revue-*.md`)
**Horizon** : 12 mois · **Posture** : due diligence pré-investissement (CTO / architecte / OWASP / PM / VC / UX / SaaS B2B)
**Hypothèse d'équipe** : 1 ingénieur-fondateur (Yves) augmenté IA + 1 contractuel ciblé (UX/mobile, sécurité) sur 2-3 épics. Effort exprimé en **jours-homme (j-h)** et en **sprints** (style projet : incrément testable unique).

---

# 1. Executive Review

**Constat.** TradingClaude est un **moteur de recherche fondamentale déterministe** de qualité rare (16 frameworks, 5 scores anti-fraude calculés en Python et substitués au LLM, fiscalité canadienne, auth de niveau production, ~206 fichiers de tests). Mais ce moteur est enfermé dans une **enveloppe mono-tenant, non monétisée, sans couche données robuste ni distribution**. L'audit a chiffré l'écart : robustesse d'ingénierie 7,5/10, maturité produit/business 4/10, **note produit investissable ≈ 5,5/10**.

**Thèse de transformation.** Ne pas pivoter vers le retail (Wealthsimple/Robinhood) — catégorie où l'enveloppe manque et la concurrence est massivement financée. **Capitaliser sur le moteur** en le transformant en **« Fundamental Research-as-a-Service »** vendu d'abord **B2B / white-label à des conseillers et family offices canadiens**, où la rigueur déterministe + la niche fiscale + la traçabilité deviennent un avantage payant et où le **risque réglementaire est porté par le conseiller enregistré** (et non par TradingClaude).

**La bascule exige des fondations, pas du polish** : multi-tenance + isolation des données (bloqueur absolu), durcissement sécurité fail-closed, couche de données multi-fournisseurs, facturation/metering, puis modernisation produit (onboarding, mobile, charts, API documentée).

**Décision d'investissement (résumé).** *Pas d'investissement equity dans la société en l'état* (pas de produit ni de revenu). **Recommandation : financer une transformation jalonnée de 12 mois** (pre-seed/SAFE ou bootstrap augmenté) avec 3 portes de sortie (go/no-go) — multi-tenance livrée (M3), 3 clients conseillers payants (M6), 25 k$ MRR + rétention (M12). Détail au §11.

**Chiffres-cadres de la transformation** :

| Indicateur | Aujourd'hui | Cible 12 mois |
|---|---|---|
| Tenance | Mono-tenant (0 `user_id` sur les données) | Multi-tenant + RLS |
| Monétisation | 0 $ | 25-40 k$ MRR (B2B/white-label) |
| Fournisseurs de données | 1 (yfinance, fragile) | 2-3 (fallback + point-in-time) |
| Latence analyse complète | ~5 min (séquentiel) | < 90 s (parallélisé) |
| Couverture sécurité | Fail-open conditionnel | Fail-closed + chiffrement + audit |
| Posture réglementaire | Disclaimer footer | Tool-vendor B2B + Loi 25/PIPEDA |

---

# 2. Méthodologie de priorisation

Score transparent et reproductible appliqué à **chaque** faiblesse :

- **Impact** (valeur créée ou risque évité) : 1 (cosmétique) → 5 (existentiel/bloquant).
- **Effort** : 1 (≤2 j) · 2 (1 sprint) · 3 (2-3 sprints) · 4 (1-2 mois) · 5 (≥2 mois / épic).
- **Confiance** (C) : H/M/L sur la solution proposée.
- **ROI** = `Impact² ÷ Effort` (récompense le haut-impact ; arrondi). Borne ~0,2 → 25.
- **Priorité** : **P0** (fondations/sécurité, 0-2 mois) · **P1** (fiabilité/profondeur, 2-5 mois) · **P2** (produit/marché, 5-9 mois) · **P3** (échelle/différenciation, 9-12 mois+).

Tableaux de scoring par faiblesse en §3 ; classement ROI consolidé en §10.

---

# 3. Analyse détaillée des faiblesses

> Couverture exhaustive de l'audit : **9 domaines, 0 point critique sans recommandation** (condition de sortie 11). Format compact : chaque faiblesse = Impact · Risque · Solution · ROI · Effort · Priorité · Critères d'acceptation (CA).

## 3.1 Architecture

| # | Faiblesse | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|
| A1 | Orchestration séquentielle ~5 min/ticker (`orchestrator/core.py`) | 4 | 3 | 5 | P2 |
| A2 | Pool asyncpg `max_size=10` + 2 pools (API/Celery), pas de pooler | 3 | 2 | 4 | P1 |
| A3 | Migrations **inline dans le lifespan** (pas d'Alembic, boot fragile) | 4 | 2 | 8 | P0 |
| A4 | Invalidation cache via `KEYS` O(N) (`analysis_cache.py`) | 3 | 1 | 9 | P1 |
| A5 | Celery sans `time_limit` ni DLQ (`workers/celery_app.py`) | 3 | 2 | 4 | P1 |
| A6 | Redis SPOF, pas de HA | 3 | 3 | 3 | P2 |

- **A3 — Migrations inline.** *Impact* : un échec de `CREATE TABLE` au boot plante l'API ; pas de versioning de schéma → migrations multi-tenant ingérables. *Risque* : corruption/incohérence de schéma en prod. *Solution* : introduire **Alembic**, extraire toutes les `CREATE TABLE` du lifespan vers des migrations versionnées, boot en read-only. *ROI 8* · *Effort 2 (1 sprint)* · *P0*. *CA* : `alembic upgrade head` idempotent en CI ; lifespan ne crée plus de table ; rollback testé.
- **A1 — Latence.** *Solution* : graphe de dépendances explicite ; exécuter en parallèle les skills sans dépendance (Graham∥Lynch∥ESG), `asyncio.gather` borné. *CA* : compounder_buffett < 90 s p50 ; tests d'ordre/déterminisme inchangés.
- **A4 — Cache O(N).** *Solution* : index secondaire (Set Redis `idx:{ticker}`) pour invalidation ciblée, suppression du scan `KEYS`. *CA* : invalidation O(log n) ; bench 100 k clés sans blocage.
- **A2/A5/A6** : pgbouncer (ou Postgres managé), `task_time_limit`/`task_soft_time_limit` + DLQ Redis, Redis managé HA (Upstash/ElastiCache). *CA* : pool ≥ 20 effectif ; task zombie tuée < 360 s ; bascule Redis sans perte de session.

## 3.2 Multi-tenancy *(bloqueur n°1)*

| # | Faiblesse | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|
| M1 | **Aucun `tenant_id`/`user_id`** sur 6 tables globales | 5 | 4 | 6 | P0 |
| M2 | Pas d'isolation (RLS) → fuite inter-comptes | 5 | 3 | 8 | P0 |
| M3 | Pas de quotas/limites par compte | 4 | 2 | 8 | P0 |
| M4 | `api_keys` sans rattachement tenant ni metering | 4 | 2 | 8 | P0 |

- **M1/M2 — Isolation des données.** *Impact* : **existentiel** — impossible d'onboarder un 2ᵉ client sans exposer les données du 1ᵉʳ. Tables concernées (vérifié) : `analysis_history`, `watchlist`, `composite_score_history`, `esg_score_history`, `alert_history`, `annotations`. *Risque* : fuite de données = fin commerciale + violation Loi 25/PIPEDA. *Solution* :
  1. Table `tenants` + `users.tenant_id` (FK) ; ajouter `tenant_id UUID NOT NULL` aux 6 tables (migration Alembic, backfill tenant « legacy »).
  2. **PostgreSQL Row-Level Security** : `ALTER TABLE … ENABLE ROW LEVEL SECURITY` + policy `tenant_id = current_setting('app.tenant_id')` ; injection du `SET app.tenant_id` par connexion via middleware.
  3. Threader `current_user`/`tenant` depuis l'auth jusqu'à l'orchestrateur (l'endpoint `analyze_stream` n'en reçoit aucun aujourd'hui — vérifié).
  *ROI 6-8* · *Effort 3-4* · **P0**. *CA* : un tenant ne lit jamais les lignes d'un autre (test d'isolation rouge→vert) ; RLS actif sur les 6 tables ; cache Redis clé préfixée `tenant`.
- **M3 — Quotas.** *Solution* : table `plan_limits` (analyses/mois, screener size, rétention) + compteur Redis ; `429` au dépassement. *CA* : quota respecté, message UX clair, override admin.
- **M4 — Clés API tenant + metering.** *Solution* : `api_keys.tenant_id`, table `usage_events` (append-only) horodatant chaque analyse/coût. *CA* : chaque appel attribué à un tenant ; base de facturation prête (§7).

## 3.3 Sécurité (OWASP)

| # | Faiblesse | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|
| S1 | **Bypass CSRF si `API_KEY` vide** (`csrf.py:64-66`) — fail-open | 5 | 1 | 25 | P0 |
| S2 | Comparaison CSRF non timing-safe (`csrf.py:77`) | 2 | 1 | 4 | P0 |
| S3 | Fallback CORS localhost si `CORS_ORIGINS` vide (`main.py:599`) | 4 | 1 | 16 | P0 |
| S4 | Pas de chiffrement at-rest (PG/Redis) | 4 | 2 | 8 | P0 |
| S5 | Secrets/données sensibles potentiels dans logs (`exc_info`, payloads) | 4 | 2 | 8 | P0 |
| S6 | `python-jose` non maintenu → `PyJWT` | 3 | 2 | 4 | P1 |
| S7 | Rate-limit sur `request.client.host` (spoof X-Forwarded-For) | 3 | 1 | 9 | P0 |
| S8 | Pas de rate-limit sur `validate_key` (brute force hash) | 3 | 1 | 9 | P1 |
| S9 | Pas d'audit trail des mutations (watchlist/annotations/clés) | 4 | 2 | 8 | P1 |
| S10 | Mot de passe PG par défaut `copilote` (compose dev) | 3 | 1 | 9 | P0 |

- **S1 — CSRF fail-closed (top ROI 25).** *Solution* : bypass UNIQUEMENT si `APP_ENV in {dev,test}` explicite, jamais sur `API_KEY` vide ; sinon `403`. *Effort 1* · **P0**. *CA* : prod sans `API_KEY` → CSRF actif ; test négatif.
- **S3 — CORS fail-fast.** *Solution* : si `APP_ENV=prod` et `CORS_ORIGINS` vide → `RuntimeError` au boot. *CA* : boot prod refusé sans origines explicites.
- **S4/S5 — Données sensibles.** *Solution* : chiffrement at-rest (volume/managed DB + Redis TLS), assainisseur de logs (filtre regex tokens/clés/emails), bannir `exc_info` complet en prod. *CA* : aucun secret dans les logs (test) ; at-rest activé.
- **S7 — Trust proxy.** *Solution* : lire `X-Forwarded-For` uniquement derrière Caddy de confiance (liste d'IP), sinon `request.client.host`. *CA* : spoofing neutralisé en test.
- **S9 — Audit trail.** *Solution* : table `audit_log` (tenant, user, action, cible, ts) append-only sur toutes les mutations. *CA* : chaque mutation tracée ; consultable admin. (Pré-requis conformité Loi 25.)
- **S2/S6/S8/S10** : `hmac.compare_digest`, migration `PyJWT` + pin `cryptography`, rate-limit Redis sur `validate_key`, secret PG généré obligatoire. *CA* : audit `pip-audit`/`bandit` propre en CI.

## 3.4 Données financières

| # | Faiblesse | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|
| D1 | **ROIC jamais extrait** (`yahoo_finance.py:494: roic=None`) | 5 | 2 | 12 | P1 |
| D2 | **Bêta figé 1.0** (`valuation_calculations.py:17`) | 4 | 1 | 16 | P1 |
| D3 | ERP/Rf/impôt figés (pas de recalcul macro) | 4 | 2 | 8 | P1 |
| D4 | Source unique yfinance, SEDAR placeholder, **pas de fallback** | 5 | 4 | 6 | P1 |
| D5 | Détection sectorielle par mot-clé naïve | 3 | 2 | 4 | P1 |
| D6 | Banques/REIT : ratios sectoriels **non calculés** (100 % LLM) | 4 | 3 | 5 | P1 |
| D7 | Owner earnings (Buffett) non calculé en Python | 3 | 2 | 4 | P2 |
| D8 | Calibration seuils (US 1999/2003) non revalidée Canada 2026 | 3 | 3 | 3 | P2 |
| D9 | Pas de snapshot point-in-time des données source | 4 | 3 | 5 | P1 |

- **D1 — ROIC.** *Impact* : ratio-cœur de Buffett/Dorsey/Damodaran absent → 3 cadres dégradés. *Solution* : service `financial_calculations.roic()` = NOPAT/(dette+capitaux propres) à partir d'`income_stmt`/bilan yfinance ; substitution déterministe (même pattern que Graham number). *ROI 12* · **P1**. *CA* : ROIC calculé et persisté pour ≥ 90 % des tickers non-financiers ; test golden.
- **D2 — Bêta (ROI 16).** *Solution* : extraire `info['beta']` yfinance ; fallback sectoriel avant 1.0 ; propager au CAPM. *CA* : bêta réel utilisé quand dispo ; sensibilité DCF documentée.
- **D3 — Macro vivante.** *Solution* : service `macro_provider` (Rf = rendement 10 ans Canada/US courant, ERP Damodaran mis à jour, impôt effectif réel si dispo) avec cache 24 h. *CA* : WACC reflète les taux du jour ; source+date affichées.
- **D4 — Multi-fournisseurs (fondation).** *Solution* : **interface `FinancialDataProvider`** ; implémentations `YFinanceProvider` (actuel) + `FmpProvider`/`PolygonProvider` (fallback) ; politique de résolution + provenance par champ (déjà partiellement présente via `ratios_provenance`). *Effort 4* · **P1**. *CA* : yfinance down → fallback transparent ; provenance par champ exposée.
- **D6 — Secteurs financiers.** *Solution* : calculs Python Tier 1/CET1, FFO, P/NAV pour sortir banques/REIT du 100 % LLM. *CA* : verdicts sectoriels reproductibles, non hallucinés.
- **D9 — Point-in-time.** *Solution* : snapshot horodaté des inputs (déjà `input_data` JSONB) versionné + immuable → backtests honnêtes, audit conformité. *CA* : toute analyse rejouable sur ses données d'origine.

## 3.5 IA

| # | Faiblesse | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|
| AI1 | Narratives non fact-checkées (hallucination résiduelle) | 4 | 2 | 8 | P1 |
| AI2 | RAG ancre la **méthode**, pas les **faits** entreprise | 3 | 4 | 2 | P3 |
| AI3 | Pas de circuit-breaker de budget intra-workflow | 3 | 1 | 9 | P1 |
| AI4 | **Evals non automatisées en CI** (drift LLM non capté) | 4 | 3 | 5 | P1 |
| AI5 | Pas de fuzzing des entrées aberrantes (GIGO) | 3 | 2 | 4 | P1 |

- **AI1 — Garde-fous narratifs.** *Solution* : règles de cohérence post-parse liant narrative et chiffres déterministes (ex. interdire « risque de faillite » si Altman Z > 2,99 ; exiger qu'un `drapeau_rouge` cite un champ chiffré). *CA* : violations détectées et rejetées/annotées ; test sur cas golden.
- **AI3 — Budget.** *Solution* : seuil `cost_usd` par workflow → court-circuit + `warning` ; coût exposé en temps réel. *CA* : dépassement stoppe proprement avec résultat partiel.
- **AI4 — Eval gate.** *Solution* : suite d'evals déterministes hors-ligne (déjà amorcée : `test_earnings_deterministic_replay.py`) en CI ; evals Claude réelles nocturnes hors-CI avec budget. *CA* : régression de concordance verdict bloque la PR.
- **AI5 — Robustesse entrées.** *Solution* : validateurs de plausibilité (P/E, D/E, total_assets>0) + tests de fuzzing. *CA* : entrées aberrantes → `None`/erreur explicite, jamais de score fantaisiste.
- **AI2 — RAG factuel (long terme).** *Solution* : ingestion de filings (SEDAR+/EDGAR) pour grounding factuel ; *P3* car coûteux et hors chemin critique B2B initial.

## 3.6 UX/UI

| # | Faiblesse | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|
| U1 | Pas d'onboarding/landing → conversion ≈ 0 | 4 | 2 | 8 | P2 |
| U2 | Desktop-first, mobile faible | 4 | 3 | 5 | P2 |
| U3 | Pas de graphique de prix/chandelier | 3 | 2 | 4 | P2 |
| U4 | Disclaimer footer-only (pas inline verdict) | 4 | 1 | 16 | P0 |
| U5 | Surcharge cognitive (16 cadres, 6 taxonomies de verdict) | 4 | 3 | 5 | P2 |
| U6 | Composite score caché, pas de mode simple/expert | 3 | 2 | 4 | P2 |
| U7 | Pas de thème clair/sombre, a11y partielle (~60 %) | 2 | 2 | 2 | P3 |

- **U4 — Disclaimer inline (ROI 16, conformité).** *Solution* : composant `<VerdictDisclaimer>` rendu adjacent à chaque verdict (Graham/Buffett/ESG…). *Effort 1* · **P0** (réglementaire). *CA* : aucun verdict affiché sans avertissement adjacent (test).
- **U5/U6 — Décomplexification.** *Solution* : **score composite unique en tête** + bandeau verdict synthétique ; mode « Simple » (3-4 cadres) vs « Expert » (16) ; tooltips sur ratios. *CA* : un débutant identifie LA recommandation en < 5 s (test utilisateur) ; mode persisté par compte.
- **U1/U2/U3** : landing + onboarding 3 écrans ; refonte responsive (grilles `1-col < 768px`, tables `reflow`, formulaire collapsible) ; chart de prix recharts/lightweight-charts 1-5 ans. *CA* : Lighthouse mobile > 85 ; E2E Playwright sur 375/768/1920.

## 3.7 Scalabilité *(débit & charge — au-delà de l'architecture)*

| # | Faiblesse | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|
| SC1 | Pas de load testing à 1000+ tickers/jour | 3 | 2 | 4 | P2 |
| SC2 | Throughput limité par séquentialité (A1) + pools (A2) | 4 | 3 | 5 | P2 |
| SC3 | yfinance rate limits non maîtrisés sous charge | 4 | 3 | 5 | P1 |
| SC4 | Celery sans autoscaling (concurrency=2 statique) | 3 | 3 | 3 | P2 |

- **Solution d'ensemble** : file de travail tenant-aware (priorité par plan), cache fournisseur de données (réduire les hits yfinance), workers autoscalables (concurrency dynamique / file dédiée par workflow), **load tests `tests/load/` cibles : 1 000 analyses/jour, p95 < 120 s**. *CA* : SLO défini et tenu en bench ; pas d'effondrement à 3× la charge nominale.

## 3.8 Produit

| # | Faiblesse | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|
| PR1 | Pas d'onboarding self-serve / gestion de compte | 4 | 3 | 5 | P2 |
| PR2 | Pas de gestion de **portefeuille/positions** (juste watchlist) | 4 | 4 | 4 | P2 |
| PR3 | Alertes basiques mono-canal | 3 | 2 | 4 | P2 |
| PR4 | Pas de partage/collaboration de rapports | 3 | 2 | 4 | P3 |
| PR5 | **API non productisée** (pas d'OpenAPI publique/SDK/clés self-serve) | 5 | 3 | 8 | P2 |
| PR6 | Périmètre étroit value-only | 3 | 5 | 2 | P3 |

- **PR5 — API produit (clé de la monétisation B2B).** *Solution* : OpenAPI publique versionnée, clés self-serve par tenant, quotas, docs développeur, SDK Python/TS, webhooks. *ROI 8* · **P2**. *CA* : un développeur s'inscrit, obtient une clé, lance une analyse en < 10 min sans support.
- **PR2 — Portefeuille.** *Solution* : import positions (CSV/Wealthsimple/IBKR read-only), suivi PBR/ACB (atout fiscal CA), agrégation de scores au niveau portefeuille. *CA* : un conseiller charge un portefeuille client et obtient une vue consolidée.
- **PR3/PR4/PR6** : alertes multi-canal (email/Slack/webhook déjà partiels) ; partage de rapport par lien signé ; élargissement périmètre (macro/technique léger) en P3.

## 3.9 Business

| # | Faiblesse | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|
| B1 | **Zéro monétisation** (pas de Stripe/plans) | 5 | 3 | 8 | P1 |
| B2 | Pas de metering/usage par compte | 4 | 2 | 8 | P0/P1 |
| B3 | Pas de GTM ni segment défini | 4 | 2 | 8 | P1 |
| B4 | Douve faible (cadres copiables) | 3 | 4 | 2 | P3 |
| B5 | **Exposition réglementaire** (advice line, AMF/CIRO/Loi 25/SEC) | 5 | 3 | 8 | P0 |
| B6 | Dépendance fournisseurs (Anthropic/OpenAI/Yahoo) | 3 | 3 | 3 | P2 |

- **B1/B2 — Facturation + metering.** *Solution* : Stripe Billing (abonnements + usage), `usage_events` (M4) comme socle. *CA* : un client souscrit, est facturé à l'usage, reçoit une facture ; dunning géré.
- **B5 — Conformité (voir §9).** *Solution* : positionnement **« fournisseur d'outil » B2B** (le conseiller enregistré CIRO/AMF porte la recommandation), CGU/disclaimer renforcés, Loi 25 (responsable vie privée, EFVP, résidence des données au Canada), pas de conseil personnalisé/discrétionnaire. *CA* : avis juridique fintech obtenu ; CGU B2B signées ; registre Loi 25.
- **B4 — Douve.** *Solution* : approfondir la spécialisation (fiscalité CA + déterminisme auditable + intégrations conseillers) ; effets de données via `usage_events` agrégés (benchmarks anonymisés). *P3*.
- **B6 — Dépendances.** *Solution* : abstraction modèle (déjà `CLAUDE_MODEL` env) + abstraction données (D4) + budget multi-fournisseur. *CA* : bascule fournisseur sans réécriture.

---

# 4. Benchmark concurrentiel

**Carte de positionnement** (2 axes : *Profondeur analyse fondamentale* ↔ *Largeur plateforme/temps réel*) :

```
Profondeur fondamentale ▲
        │  AlphaSense        Bloomberg
TradingClaude ●            (recherche)   (tout)
        │  Seeking Alpha
        │            Koyfin
        │                      TradingView
        │   Wealthsimple   Robinhood
        └───────────────────────────────► Largeur plateforme / temps réel / multi-actifs
```

| Concurrent | Cœur | Force à étudier | Faiblesse à exploiter | Menace pour TC |
|---|---|---|---|---|
| **Bloomberg Terminal** | Données + tout-en-un (24 k$/an) | Couverture, fiabilité institutionnelle | Coût, complexité, pas de synthèse IA déterministe ouverte | Faible (segments différents) |
| **AlphaSense** | Recherche IA + transcripts/filings | Grounding factuel sur documents, search sémantique | Pas de scoring déterministe value ni fiscalité CA | **Élevée** (pair le plus proche) |
| **Seeking Alpha** | Recherche crowd + quant grades | Quant ratings, communauté, SEO | Qualité variable, pas de déterminisme auditable | Moyenne |
| **Koyfin** | Données + dashboards (alt-Bloomberg) | UX dashboards, multiples, estimés | Pas d'analyse-cadre ni IA explicable | Moyenne |
| **TradingView** | Charts + technique + social | Charts best-in-class, communauté | Faible sur fondamental profond/fiscalité | Faible |
| **Wealthsimple** | Courtage retail CA + fiscalité | Mobile, fiscalité CA, marque | Pas de recherche fondamentale profonde | Faible (mais possède la niche CA retail) |
| **Robinhood** | Courtage retail US | UX, exécution, coût | Recherche superficielle, pas de CA | Faible |

**Lecture stratégique.**
- **Pair direct = AlphaSense** (recherche IA). TC gagne sur le **déterminisme auditable + fiscalité canadienne + coût**, perd sur le **grounding factuel documentaire** (→ D4/AI2 en P1/P3) et la couverture.
- **À copier** : grounding documentaire (AlphaSense), quant grades synthétiques (Seeking Alpha), UX dashboard (Koyfin), onboarding/mobile (Wealthsimple).
- **À NE PAS imiter** : largeur multi-actifs temps réel (Bloomberg/TradingView) — hors thèse, capital mal investi.
- **Espace blanc défendable** : *« recherche fondamentale déterministe + fiscale canadienne, en marque blanche pour conseillers »* — aucun des 7 ne l'occupe frontalement.

---

# 5. Architecture cible

**Principe : évolution, pas réécriture.** Conserver les actifs (déterminisme, skills, auth, tests) ; ajouter 4 couches transverses : **tenance, données, facturation, observabilité/échelle**.

```
                         ┌───────────────────────────────────────┐
                         │     Frontend React (SPA + Mobile-web)  │
                         │  Onboarding · Mode simple/expert · API docs│
                         └───────────────┬───────────────────────┘
                                         │ HTTPS (Caddy)
                  ┌──────────────────────▼─────────────────────────┐
                  │  API Gateway FastAPI (tenant-aware)             │
                  │  AuthN/Z JWT · RLS context (SET app.tenant_id)  │
                  │  Rate-limit par tenant/plan · CSRF fail-closed  │
                  └───┬───────────┬───────────────┬────────────────┘
                      │           │               │
        ┌─────────────▼──┐ ┌──────▼───────┐ ┌─────▼─────────────┐
        │ Orchestrateur   │ │ Billing/      │ │ Data Layer        │
        │ (skills //)     │ │ Metering      │ │ FinancialDataProvider│
        │ budget breaker  │ │ Stripe +      │ │  ├ YFinance         │
        │ eval gate       │ │ usage_events  │ │  ├ FMP/Polygon (fb) │
        └───┬─────────────┘ └──────┬────────┘ │  ├ Macro provider   │
            │                      │          │  └ Point-in-time    │
            │                      │          └─────────┬───────────┘
   ┌────────▼─────────┐   ┌────────▼─────────┐  ┌────────▼─────────┐
   │ Claude (det.     │   │ PostgreSQL (RLS) │  │ Qdrant (RAG méth.│
   │ substitution)    │   │ + Alembic + audit│  │ + filings P3)    │
   │ Langfuse (oblig.)│   │ pgbouncer        │  └──────────────────┘
   └──────────────────┘   └────────┬─────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │ Redis (HA) · cache tenant ·   │
                    │ quotas · Celery broker + DLQ  │
                    │ workers autoscalables         │
                    └──────────────────────────────┘
       Observabilité : Prometheus/Grafana (latence/coût/skill) + Langfuse + audit_log
       Secrets : gestionnaire dédié (pas .env en prod) · Chiffrement at-rest · Résidence CA
```

**Décisions d'architecture clés.**
1. **Isolation** : *single-DB + RLS* pour démarrer (coût/ops minimal) → option *schema-per-tenant* puis *DB-per-tenant* pour l'enterprise (chemin documenté, pas implémenté d'emblée).
2. **Données** : interface fournisseur + provenance par champ (étend l'existant `ratios_provenance`) + snapshots immuables (point-in-time).
3. **IA** : garder la substitution déterministe (différenciateur) ; ajouter eval-gate CI, budget breaker, garde-fous narratifs, Langfuse **obligatoire** en prod.
4. **Facturation** : `usage_events` append-only comme source de vérité unique (metering → Stripe → analytics).
5. **Échelle** : pgbouncer, Redis HA managé, Celery time-limit+DLQ+autoscaling, load tests SLO.
6. **Migrations** : Alembic (fin des migrations inline lifespan).

---

# 6. Roadmap P0 → P3

| Phase | Fenêtre | Thème | Sortie (gate) |
|---|---|---|---|
| **P0 — Fondations & sécurité** | M0-M2 | Multi-tenance + RLS, sécurité fail-closed, disclaimer inline, Alembic, audit_log, metering socle | *Onboardable sans fuite* + sécurité durcie |
| **P1 — Fiabilité & données & revenu** | M2-M5 | Data layer multi-fournisseurs, ROIC/bêta/macro, eval-gate CI, garde-fous IA, **Stripe + 1ers clients**, conformité B2B | *3 clients conseillers payants* |
| **P2 — Produit & marché** | M5-M9 | API productisée + SDK, onboarding/landing, mobile, charts, mode simple/expert, portefeuille, white-label | *Self-serve + white-label live* |
| **P3 — Échelle & différenciation** | M9-M12+ | Grounding factuel (filings), alt-data, HA/scale, certifs conformité, SaaS retail (option) | *Scale + douve de données* |

Jalons investisseur : **M3** (multi-tenance + sécurité), **M6** (3 clients payants), **M12** (25-40 k$ MRR + rétention).

---

# 7. Sprint Backlog détaillé

> Style projet respecté : 1 sprint = incrément testable unique, sur branche `claude/sprintNN-<nom>`, PR vers `dev`, mise à jour `ROADMAP.md` + `prompt-mise-a-jour-roadmap.md` + commit (cf. `workflow-sprint.md`). Numérotation à partir du prochain sprint réel (**154**). Chaque sprint : Objectif · Fichiers · Tests · CA.

## Épic E1 — Sécurité fail-closed (P0, ~1 sprint)
| Sprint | Objectif | Fichiers clés | CA / Tests |
|---|---|---|---|
| **154** | CSRF fail-closed + timing-safe + CORS fail-fast + trust-proxy | `app/middleware/csrf.py`, `rate_limit.py`, `api/main.py` | prod sans `API_KEY`→CSRF actif ; `hmac.compare_digest` ; boot prod refusé si CORS vide ; tests négatifs |

## Épic E2 — Migrations & socle DB (P0, ~2 sprints)
| **155** | Introduire **Alembic**, extraire les `CREATE TABLE` du lifespan | `infra/postgres/`, `app/api/main.py`, `alembic/` | `alembic upgrade head` idempotent en CI ; lifespan ne crée plus de table |
| **156** | `audit_log` append-only + branchement sur mutations | `app/services/*`, migration | toute mutation tracée (watchlist/annotation/clé) ; test |

## Épic E3 — Multi-tenance + RLS (P0, ~3-4 sprints) *(bloqueur)*
| **157** | Table `tenants` + `users.tenant_id` + backfill « legacy » | migration, `user_service.py` | users rattachés ; rétrocompat |
| **158** | `tenant_id` sur les 6 tables globales + index | migration | colonnes NOT NULL backfillées |
| **159** | **RLS** + `SET app.tenant_id` par requête (middleware) | `middleware/`, DB policies | isolation rouge→vert ; aucun cross-tenant |
| **160** | Threader `current_user`/tenant jusqu'à l'orchestrateur + clé cache préfixée | `analyze_stream.py`, `core.py`, `analysis_cache.py` | analyses/watchlist sc
opées au tenant ; tests d'isolation |

## Épic E4 — Metering & quotas (P0/P1, ~2 sprints)
| **161** | `usage_events` (append-only) + attribution coût/tenant | `services/`, migration | chaque analyse attribuée ; base facturation |
| **162** | `plan_limits` + quotas Redis + `429` clair | `middleware/rate_limit.py`, `services/` | quota respecté ; override admin |

## Épic E5 — Couche données multi-fournisseurs (P1, ~4 sprints)
| **163** | Interface `FinancialDataProvider` + refactor yfinance | `app/skills/tier1/`, `services/` | parité comportementale ; tests |
| **164** | Provider fallback (FMP/Polygon) + résolution + provenance/champ | tier1, `ratios_recon.py` | yfinance down→fallback ; provenance exposée |
| **165** | **ROIC** déterministe + substitution | `financial_calculations.py`, skills | ROIC ≥90 % tickers ; golden |
| **166** | **Bêta** réel + **macro vivante** (Rf/ERP/impôt) | `valuation_calculations.py`, `services/macro_*` | WACC = taux du jour ; source+date |

## Épic E6 — Fiabilité IA (P1, ~3 sprints)
| **167** | **Eval-gate CI** (replays déterministes) + evals nocturnes | `tests/evals/`, CI | régression verdict bloque PR |
| **168** | Garde-fous narratifs (cohérence narrative↔chiffres) | skills, `services/` | violations rejetées ; golden |
| **169** | Budget breaker + fuzzing entrées aberrantes | `orchestrator/core.py`, `utils/` | dépassement stoppe ; entrées folles→None |

## Épic E7 — Monétisation (P1, ~3 sprints)
| **170** | Intégration **Stripe Billing** (abonnement + usage) | `services/billing_*`, endpoints | souscription→facture ; webhook |
| **171** | Portail facturation (UI) + dunning | `frontend/src/pages/Billing*` | client gère son plan |
| **172** | Conformité B2B : CGU/disclaimer renforcés, registre Loi 25 | `docs/legal/`, frontend | avis juridique intégré |

## Épic E8 — Secteurs financiers & profondeur (P1/P2, ~2 sprints)
| **173** | Ratios banques (Tier1/CET1) déterministes | `financial_calculations.py` | verdict bancaire reproductible |
| **174** | Ratios REIT (FFO/P-NAV) déterministes + détection sectorielle robuste | idem, `stock_valuation` | REIT non-LLM ; faux positifs « real » corrigés |

## Épic E9 — UX conformité & décomplexification (P0→P2, ~4 sprints)
| **175** | **Disclaimer inline** sur chaque verdict (P0) | `frontend/src/components/VerdictDisclaimer` | aucun verdict sans avertissement |
| **176** | Score composite en tête + bandeau verdict synthétique | `AnalysisResult`, `pages/Analyze` | LA reco visible <5 s |
| **177** | Mode simple/expert + tooltips ratios | composants, `user_preferences` | mode persisté/compte |
| **178** | Refonte responsive mobile + chart de prix | `frontend/src/**`, lib charts | Lighthouse mobile >85 ; E2E 375/768/1920 |

## Épic E10 — API produit & onboarding (P2, ~3 sprints)
| **179** | OpenAPI publique versionnée + clés self-serve tenant | `api/`, docs | dev autonome <10 min |
| **180** | SDK Python/TS + webhooks | `sdk/`, `services/webhook_service.py` | exemples testés |
| **181** | Landing + onboarding 3 écrans + provisioning self-serve | `frontend/`, `auth` | signup→1ʳᵉ analyse sans support |

## Épic E11 — Échelle & infra (P2/P3, ~3 sprints)
| **182** | pgbouncer + pool sizing + Redis HA managé | infra, compose/prod | pool ≥20 ; bascule Redis OK |
| **183** | Celery time-limit + DLQ + autoscaling ; cache invalidation O(log n) | `workers/`, `analysis_cache.py` | zombie tuée ; invalidation ciblée |
| **184** | Load tests SLO (1000 analyses/j, p95<120s) + Prometheus/Grafana | `tests/load/`, monitoring | SLO tenu à 3× charge |

## Épic E12 — Différenciation (P3, ~3+ sprints)
| **185+** | Parallélisation skills (latence <90s) ; portefeuille/positions ; grounding factuel filings ; alt-data | orchestrateur, data, RAG | latence cible ; portefeuille consolidé |

*Total indicatif : ~32 sprints sur 12 mois (P0 ≈ 7, P1 ≈ 12, P2 ≈ 8, P3 ≈ 5+).*

---

# 8. Plan de monétisation détaillé

**Principe de séquençage (insight central)** : monétiser **d'abord là où la willingness-to-pay est haute, le volume requis faible et le risque réglementaire porté par le client** (conseillers enregistrés), **avant** le retail (coût de service et charge réglementaire les plus élevés). Socle commun : `usage_events` (metering, sprint 161) + Stripe (sprint 170).

| Modèle | Segment cible | Tarification | ACV indicatif | Pré-requis | Charge réglementaire | Marge brute | Séquence |
|---|---|---|---|---|---|---|---|
| **White-label** | Cabinets de conseil, family offices, caisses/coopératives (QC/CA) | Setup 5-25 k$ + plateforme 1-5 k$/mois + 30-80 $/conseiller/mois · contrats annuels | **Élevé** (15-60 k$/an) | Multi-tenance (E3), branding, API (E10) | **Faible** (le cabinet est l'enregistré) | 75-85 % | **1ᵉʳ (P1, M2-M6)** |
| **SaaS Conseillers** | Conseillers indépendants, représentants CIRO, planificateurs fee-only | Solo 99-149 $/mois · Équipe 79 $/siège (3+) · module fiscal CA premium | Moyen (1,2-1,8 k$/an) | Mode simple/expert (E9), portefeuille (PR2), facturation (E7) | Faible-moyenne (outil d'aide) | 80-90 % | **1ᵉʳ (P1, M3-M6)** |
| **API B2B** | Robo-advisors, apps fintech, plateformes de contenu | Pay-as-you-go : ~0,5-2 $/analyse mono-skill, 3-8 $/workflow complet · paliers Dev (gratuit 50/mois) → Startup 199 $/mois (500) → Growth 999 $/mois (5 k) → Enterprise | Variable (PLG) | API productisée + SDK (E10), quotas (E4) | Faible (B2B2x) | **85-95 %** (coût/analyse = centimes) | **2ᵉ (P2, M5-M9)** |
| **SaaS Retail** | Investisseurs value autonomes (QC/CA, communauté FIRE, self-directed) | Freemium (3 analyses/mois, `value_graham`) → Pro 19-29 $/mois (16 cadres, PDF, alertes) → Premium 49 $/mois (screener, portefeuille) · -20 % annuel | **Faible** (230-590 $/an) | Mobile + onboarding + charts (E9), conformité retail | **Élevée** (B2C, AMF/disclaimers) | 70-85 % | **3ᵉ (P3, M9-M12+)** |

**Justification du séquençage.**
- **White-label & Conseillers en premier** : ils paient pour la **rigueur déterministe + la fiscalité canadienne + le gain de temps de préparation client**, fonctionnent **même avant** le mobile/charts/scale, et **déplacent le risque réglementaire** sur le conseiller enregistré (cf. §9). Cash le plus tôt, le plus sticky.
- **API B2B ensuite** : moteur de croissance PLG une fois le metering + l'API documentée livrés ; **marge la plus élevée** (coût marginal en centimes grâce au cache + Haiku).
- **Retail en dernier** : ACV le plus faible, CAC et support les plus élevés, charge réglementaire B2C maximale — n'a de sens qu'après la modernisation produit (E9) et la conformité.

**Pont vers la cible M12 (25-40 k$ MRR)** — combinaison réaliste, non cumulative au pire cas :

| Source | Hypothèse M12 | MRR |
|---|---|---|
| White-label | 4-6 cabinets @ ~2-3 k$/mois | 10-16 k$ |
| SaaS Conseillers | 30-50 conseillers @ ~120 $ | 3,6-6 k$ |
| API B2B | 5-10 comptes payants (Startup/Growth) | 3-8 k$ |
| Retail (bêta) | 200-400 Pro @ ~25 $ | 5-10 k$ |
| **Total** | | **≈ 22-40 k$ MRR** |

**GTM par modèle** : White-label/Conseillers = vente *founder-led* + design partners + communautés de conseillers QC (referrals, contenu fiscal) ; API = self-serve/PLG (signup développeur, docs) ; Retail = SEO/contenu + communauté + freemium viral. **Add-ons transverses** : rapports PDF premium (déjà construits), module fiscal CA, benchmarks anonymisés (effet de données, P3).

---

# 9. Couverture des risques

## Techniques
- **Isolation/données** : RLS testé en rouge→vert (E3) ; snapshots point-in-time (D9) ; fallback fournisseur (D4).
- **Disponibilité** : Redis HA, pgbouncer, Celery DLQ, load tests SLO (E11).
- **Dérive LLM** : eval-gate CI + garde-fous narratifs + Langfuse obligatoire (E6).
- **Dépendances** : abstractions modèle+données ; budget multi-fournisseur.

## Réglementaires *(Québec/Canada d'abord, US ensuite)*
- **AMF / CIRO** : positionnement **« fournisseur d'outil »** ; le **conseiller enregistré** porte la recommandation → TradingClaude évite le statut de « conseiller en valeurs ». Pas de conseil personnalisé/discrétionnaire ; disclaimers inline (E9-175). **Avis juridique fintech requis avant le 1ᵉʳ client payant.**
- **Loi 25 (Québec) / PIPEDA** : responsable de la protection des renseignements, **évaluation des facteurs relatifs à la vie privée (EFVP)**, consentement, notification de brèche, **résidence des données au Canada** (choisir région cloud CA), registre. (E7-172)
- **US (si RIA US)** : Investment Advisers Act — rester *tool-vendor* ; SEC Marketing Rule si claims de performance. **GDPR/MiCA** seulement si expansion EU/crypto (hors périmètre actuel — ne pas sur-investir).
- **IA** : disclosure « contenu généré par IA, sans garantie » ; l'**auditabilité déterministe + audit_log** est un atout de conformité (traçabilité).

## Business
- **Monétisation tardive** : E7 dès P1 (revenu avant produit complet).
- **Douve faible** : spécialisation CA + effets de données (benchmarks anonymisés) en P3.
- **Concentration client** : viser 5-10 conseillers en M6 (pas 1) ; éviter dépendance à un design partner unique.
- **Risque d'exécution solo** : contractualiser UX/mobile (E9) et revue sécurité (E1/E3) ; ne pas tout porter seul.

---

# 10. Classement ROI final

Top initiatives par `ROI = Impact² ÷ Effort` (P0/P1 priorisés ; les « quick wins » à fort ROI d'abord) :

| Rang | Initiative | Domaine | Imp | Eff | ROI | Prio |
|---|---|---|---|---|---|---|
| 1 | CSRF fail-closed (S1) | Sécurité | 5 | 1 | **25** | P0 |
| 2 | CORS fail-fast (S3) | Sécurité | 4 | 1 | **16** | P0 |
| 2 | Bêta réel (D2) | Données | 4 | 1 | **16** | P1 |
| 2 | Disclaimer inline verdict (U4) | UX/Conf. | 4 | 1 | **16** | P0 |
| 5 | ROIC déterministe (D1) | Données | 5 | 2 | **12** | P1 |
| 6 | Invalidation cache O(log n) (A4) | Archi | 3 | 1 | **9** | P1 |
| 6 | Trust-proxy rate-limit (S7) | Sécurité | 3 | 1 | **9** | P0 |
| 6 | Budget breaker (AI3) | IA | 3 | 1 | **9** | P1 |
| 6 | Rate-limit `validate_key` (S8) / PG secret (S10) | Sécurité | 3 | 1 | **9** | P0/P1 |
| 10 | RLS isolation (M2) | Multi-tenance | 5 | 3 | **8** | P0 |
| 10 | Alembic / fin migrations inline (A3) | Archi | 4 | 2 | **8** | P0 |
| 10 | Quotas + metering (M3/M4/B2) | Tenance/Business | 4 | 2 | **8** | P0/P1 |
| 10 | Chiffrement at-rest + logs (S4/S5) | Sécurité | 4 | 2 | **8** | P0 |
| 10 | Audit trail (S9) | Sécurité/Conf. | 4 | 2 | **8** | P1 |
| 10 | Macro vivante (D3) | Données | 4 | 2 | **8** | P1 |
| 10 | Garde-fous narratifs (AI1) | IA | 4 | 2 | **8** | P1 |
| 10 | Stripe + metering (B1) | Business | 5 | 3 | **8** | P1 |
| 10 | Conformité B2B (B5) | Business/Rég. | 5 | 3 | **8** | P0/P1 |
| 10 | Onboarding/landing (U1) | UX/Produit | 4 | 2 | **8** | P2 |
| 10 | API productisée (PR5) | Produit | 5 | 3 | **8** | P2 |
| 21 | `tenant_id` 6 tables (M1) | Multi-tenance | 5 | 4 | **6** | P0 |
| 21 | Data layer multi-fournisseurs (D4) | Données | 5 | 4 | **6** | P1 |
| 23 | Secteurs financiers (D6), Eval-gate (AI4), Mode simple/expert (U5), Mobile (U2), Point-in-time (D9), Scale (SC2/3) | divers | — | — | **5** | P1/P2 |

**Lecture VC** : les **4 premiers (ROI 16-25) sont des quick wins sécurité/données/conformité** (jours, pas mois) — à exécuter **immédiatement** (sprints 154-155). Les **fondations multi-tenance (ROI 6-8, P0)** sont moins « rentables » au ratio mais **stratégiquement non négociables** (sans elles, aucun revenu). C'est la nuance clé : **ROI ≠ priorité absolue** quand un item est un *bloqueur*.

---

# 11. Verdict investisseur

**Décision** : **GO conditionnel — financer la transformation, pas la société-en-l'état.**

- **Ce qu'on finance** : une équipe avec un **actif technique différenciant** (déterminisme auditable + niche fiscale CA) et un **marché B2B sous-servi** (conseillers/family offices canadiens), pour franchir le gouffre produit (multi-tenance → revenu → distribution).
- **Stade** : **pre-seed / SAFE** ou **bootstrap augmenté**. Pas de Série A tant que M6 (revenu) n'est pas atteint.
- **Cadre de valorisation** : aujourd'hui = *asset deal* (valeur du moteur + IP, pas du business). Re-rating à M6 (clients payants = preuve de willingness-to-pay) puis M12 (MRR + rétention = multiple SaaS).
- **Emploi des fonds (12 mois)** : ~60 % ingénierie (fondations P0/P1 + 1 contractuel UX/mobile), ~20 % conformité/juridique (avis fintech, Loi 25), ~20 % GTM design-partners conseillers.

**Portes go/no-go (KPIs)** :

| Jalon | KPI de passage | No-go si… |
|---|---|---|
| **M3** | Multi-tenance + RLS livrés, sécurité P0 fermée, isolation prouvée | Isolation non démontrée |
| **M6** | **≥ 3 conseillers payants**, 1ʳᵉ facture Stripe, NPS design-partners > 30 | 0 client payant |
| **M9** | API self-serve + white-label live, < 10 min time-to-first-analysis | Pas d'adoption self-serve |
| **M12** | **25-40 k$ MRR**, rétention logo > 85 %, p95 < 120 s | MRR < 10 k$ ou churn élevé |

**Risque principal** : **exécution solo** sur un périmètre large + **banalisation** par un acteur IA financé. Mitigation : séquencer revenu tôt (E7 en P1), spécialiser la douve (fiscalité CA + intégrations conseillers), contractualiser les épics hors-cœur.

**Verdict en une phrase** : *Le moteur vaut qu'on parie sur l'équipe ; le pari réussit si la multi-tenance et les 3 premiers clients conseillers arrivent en 6 mois — sinon, l'actif reste un excellent copilote personnel sans entreprise autour.*

---

*Toutes les faiblesses de l'audit sont couvertes (Architecture, Multi-tenance, Sécurité, Données, IA, UX/UI, Scalabilité, Produit, Business) avec Impact·Risque·Solution·ROI·Effort·Priorité·CA. Le backlog (sprints 154→185+) est aligné sur le workflow de sprint du projet et directement exécutable.*
