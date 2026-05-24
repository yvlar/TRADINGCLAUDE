# Types de revenus de placement et leur traitement fiscal

⚠️ Taux 2026 pour résident du Québec en haut taux marginal (~53.31 %). Vérifier via web_search pour valeurs courantes.

## Tableau récapitulatif (haut taux Québec)

| Type de revenu | Taux marginal effectif | Pire / Meilleur |
|----------------|------------------------|-----------------|
| Intérêts | ~53 % | Le **pire** |
| Dividendes ordinaires (sociétés privées canadiennes au petit taux) | ~48 % | Mauvais |
| Dividendes éligibles (sociétés canadiennes publiques) | ~40 % | Bon |
| Dividendes étrangers (US et autres) | ~53 % | Mauvais |
| Gains en capital | ~26.65 % (50 % × 53.31 %) | Le **meilleur** |

## Intérêts

- **Imposés à 100 %** au taux marginal
- Le pire traitement fiscal disponible
- **Sources** : obligations, GIC, comptes d'épargne haut intérêt, fonds obligataires
- **À privilégier dans REER ou CELI** — jamais en non-enregistré si possible

## Dividendes éligibles canadiens

Sociétés canadiennes publiques imposées au **taux corporatif général** (~25-27 %).

### Mécanique
1. **Majoration (gross-up)** : le montant reçu est multiplié par 1.38 (38 %)
2. **Crédit d'impôt fédéral** : 15.0198 % du montant majoré
3. **Crédit d'impôt provincial Québec** : 11.7 % du montant majoré

### Exemple
Dividende reçu : 100 $
- Majoration : 138 $ ajoutés au revenu imposable
- Impôt brut (haut taux 53.31 %) : ~73.57 $
- Crédit fédéral : 138 × 15.0198 % = 20.73 $
- Crédit provincial : 138 × 11.7 % = 16.15 $
- Impôt net : 73.57 − 20.73 − 16.15 = 36.69 $
- **Taux effectif : ~36.7 %** (plus proche de 40 % en pratique avec d'autres ajustements)

### Cas particulier des dividendes en CELI
Pas d'impôt mais **pas de crédit pour dividende** non plus. C'est mathématiquement équivalent puisque le revenu n'est pas imposé. **Net** : zéro impôt sur ces dividendes, optimisé.

## Dividendes ordinaires (non éligibles)

Sociétés privées canadiennes imposées au **petit taux corporatif** (sociétés exploitant une entreprise active, jusqu'à 500k$ de revenu admissible).

- Majoration de 15 %
- Crédits réduits proportionnellement
- **Taux effectif Québec haut revenu : ~48 %**

Pertinent surtout pour les actionnaires de PME. Pour l'investisseur en actions cotées, ce type de dividende est rare.

## Dividendes étrangers (US et autres)

- **Imposés à 100 %** au taux marginal au Canada
- **Pas de crédit pour dividende** canadien (le crédit est réservé aux dividendes de sociétés canadiennes)
- **Retenue à la source de 15 %** (US) selon convention fiscale Canada-US
- **Créditable** au Canada via crédit pour impôt étranger (compte non-enreg seulement)

### Compte CELI vs REER pour dividendes US
- **CELI** : retenue 15 % NON récupérable → perte sèche
- **REER** : exempté de retenue par convention fiscale (titres directs seulement)
- **Non-enreg** : retenue 15 % créditable, mais impôt complet sur le brut

### Piège des ETF canadiens détenant des actions US
La retenue 15 % s'applique **au niveau de l'ETF** avant distribution. Mettre un ETF canadien (ex. VFV, XUS) en REER **ne donne pas** l'exemption. Pour bénéficier de l'exemption REER, il faut détenir des actions US **directement** ou un ETF coté aux US (ex. VOO).

## Gains en capital

- **Inclusion à 50 %** dans le revenu imposable
- Au haut taux Québec : 50 % × 53.31 % = **~26.65 %**
- Réalisés seulement (paper gains non imposés)

### Pertes en capital
- Déductibles **uniquement contre des gains en capital** (pas contre revenu d'intérêts ou dividendes)
- Report en arrière : 3 ans
- Report en avant : indéfini
- Voir `references/strategies-fin-annee.md` pour la récolte de pertes

### Statut historique : tentative d'inclusion 67 %
Une proposition de hausse à 67 % avait été annoncée en 2024 puis abandonnée fin 2024 / début 2025. À surveiller à chaque budget fédéral. Pour 2026, l'inclusion reste à 50 %.

## Cas particulier : revenu d'entreprise active

Si l'investissement génère du revenu d'entreprise (achat-vente fréquent, day-trading), l'ARC peut requalifier en revenu d'entreprise (100 % imposé) plutôt qu'en gain en capital. Critères de l'ARC :
- Fréquence des transactions
- Période de détention courte
- Connaissance des marchés
- Temps consacré
- Lien avec l'occupation principale

**Si tu fais > 200 transactions/an avec holding period < 30 jours**, risque significatif de requalification. Documenter sa stratégie d'investissement à long terme aide à défendre le statut de capital gains en cas de vérification.

## Types de revenus dans l'ordre de priorité fiscale

Du **plus efficace** au moins efficace :
1. Gain en capital non réalisé (zéro)
2. Gain en capital réalisé (~27 %)
3. Dividendes éligibles canadiens (~40 %)
4. Dividendes étrangers + intérêts (~53 %)

Cette hiérarchie explique pourquoi **les vrais investisseurs long-terme privilégient les actions à croissance composée** plutôt que les actions à dividendes : le report d'imposition (gains non réalisés) est un avantage massif sur 20-30 ans.
