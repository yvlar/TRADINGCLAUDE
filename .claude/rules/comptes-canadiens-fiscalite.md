---
paths:
  - "app/skills/tier2/canadian_tax/**"
  - "analyses/**"
---

# Comptes canadiens et fiscalité québécoise

## Quand cette règle s'applique

Lors de l'édition du skill `canadian_tax` ou de la rédaction d'analyses incluant des recommandations d'allocation par compte ou des considérations fiscales.

## Règles

### Comptes enregistrés — priorités

| Compte | Sigle EN | Avantage principal | Priorité |
|---|---|---|---|
| **CELI** | TFSA | Croissance libre d'impôt, retraits flexibles | 1 — maximiser en premier |
| **CELIAPP** | FHSA | Déduction + croissance libre d'impôt pour achat propriété | 2 — si achat propriété envisagé |
| **REER** | RRSP | Déduction fiscale, horizon long terme | 3 — cotiser selon revenu marginal |
| **REEE** | RESP | Subventions gouvernementales pour éducation des enfants | Spécialisé |
| **Marge Atout Desjardins** | HELOC | Smith Manœuvre — levier | Avec prudence et traçabilité |

### Cadre fiscal — Québec

- **Gains en capital** : 50 % inclusion (particulier) — ex. gain de 10 000 $ = 5 000 $ imposables
- **Dividendes canadiens éligibles** : crédit d'impôt applicable — traitement préférentiel vs intérêts
- **Dividendes ordinaires** : moins favorables que les dividendes éligibles
- **Intérêts d'emprunt** : déductibles si les fonds empruntés sont investis dans des placements générateurs de revenus (Smith Manœuvre) — documenter la traçabilité pour l'ARC/Revenu Québec
- **Retenue à la source US (15 %)** : sur dividendes US dans CELI — non récupérable ; récupérable dans REER via convention fiscale Canada-États-Unis
- **Règle de perte apparente** : vente et rachat du même titre dans les 30 jours — perte en capital refusée par l'ARC

### Logique d'allocation par compte

| Type de revenu / actif | Compte recommandé | Raison |
|---|---|---|
| Actions US à dividendes | REER | Évite la retenue 15 % non récupérable du CELI |
| Actions CA à dividendes éligibles | CELI | Dividendes déjà avantageux, croissance libre d'impôt |
| Actions de croissance (pas de dividendes) | CELI | Maximise la valeur de l'espace libre d'impôt |
| Obligations et revenus d'intérêts | REER | Revenu entièrement imposable — mieux à l'abri |
| ETF indiciels larges (ex. XEQT) | CELI ou REER selon l'espace disponible | |

### Smith Manœuvre

Stratégie de conversion d'intérêts non déductibles (hypothèque) en intérêts déductibles (investissement) :
- Les fonds empruntés via HELOC **doivent** être investis dans des placements générateurs de revenus
- Documenter chaque transfert — l'ARC et Revenu Québec exigent la traçabilité
- Toujours mentionner le risque d'effet de levier dans les recommandations
- Distinguer explicitement compte enregistré vs non enregistré dans l'analyse
