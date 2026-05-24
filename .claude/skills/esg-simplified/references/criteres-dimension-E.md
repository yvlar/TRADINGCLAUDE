# Dimension E — Environnement (5 critères)

Les 5 critères environnementaux évaluent la soutenabilité opérationnelle de l'entreprise via des proxies
financiers. Ils ne mesurent pas les émissions directes ou l'empreinte carbone.

---

## E1 — Efficience du capital

**Logique** : Un ROE élevé et stable indique une utilisation efficiente des ressources — moins de capital immobilisé
pour produire la même valeur. Les entreprises qui gaspillent les ressources tendent à avoir un ROE dégradé.

**Proxy** : `roe` (Return on Equity)

**Seuil standard** :
```
passe = roe >= 0.12   (12%)
```

**Ajustements sectoriels** :
| Secteur | Seuil ajusté | Justification |
|---|---|---|
| Énergie, Mines | `roe >= 0.08` (8%) | Intensité capitalistique élevée réduit structurellement le ROE |
| Utilities | `roe >= 0.08` (8%) | Régulation tarifaire plafonne le ROE |
| Technologie | `roe >= 0.15` (15%) | Faible actif physique — ROE doit être plus élevé |
| Finance / Banques | `roe >= 0.10` (10%) | Bilan structurellement différent — ajustement modéré |

**Données absentes** :
- `roe is None` → `passe = False`, observation "Données ROE indisponibles — proxy E1 non calculable"

---

## E2 — Soutenabilité de la croissance

**Logique** : Une croissance BPA solide sur 10 ans sans endettement excessif démontre un modèle économique
durable et efficace en ressources. La croissance par la dette est moins soutenable que la croissance organique.

**Proxy** : `eps_growth_10y` + `debt_equity`

**Seuil standard** :
```
passe = eps_growth_10y >= 0.50 ET debt_equity <= 2.0
```
*(50% de croissance cumulée sur 10 ans = ~4% CAGR)*

**Cas partiels** :
```
Si eps_growth_10y absent et debt_equity <= 1.5 → passe = True (faible endettement seul suffisant)
Si eps_growth_10y absent et debt_equity absent → passe = False (données insuffisantes)
Si eps_growth_10y >= 0.50 et debt_equity absent → passe = True (croissance suffit, dette inconnue)
```

**Ajustements sectoriels** :
| Secteur | Ajustement |
|---|---|
| Banques | Croissance BPA suffit si positive ; ignorer `debt_equity` (structurellement élevé) |
| Utilities | Croissance BPA ≥ 20% sur 10 ans suffit (secteur défensif à faible croissance) |
| Énergie | Cyclique — cycle complet préférable à 10 ans linéaires |

---

## E3 — Gestion de la dette (impact environnemental indirect)

**Logique** : Les entreprises fortement endettées sont contraintes de réduire leurs investissements ESG
en période de stress financier. Un levier modéré préserve la capacité à financer des transitions environnementales.

**Proxy** : `debt_equity`

**Seuil standard** :
```
passe = debt_equity <= 1.5
```

**Cas spéciaux** :
```
Secteur financier (banques, assurances) :
  → passe = True systématiquement
  → observation : "Secteur financier : dette structurelle — critère E3 non applicable"
```

**Ajustements sectoriels non-financiers** :
| Secteur | Seuil ajusté |
|---|---|
| Utilities | `debt_equity <= 3.0` (infrastructure réglementée, dette normale) |
| Immobilier (REIT) | `debt_equity <= 2.0` |
| Énergie | `debt_equity <= 2.0` |

**Données absentes** : `debt_equity is None` → `passe = False` (prudence par défaut) sauf secteur financier.

---

## E4 — Maturité et stabilité (résilience aux transitions environnementales)

**Logique** : Les entreprises établies (revenus ≥ 1 Md$) ont les ressources financières, les équipes, et
l'accès aux marchés de capitaux pour absorber les coûts de transition environnementale. Les micro-caps
sont structurellement moins résilientes aux chocs ESG.

**Proxy** : `revenue_bn` (revenus annuels en milliards)

**Seuil standard** :
```
passe = revenue_bn >= 1.0   (1 milliard $)
```

**Barème interprétatif** :
| Revenus | Lecture E4 |
|---|---|
| ≥ 10 Md$ | Ressources ESG importantes — grande entreprise |
| 1-10 Md$ | Ressources suffisantes — mid-cap |
| 0.1-1 Md$ | Ressources limitées — small-cap |
| < 0.1 Md$ | Ressources très limitées — micro-cap |

**Données absentes** : `revenue_bn is None` → `passe = False`

---

## E5 — Longévité opérationnelle (optimisation continue des processus)

**Logique** : Une entreprise profitable depuis ≥ 10 ans a nécessairement optimisé ses processus opérationnels.
Cette optimisation longue durée est une forme indirecte d'efficience environnementale (moins de gaspillage
par unité produite vs une entreprise jeune encore en apprentissage).

**Proxy** : `dividend_years` (années consécutives de dividendes)

**Seuil standard** :
```
passe = dividend_years >= 10
```

**Interprétation** :
- Les dividendes exigent des flux de trésorerie réels — une entreprise ne peut maintenir les dividendes
  10 ans de suite sans opérations optimisées et profitables.
- Ne s'applique pas aux entreprises de croissance qui ne versent pas de dividendes (ex. tech non profitable).
  Dans ce cas : données absentes → `passe = False` avec observation contextualisant.

**Données absentes** : `dividend_years is None` → `passe = False`

---

## Récapitulatif Dimension E

| Critère | Proxy principal | Seuil standard | Exception sectorielle |
|---|---|---|---|
| E1 Efficience capital | ROE | ≥ 12% | 8% énergie/utilities, 15% tech |
| E2 Soutenabilité croissance | EPS growth 10y + D/E | ≥ 50% ET D/E ≤ 2.0 | Banques : ignorer D/E |
| E3 Gestion dette | Debt/Equity | ≤ 1.5 | Banques : passe=True systématique |
| E4 Maturité entreprise | Revenus (Md$) | ≥ 1.0 Md$ | Aucune |
| E5 Longévité opérationnelle | Années dividendes | ≥ 10 ans | Tech croissance : données absentes acceptable |

**e_score** = nombre de critères E1-E5 avec `passe = True` (0 à 5)
