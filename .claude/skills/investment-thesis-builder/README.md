# investment-thesis-builder

Synthèse formelle multi-skills — construit un document de thèse structuré avec scenarios pondérés, kill criteria, devil's advocate et position size recommandée.

## À quoi ça sert

C'est le **skill final** qui agrège l'analyse de tous les autres skills en une thèse formelle écrite, prête à être archivée et révisée annuellement.

Cinq composants principaux :

1. **Structure formelle** : 9 sections obligatoires (résumé, business, moat, économie, direction, valorisation, scenarios, risques, décision)
2. **Scenarios pondérés** bull/base/bear avec probabilités et calcul d'EV
3. **Kill criteria** explicites (3-5 critères mesurables qui déclenchent la sortie)
4. **Devil's advocate** : 5 raisons les plus convaincantes de NE PAS investir
5. **Position size** calibrée selon la conviction

## Quand l'utiliser

- Avant toute position significative (≥ 5 % du portfolio)
- "Aide-moi à construire une thèse formelle pour CSU.TO"
- "Scenarios bull/base/bear pour Boeing avec EV pondérée ?"
- "Quels kill criteria pour ma position en Tesla ?"
- "Devil's advocate sur ma thèse Costco ?"
- Pour formaliser une décision et créer un document révisable

## Quand ne pas l'utiliser

- Pour les positions petites (< 2 %) — effort disproportionné
- Avant d'avoir fait l'analyse de base avec les autres skills
- Pour le trading court-terme

## Composants

```
investment-thesis-builder/
├── SKILL.md
├── references/
│   ├── structure-these.md       ← 9 sections détaillées
│   ├── scenarios-pondere.md     ← Bull/base/bear avec calibration
│   ├── kill-criteria.md         ← Critères de sortie automatique
│   └── devils-advocate.md       ← Test inversion + 5 arguments contre
├── scripts/
│   ├── build_thesis.py          ← Génère le markdown de la thèse
│   └── scenarios_ev.py          ← Calcul EV pondérée + annualisé
├── templates/
│   └── template-compounder.md   ← Template Buffett-style à remplir
└── evals/
    ├── evals.json
    └── test_csu_thesis.json     ← Thèse complète CSU
```

## Workflow recommandé

### Étape 1 — Pré-conditions

Avoir effectué les analyses des skills appropriés :

| Type d'opportunité | Skills à appliquer |
|---------------------|--------------------|
| Compounder Buffett | buffett-quality + dorsey-moat + fisher-scuttlebutt |
| Value Graham | graham-screening + earnings-quality + canadian-tax |
| Special situation | greenblatt-magic-formula + klarman-margin |
| Fast grower Lynch | lynch-categories + damodaran-narrative |
| Distressed / Pabrai | pabrai-dhandho + klarman-margin |

Sans ces analyses préalables, **stop** et les faire d'abord.

### Étape 2 — Construire la thèse

```bash
cd investment-thesis-builder
python scripts/build_thesis.py inputs.json
```

Génère un document markdown structuré.

### Étape 3 — Scenarios pondérés

```bash
python scripts/scenarios_ev.py --bear-pct -30 --bear-prob 20 --base-pct 80 --base-prob 55 --bull-pct 250 --bull-prob 25 --horizon 7
```

Output :
```
ESPÉRANCE PONDÉRÉE — SCENARIOS BULL/BASE/BEAR
Bear   20%   -30%   -6.00%
Base   55%   +80%   +44.00%
Bull   25%  +250%   +62.50%
─────────────────────────
TOTAL          +100.50%

Horizon : 7 ans
Rendement annualisé : +10.45%/an

🟢 EV positive solide — position normale
```

## Position Size selon conviction

| Niveau | Critères | Position |
|--------|----------|----------|
| **Très haute** | Compounder + Fisher 14-15/15 + asymétrie 4:1+ | 8-15 % |
| **Haute** | 3 skills convergents positivement | 5-8 % |
| **Moyenne** | Analyse positive avec doutes | 2-5 % |
| **Spéculative** | Asymétrie attractive mais risque réel | 1-2 % |

## Kill Criteria — exemples

Pour un compounder type CSU :

1. ROIC < 18 % pendant 2 années consécutives
2. Mark Leonard quitte sans plan succession clair
3. Croissance organique nette < 3 % pendant 2 ans
4. Multiples acquisitions > 1.5× médiane historique pendant 3 ans
5. Concentration client > 15 % des revenus

Pour un cyclique au creux :

1. Coûts d'extraction > 1.2× médiane peer pendant 2 ans
2. Net Debt / EBITDA > 3.5× au creux du cycle
3. Vente d'actifs non-core forced
4. Direction change sans plan

## Devil's Advocate — exemple

Pour CSU :
1. Multiples acquisitions ont monté (5-7× EBITDA vs 3-4× historique)
2. Mark Leonard avancé en âge, succession non clair
3. Loi des grands nombres — difficile maintenir 25 % CAGR
4. Concurrence accrue (Vista, Roper, Thoma Bravo)
5. Multiple actuel élevé (P/E 35×)

→ Thèse résiste si chaque argument a une mitigation crédible.

## Exemple de thèse complète

Voir `evals/test_csu_thesis.json` puis `python scripts/build_thesis.py evals/test_csu_thesis.json` pour le rendu complet.

## Calendrier de révision

| Position size | Fréquence de révision |
|---------------|------------------------|
| > 10 % | Trimestrielle |
| 5-10 % | Semestrielle |
| 2-5 % | Annuelle |
| < 2 % | Annuelle ou ad-hoc (events) |

Plus toute révision **ad-hoc** quand un kill criterion est sur le point d'être déclenché.

## Ce qu'il ne fait pas

- Ne **fait pas** l'analyse fondamentale (assume que les autres skills l'ont fait)
- Ne **garantit pas** le succès — la rigueur du processus est l'objectif
- Ne **remplace pas** la discipline de révision active

## Garde-fous

- Une thèse écrite n'est **pas une garantie** — même les bonnes thèses échouent
- Les **probabilités sont subjectives** — utiliser arrondis (5 %, 10 %, 25 %) plutôt que faux précision
- L'optimisme se cache facilement dans les hypothèses — forcer le scenario bear AVANT le bull
- **Réviser, pas réécrire** : si la thèse échoue, reconnaître l'erreur, sortir, apprendre

## Voir aussi

Tous les autres skills sont des **inputs** pour celui-ci. Le workflow complet :

1. Filtres : graham + greenblatt + earnings-quality
2. Qualité : dorsey-moat + fisher-scuttlebutt + lynch-categories
3. Valorisation : stock-valuation-triangulation + damodaran + buffett-quality
4. Discipline : klarman-margin + marks-cycles + munger-mental + pabrai-dhandho
5. Fiscalité : canadian-tax-considerations
6. **Synthèse finale : investment-thesis-builder ← ce skill**
