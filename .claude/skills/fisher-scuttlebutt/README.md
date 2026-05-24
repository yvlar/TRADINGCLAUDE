# fisher-scuttlebutt

Méthode Phil Fisher — 15 points qualitatifs + recherche terrain ("scuttlebutt") auprès des stakeholders pour évaluer une entreprise au-delà des chiffres.

## À quoi ça sert

Phil Fisher (*Common Stocks and Uncommon Profits*, 1958) a été le premier à formaliser l'**analyse qualitative** comme partie intégrante du value investing. Buffett dit être *"85 % Graham, 15 % Fisher"*.

Deux outils principaux :

1. **15 points** : checklist qualitative (capacité R&D, marges, relations employés, intégrité direction, etc.) — **dont 2 sont éliminatoires** (transparence + intégrité)
2. **Scuttlebutt** : recherche terrain auprès des ex-employés, clients, fournisseurs, concurrents pour révéler ce que les filings ne disent pas

## Quand l'utiliser

- Avant une position concentrée (>5 % du portfolio)
- Pour évaluer la qualité de la direction
- "Comment faire du scuttlebutt sur Constellation Software ?"
- Pour détecter les drapeaux rouges qualitatifs (Theranos, Wirecard rétrospectivement)

## Quand ne pas l'utiliser

- Pour les positions petites (< 2 %) — effort disproportionné
- Pour le trading court-terme — irrelevant
- Pour les ETF / fonds indiciels

## Composants

```
fisher-scuttlebutt/
├── SKILL.md
├── references/
│   ├── 15-points-fisher.md         ← Détail des 15 points + #14, #15 éliminatoires
│   ├── scuttlebutt-methode.md      ← Comment interroger ex-employés, clients, etc.
│   └── qualite-direction.md        ← 4 dimensions: compétence, allocation, intégrité, vision
├── scripts/
│   └── fisher_15_points.py         ← Scoring + flag éliminatoires
└── evals/
    ├── evals.json
    └── test_csu.json               ← CSU passe 15/15
```

## Les 15 points (résumé)

| # | Point | Type |
|---|-------|------|
| 1 | Potentiel de croissance du marché | Important |
| 2 | Volonté de développer nouveaux produits | Important |
| 3 | Efficacité de la R&D | Modéré |
| 4 | Organisation commerciale | Modéré |
| 5 | Marges bénéficiaires | Très important |
| 6 | Effort pour maintenir/améliorer marges | Important |
| 7 | Relations direction-personnel | Important |
| 8 | Profondeur de l'équipe exécutive | Important |
| 9 | Profondeur du middle management | Modéré |
| 10 | Contrôle des coûts et comptable | Important |
| 11 | Facteurs spécifiques à l'industrie | Modéré |
| 12 | Vision long-terme vs court-terme | Très important |
| 13 | Besoin de capital nouveau (dilution) | Important |
| **14** | **Communication franche en cas de problème** | **ÉLIMINATOIRE** |
| **15** | **Intégrité de la direction** | **ÉLIMINATOIRE** |

## Méthode scuttlebutt

Sources à interroger (par ordre d'accessibilité) :

1. **Ex-employés** (LinkedIn, Glassdoor, Reddit, Blind)
2. **Clients** (interviews, reviews G2, conférences sectorielles)
3. **Fournisseurs** (relations commerciales)
4. **Concurrents** (vue interne sur les leaders)
5. **Distributeurs / partenaires**
6. **Analystes sectoriels** (avec filtre des biais)
7. **Régulateurs** (filings publics)

## Exemples d'utilisation

### Via prompt

> "Évalue la qualité de la direction de Constellation Software via les 15 points Fisher"

### Via script direct

```bash
cd fisher-scuttlebutt
python scripts/fisher_15_points.py evals/test_csu.json
```

Output CSU :
```
🔴 14. Communication franche en cas de problème     5/5  ✓
🔴 15. Intégrité de la direction                     5/5  ✓

Score moyen : 4.73/5
Points passés : 15/15

✅ EXCELLENT — qualité Fisher
```

## Cas d'application

### Qui passe les 15 points (rétrospectivement)
- Berkshire Hathaway (Buffett-Munger)
- Constellation Software (Mark Leonard)
- Costco (Sinegal puis Galanti)
- Amazon (Bezos jusqu'en 2020)
- See's Candies (avant et après acquisition)

### Qui rate les éliminatoires (rétrospectivement)
- Wirecard 2015-2020 (point 14 et 15)
- Theranos 2014-2018 (point 15)
- Sears Holdings 2010-2018 (point 15 — Lampert self-dealing)
- Enron 1999-2001 (point 15)

## Limites de la méthode

- Le scuttlebutt demande **du temps** (semaines par entreprise)
- Insider trading vs research légitime — ne demander que des **opinions et perceptions**
- Glassdoor a un biais des disgruntled (mécontents écrivent plus)
- Les directions sophistiquées peuvent maintenir une façade (Theranos)

## Garde-fous

- Les points 14 et 15 sont **éliminatoires absolus** — peu importe le reste, si manqués, refuser
- Triangulation requise : 5+ sources avant de conclure sur un pattern
- Ne jamais utiliser des informations matérielles non publiques
- Le scuttlebutt complète, ne remplace pas l'analyse fondamentale

## Voir aussi

- [buffett-quality-investing](../buffett-quality-investing/) — Buffett applique systématiquement Fisher
- [munger-mental-models](../munger-mental-models/) — biais cognitifs des analystes complaisants
- [earnings-quality-fraud-detection](../earnings-quality-fraud-detection/) — détection quantitative complémentaire
- [investment-thesis-builder](../investment-thesis-builder/) — synthèse pour décision finale
