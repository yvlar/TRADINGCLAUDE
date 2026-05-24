# Barème, Verdicts et Exemples Chiffrés

## Barème de scoring

```
esg_score = e_score + s_score + g_score   (0 à 15)
```

| Plage | Verdict | Signification |
|---|---|---|
| 10 - 15 | `ESG_FORT` | Profil ESG solide par proxy — comportements ESG favorables démontrés |
| 5 - 9 | `ESG_MODERE` | Profil ESG mixte — forces et faiblesses coexistent |
| 0 - 4 | `ESG_FAIBLE` | Profil ESG préoccupant — risques ESG matériels potentiels |

**Note sur les scores extrêmes** :
- Score 15/15 : ne signifie pas que l'entreprise est parfaite sur le plan ESG — seulement qu'elle passe tous les proxies financiers
- Score 0/15 : peut refléter des données manquantes plutôt qu'un réel profil ESG désastreux — documenter dans `limites`

---

## Exemples chiffrés par profil

### Profil 1 — Grande banque canadienne (ex : BNS.TO)

**Données** : `sector="Financial Services"`, `revenue_bn=32`, `roe=0.13`, `debt_equity=None` (secteur financier), `dividend_years=28`, `eps_growth_10y=0.45`

| Critère | Proxy | Valeur | Passe ? |
|---|---|---|---|
| E1 Efficience capital | ROE | 13% ≥ 10% (ajusté banque) | ✅ |
| E2 Soutenabilité croissance | EPS + D/E | 45% ≥ 0% (D/E ignoré banque) | ✅ |
| E3 Gestion dette | D/E | N/A — secteur financier | ✅ |
| E4 Maturité | Revenus | 32 Md$ ≥ 1 Md$ | ✅ |
| E5 Longévité | Dividendes | 28 ans ≥ 10 ans | ✅ |
| S1 Capacité parties prenantes | Revenus | 32 Md$ ≥ 5 Md$ | ✅ |
| S2 Stabilité emploi | Dividendes | 28 ans ≥ 15 ans | ✅ |
| S3 Rentabilité équitable | ROE | 13% entre 8-25% (banque) | ✅ |
| S4 Solidité financière | D/E | N/A — secteur financier | ✅ |
| S5 Croissance inclusive | EPS | 45% ≥ 30% | ✅ |
| G1 Discipline capital | ROE + divid. | 13% ≥ 10% ET 28 ≥ 5 | ✅ |
| G2 Transparence | Dividendes | 28 ans ≥ 10 ans | ✅ |
| G3 Prudence endettement | D/E | N/A — secteur financier | ✅ |
| G4 Création valeur LT | EPS | 45% ≥ 0% | ✅ |
| G5 Engagement actionnarial | Dividendes | 28 ans ≥ 20 ans | ✅ |

**Résultat** : E=5, S=5, G=5 → **esg_score=15, ESG_FORT**
*Note : Score élevé reflète en partie les ajustements sectoriels favorables aux banques.*

---

### Profil 2 — Entreprise technologique en croissance (ex : Shopify)

**Données** : `sector="Technology"`, `revenue_bn=8`, `roe=0.05`, `debt_equity=0.2`, `dividend_years=None` (pas de dividendes), `eps_growth_10y=None` (perte récentes)

| Critère | Proxy | Valeur | Passe ? |
|---|---|---|---|
| E1 Efficience capital | ROE | 5% < 15% (tech) | ❌ |
| E2 Soutenabilité croissance | EPS + D/E | EPS absent | ❌ |
| E3 Gestion dette | D/E | 0.2 ≤ 1.5 | ✅ |
| E4 Maturité | Revenus | 8 Md$ ≥ 1 Md$ | ✅ |
| E5 Longévité | Dividendes | Absent | ❌ |
| S1 Capacité parties prenantes | Revenus | 8 Md$ ≥ 5 Md$ | ✅ |
| S2 Stabilité emploi | Dividendes | Absent | ❌ |
| S3 Rentabilité équitable | ROE | 5% < 12% (tech) | ❌ |
| S4 Solidité financière | D/E | 0.2 ≤ 2.0 | ✅ |
| S5 Croissance inclusive | EPS | Absent | ❌ |
| G1 Discipline capital | ROE + divid. | divid. absent | ❌ |
| G2 Transparence | Dividendes | Absent | ❌ |
| G3 Prudence endettement | D/E | 0.2 ≤ 1.0 | ✅ |
| G4 Création valeur LT | EPS | Absent | ❌ |
| G5 Engagement actionnarial | Dividendes | Absent | ❌ |

