# Prix de base rajusté (PBR / ACB)

Le **PBR** est le coût fiscal d'un titre — utilisé pour calculer le gain ou la perte en capital à la vente. C'est un sujet apparemment trivial mais source de la majorité des erreurs fiscales chez les investisseurs canadiens.

## Définition

```
PBR par action = (Coût total des achats + frais de courtage à l'achat) / Nombre d'actions
Gain/perte en capital = (Prix de vente − frais de vente) − PBR
```

Le PBR n'est pas le prix d'achat le plus récent — c'est la **moyenne pondérée** de tous les achats (méthode obligatoire au Canada, contrairement aux USA où FIFO/LIFO sont permis).

## Cas standard — plusieurs achats à différents prix

### Exemple
- Janvier 2024 : achat de 100 actions XYZ à 50 $/action + commission 10 $
  - Coût total : 100 × 50 + 10 = 5 010 $
- Juin 2024 : achat de 100 actions XYZ à 60 $/action + commission 10 $
  - Coût additionnel : 100 × 60 + 10 = 6 010 $
- **PBR total** : 5 010 + 6 010 = 11 020 $
- **Actions détenues** : 200
- **PBR par action** : 55.10 $

### Si vente partielle
Vente de 50 actions à 70 $ + frais 10 $ :
- Produit net : 50 × 70 − 10 = 3 490 $
- Coût attribué : 50 × 55.10 = 2 755 $
- **Gain en capital** : 3 490 − 2 755 = 735 $
- PBR mis à jour : (200 − 50) × 55.10 = 8 265 $ pour 150 actions restantes (PBR/action inchangé à 55.10)

## Cas particuliers

### Réinvestissement de dividendes (DRIP)
Chaque dividende réinvesti **augmente le PBR**.
- Dividende reçu : 50 $
- Réinvesti pour acheter 1 action à 50 $
- Nouveau coût total : ancien coût + 50 $
- Nouvelles actions : ancienne quantité + 1

### Distribution de retour de capital (ROC)
Diminue le PBR. Fréquent avec les **fiducies de revenu, REIT, ETF de revenu**.
- Si tu reçois 100 $ de retour de capital, ton PBR diminue de 100 $
- Si le PBR descend à zéro, tout retour de capital subséquent devient un gain en capital immédiat

### Distribution de dividende en titres (stock dividend)
Les nouvelles actions reçues s'ajoutent à un PBR fractionné. Le PBR/action diminue mécaniquement.

### Fractionnement (split) ou regroupement (consolidation)
Le PBR/action est recalculé proportionnellement, mais le PBR total reste identique.
- Split 2:1 → PBR/action divisé par 2
- Consolidation 1:5 → PBR/action multiplié par 5

### Échange d'actions (acquisition payée en actions)
Roulement obligatoire à la valeur comptable selon les règles ITA. Souvent traité automatiquement par le courtier mais à vérifier.

### Conversion CAD ↔ USD
Le PBR doit être tenu **dans la devise de référence fiscale** (CAD pour résident canadien). Une action achetée 100 USD à 1.30 CAD/USD a un PBR de 130 CAD, peu importe le taux à la vente.

## Tracking obligatoire

**Le courtier ne suit pas toujours le PBR correctement.** Cas problématiques fréquents :
- Transferts entre courtiers (le PBR n'est pas toujours transmis)
- Achats sur plusieurs comptes du même titre (le courtier ne voit que son compte)
- DRIP avec accumulation sur plusieurs années
- Distributions de retour de capital mal qualifiées par le courtier
- Successions et changements de propriétaire

**Solution** : tenir un registre personnel du PBR dans un tableur, mis à jour à chaque transaction.

## Outils gratuits pour le tracking

### AdjustedCostBase.ca
Site web canadien gratuit, le plus complet pour le suivi des PBR de titres canadiens et des distributions ROC. Couvre les DRIP, splits, conversions de devise. Recommandé.

### Wealthica
Agrégateur de comptes. Affiche PBR mais à vérifier en cas de transferts.

### Excel maison
Le plus fiable. Une ligne par transaction, formules de PBR moyen pondéré.

## Conséquences d'un mauvais PBR

- **Si PBR sous-estimé** : tu paies trop d'impôt (gain en capital surestimé)
- **Si PBR surestimé** : tu paies trop peu maintenant, mais l'ARC peut te réclamer + intérêts + pénalité en cas de vérification

L'ARC peut vérifier jusqu'à 6 ans en arrière (3 ans normalement, 6 ans si négligence flagrante). Tenir des registres pendant **au moins 7 ans** par sécurité.

## Drapeau rouge à connaître

Si ton courtier affiche un PBR à zéro pour un titre que tu as acheté il y a longtemps, c'est presque certainement une erreur (ou le titre a accumulé tellement de retours de capital qu'il est passé à zéro légitimement). Investiguer avant de vendre — un PBR à zéro signifie que **tout** le produit de vente devient gain en capital.

## En CELI / REER : le PBR n'a pas d'importance

Dans les comptes enregistrés, gains et pertes ne sont pas réalisés fiscalement. **Pas besoin de tenir le PBR.** Cette simplicité est un avantage pratique sous-estimé du CELI/REER au-delà du seul gain fiscal.
