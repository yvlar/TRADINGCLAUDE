# F-Score (Piotroski, 2000)

## Origine et utilité

Joseph Piotroski, Stanford (à l'époque University of Chicago). Article fondateur : *Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers* (Journal of Accounting Research, 2000).

**L'idée** : appliqué à l'univers des actions value (haut book-to-market = bas P/B), un score binaire de 9 critères distingue les vraies opportunités des *value traps*. Backtesté sur 1976-1996 : les actions à F-Score 8-9 du décile value ont surperformé la moyenne value de **7.5 % par an**, et la stratégie long-short a généré **23 % par an**.

**Particularité** : le F-Score ne fonctionne **que** sur les actions value (faible P/B). Sur le marché général, son pouvoir prédictif est nettement plus faible.

## Les 9 critères (1 point chacun si rempli, 0 sinon)

### Profitabilité (4 points possibles)

**1. ROA > 0**
Bénéfice net positif sur l'exercice courant rapporté au total des actifs. Élimine simplement les entreprises non rentables.

**2. CFO > 0**
Cash flow d'exploitation positif. Plus important que le ROA — confirme que la rentabilité comptable se traduit en cash réel.

**3. ROA en hausse**
ROA_t > ROA_{t-1}. Tendance amélioratrice.

**4. CFO > Net Income (qualité des accruals)**
Si CFO dépasse le bénéfice net, les bénéfices sont *« soutenus par le cash »* — pas gonflés par des accruals positifs. C'est un test direct anti-manipulation.

### Levier, liquidité et source de fonds (3 points possibles)

**5. Diminution de la dette long terme**
Ratio LTD/TA en baisse vs T-1. Désendettement = signal positif (les entreprises en difficulté n'ont pas le luxe de se désendetter).

**6. Augmentation du current ratio**
Current ratio_t > Current ratio_{t-1}. Liquidité court terme qui s'améliore.

**7. Pas d'émission nette d'actions**
Aucune dilution sur l'exercice. Une émission d'actions est un signal négatif (besoin de cash externe).

### Efficacité opérationnelle (2 points possibles)

**8. Marge brute en hausse**
Gross margin_t > Gross margin_{t-1}. Pricing power qui s'améliore ou coûts qui se compressent.

**9. Asset turnover en hausse**
(Sales/TA)_t > (Sales/TA)_{t-1}. L'entreprise tire plus de revenus de ses actifs.

## Seuils d'interprétation

| F-Score | Lecture |
|---------|---------|
| 8-9 | Forte qualité — candidate forte dans l'univers value |
| 7 | Bon — acceptable |
| 4-6 | Moyen — investiguer |
| 0-3 | Qualité dégradée — éviter (probable value trap) |

## Application pratique

### Pipeline value classique
1. Filtrer l'univers sur **bottom 20 % par P/B** (l'univers value de Piotroski)
2. Calculer le F-Score sur ces candidats
3. Conserver F ≥ 7 (idéalement 8-9)
4. Faire l'analyse fondamentale sur les survivants (avec `buffett-quality-investing` ou `dorsey-moat-analysis`)

### Pourquoi ça marche
Les actions à faible P/B sont mécaniquement soit :
- Des entreprises **vraiment** sous-évaluées (fondamentaux solides, marché pessimiste)
- Des entreprises en **déclin structurel** que le marché fuit à raison

Le F-Score sépare les deux en mesurant la **direction** des fondamentaux. Une vraie opportunité value a des fondamentaux qui s'améliorent ; un value trap a des fondamentaux qui se détériorent.

## Cas limites et inapplicabilités

- **Financières** : les ratios de marge brute et asset turnover n'ont pas le même sens
- **Capex-heavy / cycliques** : le critère d'augmentation du current ratio peut être trompeur dans certaines phases
- **Croissance non rentable** (jeunes SaaS) : échouent mécaniquement sur ROA mais ce n'est pas pertinent
- **Année avec one-off** (vente d'actif, restructuration) : peut donner faux positifs sur la profitabilité

## Source primaire

Piotroski, Joseph D. (2000). *Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers*. Journal of Accounting Research, 38, 1-41.

Mise à jour : Piotroski & So (2012) — *Identifying Expectation Errors in Value/Glamour Strategies*.
