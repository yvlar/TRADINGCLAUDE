# DCF — Discounted Cash Flow

## Principe

La valeur intrinsèque d'une entreprise = somme des FCF futurs actualisés au coût du capital + valeur terminale actualisée. La méthode est théoriquement irréprochable mais empiriquement **ultra-sensible aux hypothèses lointaines** — d'où l'importance de la matrice de sensibilité.

## Formule générale

```
Valeur d'entreprise = Σ [FCF_t / (1 + WACC)^t] + VT / (1 + WACC)^n
Valeur des capitaux propres = VE − Dette nette + Cash excédentaire
Prix par action = Valeur des CP / Actions diluées
```

## Calcul du WACC (CMPC)

```
WACC = (E/V) × Re + (D/V) × Rd × (1 − T)
```

| Composante | Définition |
|------------|------------|
| Re | Coût des capitaux propres (CAPM) |
| Rd | Coût marginal de la dette (yield des obligations émises) |
| T | Taux d'imposition effectif |
| E/V, D/V | Pondérations à valeur de marché |

### CAPM pour Re
```
Re = Rf + β × (Rm − Rf)
```

- **Rf** = taux sans risque (bond souverain 10 ans dans la devise de l'entreprise)
- **β** = bêta de l'action vs son indice de référence
- **Rm − Rf** = prime de risque actions implicite (utiliser Damodaran 4.23 % pour mature market en 2026, plus country risk premium pour émergents)

### Pour le Canada
- Rf = rendement obligation Canada 10 ans
- Country risk premium = 0 (Canada noté AAA)
- T = 26.5 % combiné fédéral + Québec (autres provinces ~25-27 %)

## Projection des FCF (5-10 ans)

Chaque année :
```
FCF = EBIT × (1 − T) + D&A − Capex − ΔBFR
```

**Hypothèses à justifier explicitement** :
- Croissance des revenus (chaque année, pas un seul taux moyen)
- Évolution de la marge opérationnelle (pression concurrentielle ? amélioration de l'échelle ?)
- Capex / Sales (steady state vs croissance)
- BFR / Sales (besoin en fonds de roulement)

**Règle d'or de Damodaran** : si l'historique 5 ans contredit ta projection, justifier le pivot ou abandonner. Une projection de 15 % de croissance pour une entreprise qui a fait 3 % les 5 dernières années nécessite une explication structurelle, pas un wishful thinking.

## Valeur terminale

Deux méthodes, à confronter :

### Gordon (croissance perpétuelle)
```
VT = FCF_(n+1) / (WACC − g)
```
- g typiquement 2-3 % (proche de l'inflation long terme)
- Sensibilité explosive : g = 3 % vs g = 2 % avec WACC = 8 % donne VT × 1.20

### Multiples de sortie
```
VT = EBITDA_n × multiple cible
```
- Multiple cohérent avec les pairs matures (10-12× EV/EBITDA pour mature, 6-8× pour cyclique)

**Test de cohérence** : si les deux méthodes divergent de plus de 20 %, investiguer. Souvent le multiple de sortie révèle un g implicite irréaliste dans Gordon.

## Cohérence dynamique (test Damodaran)

Le test que la majorité des DCF amateurs échouent :

```
Croissance soutenable = ROIC × Taux de réinvestissement
```

Si tu projettes 10 % de croissance et 80 % de FCF/EBIT, ton ROIC implicite doit être > 50 % — ce qui est **impossible à long terme** sans monopole structurel. Si ton modèle viole cette équation, soit la croissance est trop élevée, soit le FCF est trop élevé, soit le ROIC implicite est irréaliste.

## Matrice de sensibilité (obligatoire)

Présenter une grille 5×5 :

|  | g = 1.5% | g = 2.0% | g = 2.5% | g = 3.0% | g = 3.5% |
|--|---------|---------|---------|---------|---------|
| WACC = 7% | … | … | … | … | … |
| WACC = 8% | … | … | … | … | … |
| WACC = 9% | … | … | … | … | … |
| WACC = 10% | … | … | … | … | … |
| WACC = 11% | … | … | … | … | … |

La fourchette basse/centrale/haute doit refléter cette dispersion, pas une seule combinaison.

## Cas limites

- **Entreprises non rentables (jeunes SaaS)** : utiliser un DCF en deux phases (croissance haute, puis maturité avec rentabilité positive). Damodaran appelle ça *« story-driven DCF »* — voir le skill damodaran-narrative-and-numbers.
- **Cycliques** : utiliser des marges normalisées sur cycle complet, pas les marges actuelles.
- **Entreprises avec optionalité (biotechs, exploration)** : DCF + valeur d'option (modèle Black-Scholes adapté).
- **Inapplicabilité** : banques, assureurs, REIT — leurs FCF n'ont pas le même sens. Utiliser des méthodes sectorielles spécialisées.

## Sources

- Damodaran, A. *Investment Valuation* (3e éd.) — la référence absolue
- Koller, Goedhart & Wessels — *Valuation: Measuring and Managing the Value of Companies* (McKinsey)
