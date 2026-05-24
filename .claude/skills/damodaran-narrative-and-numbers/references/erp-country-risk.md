# ERP (Equity Risk Premium) et Country Risk

L'**ERP** est la prime exigée par les investisseurs en actions au-dessus du taux sans risque. C'est un paramètre central du WACC et du DCF — Damodaran le calcule mensuellement.

⚠️ Les valeurs ci-dessous datent de début 2026. Vérifier les valeurs courantes via web_search sur le site de Damodaran (pages.stern.nyu.edu/~adamodar/) avant utilisation pour décision réelle.

## L'ERP implicite (méthode Damodaran)

Plutôt que d'utiliser l'ERP historique (moyenne des excédents de rendement passés, méthode classique), Damodaran calcule un **ERP implicite** :

```
ERP implicite = Rendement attendu actions − Taux sans risque
```

### Méthode

À partir des dividendes + buybacks projetés sur le S&P 500, on résout pour le **taux de rendement implicite** qui équilibre prix actuel et flux futurs. Soustraire le 10-year Treasury donne l'ERP implicite.

Cette méthode capture **les conditions de marché actuelles**, pas la moyenne historique. En période de marché tendu, l'ERP implicite descend (les investisseurs acceptent moins de prime). En crise, il monte.

## Valeurs de référence (début 2026)

| Marché | ERP | Rf | Rendement actions exigé |
|--------|-----|----|----|
| US (mature, AAA) | 4.23 % | 4.5 % (10y) | 8.73 % |
| Canada | 4.23 % + 0 | 3.7 % (10y) | 7.93 % |
| France | 4.23 % + 0.5 % | 3.0 % (10y) | 7.73 % |
| UK | 4.23 % + 0 | 4.2 % (10y) | 8.43 % |
| Brésil | 4.23 % + 2.85 % | 12 % (local) | 19.08 % |
| Argentine | 4.23 % + 12.4 % | n/a | n/a |

### Comment lire ces chiffres

Pour valoriser une entreprise canadienne :
- **WACC** = E/V × 7.93 % + D/V × Kd × (1 − tax)
- Le 7.93 % est le coût des fonds propres exigé pour une entreprise opérant en environnement Canada AAA

Pour une entreprise opérant principalement au Brésil, ajouter le **country risk premium** au coût des fonds propres pour refléter le risque souverain et de devise.

## Country Risk Premium (CRP)

Damodaran calcule un CRP par pays basé sur :
1. **Default spread** des obligations souveraines (proxy du risque pays)
2. **Volatilité relative** marché actions / marché obligations (amplification du risque)

```
CRP = Default Spread × σ_actions / σ_obligations
```

### Exemples (début 2026)

| Pays | Rating | Default spread | CRP |
|------|--------|----------------|-----|
| Canada, US | AAA / AA+ | 0 | 0 % |
| France, UK | AA / AA+ | ~0.5 % | 0.5 % |
| Espagne, Italie | A− / BBB | ~1.5-2.5 % | 2-3 % |
| Brésil | BB | ~2.85 % | 2.85 % |
| Inde | BBB− | ~1.5 % | 1.5 % |
| Argentine | CCC | ~12.4 % | 12.4 % |

### Application

Pour une entreprise multinationale, **pondérer le CRP** par exposition géographique des revenus :

```
CRP effectif = Σ (% revenus pays_i × CRP pays_i)
```

Exemple : entreprise canadienne réalisant 60 % au Canada, 30 % aux US, 10 % au Brésil :
```
CRP effectif = 0.6 × 0% + 0.3 × 0% + 0.1 × 2.85% = 0.285 %
```

À ajouter au coût des fonds propres pour refléter l'exposition réelle.

## Mise à jour des chiffres

Damodaran publie :
- **ERP** mensuel pour US et marchés matures
- **Country risk** par pays trimestriel (mis à jour avec ratings)
- **Tax rates effectifs** par pays
- **Industry betas** par secteur globaux

Site : pages.stern.nyu.edu/~adamodar/

Section principale : "Updated Data". Excel téléchargeables gratuitement.

### Fréquence d'utilisation

Pour un DCF :
- **Vérifier l'ERP implicite** au moment de la valorisation (peut avoir bougé 0.5-1 % vs il y a 6 mois)
- **CRP** plus stable, mise à jour annuelle suffit (sauf événement majeur de souverain)

## Pièges et nuances

### 1. ERP historique vs implicite

Beaucoup d'analystes utilisent l'ERP historique (~5-6 % USA) sans réfléchir. Damodaran montre que :
- **Historique** : 5-6 %, mais varie 4-7 % selon période choisie
- **Implicite** : 4-5 % typique

Différence de 1 % d'ERP change la valorisation de 10-15 %. **Choisir avec rigueur**.

### 2. Risk-free rate

Pour Canada, utiliser le **10-year Government of Canada bond yield**. Pour US, le **10-year Treasury**.

⚠️ Ne **pas utiliser** un taux à plus court terme (3-month T-bill) pour DCF — la durée du modèle exige un taux long.

### 3. Beta sectoriel vs spécifique

Damodaran calcule des betas **sectoriels** (moyenne unleveraged d'un secteur) qui sont plus stables que les betas individuels.

Méthode :
1. Prendre le beta unleveraged sectoriel
2. Re-leverager selon la structure de capital de l'entreprise spécifique :
```
Beta levered = Beta unlevered × (1 + (1 − tax) × D/E)
```

Cette méthode évite les artefacts statistiques des betas spécifiques calculés sur 5 ans (qui peuvent être biaisés par événements idiosyncratiques).

### 4. Période d'estimation du beta

- 5 ans, hebdomadaire : standard de l'industrie
- 2-3 ans : capture mieux les tendances récentes mais plus bruité
- 10 ans : trop long, secteur a peut-être changé

Damodaran préfère 5 ans hebdomadaire.

### 5. Taux d'imposition à utiliser

- **Marginal tax rate** : pour le DCF (le levier fiscal s'applique sur la marge)
- **Effective tax rate** : pour le calcul historique de l'EBIT après impôt
- **Cash tax rate** : pour les cash flows réels

Utiliser le **marginal** pour la projection long-terme.

## Implémentation rapide

```python
# Pour une entreprise canadienne mature
rf = 0.037  # Canada 10-year
erp_mature = 0.0423
crp_canada = 0.0
beta_levered = 1.0  # unleveraged 0.85, ré-leveragé pour D/E ~ 0.3

cost_of_equity = rf + beta_levered * (erp_mature + crp_canada)
# = 0.037 + 1.0 * 0.0423 = 7.93 %

# Coût de la dette (selon rating)
cost_of_debt_pretax = 0.045  # exemple BBB
tax_rate = 0.27  # taux marginal Canada+QC corporatif
cost_of_debt_aftertax = cost_of_debt_pretax * (1 - tax_rate)
# = 3.29 %

# WACC
weight_equity = 0.75
weight_debt = 0.25
wacc = weight_equity * cost_of_equity + weight_debt * cost_of_debt_aftertax
# = 0.75 * 0.0793 + 0.25 * 0.0329 = 6.77 %
```

## Conclusion

L'ERP est **le paramètre le plus sensible** d'un DCF (avec la croissance terminale). Le calculer rigoureusement avec les valeurs Damodaran courantes et le faire varier en sensibilité (±1 %) montre l'incertitude du modèle.

Sans rigueur sur l'ERP, le DCF n'est qu'un exercice de précision fictive.
