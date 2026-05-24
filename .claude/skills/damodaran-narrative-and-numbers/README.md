# damodaran-narrative-and-numbers

Méthode Aswath Damodaran (NYU Stern) — alignement entre **narrative (story)** et **numbers (modèle)**, valorisation rigoureuse pour story stocks et entreprises en transformation.

## À quoi ça sert

Aswath Damodaran (Professor of Finance, NYU Stern) a popularisé l'idée que **toute valorisation est une histoire racontée en chiffres**. Si l'histoire et les chiffres ne s'alignent pas, la valorisation est fausse.

Trois outils principaux :

1. **Test possible / plausible / probable** — filtre la qualité d'une story
2. **DCF en 2 phases** pour story stocks (croissance haute → état stable)
3. **Cohérence dynamique** — vérifier que `g = ROIC × Reinvestment` tient

Plus l'**Equity Risk Premium** (ERP) calculé mensuellement par Damodaran et le **country risk premium**.

## Quand l'utiliser

- "Snowflake mérite-t-il sa valorisation ?" (story stock)
- "Mon DCF donne ROIC implicite 60 %, c'est cohérent ?"
- "Country risk premium pour le Brésil ?"
- "Tesla story possible / plausible / probable ?"
- Pour valoriser une entreprise non rentable mais à fort potentiel

## Quand ne pas l'utiliser

- Pour les actifs sans cash flows — Bitcoin/crypto/NFTs ne se valorisent pas selon Damodaran
- Pour les compounders matures simples — le DCF classique de `stock-valuation-triangulation` suffit

## Composants

```
damodaran-narrative-and-numbers/
├── SKILL.md
├── references/
│   ├── test-narrative.md           ← Possible / Plausible / Probable
│   ├── valorisation-story-stocks.md ← DCF 2-phase, transition, terminal
│   ├── coherence-dynamique.md      ← g = ROIC × Reinvestment, validation
│   └── erp-country-risk.md         ← ERP US 4.23%, country risk par pays
├── scripts/
│   ├── dcf_story.py                ← DCF avec paths année par année
│   └── check_coherence.py          ← Validation cohérence
└── evals/
    ├── evals.json
    ├── test_saas.json              ← SaaS pre-profit, EV 36 USD à 75% survie
    └── test_coherence_failed.json  ← Cas où g/r implique ROIC absurde
```

## Test possible / plausible / probable

| Niveau | Question | Décision |
|--------|----------|----------|
| **Possible** | Cela peut-il arriver sans violer la physique/math ? | Trop bas pour investir |
| **Plausible** | C'est arrivé pour des cas comparables ? | Peut justifier petite spéculation |
| **Probable** | C'est plus probable qu'improbable pour cette entreprise ? | Investissement justifié |

**Investir uniquement sur "probable"**, pas sur "possible" ou "plausible".

## ERP et Country Risk (référentiel début 2026)

⚠️ Vérifier valeurs courantes via web_search sur pages.stern.nyu.edu/~adamodar/

| Pays | ERP base | Country risk premium |
|------|----------|----------------------|
| US | 4.23 % | 0 |
| Canada | 4.23 % | 0 |
| France, UK | 4.23 % | 0-0.5 % |
| Brésil | 4.23 % | 2.85 % |
| Inde | 4.23 % | 1.5 % |
| Argentine | 4.23 % | 12.4 % |

## Exemples d'utilisation

### Via prompt

> "Valorise un SaaS hypothétique avec croissance 45% an 1, marges qui passent de -10% à +22% sur 10 ans, 75% probabilité de survie"

### Via script direct

```bash
cd damodaran-narrative-and-numbers
python scripts/dcf_story.py evals/test_saas.json
```

Output :
```
DCF DEUX PHASES — SAASCO
Année 1 : revenu 2900, croiss 45%, marge -10%, EBIT -290, FCF -290
Année 2 : revenu 4060, croiss 40%, marge -2%, FCF -81
...
Année 10 : revenu 12988, marge 22%, FCF 1822

PV flows phase 1     : 3426
PV valeur terminale  : 11080 (76% EV — sensible)
Enterprise value     : 14506

Valeur/action si SUCCÈS    : 45.73 USD
Probabilité de survie      : 75%
Valeur/action ESPÉRÉE      : 36.30 USD
```

### Test cohérence dynamique

```bash
python scripts/check_coherence.py --growth 25 --reinv 40 --industry-roic-leader 25
```

Output :
```
ROIC implicite: 62.5%
❌ ROIC implicite > leader sectoriel + 10pts
❌ ROIC > 50% est rarement atteint

→ MODÈLE CASSÉ. Réviser g, reinvestment, ou marges.
```

## Cohérence dynamique — règle fondamentale

```
Croissance soutenable = ROIC × Taux de réinvestissement
```

Si tu projettes 25 % de croissance avec 40 % de réinvestissement, ROIC implicite = 62.5 %. Au-delà des leaders sectoriels = **modèle incohérent**.

| ROIC implicite | Durabilité maximale |
|----------------|---------------------|
| < 15 % | Acceptable long-terme |
| 15-20 % | Acceptable pour leaders avec moat |
| 20-30 % | 7-10 ans max |
| 30-50 % | 5-7 ans max |
| > 50 % | Quasi-impossible à maintenir |

## Probabilité de survie

Pour les story stocks, ajouter explicitement :

```
EV = P(succès) × Valeur_si_succès + P(échec) × Valeur_si_échec
```

Pour SaaS : 70-80 % typique
Pour biotech early-stage : 20-40 %
Pour distressed turnaround : 30-50 %

## Ce qu'il ne fait pas

- Ne valorise pas les actifs sans cash flows (crypto, NFTs)
- Ne fait pas Monte Carlo automatique (mais le `dcf_story.py` permet sensitivity)
- Ne remplace pas l'analyse fondamentale du moat

## Garde-fous

- Story stocks ont des **fourchettes énormes** (P10 à P90 souvent 50-200 % du prix de marché)
- Le terminal value est **sensible** aux paramètres terminaux (g_term, ROIC_term)
- L'ERP varie 1-2 % selon les conditions de marché — recalculer trimestriellement
- Damodaran lui-même se trompe (sous-estimait Tesla pendant des années)

## Voir aussi

- [stock-valuation-triangulation](../stock-valuation-triangulation/) — DCF classique pour entreprises matures
- [lynch-categories-and-tenbaggers](../lynch-categories-and-tenbaggers/) — story stocks = fast growers Lynch
- [klarman-margin-of-safety](../klarman-margin-of-safety/) — marge requise pour story stocks (50%+)
- Site Damodaran : pages.stern.nyu.edu/~adamodar/
