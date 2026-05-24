# canadian-tax-considerations

Considérations fiscales canadiennes pour l'investisseur — comptes enregistrés (CELI/REER/CELIAPP), retenues d'impôt US, PBR/ACB, Norbert's Gambit, stratégies de fin d'année.

## À quoi ça sert

Optimiser **après-impôt** plutôt qu'avant-impôt. Pour un investisseur québécois, la différence peut atteindre **30-50 % du rendement final** sur des décennies.

Cinq dimensions principales :

1. **Comptes enregistrés** : CELI, REER, CELIAPP — quel actif dans quel compte
2. **Types de revenus** : intérêts, dividendes canadiens (DTC), dividendes étrangers, gains en capital
3. **PBR/ACB** : Prix de Base Rajusté pour calcul des gains en capital
4. **Retenues d'impôt US** : 15 % sur dividendes US (sauf REER), Foreign Tax Credit
5. **Norbert's Gambit** : conversion CAD ↔ USD à coût quasi-nul

Plus les **stratégies de fin d'année** : tax-loss harvesting, contributions REER, planification CELI.

## Quand l'utiliser

- "REER ou CELI pour mes actions américaines ?"
- "Calcule mon PBR sur AAPL après plusieurs achats"
- "Norbert's Gambit pour 50 000 USD chez Disnat ?"
- "Tax-loss harvesting avant le 31 décembre ?"
- "Quel taux marginal québécois 2026 sur 120 000 $ ?"

## Quand ne pas l'utiliser

- Pour les non-résidents canadiens
- Pour les corporations (régime différent)
- Pour les fiducies (OFCT, Trusts) — règles complexes spécifiques

## Composants

```
canadian-tax-considerations/
├── SKILL.md
├── references/
│   ├── comptes-enregistres.md       ← CELI / REER / CELIAPP / FERR
│   ├── types-revenus.md             ← Intérêts, dividendes (DTC), gains en capital
│   ├── pbr-acb.md                   ← Calcul Prix de Base Rajusté
│   ├── retenues-us.md               ← 15% withholding + Foreign Tax Credit
│   ├── strategies-fin-annee.md      ← Tax-loss harvesting, last contributions
│   └── norberts-gambit.md           ← Conversion devise low-cost
├── scripts/
│   ├── calc_taux_marginal.py        ← Taux marginal QC + fédéral 2026
│   ├── calc_pbr.py                  ← ACB après achats multiples
│   └── calc_norberts_gambit.py      ← Économies vs conversion bancaire
└── evals/
    └── evals.json
```

## Choix d'allocation par compte

| Type de revenu | CELI | REER | Compte non-enregistré |
|----------------|------|------|------------------------|
| **Dividendes canadiens** | Bon | OK | **Optimal** (DTC) |
| **Dividendes US** | OK (15% retenu perdu) | **Optimal** (pas de retenue) | OK (FTC récupère) |
| **Intérêts (obligations)** | **Optimal** | Bon | Mauvais (taxé plein) |
| **Croissance pure (no div)** | **Optimal** | Bon | OK (gain en capital 50%) |
| **REITs** | **Optimal** (distributions taxables) | Bon | Mauvais |

## Taux marginaux Québec 2026 (référentiel)

⚠️ Vérifier valeurs courantes — tranches indexées annuellement.

| Tranche revenu | Fédéral | Québec | Combiné |
|----------------|---------|--------|---------|
| 0 - 53 359 $ | 15 % | 14 % | ~29 % |
| 53 359 - 106 717 $ | 20.5 % | 19 % | ~39.5 % |
| 106 717 - 165 430 $ | 26 % | 24 % | ~50 % |
| 165 430 - 235 675 $ | 29 % | 25.75 % | ~54 % |
| 235 675 $ + | 33 % | 25.75 % | **~54.4 %** (top marginal QC) |

Sur dividendes canadiens éligibles : taux marginal effectif réduit grâce au crédit d'impôt pour dividendes (DTC). Top : ~40 %.

Sur gains en capital : taux marginal × 50 % (inclusion rate). Top QC : ~27 %.

## Exemples d'utilisation

### Via prompt

> "J'ai 100 actions AAPL achetées en 4 lots à des prix différents. Calcule mon PBR moyen."

> "REER ou CELI pour mes actions canadiennes à dividendes ?"

### Via script direct

```bash
cd canadian-tax-considerations
python scripts/calc_taux_marginal.py --revenu 120000 --province QC
python scripts/calc_pbr.py --achats "100@150,50@180,75@200"
python scripts/calc_norberts_gambit.py --montant 50000 --courtier disnat
```

## Norbert's Gambit — économie typique

Conversion 50 000 CAD → USD :
- **Banque traditionnelle** (RBC Direct) : spread ~1.5 % = perte 750 USD
- **Norbert's Gambit** (Disnat, Questrade) : spread ~0.05 % + commissions ~10$ = perte ~35 USD
- **Économie** : ~715 USD par 50 000 USD converti

## Stratégies de fin d'année

À considérer en novembre-décembre :

1. **Tax-loss harvesting** : vendre les positions en perte pour réaliser le loss avant 31 décembre
2. **Superficial loss rule** : ne pas racheter les mêmes titres dans les 30 jours (sinon perte refusée)
3. **Contribution REER** : limite avant 1er mars de l'année suivante pour annee fiscale précédente
4. **Contribution CELI** : limite annuelle 7 000 $ en 2026 (à confirmer)
5. **CELIAPP** : 8 000 $/an, 40 000 $ lifetime — premier acheteur seulement

## Ce qu'il ne fait pas

- Ne remplace pas un fiscaliste professionnel pour situations complexes
- Ne couvre pas les options stock employees, REER de groupe, RSU/PSU avec règles particulières
- Ne couvre pas les holdings via société (régime corporatif différent)

## Garde-fous

- Les **règles fiscales changent** chaque année (budget fédéral mars, budget Québec mars)
- Le **Inclusion rate des gains en capital** était à 66.67 % au-dessus de 250 k$ (proposition 2024) — vérifier statut courant
- Les **CELIAPP** sont assez nouveaux — règles évolutives
- Toujours **garder les preuves d'achat** (PBR) — ARC peut demander 6 ans rétroactivement

## Voir aussi

- [investment-thesis-builder](../investment-thesis-builder/) — intégrer les considérations fiscales dans la thèse
- Site Revenu Québec : revenuquebec.ca
- Site ARC : canada.ca/fr/agence-revenu
