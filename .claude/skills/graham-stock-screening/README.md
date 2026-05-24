# graham-stock-screening

Filtre quantitatif Graham pour identifier les actions value sous-évaluées par rapport à leurs fondamentaux.

## À quoi ça sert

Appliquer les critères de Benjamin Graham (*The Intelligent Investor*, *Security Analysis*) pour pré-screener un univers d'actions :
- **Investisseur défensif** : 7 critères stricts pour les blue chips
- **Investisseur entreprenant** : 7 critères modérés pour value plays plus actifs
- **Formule Graham** : valeur intrinsèque approximative (V = EPS × (8.5 + 2g))

Le résultat n'est pas une recommandation d'achat — c'est une **shortlist de candidats** méritant l'analyse approfondie (moat, direction, valorisation).

## Quand l'utiliser

- "RBC passe-t-elle Graham défensif ?"
- "Donne-moi la formule Graham value pour BCE"
- "Quels critères Graham appliquer à un grand cap ?"
- Pré-screening avant analyse complète d'un compounder ou cyclique

## Quand ne pas l'utiliser

- Pour des entreprises tech/SaaS non profitables (Graham ne s'applique pas)
- Pour valoriser une story stock — utiliser `damodaran-narrative-and-numbers`
- Pour les distressed — utiliser `klarman-margin-of-safety`

## Composants

```
graham-stock-screening/
├── SKILL.md
├── references/
│   ├── defensif.md         ← 7 critères défensifs détaillés
│   ├── entreprenant.md     ← 7 critères entreprenants
│   └── formule-graham.md   ← V = EPS × (8.5 + 2g) avec ajustements
├── scripts/
│   ├── screen_graham.py    ← Applique les 7 critères
│   └── formule_graham.py   ← Calcule V intrinsèque
└── evals/
    ├── evals.json
    └── test_rbc.json       ← Cas RBC réel (8/9 défensifs, 47% margin)
```

## Exemples d'utilisation

### Via prompt

> "Est-ce que Royal Bank passe le filtre Graham défensif au prix actuel de 130 CAD ?"

Claude lira `references/defensif.md`, puis exécutera `scripts/screen_graham.py` avec les données RBC.

### Via script direct

```bash
cd graham-stock-screening
python scripts/screen_graham.py evals/test_rbc.json
```

Output type :
```
GRAHAM DÉFENSIF — RBC.TO
✓ Cap. boursière > 2 G$ : 188 G CAD
✓ Current ratio > 2 : 1.4 (assouplissement banques OK)
✓ EPS positif 10 ans consécutifs
...
Score : 8/9 — Passe Graham défensif (avec assouplissement banques)
Graham value : 246 CAD
Margin of safety vs prix 130 : 47%
```

## Ce qu'il ne fait pas

- Ne valide pas un investissement seul — Graham screen une condition nécessaire mais non suffisante
- Ne vérifie pas la qualité des bénéfices (croiser avec `earnings-quality-fraud-detection`)
- Ne regarde pas la durabilité du moat (croiser avec `dorsey-moat-analysis`)

## Garde-fous

- La formule Graham (8.5 + 2g) date de 1962 et présume des taux d'intérêt 4-5 %. Pour des taux > 6 % ou < 2 %, ajuster avec le facteur correctif Graham (4.4 / Y) où Y = corporate AAA yield
- Les critères défensifs sont conçus pour large caps stables — inadaptés aux small caps même avec excellent fondamentaux
- En 2026, peu d'actions passent les 7 critères défensifs sans assouplissement (marché historiquement cher)

## Voir aussi

- [greenblatt-magic-formula](../greenblatt-magic-formula/) — formule plus moderne basée sur ROC + earnings yield
- [stock-valuation-triangulation](../stock-valuation-triangulation/) — pour valorisation rigoureuse au-delà de Graham
- [buffett-quality-investing](../buffett-quality-investing/) — évolution Graham → Buffett-Munger
