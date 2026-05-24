# Dimension S — Social (5 critères)

Les 5 critères sociaux évaluent la capacité de l'entreprise à créer et maintenir de la valeur pour
ses employés, clients, et communautés, via des proxies financiers de stabilité et de taille.

---

## S1 — Capacité à rémunérer les parties prenantes

**Logique** : Les grandes entreprises (revenus ≥ 5 Md$) disposent d'économies d'échelle suffisantes pour
offrir des avantages sociaux substantiels (assurances, retraites, formation), financer des programmes
communautaires, et maintenir des relations fournisseurs équitables. La taille est un proxy imparfait
mais corrélé aux ressources disponibles pour les parties prenantes.

**Proxy** : `revenue_bn`

**Seuil standard** :
```
passe = revenue_bn >= 5.0   (5 milliards $)
```

**Barème interprétatif** :
| Revenus | Lecture S1 |
|---|---|
| ≥ 20 Md$ | Grandes capacités sociales — multinationale |
| 5-20 Md$ | Ressources suffisantes pour programmes sociaux structurés |
| 1-5 Md$ | Ressources limitées mais présentes |
| < 1 Md$ | Ressources insuffisantes pour programmes sociaux significatifs |

**Note** : Ce critère avantage mécaniquement les grandes capitalisations. Documenter cet biais dans `limites`.

**Données absentes** : `revenue_bn is None` → `passe = False`

---

## S2 — Stabilité de l'emploi

**Logique** : Une entreprise qui verse des dividendes depuis ≥ 15 ans consécutifs a traversé plusieurs
cycles économiques (2008-09, 2020, etc.) en maintenant ses opérations. Cette continuité implique une
capacité démontrée à conserver ses équipes et maintenir des emplois stables même en période difficile.

**Proxy** : `dividend_years`

**Seuil standard** :
```
passe = dividend_years >= 15
```

**Interprétation** :
- 15 ans couvrent au minimum la crise financière de 2008-2009 — test de résilience significatif
- Une entreprise qui a maintenu ses dividendes 15+ ans a structurellement préservé ses emplois
- Ne s'applique pas aux entreprises de croissance sans politique de dividendes — observation contextuelle

**Ajustements** :
| Situation | Traitement |
|---|---|
| Entreprise tech/croissance sans dividendes | `passe = False` + "Politique sans dividendes — proxy S2 non applicable" |
| Dividende initié récemment (< 15 ans) mais entreprise ancienne | `passe = False` |

**Données absentes** : `dividend_years is None` → `passe = False`

---

## S3 — Rentabilité équitable (partage de la valeur créée)

**Logique** : Un ROE entre 10% et 30% représente un équilibre sain entre rémunération des actionnaires
et réinvestissement dans l'entreprise (salaires, R&D, conditions de travail). Un ROE excessif (> 30%)
peut signaler une extraction agressive au détriment des employés et des investissements sociaux.
Un ROE trop faible (< 10%) indique une création de valeur insuffisante pour partager.

**Proxy** : `roe`

**Seuil standard** :
```
passe = 0.10 <= roe <= 0.30
```

**Interprétation des cas limites** :
| ROE | Lecture S3 |
|---|---|
| > 30% | ROE excessif — potentielle extraction agressive de valeur |
| 10-30% | Zone équilibrée — partage sain de la valeur |
| 8-10% | Zone grise — acceptable pour secteurs à forte intensité capitalistique |
| < 8% | Création de valeur insuffisante |

**Ajustements sectoriels** :
| Secteur | Seuil ajusté |
|---|---|
| Banques | `0.08 <= roe <= 0.25` (seuils ajustés — bilan différent) |
| Utilities | `0.07 <= roe <= 0.20` |
| Technologie | `0.12 <= roe <= 0.40` (ROE plus élevé structurel) |

**Données absentes** : `roe is None` → `passe = False`

---

## S4 — Solidité financière (protection des employés en cas de choc)

**Logique** : Un levier financier modéré protège les emplois en période de crise. Les entreprises
surendettées sont forcées de procéder à des licenciements massifs ou des restructurations brutales
pour honorer leurs obligations financières. La solidité du bilan est donc une forme de protection sociale.

**Proxy** : `debt_equity`

**Seuil standard** :
```
passe = debt_equity <= 2.0
```

**Justification du seuil 2.0 (vs 1.5 pour E3)** :
- E3 mesure la prudence environnementale — seuil plus strict
- S4 mesure la protection sociale minimale — seuil plus permissif
- Un D/E de 2.0 est gérable avec des flux de trésorerie positifs

**Cas spéciaux** :
```
Secteur financier :
  → passe = True systématiquement (dette structurelle)
  → observation : "Secteur financier : dette structurelle — critère S4 non applicable"

Utilities / REIT :
  → passe si debt_equity <= 3.0
```

**Données absentes** : `debt_equity is None` → `passe = False`

---

## S5 — Croissance inclusive (BPA croissant = partage de la prospérité)

**Logique** : Une entreprise dont les bénéfices par action croissent de ≥ 30% sur 10 ans génère
suffisamment de surplus pour redistribuer davantage aux parties prenantes (salaires, avantages sociaux,
investissements communautaires). La croissance profitable est une condition nécessaire (mais non suffisante)
à la distribution inclusive de valeur.

**Proxy** : `eps_growth_10y`

**Seuil standard** :
```
passe = eps_growth_10y >= 0.30   (30% cumulé sur 10 ans ≈ 2.7% CAGR)
```

**Barème interprétatif** :
| Croissance BPA 10 ans | Lecture S5 |
|---|---|
| ≥ 100% | Croissance forte — surplus abondant |
| 50-100% | Croissance saine — redistribution possible |
| 30-50% | Croissance modeste mais positive |
| 0-30% | Croissance insuffisante pour redistribution significative |
| < 0% | Bénéfices en recul — redistribution compromise |

**Ajustements sectoriels** :
| Secteur | Seuil ajusté |
|---|---|
| Utilities | `eps_growth_10y >= 0.15` (secteur défensif à faible croissance) |
| Énergie | Cyclique — évaluer un cycle complet, seuil standard maintenu |

**Données absentes** : `eps_growth_10y is None` → `passe = False`

---

## Récapitulatif Dimension S

| Critère | Proxy principal | Seuil standard | Exception sectorielle |
|---|---|---|---|
| S1 Capacité parties prenantes | Revenus (Md$) | ≥ 5.0 Md$ | Aucune |
| S2 Stabilité emploi | Années dividendes | ≥ 15 ans | Tech/croissance : observation contextuelle |
| S3 Rentabilité équitable | ROE | 10% ≤ ROE ≤ 30% | Banques : 8-25%, Tech : 12-40% |
| S4 Solidité financière | Debt/Equity | ≤ 2.0 | Banques : passe=True, Utilities : ≤ 3.0 |
| S5 Croissance inclusive | EPS growth 10y | ≥ 30% | Utilities : ≥ 15% |

**s_score** = nombre de critères S1-S5 avec `passe = True` (0 à 5)
