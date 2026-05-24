# M-Score (Beneish, 1999)

## Origine et utilité

Messod Beneish, Indiana University Kelley School of Business. Publié dans *Financial Analysts Journal* (1999), **The Detection of Earnings Manipulation**. Backtesté sur 74 entreprises ayant manipulé leurs bénéfices entre 1982 et 1992, avec 76 % de précision (vs faux positifs ~17.5 %).

**Notoriété historique** : des étudiants de Cornell ont identifié Enron comme manipulateur dès 1998 grâce au M-Score, soit 3 ans avant la faillite de décembre 2001 — alors que Wall Street recommandait toujours l'achat.

## Formule

```
M = -4.84 + 0.92×DSRI + 0.528×GMI + 0.404×AQI + 0.892×SGI
    + 0.115×DEPI - 0.172×SGAI + 4.679×TATA - 0.327×LVGI
```

## Les 8 variables (toutes sont des ratios T / T-1)

### 1. DSRI — Days Sales in Receivables Index
```
DSRI = (Receivables_t / Sales_t) / (Receivables_{t-1} / Sales_{t-1})
```
Une augmentation suggère du *channel stuffing* (livrer aux clients pour gonfler les ventes) ou des clients qui ne paient pas (qualité de revenu dégradée).

### 2. GMI — Gross Margin Index
```
GMI = ((Sales_{t-1} - COGS_{t-1}) / Sales_{t-1}) / ((Sales_t - COGS_t) / Sales_t)
```
GMI > 1 = marges qui se compressent. Pression à manipuler les bénéfices.

### 3. AQI — Asset Quality Index
```
AQI = (1 - (CA_t + PPE_t + Securities_t) / TA_t) /
      (1 - (CA_{t-1} + PPE_{t-1} + Securities_{t-1}) / TA_{t-1})
```
Mesure la part des actifs "non tangibles" (autres que courants, PP&E, titres). AQI > 1 = goodwill et intangibles qui croissent — souvent zone de capitalisation abusive.

### 4. SGI — Sales Growth Index
```
SGI = Sales_t / Sales_{t-1}
```
Beneish a observé que les manipulateurs ont une croissance des ventes anormalement élevée (pression du marché à maintenir le rythme).

### 5. DEPI — Depreciation Index
```
DEPI = (Dep_{t-1} / (Dep_{t-1} + PPE_{t-1})) /
       (Dep_t / (Dep_t + PPE_t))
```
DEPI > 1 = ralentissement de la dépréciation. Étirement des durées de vie utiles pour gonfler le résultat.

### 6. SGAI — SG&A Expenses Index
```
SGAI = (SGA_t / Sales_t) / (SGA_{t-1} / Sales_{t-1})
```
Inverse intuitif : SGAI **élevé** est moins suspect que SGAI bas — Beneish a trouvé que les manipulateurs *réduisent* leurs SG&A pour gonfler les marges.

### 7. TATA — Total Accruals to Total Assets
```
TATA = (Net Income_t - CFO_t) / TA_t
```
Le coefficient le plus élevé (4.679) — le **plus puissant prédicteur**. Mesure l'écart entre bénéfice comptable et cash flow réel.

### 8. LVGI — Leverage Index
```
LVGI = ((LTD_t + CL_t) / TA_t) / ((LTD_{t-1} + CL_{t-1}) / TA_{t-1})
```
Coefficient négatif — Beneish a trouvé que les manipulateurs ne sont pas particulièrement endettés (contre-intuitif).

## Seuils d'interprétation

| M-Score | Lecture |
|---------|---------|
| M ≤ -2.22 | Faible probabilité de manipulation — OK |
| -2.22 < M ≤ -1.78 | Zone grise — investiguer |
| M > -1.78 | Probabilité élevée de manipulation — drapeau rouge |

## Cas limites et faux positifs courants

- **Croissance organique très rapide** (SaaS jeune, retail en expansion géographique) : DSRI et SGI peuvent gonfler le M-Score sans manipulation
- **Acquisitions récentes** : AQI bondit mécaniquement (goodwill ajouté)
- **Restatement comptable** : crée un T vs T-1 incomparable
- **Changement de norme comptable** (IFRS 15, IFRS 16) : peut faire basculer plusieurs variables

Toujours lire les notes des états financiers avant de conclure — un M-Score élevé sans contexte n'est pas une preuve de fraude, c'est un signal d'alerte qui justifie une investigation.

## Inapplicabilité

Beneish a explicitement **exclu les institutions financières** de son échantillon. Banques, assureurs et REITs ne sont pas analysables avec ce modèle parce que leurs revenus et créances obéissent à une logique différente (intérêts vs ventes, créances de prêts vs créances clients).

## Source primaire

Beneish, Messod D. (1999). *The Detection of Earnings Manipulation*. Financial Analysts Journal, 55(5), 24-36. [DOI:10.2469/faj.v55.n5.2296](https://doi.org/10.2469/faj.v55.n5.2296)

Mises à jour : Beneish, Lee, Nichols (2013) ; Beneish & Vorst (2020).
