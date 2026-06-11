# Design — Découverte par catégorie pour débutants

> **Statut** : proposition de conception (design-first, aucun code écrit).
> **Périmètre du 1er lot** : 1 page « Découvrir » + 1 catégorie pilote **« Solides et stables »**.
> **Mécanisme** : hybride — suggestions précalculées (gratuit/instantané) + analyse approfondie live au clic.
> **Objectif** : permettre à un débutant d'explorer des actions de qualité **sans connaître aucun ticker**, avec pédagogie intégrée et un chemin progressif vers l'analyse avancée.

---

## 1. Principes directeurs

1. **Objectif avant jargon** — l'utilisateur choisit un *but* (« des placements solides et stables »), pas un framework ni un symbole.
2. **Qualité garantie en amont** — on ne montre que des titres qui passent un filtre qualité ; un débutant ne doit jamais tomber sur un piège.
3. **Divulgation progressive** — 3 niveaux (Débutant → Intermédiaire → Avancé). On ne submerge jamais ; on permet de creuser.
4. **Pédagogie permanente** — chaque terme financier est cliquable (tooltip + définition) ; le corpus RAG existant alimente les explications.
5. **Garde-fous responsables** — badges de risque, rappel de diversification, mention « ceci n'est pas un conseil financier », orientation par type de compte (CELI/REER).

---

## 2. Parcours utilisateur (débutant)

```
1. Arrivée → page « Découvrir » (nouvelle page d'accueil par défaut)
2. « Quel est ton objectif ? » → grille de cartes-catégories en langage simple
3. Clic sur « 🟢 Solides et stables »
   → affichage INSTANTANÉ de 8 titres de qualité (données précalculées, gratuit)
   → chaque titre : nom, badge risque, « pourquoi », 1 ratio clé vulgarisé
4. Clic sur un titre (ex. « Banque Royale »)
   → fiche niveau Débutant : pourquoi c'est solide, risque, « bon pour ton CELI ? »
   → bouton « Analyse approfondie » → lance l'analyse complète LIVE (multi-frameworks)
5. À tout moment : tooltip sur un terme → définition + « en savoir plus »
6. Bascule « mode Avancé » dans l'en-tête → débloque ratios, workflows, DCF
```

**Trois portes d'entrée, une seule destination (l'analyse) :**

| Profil | Entrée | Aujourd'hui |
|---|---|---|
| Débutant | Catégorie → suggestion → fiche simple | ❌ n'existe pas |
| Intermédiaire | Catégorie → fiche → ratios décomposés | ⚠️ partiel |
| Avancé | Ticker direct ou screener | ✅ existe (`AnalyzeForm`, `ScreenerPage`) |

---

## 3. Wireframes (ASCII)

### 3.1 Page « Découvrir » (accueil)

```
┌──────────────────────────────────────────────────────────────┐
│  TradingClaude        Découvrir  Screener  Historique   [Déb.▾]│  ← bascule mode
├──────────────────────────────────────────────────────────────┤
│                                                                │
│   👋 Bienvenue. Quel est ton objectif d'investissement ?       │
│                                                                │
│   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│   │ 🟢             │  │ 🟢             │  │ 🟡             │  │
│   │ Solides &      │  │ Pour démarrer  │  │ Croissance     │  │
│   │ stables        │  │ (ETF)          │  │ de qualité     │  │
│   │                │  │                │  │                │  │
│   │ Banques &      │  │ Paniers        │  │ Entreprises    │  │
│   │ dividendes     │  │ diversifiés    │  │ qui grandissent│  │
│   │ canadiens      │  │ clé en main    │  │ (+ de risque)  │  │
│   │ Risque: faible │  │ Risque: faible │  │ Risque: moyen  │  │
│   └────────────────┘  └────────────────┘  └────────────────┘  │
│         ▲ catégorie pilote du 1er lot                          │
│                                                                │
│   💡 Nouveau ? Commence par « Pour démarrer (ETF) » →          │
│   📚 Pas sûr d'un mot ? Tout est expliqué en cliquant dessus.  │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Vue catégorie « Solides et stables » (suggestions précalculées)

```
┌──────────────────────────────────────────────────────────────┐
│  ← Retour        🟢 Solides et stables                          │
├──────────────────────────────────────────────────────────────┤
│  Des entreprises établies, rentables depuis des années, qui    │
│  versent souvent un dividende régulier. Moins de surprises —   │
│  le point de départ classique d'un portefeuille prudent.       │
│  ⓘ Risque faible · Mis à jour le 11 juin · 8 titres de qualité│
│                                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 🟢 Banque Royale (RY.TO)              Qualité: FORT 78  │  │
│  │ Plus grande banque du Canada, dividende versé depuis    │  │
│  │ 150 ans. Rendement du dividende ⓘ : 4,1 %               │  │
│  │                                  [ Voir la fiche → ]    │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ 🟢 Banque TD (TD.TO)                  Qualité: FORT 74  │  │
│  │ ...                                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                │
│  📚 « Qu'est-ce qu'un dividende ? » · « C'est quoi un score    │
│      de qualité ? » · « Faut-il diversifier ? »                │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Fiche titre — niveau Débutant

