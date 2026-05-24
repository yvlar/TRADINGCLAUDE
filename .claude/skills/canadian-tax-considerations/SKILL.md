---
name: canadian-tax-considerations
description: Optimise les décisions de placement selon la fiscalité canadienne et québécoise — comptes enregistrés (CELI, REER, CELIAPP, REEE), traitement des dividendes éligibles vs ordinaires, gains en capital à 50%, prix de base rajusté (PBR/ACB), retenues d'impôt américain, règles de perte apparente, Norbert's Gambit. À utiliser dès que l'utilisateur mentionne CELI, TFSA, REER, RRSP, CELIAPP, FHSA, REEE, RESP, fiscalité, dividendes éligibles, gain en capital, ACB, PBR, retenue impôt US, W-8BEN, Norbert's Gambit, perte apparente, ou veut savoir dans quel compte placer un titre. Utilise toujours ce skill avant de décider dans quel compte loger un investissement, ou avant une opération de fin d'année.
---

# Fiscalité canadienne et québécoise pour l'investisseur

Le rendement après impôt est ce qui compte vraiment. L'écart entre une stratégie naïve et une stratégie fiscalement optimisée peut atteindre 1-2 % par an composés — sur 30 ans, c'est la différence entre une retraite confortable et une retraite difficile.

## Quand utiliser quelle référence

| Question posée | Référence |
|----------------|-----------|
| Quel compte enregistré utiliser ? | `references/comptes-enregistres.md` |
| Comment sont taxés mes dividendes / gains / intérêts ? | `references/types-revenus-placement.md` |
| Comment calculer mon PBR (ACB) ? | `references/pbr-acb.md` |
| Détails sur retenues US et W-8BEN | `references/retenues-impot-us.md` |
| Stratégies de fin d'année | `references/strategies-fin-annee.md` |
| Norbert's Gambit (conversion CAD↔USD) | `references/norberts-gambit.md` |

## Hiérarchie de priorité (synthèse)

1. **CELI** — toujours, pour la croissance long terme (titres canadiens)
2. **CELIAPP** — si projet d'achat immobilier dans 15 ans
3. **REEE** — si enfant, jusqu'à 2 500 $/an pour la subvention
4. **REER** — si haut taux marginal actuel > taux anticipé à la retraite
5. **Compte non-enregistré** — pour le surplus

## Décision rapide : où loger quel actif

| Type d'actif | Compte optimal | Raison fiscale |
|--------------|----------------|----------------|
| Actions canadiennes croissance | CELI | Capital gains protégés à vie |
| Actions canadiennes à dividendes éligibles | CELI ou non-enregistré | Crédit pour dividende non disponible en CELI mais zero impôt total |
| Actions américaines à dividendes | REER (titres directs) | Exempté de la retenue US 15% par convention fiscale |
| Actions américaines croissance | CELI | Capital gains > dividendes pour ces titres |
| Obligations à intérêts | REER | Intérêts pleinement taxables sinon |
| ETF d'actions internationales | REER | Évite la double couche de retenue |

## Workflow recommandé

### Pour une décision de placement standard

1. Identifier le **type de revenu attendu** (intérêts, dividendes éligibles, dividendes US, gains en capital)
2. Identifier le **compte optimal** selon le tableau ci-dessus
3. Vérifier le **plafond restant** (ARC envoie un avis de cotisation annuel)
4. **Pour un compte non-enregistré** : maintenir un registre PBR (voir `references/pbr-acb.md`)

### Pour une opération spécifique

```bash
python scripts/calc_taux_marginal.py        # taux marginal selon revenu et type de revenu
python scripts/calc_pbr.py                  # PBR moyen pondéré après plusieurs achats
python scripts/calc_retrait_reer.py         # impact fiscal d'un retrait REER/FERR
python scripts/calc_norberts_gambit.py      # économie vs conversion classique
```

### Stratégie de fin d'année (décembre)

Voir `references/strategies-fin-annee.md` pour la checklist détaillée. Points clés :
- Récolte de pertes en capital (compte non-enregistré seulement)
- Maximiser CELI avant 31 décembre (mais l'année suivante ouvre au 1er janvier)
- Cotisation REER : date limite début mars de l'année suivante
- REEE : 2 500 $ avant 31 décembre pour capturer la subvention (sinon perte permanente du droit)

## Mise à jour régulière des données fiscales

Les paramètres fiscaux changent chaque année. Avant d'utiliser des chiffres précis (plafonds, tranches, taux marginaux), **vérifier via web_search** les valeurs courantes sur :
- canada.ca (ARC)
- revenuquebec.ca
- Tables EY ou KPMG (publiées annuellement)

Les plafonds de référence à la date d'écriture (2026) sont dans `references/comptes-enregistres.md`, mais ils se périment.

## Garde-fous

- **Pas un conseil fiscal personnalisé.** Cette analyse fournit un cadre général. Pour les décisions importantes (succession, déménagement entre provinces, gros gains, structures complexes), consulter un fiscaliste accrédité.
- **L'optimisation fiscale ne dicte pas le choix d'investissement.** Acheter une mauvaise action dans le bon compte reste un mauvais investissement.
- **La règle de perte apparente s'étend au conjoint et aux comptes enregistrés.** Vendre dans ton compte non-enreg et le conjoint qui rachète déclenche aussi la règle. Voir `references/strategies-fin-annee.md`.
- **Les courtiers ne sont pas fiscalistes.** Le PBR affiché par Questrade ou Wealthsimple est souvent incorrect après transferts. Tenir son propre registre — voir `references/pbr-acb.md` et le script `calc_pbr.py`.
