# buffett-quality-investing

Cadre Warren Buffett — 4 filtres séquentiels, owner earnings, "wonderful businesses at fair prices" (évolution de Graham vers Buffett-Munger).

## À quoi ça sert

Warren Buffett (Berkshire Hathaway, 1965-présent, +20 % CAGR sur 60 ans) applique systématiquement 4 filtres :

1. **Cercle de compétence** : "a business we understand"
2. **Économie long-terme favorable** : moat durable + ROIC élevé
3. **Direction compétente et intègre** : capital allocator + transparence
4. **Prix sensible** : pas de discount Graham 50%, mais pas n'importe quel prix

Plus le concept central des **owner earnings** (Net Income + D&A − maintenance capex), version Buffett du cash flow disponible pour les actionnaires, plus précise que FCF standard.

## Quand l'utiliser

- "Apple est-elle une wonderful business à 200 USD ?"
- "Calcule les owner earnings de Coca-Cola"
- "Comment Buffett évalue la qualité d'un capital allocator ?"
- "Évolution Graham → Buffett-Munger ?"
- Pour toute analyse long-terme d'un compounder potentiel

## Quand ne pas l'utiliser

- Pour les pre-revenue companies (filtre 1 cercle de compétence)
- Pour les special situations / distressed (utiliser Klarman/Greenblatt)
- Pour les positions court-terme

## Composants

```
buffett-quality-investing/
├── SKILL.md
├── references/
│   ├── 4-filtres-buffett.md            ← Détail des 4 filtres séquentiels
│   ├── owner-earnings.md               ← Formule + ajustements + SBC treatment
│   ├── evolution-graham-buffett.md     ← Cigar butts → wonderful businesses
│   └── annual-letters.md               ← Lecture des Berkshire letters 60 ans
├── scripts/
│   ├── buffett_quality_score.py        ← 6 critères quantitatifs
│   └── owner_earnings.py               ← Calcul + yield + verdict
└── evals/
    ├── evals.json
    ├── test_apple_quality.json         ← AAPL 5/6 (proche quality)
    └── test_apple_oe.json              ← AAPL OE 100 G$, yield 3.3% (cher)
```

## Les 4 filtres (séquentiels)

### Filtre 1 — Cercle de compétence
Test : peux-tu écrire en 5 phrases comment l'entreprise gagne de l'argent + 3 facteurs critiques + 3 risques ? Si non, **passer**.

### Filtre 2 — Économie long-terme favorable
- ROIC > 15 % moyenne 10 ans (et > WACC chaque année)
- Marges brutes stables ou en amélioration
- FCF / Revenus ≥ 15 %
- Capex de maintenance modeste

### Filtre 3 — Direction compétente et intègre
- Allocation de capital exemplaire (track record acquisitions, buybacks au bon prix)
- Communication transparente (lettres aux actionnaires admettant erreurs)
- Compensation modeste vs création de valeur
- Croiser avec [fisher-scuttlebutt](../fisher-scuttlebutt/) (15 points)

### Filtre 4 — Prix sensible
Pour Buffett 2.0 : pas de discount Graham, mais **toujours un prix**. Un compounder à 50× P/E reste un mauvais investissement.

## Owner Earnings — la formule clé

```
Owner Earnings = Net Income
              + Depreciation, Depletion, Amortization (non-cash)
              + Other non-cash charges
              − Maintenance Capex
              ± Changes in Working Capital
```

Différence cruciale vs FCF standard : on déduit uniquement le **capex de maintenance**, pas le capex de croissance (qui crée de la valeur future).

## Exemples d'utilisation

### Via prompt

> "Apple FY2023 — passe-t-elle les 4 filtres Buffett au prix actuel de 200 USD ?"

### Via script direct

```bash
cd buffett-quality-investing
python scripts/buffett_quality_score.py evals/test_apple_quality.json
python scripts/owner_earnings.py evals/test_apple_oe.json
```

Output Apple :
```
BUFFETT QUALITY SCORE — AAPL
ROIC moyen 10 ans : 38.3% ✓
ROIC stable : CV 0.23 (légèrement volatil ✗)
Marges brutes : +6 pts sur 5 ans ✓
FCF/Revenue : 24.8% ✓
Capex/D&A : 0.91× ✓
SBC : 2.8% du revenu ✓

Score : 5/6
🟡 PROCHE QUALITY

OWNER EARNINGS — AAPL FY2023
NI 96995 + D&A 11519 − Capex maint 9000 = 100014 M$
Owner Earnings yield : 3.3%
🔴 CHER (yield < 4%)
```

## Évolution Graham → Buffett-Munger

| | Buffett 1.0 (Graham, 1956-1972) | Buffett 2.0 (Munger, 1972+) |
|--|---------------------------------|------------------------------|
| Cible | Cigar butts | Wonderful businesses |
| Discount | 50%+ | 0-30% (fair price OK) |
| Concentration | 30-40 positions | 5-15 positions |
| Holding | 1-3 ans | 10-30 ans (forever) |
| Métriques | P/B, NCAV | ROIC, moat |

Tournant : See's Candies (1972, achetée 3× book value).

## Holdings emblématiques Berkshire (en 2026)

- **Apple** (10 % à pic) — depuis 2016
- **Coca-Cola** — depuis 1988, ×28 sur 35 ans
- **American Express** — depuis 1964 (avec adds successifs)
- **Bank of America** — depuis 2011
- **Occidental Petroleum** — depuis 2022
- **BNSF Railway** (private) — depuis 2010

## Ce qu'il ne fait pas

- Ne donne pas un seul score numérique d'investissement (les 4 filtres restent qualitatifs)
- Ne couvre pas les financières en détail (banques, assurances)
- Ne remplace pas le scuttlebutt (croiser avec Fisher)

## Garde-fous

- "Quality" est trop souvent un cliché — vérifier rigoureusement (10+ ans ROIC > WACC)
- Cercle de compétence non extensible par enthousiasme — Buffett a évité tech 50 ans
- "Fair price" n'est pas "n'importe quel prix" — toujours faire test de valorisation
- Buffett lui-même se trompe (IBM, Tesco, Dexter Shoes documentés)

## Voir aussi

- [dorsey-moat-analysis](../dorsey-moat-analysis/) — pour le filtre 2 (économie long-terme)
- [fisher-scuttlebutt](../fisher-scuttlebutt/) — pour le filtre 3 (direction)
- [stock-valuation-triangulation](../stock-valuation-triangulation/) — pour le filtre 4 (prix)
- [investment-thesis-builder](../investment-thesis-builder/) — synthèse formelle finale