```
┌──────────────────────────────────────────────────────────────┐
│  ← Solides et stables    Banque Royale (RY.TO)      🟢 FORT 78 │
├──────────────────────────────────────────────────────────────┤
│  💬 POURQUOI ON LA SUGGÈRE                                      │
│  Grande banque rentable et stable, dividende fiable. Bilan     │
│  jugé sain par nos filtres de qualité. Peu volatile.           │
│                                                                │
│  ⚠️ À GARDER EN TÊTE                                            │
│  Le secteur bancaire suit l'économie : en récession, le cours  │
│  peut baisser. Aucun placement n'est sans risque.              │
│                                                                │
│  🏦 BON POUR QUEL COMPTE ?                                      │
│  Dividende canadien → avantageux en CELI ou compte non         │
│  enregistré (crédit d'impôt pour dividendes). ⓘ                │
│                                                                │
│  📊 EN UN COUP D'ŒIL          [ tooltips sur chaque ligne ]    │
│  Prix          82,40 $                                          │
│  Dividende ⓘ   4,1 % par an                                    │
│  Qualité ⓘ     FORT (78/100)                                   │
│  P/E ⓘ         11,2  (← « combien on paie pour 1$ de profit »)│
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │   🔬 Analyse approfondie (live, ~30s)                 │    │  ← déclenche /analyze
│  │   12 angles d'experts : Graham, Buffett, valorisation │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 3.4 Tooltip / glossaire (overlay)

```
        P/E ⓘ ← survol/clic
        ┌─────────────────────────────────────────┐
        │ Ratio cours/bénéfice (P/E)              │
        │ Combien tu paies pour 1 $ de profit     │
        │ annuel. P/E de 11 = tu paies 11 $ pour  │
        │ 1 $ de bénéfice. Plus bas = moins cher  │
        │ (à qualité égale).                      │
        │                         [ En savoir + ] │ → /semantic-search
        └─────────────────────────────────────────┘
