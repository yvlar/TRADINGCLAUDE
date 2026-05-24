---
name: esg-simplified
description: Évalue 15 critères ESG (5E + 5S + 5G) via des proxies financiers disponibles — sans accès à des fournisseurs ESG externes (MSCI, Sustainalytics). Produit un score 0-15, un verdict ESG_FORT/ESG_MODERE/ESG_FAIBLE, et des limites honnêtes. À utiliser dès que l'utilisateur mentionne ESG, critères extra-financiers, Environnement/Social/Gouvernance, notation ESG, durabilité d'entreprise, ou veut intégrer une dimension ESG dans une analyse de portefeuille. Utilise toujours ce skill avant d'inclure une dimension ESG dans une analyse d'investissement responsable ou de screener.
---

# ESG Simplifié — Notation par Proxy Financier

Évalue 15 critères ESG répartis en 3 dimensions — Environnement (E), Social (S), Gouvernance (G) — à partir
de données financières standard disponibles dans Yahoo Finance ou les rapports annuels. **Aucune base ESG externe requise.**

Code API : `esg_simplified` | Tier : 2 | Modèle : Sonnet (défaut)

## Principe fondamental

Les données financières révèlent des comportements ESG indirects :

| Donnée financière | Proxy ESG |
|---|---|
| ROE élevé et stable | Efficience des ressources (E) + discipline de gouvernance (G) |
| Faible dette/capitaux propres | Prudence environnementale (E) + protection des emplois (S) |
| Dividendes versés 20+ ans consécutifs | Stabilité des parties prenantes (S/G) |
| Revenus ≥ 5 Md$ | Ressources disponibles pour programmes sociaux (S) |
| BPA croissant sur 10 ans | Croissance inclusive et gouvernance long terme (S/G) |

L'approche est transparente : ses limites sont documentées dans chaque analyse.

## Données d'entrée (EsgInput)

| Champ | Type | Usage |
|---|---|---|
| `ticker` | `str` | Identifiant obligatoire |
| `sector` | `str \| None` | Ajustements sectoriels (banques, énergie, utilities) |
| `revenue_bn` | `float \| None` | Revenus en milliards — proxy taille S et E |
| `roe` | `float \| None` | Return on Equity (fraction : 0.15 = 15%) |
| `debt_equity` | `float \| None` | Dette totale / Capitaux propres |
| `dividend_years` | `int \| None` | Années consécutives de dividendes versés |
| `eps_growth_10y` | `float \| None` | Croissance totale BPA sur 10 ans (0.85 = 85%) |

## Workflow d'évaluation

### Étape 1 — Identification sectorielle

Adapter les seuils selon le secteur :

| Secteur | Ajustements |
|---|---|
| Banques / Assurances | `current_ratio` non applicable ; E3 (dette) → passe=True systématique |
| Énergie / Mines | Seuil E1 (ROE) abaissé à 8% ; impact environnemental inhérent — standards E plus stricts |
| Utilities | Transition énergétique centrale pour E ; seuil ROE abaissé à 8% |
| Technologie | Faible empreinte physique — standards E plus flexibles ; seuil ROE relevé à 15% |
| Consommation | Chaîne d'approvisionnement = enjeu S central |

### Étape 2 — Évaluation des 15 critères

Pour chaque critère (voir `references/criteres-dimension-E.md`, `S.md`, `G.md`) :
1. Identifier le proxy utilisé
2. Vérifier la disponibilité de la donnée
3. Appliquer le seuil (ajusté sectoriellement si nécessaire)
4. Documenter l'observation factuelle (1-2 phrases)
5. Si données absentes → `passe=False` + observation "Données indisponibles — proxy non calculable"
   (exception : absence normale par secteur → `passe=True` avec explication)

### Étape 3 — Calcul des scores et verdict

```
e_score = nombre de critères E avec passe=True  (0-5)
s_score = nombre de critères S avec passe=True  (0-5)
g_score = nombre de critères G avec passe=True  (0-5)
esg_score = e_score + s_score + g_score          (0-15)
```

Verdict (voir `references/scoring-verdicts.md`) :
- `ESG_FORT` : esg_score ≥ 10
- `ESG_MODERE` : esg_score entre 5 et 9
- `ESG_FAIBLE` : esg_score ≤ 4

### Étape 4 — Limites obligatoires (3-5 points)

Toujours documenter dans `limites` :
- La nature proxy de l'analyse (pas de données ESG directes)
- Les données manquantes et leur impact sur le score
- Les spécificités sectorielles non capturées
- Recommandation de croiser avec MSCI, Sustainalytics pour décisions significatives

## Structure de sortie (EsgOutput)

| Champ | Type | Description |
|---|---|---|
| `ticker` | `str` | Ticker analysé |
| `esg_score` | `int` (0-15) | Score global — somme des 15 critères passés |
| `e_score` | `int` (0-5) | Score Environnement |
| `s_score` | `int` (0-5) | Score Social |
| `g_score` | `int` (0-5) | Score Gouvernance |
| `criteres` | `list[EsgCritere]` | Exactement 15 critères (5E + 5S + 5G) |
| `verdict` | `Literal` | `ESG_FORT` / `ESG_MODERE` / `ESG_FAIBLE` |
| `verdict_detail` | `str` | Narrative 2-3 phrases contextualisant le score |
| `limites` | `list[str]` | Limites honnêtes de l'analyse par proxy |
| `citations` | `list[Citation]` | Citations RAG — vide si OPENAI_API_KEY absente |
| `cost_usd` | `float` | Coût API Claude en USD |

Chaque `EsgCritere` contient : `dimension`, `nom`, `passe`, `observation`, `proxy_utilise`.

## Validation Pydantic automatique

Le `model_validator` dans `EsgOutput` corrige silencieusement les sous-scores si Claude retourne
des valeurs inconsistantes, et rejette tout output avec ≠ 15 critères ou ≠ 5 critères par dimension.

## Garde-fous

- **Ce skill est un proxy, pas une évaluation ESG primaire.** Ne jamais présenter ce score comme équivalent à une notation MSCI ou Sustainalytics.
- **Ajustement sectoriel obligatoire.** Un score faible pour une banque sur E3 (dette) sans ajustement invalide l'analyse.
- **Données absentes ≠ ESG mauvais.** Un champ absent réduit mécaniquement le score — documenter l'impact dans `limites`.
- **Cohérence avec les autres skills.** L'ESG est complémentaire à `buffett_quality`, `dorsey_moat`, `graham_analysis` — pas un filtre éliminatoire autonome.

## Références

- `references/esg-proxies-rationale.md` — Justification académique de l'approche proxy
- `references/criteres-dimension-E.md` — 5 critères Environnement avec formules et seuils
- `references/criteres-dimension-S.md` — 5 critères Social
- `references/criteres-dimension-G.md` — 5 critères Gouvernance
- `references/scoring-verdicts.md` — Barème, exemples chiffrés, ajustements sectoriels
