# Dimension G — Gouvernance (5 critères)

Les 5 critères de gouvernance évaluent la qualité du management, la discipline d'allocation du capital,
et la transparence financière via des proxies mesurables dans les états financiers.

---

## G1 — Discipline de capital (allocation rigoureuse)

**Logique** : Un ROE élevé (≥ 15%) maintenu sur plusieurs années implique un conseil d'administration
qui surveille activement l'utilisation du capital et des dirigeants capables d'allouer efficacement
les ressources. La durée (proxy via `dividend_years`) valide la consistance dans le temps.

**Proxy** : `roe` ET `dividend_years`

**Seuil standard** :
```
passe = roe >= 0.15 ET dividend_years >= 5
```

**Justification du double critère** :
- `roe >= 0.15` seul peut refléter un exercice exceptionnel ou une manipulation comptable
- `dividend_years >= 5` valide que la performance est soutenue sur plusieurs années
- La combinaison des deux filtre les one-hit wonders et les manipulations temporaires

**Cas partiels** :
```
roe >= 0.15 mais dividend_years absent → passe = False (durée non vérifiable)
roe absent mais dividend_years >= 10 → passe = False (ROE non vérifiable)
roe >= 0.20 ET dividend_years >= 10 → passe = True (signal fort)
```

**Ajustements sectoriels** :
| Secteur | Seuil ROE ajusté |
|---|---|
| Banques | `roe >= 0.10` (bilan différent — ROE structurellement ajusté) |
| Utilities | `roe >= 0.08` (régulation tarifaire) |
| Énergie | `roe >= 0.10` (intensité capitalistique élevée) |

---

## G2 — Transparence financière (prévisibilité des résultats)

**Logique** : Le maintien de dividendes sur ≥ 10 ans consécutifs requiert une planification financière
rigoureuse, une communication transparente avec les actionnaires, et des prévisions fiables. Une entreprise
qui ne peut pas prédire ses flux de trésorerie à 12-18 mois ne peut pas s'engager sur une politique
de dividendes long terme.

**Proxy** : `dividend_years`

**Seuil standard** :
```
passe = dividend_years >= 10
```

**Barème interprétatif** :
| Années dividendes | Lecture G2 |
|---|---|
| ≥ 25 ans | Aristocrate du dividende — transparence exemplaire |
| 10-25 ans | Transparence solide — planification financière démontrée |
| 5-10 ans | Transparence en construction |
| < 5 ans | Historique trop court pour conclure |

**Relation avec G5** : G2 mesure la transparence (10 ans), G5 mesure l'engagement long terme (20 ans).
Une entreprise peut passer G2 mais pas G5 — les deux critères sont complémentaires, non redondants.

**Données absentes** : `dividend_years is None` → `passe = False`

---

## G3 — Prudence de l'endettement (gouvernance des risques financiers)

**Logique** : Un ratio dette/capitaux propres faible (< 1.0) indique un conseil d'administration
conservateur qui refuse l'ingénierie financière excessive. Cette prudence protège les actionnaires
à long terme et signale une gouvernance du risque rigoureuse.

**Proxy** : `debt_equity`

**Seuil standard** :
```
passe = debt_equity <= 1.0
```

**Note** : Ce seuil est plus strict que E3 (≤ 1.5) et S4 (≤ 2.0). La gouvernance exige la plus haute
rigueur — un conseil vraiment prudent garde le D/E sous 1.0.

**Cas spéciaux** :
```
Secteur financier (banques, assurances) :
  → passe = True systématiquement
  → observation : "Secteur financier : dette structurelle — critère G3 non applicable au sens traditionnel"
```

**Ajustements pour secteurs à dette structurelle** :
| Secteur | Seuil ajusté |
|---|---|
| Utilities | `debt_equity <= 2.0` (infrastructure réglementée) |
| Immobilier (REIT) | `debt_equity <= 1.5` |
| Énergie | `debt_equity <= 1.5` |

