# stock-valuation-triangulation

Valorisation multi-méthodes (DCF + comparables + sectoriel) avec triangulation pour réduire l'incertitude d'une seule estimation.

## À quoi ça sert

Une seule méthode de valorisation a une marge d'erreur de 20-50 %. La **triangulation** combine 3 méthodes indépendantes :

1. **DCF (Discounted Cash Flow)** : projection des FCF + valeur terminale, discountés au WACC
2. **Comparables** : multiples de pairs (P/E, EV/EBITDA, EV/Sales)
3. **Sectoriel** : méthode appropriée au secteur (NAV pour REITs, P/B pour banques, etc.)

La médiane des 3 estimations sert de **valeur intrinsèque centrale** ; la dispersion révèle l'incertitude.

## Quand l'utiliser

- "DCF de Microsoft à 8 % WACC ?"
- "Compare Apple à ses peers (META, GOOGL, MSFT)"
- "Quelle valeur intrinsèque pour BCE ?"
- Pour toute position avant achat, surtout > 3 % du portfolio

## Quand ne pas l'utiliser

- Pour les actifs sans cash flows (Bitcoin, NFTs) — Damodaran recommande ne pas valoriser
- Pour les biotechs pre-revenue — méthode d'option requise
- Pour les special situations très complexes — voir Klarman/Greenblatt

## Composants

```
stock-valuation-triangulation/
├── SKILL.md
├── references/
│   ├── dcf.md                  ← Méthode classique 2 phases
│   ├── comparables.md          ← Sélection peers, multiples
│   └── sectoriel.md            ← REITs (NAV), banques (P/B), assurance, ressources
├── scripts/
│   ├── dcf_simple.py           ← DCF avec WACC, g, période explicite
│   ├── comparables.py          ← Median peer multiples × metrics actuels
│   ├── triangulation.py        ← Combine les 3 méthodes
│   └── nav_reit.py             ← Spécifique REITs (NOI / cap rate)
└── evals/
    ├── evals.json
    ├── test_apple_dcf.json     ← Apple FY2023, DCF = 121
    ├── test_apple_comp.json    ← Apple peers, comp = 177
    └── test_apple_tri.json     ← Triangulation = 147 (vs marché 175)
```

## Méthodes selon le type d'entreprise

| Type d'entreprise | Méthode dominante | Méthodes secondaires |
|-------------------|-------------------|----------------------|
| Compounder mature | DCF + comparables | Sectoriel si applicable |
| Cyclique au creux | Earnings normalisés × P/E historique | Comparables au sommet |
| Banque | P/B × ROE / cost of equity | DCF dividend discount |
| REIT | NAV (NOI / cap rate) | FFO multiple |
| Assurance | P/B + IFRS 17 considerations | DCF dividend |
| Resources | Coûts marginaux + LT prix | EV/Réserves |
| SaaS | DCF avec paths réalistes | EV/Sales sur growth path |

## Exemples d'utilisation

### Via prompt

> "Triangule la valeur intrinsèque d'Apple en utilisant DCF, comparables tech mega-caps, et un sanity check"

### Via script direct

```bash
cd stock-valuation-triangulation
python scripts/dcf_simple.py evals/test_apple_dcf.json
python scripts/comparables.py evals/test_apple_comp.json
python scripts/triangulation.py evals/test_apple_tri.json
```

Output Apple :
```
DCF (2-phase, 5%g 10ans, 2.5%g terminal) : 121 USD
Comparables (mega-cap tech median)        : 177 USD
Sectoriel (consumer ecosystem premium)    : 142 USD
─────────────────────────────────────────
Médiane triangulée                        : 147 USD
Prix marché                               : 175 USD

Marge actuelle : -19% (acheter 25% sous médiane = sous 110)
```

## DCF — paramètres clés

```python
{
  "free_cash_flows": [...],      # 5-10 ans projetés
  "growth_rate_terminal": 0.025, # 2.5% typique
  "wacc": 0.085,                 # ajuster selon entreprise
  "shares_outstanding": ...,
  "net_debt": ...
}
```

WACC typiques par secteur (référentiel approximatif 2026) :
- Mega-cap tech : 8-9 %
- Banques canadiennes : 9-10 %
- Utilities régulées : 6-7 %
- Compagnies aériennes : 11-13 %
- REITs : 6-8 %

## Triangulation — interprétation de la dispersion

| Dispersion (P10-P90) / Médiane | Interprétation |
|--------------------------------|----------------|
| < 20 % | Valeur **fiable**, position normale possible |
| 20-50 % | Incertitude **modérée**, marge de sécurité accrue |
| > 50 % | Valeur **non fiable**, refuser ou méthode différente |

Si la dispersion est énorme, c'est typiquement parce qu'une méthode n'est pas applicable correctement.

## Ce qu'il ne fait pas

- Ne valorise pas les pre-revenue companies (utiliser story stocks chez Damodaran)
- Ne capture pas les options réelles (R&D, expansion géographique)
- Ne remplace pas l'analyse de moat (ROIC du DCF présume moat)

## Garde-fous

- Le **terminal value** représente typiquement 60-80 % de l'EV — sensibilité énorme aux paramètres terminaux
- Les comparables exigent des peers vraiment comparables (taille, géographie, business model)
- Le DCF "garbage in garbage out" — vérifier la cohérence dynamique (croiser avec damodaran)
- WACC sous-estimé = sur-valorisation systématique. Appliquer le test de sensibilité ±1 %

## Voir aussi

- [damodaran-narrative-and-numbers](../damodaran-narrative-and-numbers/) — cohérence dynamique du DCF, ERP
- [klarman-margin-of-safety](../klarman-margin-of-safety/) — quelle marge exiger sur la valeur triangulée
- [buffett-quality-investing](../buffett-quality-investing/) — owner earnings comme alternative au FCF standard