```

---

## 4. Spécification — catégorie pilote « Solides et stables »

### 4.1 Définition produit
Entreprises **établies, rentables et peu volatiles**, versant souvent un dividende régulier. Cible : rassurer le débutant avec des noms connus et un profil de risque faible.

### 4.2 Univers de départ (TSX, suffixe `.TO`)
Banques canadiennes + « stalwarts » à dividende défensif :
```
RY.TO, TD.TO, BNS.TO, BMO.TO, CM.TO, NA.TO      (banques)
BCE.TO, T.TO                                     (télécom)
ENB.TO, TRP.TO                                   (pipelines)
FTS.TO, EMA.TO                                   (services publics)
CNR.TO, CP.TO                                    (rail)
```
> Stocké dans une config dédiée, sur le modèle de `.claude/skills/graham-screener/assets/universes.json`.

### 4.3 Filtre qualité (sector-aware — point important)
Les 7 critères Graham **ne s'appliquent pas tels quels aux banques** (`current_ratio` nul est normal — cf. `.claude/rules/donnees-financieres.md`). Pour cette catégorie, le gate s'appuie sur :
- **`composite_score` ≥ MODÉRÉ (45)** (combine déjà graham/buffett/valuation/moat/earnings/marks — `app/services/composite_score.py`),
- **`earnings_quality.verdict ≠ REJETER`** (pas de risque de faillite/manipulation),
- **dividende présent et historiquement régulier** (proxy de stabilité),
- exclusion si `partial_data = true` (données trop incomplètes pour suggérer à un débutant).

Tri d'affichage : `composite_score` décroissant, plafonné à 8 titres.

### 4.4 Badge de risque (🟢/🟡/🔴)
Dérivé de façon déterministe :
- 🟢 **faible** : composite FORT/MODÉRÉ **et** secteur défensif (banque/utilities/télécom/rail) **et** faible volatilité.
- 🟡 **moyen** : composite MODÉRÉ hors secteur défensif, ou volatilité plus élevée.
- 🔴 **élevé** : composite FAIBLE ou drapeau rouge `earnings_quality`. *(En principe filtré en amont pour cette catégorie.)*

### 4.5 Phrase « pourquoi » (1 ligne)
Deux options à trancher (voir §8) :
- **(a) Template déterministe** depuis les scores (gratuit, instantané) — ex. « Grande banque rentable, dividende fiable, bilan jugé sain. »
- **(b) Résumé Haiku mis en cache** lors du rafraîchissement batch (~0,001 $/titre, plus naturel).

---

## 5. Architecture technique — mécanisme hybride

### 5.1 Vue d'ensemble
```
   ┌─────────────── COUCHE PRÉCALCULÉE (gratuit, instantané) ───────────────┐
   │  Celery beat (hebdo, réutilise le pattern run_scheduled_screener)        │
   │     → pour chaque catégorie : univers → ScreenerService.screen()         │
   │       + composite_score + gate qualité + badge risque + phrase « pourquoi»│
   │     → persiste dans `discovery_suggestions` (table) ou cache Redis        │
   └───────────────────────────────┬─────────────────────────────────────────┘
                                    │  GET /discovery/{category}  (lecture seule, rapide)
                                    ▼
   ┌──────────────────────── FRONTEND DiscoveryPage ─────────────────────────┐
   │  cartes catégories → liste suggestions → fiche débutant                  │
   └───────────────────────────────┬─────────────────────────────────────────┘
                                    │  clic « Analyse approfondie »
                                    ▼
   ┌─────────────── COUCHE LIVE (à la demande, coût Claude) ──────────────────┐
   │  POST /analyze (workflow adapté débutant) → analyse multi-frameworks      │
   │  GET /semantic-search → explications pédagogiques inline                  │
   └──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Nouveaux composants à créer
| Composant | Type | Rôle | Réutilise |
|---|---|---|---|
| `app/config/discovery_categories.json` | Data | Catégories : univers, libellés FR, gate, pédagogie | pattern `universes.json` |
| `app/services/discovery_service.py` | Backend | Calcule/sert les suggestions par catégorie | `ScreenerService`, `composite_score` |
| Table `discovery_suggestions` (ou cache Redis) | DB | Stocke le résultat précalculé + `as_of` | migration Alembic |
| `app/workers/tasks.py` → `refresh_discovery` | Worker | Rafraîchit périodiquement (Celery beat) | pattern `run_scheduled_screener` |
| `app/api/endpoints/discovery.py` | Backend | `GET /discovery/categories`, `GET /discovery/{category}` | schemas Pydantic |
| `frontend/src/pages/DiscoveryPage.tsx` | Frontend | Page découverte | `Card`, `Badge`, `ScreenerTable` |
| `frontend/src/components/CategoryCard.tsx`, `SuggestionCard.tsx` | Frontend | Cartes | composants `ui/` |
| `frontend/src/components/Glossary.tsx` + `glossary.json` | Frontend | Tooltips pédagogiques | `/semantic-search` pour « en savoir + » |

### 5.3 Réutilisé tel quel (zéro réécriture)
`ScreenerService.screen()` · `composite_score` · batch `graham-screener` + collection `graham_screening` · `/semantic-search` (corpus `investment_knowledge`) · skill `canadian_tax` (orientation compte) · `POST /analyze` (analyse approfondie live) · catégories `lynch_categories` (pour les futures catégories croissance).

