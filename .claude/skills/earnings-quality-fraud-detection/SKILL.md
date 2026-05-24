---
name: earnings-quality-fraud-detection
description: Détecte les manipulations comptables et le risque de faillite via cinq cadres académiques mécaniques — M-Score (Beneish), Z-Score (Altman), F-Score (Piotroski), C-Score (Montier), accruals (Sloan). À utiliser dès que l'utilisateur mentionne Beneish, Altman, Piotroski, Montier, Sloan, M-score, Z-score, F-score, "cooking the books", earnings management, accruals, "earnings quality", red flags comptables, risque de faillite, value trap, ou veut vérifier qu'une action en apparence sous-évaluée n'est pas un piège. Utilise toujours ce skill avant tout achat important pour s'assurer que les chiffres affichés ne sont pas manipulés ou ne masquent pas un risque de faillite.
---

# Earnings Quality & Fraud Detection

Cinq cadres académiques mécaniques pour détecter manipulations comptables et risque de faillite. L'idée centrale : une action peut paraître bon marché parce qu'elle l'est *vraiment*, ou parce qu'elle cache une fraude / une faillite. Ces cadres distinguent les deux **avant** que le marché ne s'en rende compte.

## Quand utiliser quel cadre

Tu n'as pas besoin de tout calculer à chaque fois. Choisis selon la question :

| Question posée | Cadre à utiliser | Référence |
|----------------|------------------|-----------|
| Les bénéfices sont-ils manipulés ? | M-Score (Beneish) | `references/beneish-m-score.md` |
| L'entreprise risque-t-elle la faillite ? | Z-Score (Altman) | `references/altman-z-score.md` |
| Cette action value est-elle un piège ? | F-Score (Piotroski) | `references/piotroski-f-score.md` |
| Y a-t-il des signaux qualitatifs de "cooking" ? | C-Score (Montier) | `references/montier-c-score.md` |
| La qualité des bénéfices se dégrade-t-elle ? | Accruals (Sloan) | `references/sloan-accruals.md` |
| Pré-achat important — passe-t-elle tous les filtres ? | Les 5, dans cet ordre | (workflow ci-dessous) |

## Workflow recommandé

Pour un audit pré-achat complet, lance les cinq cadres en parallèle. Pour gagner du temps et éviter les erreurs arithmétiques, **utilise les scripts Python bundled** — ils prennent les ratios bruts en entrée et sortent les scores avec interprétation.

### Étape 1 — Récupérer les données

Récupère les états financiers récents (T et T-1, sur le site de l'entreprise, SEC EDGAR pour les US, SEDAR+ pour les canadiennes) ou via web_search. Tu auras besoin de :
- Bilan (actifs, passifs, fonds de roulement, immobilisations, dette LT)
- Compte de résultat (revenus, COGS, SG&A, dépréciation, EBIT, bénéfice net)
- Flux de trésorerie (CFO, CFI)
- Capitalisation et nombre d'actions

### Étape 2 — Lance les calculs

Utilise les scripts Python bundled plutôt que de calculer en mémoire :

```bash
python scripts/compute_mscore.py     # M-Score Beneish (8 variables)
python scripts/compute_zscore.py     # Z-Score Altman (5 variables)
python scripts/compute_fscore.py     # F-Score Piotroski (9 critères binaires)
python scripts/compute_cscore.py     # C-Score Montier (6 signaux binaires)
python scripts/compute_accruals.py   # Ratio des accruals de Sloan
```

Chaque script demande les ratios via stdin ou prend un JSON en argument. Voir le header de chaque script pour les détails.

Si tu calcules manuellement (pas d'environnement Python), lis le fichier de référence du cadre — il contient les formules, les seuils et un exemple complet.

### Étape 3 — Interpréter le verdict combiné

Une action passe le filtre qualité si :
- M-Score ≤ -2.22 (faible probabilité de manipulation)
- Z-Score > 2.99 (zone sûre — version Z' ou Z'' selon le secteur)
- F-Score ≥ 7 (qualité financière solide)
- C-Score ≤ 1 (pas de signaux de cooking)
- Accruals dans la moitié basse du secteur

Si **3 cadres ou plus échouent**, c'est un signal fort de ne pas investir. Si 1-2 échouent, lis la section "Cas limites" du fichier de référence concerné avant de décider — un signal isolé peut avoir une explication légitime (ex : forte croissance organique fait gonfler les accruals sans manipulation).

## Pourquoi cinq cadres et pas un seul

Chaque cadre a été conçu pour un type de risque différent et calibré sur une population différente. Ils sont **complémentaires** :

- Le M-Score détecte la **fraude active** (manipulation intentionnelle des chiffres)
- Le Z-Score détecte la **détresse passive** (l'entreprise va couler, sans fraude nécessaire)
- Le F-Score détecte les **value traps** (action bon marché qui le mérite)
- Le C-Score détecte les **drapeaux qualitatifs** que les ratios pondérés peuvent rater
- Les accruals détectent la **qualité dégradante des bénéfices** (signal le plus en amont)

Un investisseur peut être protégé par les chiffres pondérés (M-Score, Z-Score) tout en se faisant piéger par une situation que seuls les drapeaux qualitatifs (C-Score) auraient révélée. C'est pourquoi la doctrine est *« ces cadres sont un filet de sécurité, pas une checklist mutuellement exclusive »*.

## Inapplicabilités sectorielles

Aucun de ces cadres n'a été calibré sur les institutions financières (banques, assureurs) parce que leur structure de bilan rend les ratios non comparables — leur "stock" est constitué de prêts et de polices, pas d'inventaire et d'immobilisations. Si tu analyses une banque ou un assureur :
- Skip le Z-Score classique (utilise éventuellement Z'' adapté aux marchés émergents)
- Skip le F-Score classique
- Le M-Score reste utilisable avec prudence (Beneish lui-même a exclu les financières de son échantillon)
- Utilise plutôt des cadres sectoriels : pour les banques, le **Texas Ratio** (NPL / equity + reserves) et le **CET1 ratio** sont plus pertinents

Les utilities régulées posent un problème similaire (ROIC contraint par la régulation). Les holdings et REITs aussi.

## Garde-fous

Les modèles ont **76-90 % de précision en backtesting**, ce qui signifie aussi 10-24 % de faux positifs et faux négatifs. Un score limite isolé ne suffit pas pour rejeter — il faut lire les notes des états financiers pour comprendre le contexte (transformation, M&A récent, changement comptable légitime). Cette précaution évite à la fois de passer à côté de bonnes opportunités et de se laisser piéger par des explications post-hoc.

L'effet Goodhart s'applique : depuis que ces modèles sont publics et calculés automatiquement par toutes les plateformes, les manipulateurs sophistiqués apprennent à les contourner. Ces modèles sont efficaces contre la **fraude moyenne**, pas contre Wirecard ou Luckin Coffee.

Ce sont des **filtres mécaniques**, pas des analyses fondamentales. Une action qui passe les 5 tests mais n'a pas de moat reste un mauvais investissement long terme. Croiser systématiquement avec `buffett-quality-investing` ou `dorsey-moat-analysis` pour la dimension qualitative.
