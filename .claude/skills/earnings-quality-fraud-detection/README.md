# earnings-quality-fraud-detection

Détection systématique de fraude comptable et évaluation de la qualité des bénéfices via 5 modèles académiques validés.

## À quoi ça sert

Avant d'investir significativement, vérifier que les chiffres publiés sont **fiables**. Cinq modèles complémentaires :

| Modèle | Auteur | Détecte | Score type |
|--------|--------|---------|------------|
| **M-Score** | Beneish (1999) | Manipulation comptable | M < -2.22 = OK |
| **Z-Score** | Altman (1968) | Risque de faillite | Z > 2.99 = sécuritaire |
| **F-Score** | Piotroski (2000) | Qualité financière | F ≥ 7/9 = excellent |
| **C-Score** | Montier (2008) | Earnings management | C ≤ 2/6 = OK |
| **Sloan Accruals** | Sloan (1996) | Bénéfices "papier" vs cash | Accruals/Assets < -5% = warning |

## Quand l'utiliser

- "Tesla M-score 2024 ?"
- "Vérifie la qualité comptable d'Apple FY2023"
- "Y a-t-il des signes de manipulation chez Wirecard avant 2020 ?"
- Avant toute position concentrée >5 %

## Quand ne pas l'utiliser

- Pour les financières (banques, assureurs) — modèles non applicables
- Pour pre-revenue companies — F-Score et M-Score nécessitent revenus historiques
- Pour les startups privées — données comptables insuffisantes

## Composants

```
earnings-quality-fraud-detection/
├── SKILL.md
├── references/
│   ├── beneish-m-score.md       ← 8 variables M-Score
│   ├── altman-z-score.md        ← 5 ratios bilan/marché
│   ├── piotroski-f-score.md     ← 9 critères binaires
│   ├── montier-c-score.md       ← 6 indicateurs earnings management
│   └── sloan-accruals.md        ← Distinction cash vs paper earnings
├── scripts/
│   ├── beneish_mscore.py
│   ├── altman_zscore.py
│   ├── piotroski_fscore.py
│   ├── montier_cscore.py
│   └── sloan_accruals.py
└── evals/
    ├── evals.json
    └── test_apple.json          ← Apple FY2023 (M -2.66, Z 7.29, F 7/9...)
```

## Exemples d'utilisation

### Via prompt

> "Calcule M-Score, Z-Score et F-Score pour Apple FY2023 et flagge tout drapeau rouge"

### Via script direct

```bash
cd earnings-quality-fraud-detection
python scripts/beneish_mscore.py evals/test_apple.json
python scripts/altman_zscore.py evals/test_apple.json
python scripts/piotroski_fscore.py evals/test_apple.json
```

Output Apple FY2023 :
```
M-SCORE BENEISH
M = -2.66
✓ M < -2.22 → faible probabilité de manipulation

Z-SCORE ALTMAN
Z = 7.29
✓ Z > 2.99 → entreprise très sécuritaire (zone "safe")

F-SCORE PIOTROSKI
F = 7/9
✓ F ≥ 7 → qualité financière excellente
```

## Cas historiques détectés (rétrospectivement)

| Entreprise | Année | Modèle | Signal | Issue |
|------------|-------|--------|--------|-------|
| Enron | 2000 | M-Score | M = +0.12 (rouge) | Faillite 2001 |
| Wirecard | 2018 | M-Score | M = +1.5 (rouge) | Fraude 2020 |
| Theranos | n/a | Pas applicable | Pas de comptabilité publique | Fraude révélée 2018 |
| Lehman | 2007 | Z-Score | Z = 1.8 (zone grise) | Faillite 2008 |

## Ce qu'il ne fait pas

- Ne garantit pas la détection de toutes les fraudes (Theranos privé, audit complaisant)
- Ne capture pas les fraudes structurelles non visibles dans les chiffres GAAP
- Ne couvre pas les financières (Lehman partiellement détecté seulement)
- Ne remplace pas le scuttlebutt (croiser avec `fisher-scuttlebutt`)

## Garde-fous

- Faux positifs : entreprises en croissance rapide ou en transformation peuvent flagger M-Score sans fraude réelle
- Vérifier la **cohérence multi-modèles** : si 3-4 modèles flaggent, suspicion forte ; si 1 seul, probablement faux positif
- Les modèles sont **probabilistes**, pas déterministes
- Ne pas se fier aux audits publics seuls (KPMG a audité Wirecard 10+ ans)

## Voir aussi

- [fisher-scuttlebutt](../fisher-scuttlebutt/) — recherche qualitative pour détecter ce que les chiffres cachent
- [munger-mental-models](../munger-mental-models/) — biais cognitifs des analystes complaisants
- [klarman-margin-of-safety](../klarman-margin-of-safety/) — discipline pour résister aux opportunités douteuses