**Résultat** : E=2, S=2, G=1 → **esg_score=5, ESG_MODERE**
*Note : Score bas reflète le biais du cadre contre les entreprises de croissance sans dividendes, pas nécessairement un mauvais profil ESG réel. À documenter dans `limites`.*

---

### Profil 3 — Entreprise industrielle surendettée

**Données** : `sector="Industrials"`, `revenue_bn=2`, `roe=0.08`, `debt_equity=3.5`, `dividend_years=3`, `eps_growth_10y=-0.15`

| Critère | Proxy | Valeur | Passe ? |
|---|---|---|---|
| E1 Efficience capital | ROE | 8% < 12% | ❌ |
| E2 Soutenabilité croissance | EPS + D/E | EPS<0 OU D/E > 2.0 | ❌ |
| E3 Gestion dette | D/E | 3.5 > 1.5 | ❌ |
| E4 Maturité | Revenus | 2 Md$ ≥ 1 Md$ | ✅ |
| E5 Longévité | Dividendes | 3 ans < 10 ans | ❌ |
| S1 Capacité parties prenantes | Revenus | 2 Md$ < 5 Md$ | ❌ |
| S2 Stabilité emploi | Dividendes | 3 ans < 15 ans | ❌ |
| S3 Rentabilité équitable | ROE | 8% < 10% | ❌ |
| S4 Solidité financière | D/E | 3.5 > 2.0 | ❌ |
| S5 Croissance inclusive | EPS | -15% < 0% | ❌ |
| G1 Discipline capital | ROE + divid. | ROE < 15% ET divid. < 5 | ❌ |
| G2 Transparence | Dividendes | 3 ans < 10 ans | ❌ |
| G3 Prudence endettement | D/E | 3.5 > 1.0 | ❌ |
| G4 Création valeur LT | EPS | -15% < 0% | ❌ |
| G5 Engagement actionnarial | Dividendes | 3 ans < 20 ans | ❌ |

**Résultat** : E=1, S=0, G=0 → **esg_score=1, ESG_FAIBLE**

---

## Règles de rédaction du `verdict_detail`

Le champ `verdict_detail` (2-3 phrases) doit :
1. Contextualiser le score global avec la dimension la plus forte et la plus faible
2. Mentionner le secteur si un ajustement sectoriel a été appliqué
3. Signaler si le score est influencé par des données manquantes

**Exemple ESG_FORT** :
> "BNS.TO affiche un profil ESG proxy solide (15/15) avec une domination dans les trois dimensions.
> Les 28 années consécutives de dividendes signalent une gouvernance stable et un engagement actionnarial
> durable. L'ajustement sectoriel bancaire a rendu non applicables les critères de dette (E3, G3, S4),
> ce qui favorise mécaniquement le score — une notation ESG primaire (MSCI) est recommandée pour validation."

**Exemple ESG_MODERE** :
> "Le profil ESG proxy (5/15) est pénalisé principalement par l'absence de politique de dividendes,
> qui rend non mesurables plusieurs critères S et G nécessitant cet historique. La faible dette (D/E=0.2)
> et la taille (8 Md$) sont deux points favorables. Ce cadre proxy sous-évalue structurellement les
> entreprises de croissance tech — croiser avec une source ESG primaire avant toute décision."

---

## Interprétation dans le contexte d'investissement

| Score ESG | Impact sur la décision d'investissement |
|---|---|
| ESG_FORT (10-15) | Aucun signal négatif ESG — procéder à l'analyse fondamentale normale |
| ESG_MODERE (5-9) | Surveillance — identifier les dimensions faibles et leur cause |
| ESG_FAIBLE (0-4) | Signal d'alerte — investiguer les causes avant position |

**Important** : Un score ESG_FAIBLE n'est PAS un signal de vente ou de refus automatique.
C'est un signal d'investigation approfondie (sources primaires, actualité, politique ESG publiée).
L'ESG simplifié est un outil de surveillance, pas un filtre éliminatoire.