**Données absentes** : `debt_equity is None` → `passe = False` (sauf secteur financier)

---

## G4 — Création de valeur long terme

**Logique** : Des bénéfices par action positifs et croissants sur 10 ans démontrent qu'un management
travaille dans l'intérêt des actionnaires à long terme, pas seulement à court terme. Ce critère est
intentionnellement minimal (croissance positive suffit) — il filtre les entreprises en déclin structurel,
pas les meilleures d'entre elles.

**Proxy** : `eps_growth_10y`

**Seuil standard** :
```
passe = eps_growth_10y >= 0.0   (croissance totale positive sur 10 ans)
```

**Interprétation** :
- Seuil minimal : même +5% sur 10 ans suffit à passer G4
- L'objectif est d'éliminer les entreprises en stagnation ou déclin, pas de qualifier les meilleurs
- La magnitude de la croissance est capturée par S5 (≥ 30%) et E2 (≥ 50%)

**Cas spéciaux** :
- EPS négatif (pertes) sur 10 ans → passe = False
- EPS volatil avec trend positif → laisser le jugement à Claude avec observation explicite

**Données absentes** : `eps_growth_10y is None` → `passe = False`

---

## G5 — Engagement actionnarial (retour aux actionnaires cohérent)

**Logique** : Une politique de dividendes de ≥ 20 ans consécutifs représente un engagement explicite
envers les actionnaires sur deux décennies. Ce signal fort témoigne d'une gouvernance stable,
d'une culture d'entreprise axée sur la création de valeur durable, et d'un management qui
respecte ses engagements envers les actionnaires même en période difficile.

**Proxy** : `dividend_years`

**Seuil standard** :
```
passe = dividend_years >= 20
```

**Relation avec G2** :
- G2 (10 ans) = transparence financière démontrée
- G5 (20 ans) = engagement actionnarial institutionnel
- Les deux critères mesurent des dimensions différentes de la gouvernance via le même proxy

**Barème interprétatif** :
| Années dividendes | Lecture G5 |
|---|---|
| ≥ 50 ans | Dividend King — engagement multigénérationnel |
| 25-50 ans | Dividend Aristocrat (US) / équivalent canadien |
| 20-25 ans | Engagement actionnarial fort |
| 10-20 ans | Passe G2, échoue G5 — engagement en construction |
| < 10 ans | Historique trop court |

**Exemples canadiens typiques** :
- BNS.TO, TD.TO, RY.TO : >25 ans → passe G5 ✅
- BCE.TO, ENB.TO : >20 ans → passe G5 ✅
- TRI.TO : >20 ans → passe G5 ✅

**Données absentes** : `dividend_years is None` → `passe = False`

---

## Récapitulatif Dimension G

| Critère | Proxy principal | Seuil standard | Exception sectorielle |
|---|---|---|---|
| G1 Discipline capital | ROE + Années dividendes | ROE ≥ 15% ET divid. ≥ 5 ans | Banques : ROE ≥ 10% |
| G2 Transparence financière | Années dividendes | ≥ 10 ans | Aucune |
| G3 Prudence endettement | Debt/Equity | ≤ 1.0 | Banques : passe=True, Utilities : ≤ 2.0 |
| G4 Création valeur LT | EPS growth 10y | ≥ 0% (positif) | Aucune |
| G5 Engagement actionnarial | Années dividendes | ≥ 20 ans | Aucune |

**g_score** = nombre de critères G1-G5 avec `passe = True` (0 à 5)

---

## Note sur la surreprésentation de `dividend_years` en Gouvernance

Trois critères G (G2, G4 via G5, G5) utilisent `dividend_years`. Ce n'est pas un défaut : la politique
de dividendes est l'un des signaux de gouvernance les plus forts et les plus difficiles à manipuler.
En revanche, ce biais exclut mécaniquement les entreprises de croissance qui ne versent pas de dividendes
(Berkshire, Amazon historiquement, Shopify). Cette limitation est à documenter dans `limites` quand applicable.
