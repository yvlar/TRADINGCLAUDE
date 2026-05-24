# dorsey-moat-analysis

Analyse du moat économique selon Pat Dorsey — 5 sources d'avantages concurrentiels durables avec test quantitatif via durabilité du ROIC.

## À quoi ça sert

Pat Dorsey (ex-Morningstar, *The Five Rules for Successful Stock Investing*) identifie 5 sources de moats durables :

1. **Actifs intangibles** : marques, brevets, licences réglementaires
2. **Coûts de transfert** : switching costs élevés
3. **Effets de réseau** : valeur croît avec utilisateurs
4. **Avantages de coût** : structurels (échelle, géographie, processus)
5. **Échelle efficiente** : marché trop petit pour > 1-3 acteurs viables

Le test quantitatif : un moat réel doit se manifester par un **ROIC élevé et stable durablement supérieur au WACC**.

## Quand l'utiliser

- "Apple a-t-elle un moat selon Dorsey ?"
- "Pourquoi Visa et Mastercard sont-ils si rentables durablement ?"
- "Constellation Software — durabilité du moat ?"
- Avant d'accepter une "qualité" sur la base d'un narrative marketing

## Quand ne pas l'utiliser

- Pour les commodity producers (le moat est typiquement géologique, pas économique)
- Pour les très jeunes entreprises sans 10 ans d'historique ROIC
- Pour valider un investissement court-terme — le moat compte sur 10+ ans

## Composants

```
dorsey-moat-analysis/
├── SKILL.md
├── references/
│   ├── moat-intangibles.md         ← Marques, brevets, licences
│   ├── moat-switching-costs.md     ← Coûts de transfert
│   ├── moat-network-effects.md     ← Effets de réseau
│   ├── moat-cost-advantages.md     ← Avantages de coût durables
│   └── moat-efficient-scale.md     ← Marchés à échelle efficiente
├── scripts/
│   └── roic_durability.py          ← Test ROIC moyenne, CV, spread vs WACC
└── evals/
    ├── evals.json
    ├── test_csu.json               ← CSU: ROIC 29%, CV 0.06, MOAT PROBABLE
    └── test_aircanada.json         ← AC: ROIC 3.1%, volatil, PAS DE MOAT
```

## Exemples d'utilisation

### Via prompt

> "Constellation Software a-t-elle un moat durable ?"

Claude lira les références appropriées (switching costs principalement pour CSU) et exécutera `roic_durability.py` sur l'historique 10 ans.

### Via script direct

```bash
cd dorsey-moat-analysis
python scripts/roic_durability.py evals/test_csu.json
```

Output CSU :
```
ROIC moyen : 29.1%
CV : 0.057 (très stable)
Spread vs WACC : +20.6 pts
Tendance : +0.38 pts/an

✅ MOAT PROBABLE — ROIC élevé, stable, durablement > WACC
```

Vs Air Canada :
```
ROIC moyen : 3.1%
CV : 3.59 (extrêmement volatil)
Spread vs WACC : -5.9 pts

❌ PAS DE MOAT — ROIC trop faible et volatil, sous le WACC
```

## Le test des 3 critères

Une entreprise a un moat probable si :

1. **ROIC moyen ≥ 15 %** sur 10 ans
2. **Coefficient de variation < 0.20** (stabilité)
3. **Spread vs WACC > 5 %** (création de valeur claire)

Si les 3 sont satisfaits, moat probable. Si 1-2 sur 3, moat possible — investiguer la source.

## Calibration des moats

| Niveau | Indicateurs | Exemples |
|--------|-------------|----------|
| **Wide moat** | ROIC > 20 % stable, > 10 ans documenté | Visa, Mastercard, Costco, MSCI, CSU |
| **Narrow moat** | ROIC 12-20 %, 5-10 ans | Banques canadiennes, Couche-Tard |
| **Pas de moat** | ROIC < 10 % ou volatil | Compagnies aériennes, retailers commodity |

## Ce qu'il ne fait pas

- Ne distingue pas mécaniquement quelle source de moat (qualitatif requis)
- Ne prédit pas la disruption future (Kodak avait un moat avant le digital)
- Ne valide pas le prix d'achat (croiser avec valuation)

## Garde-fous

- Le ROIC élevé peut venir de **leverage** (banques) — vérifier le spread vs WACC ajusté
- Les moats peuvent **éroder** : surveiller la tendance et les marges
- Les concurrents qui veulent imiter prennent 5-10 ans — un moat actuel ne garantit pas 20 ans
- Le test exige 10 ans d'historique — inadéquat pour les jeunes entreprises

## Voir aussi

- [buffett-quality-investing](../buffett-quality-investing/) — Buffett insiste sur "favorable long-term economics" = moat
- [fisher-scuttlebutt](../fisher-scuttlebutt/) — vérifier qualitativement le moat via stakeholders
- [damodaran-narrative-and-numbers](../damodaran-narrative-and-numbers/) — cohérence dynamique du ROIC dans le DCF