### 5.4 Schéma d'un item de suggestion (contrat API)
```jsonc
{
  "ticker": "RY.TO",
  "name": "Banque Royale du Canada",
  "composite_score": 78,
  "composite_label": "FORT",
  "risk_badge": "faible",          // faible | moyen | élevé
  "why": "Grande banque rentable, dividende fiable, bilan jugé sain.",
  "dividend_yield": 0.041,
  "pe": 11.2,
  "price": 82.40,
  "account_hint": "CELI",          // issu de la logique canadian_tax
  "as_of": "2026-06-11"
}
```

---

## 6. Couche pédagogique

| Élément | Source | Mécanisme |
|---|---|---|
| **Tooltips de termes** | `glossary.json` (statique, ~30 termes : P/E, dividende, ROE, volatilité, CELI…) | survol/clic inline, gratuit |
| **« En savoir plus »** | corpus RAG `references/*.md` via `GET /semantic-search` | à la demande |
| **Mini-leçons** | sélection vulgarisée du corpus | page « Apprendre » (lot ultérieur) |
| **Explication des scores** | texte produit fixe (« FORT = passe la majorité des filtres ») | inline |

> Le corpus `.claude/skills/*/references/` est déjà riche (~68 fichiers) — il sert de source unique de vérité pédagogique, pas de contenu réinventé.

---

## 7. Garde-fous responsables (non négociables)

- Bandeau permanent discret : **« Outil d'aide à la décision — ceci n'est pas un conseil financier. »**
- **Badge de risque** visible sur chaque suggestion et chaque fiche.
- **Rappel de diversification** dans chaque catégorie (« ne mets pas tout sur un seul titre »).
- Pour un vrai débutant, **mise en avant de la catégorie ETF** comme point de départ recommandé.
- Aucune formulation impérative (« achète »), toujours « à étudier / à considérer ».

---

## 8. Décisions ouvertes (à trancher avant implémentation)

1. **Phrase « pourquoi »** : template déterministe (gratuit) vs résumé Haiku mis en cache (plus naturel, ~0,001 $/titre) ? → *recommandation : template au 1er lot, Haiku ensuite.*
2. **Stockage précalculé** : table Postgres `discovery_suggestions` (historisable, requêtable) vs cache Redis (plus simple, volatil) ? → *recommandation : table (cohérent avec `analysis_history`).*
3. **Données dividende / volatilité** : disponibles via yfinance `info` ? sinon proxy à définir. → à confirmer côté tier1.
4. **Page d'accueil par défaut** : « Découvrir » remplace-t-elle l'accueil actuel, ou s'ajoute-t-elle au menu ?
5. **Workflow de l'analyse approfondie depuis une fiche débutant** : `value_graham` (5 steps, bien documenté) recommandé plutôt que `compounder_buffett` (10 steps, lourd).

---

## 9. Plan d'implémentation (après validation du design)

**Phase 1 — Backend découverte (catégorie pilote)**
1. `discovery_categories.json` (catégorie « Solides et stables » + univers).
2. `discovery_service.py` : gate qualité sector-aware + badge risque + phrase « pourquoi » (template).
3. Table `discovery_suggestions` + migration Alembic.
4. `GET /discovery/categories` + `GET /discovery/{category}` + schemas + tests (pyramide).

**Phase 2 — Rafraîchissement automatique**
5. Tâche Celery `refresh_discovery` + entrée beat (réutilise le pattern existant).

**Phase 3 — Frontend découverte**
6. `DiscoveryPage` + `CategoryCard` + `SuggestionCard` + client API typé + tests Vitest.
7. Fiche titre niveau Débutant + bouton « Analyse approfondie » (branché sur `/analyze`).

**Phase 4 — Pédagogie**
8. `glossary.json` + composant `Glossary` (tooltips) + « en savoir plus » via `/semantic-search`.
9. Bascule mode Débutant/Avancé.

**Phase 5 — Élargissement**
10. Catégories suivantes (ETF, Croissance de qualité, Ce que je connais) en réutilisant le même cadre.

---

*Fin du document de conception. Aucun code n'a été écrit. Prochaine étape : validation, puis Phase 1.*
