---
name: klarman-margin-of-safety
description: Applique le cadre de Seth Klarman (Baupost Group, +20% CAGR sur 35 ans) — primauté absolue de la marge de sécurité, préservation du capital, situations spéciales, distressed debt, contre-cyclisme. À utiliser dès que l'utilisateur mentionne Klarman, Baupost, Margin of Safety (le livre), préservation du capital, distressed, situations spéciales, "absolute return" vs "relative return", contrarian, ou veut évaluer une opportunité avec lentille de prudence extrême. Utilise toujours ce skill avant d'investir dans une opportunité distressed ou complexe.
---

# Klarman — Margin of Safety

Seth Klarman dirige Baupost Group depuis 1982 (gestion ~28 G$ en 2024, +20 % CAGR sur 35+ ans). Son livre éponyme, *Margin of Safety* (1991, hors impression — exemplaires originaux à 2000+ USD), est devenu une référence culte du value investing.

Différence clé avec Buffett : Klarman accepte des positions **en distressed debt, special situations, real estate** que Buffett évite. Mais le principe central reste le même — **ne jamais perdre de capital**.

## Quand utiliser quelle référence

| Question | Référence |
|----------|-----------|
| Comment calculer la marge de sécurité requise | `references/marge-securite-niveau.md` |
| Distressed debt et restructurations | `references/distressed-debt-restructurations.md` |
| Situations spéciales (Klarman version) | `references/situations-speciales-klarman.md` |
| Préservation du capital — discipline psychologique | `references/preservation-capital.md` |

## Workflow

### Étape 1 — Estimer la valeur intrinsèque de manière conservatrice

Klarman utilise plusieurs méthodes en parallèle, prend la **plus basse** (et non la médiane) :
- Liquidation value (NCAV-style)
- Sum-of-the-parts à valeurs conservatrices
- DCF à hypothèses prudentes (g modeste, marges actuelles, pas d'amélioration)

```bash
python scripts/marge_securite.py --intrinsic 100 --price 65
```

### Étape 2 — Exiger une marge de sécurité explicite

| Type d'opportunité | Marge minimum exigée |
|---------------------|----------------------|
| Compounder de qualité | 25-30 % |
| Cyclical au creux | 40-50 % |
| Special situation (spinoff, restructuring) | 30-40 % |
| Distressed debt | 50 %+ |
| Asset play en distress | 50-60 %+ |

Plus l'incertitude est élevée, plus la marge exigée est large.

### Étape 3 — Définir le pire cas réaliste

Klarman insiste : avant d'investir, articuler le **scenario "blow-up"** :
- Quels sont les facteurs qui pourraient invalider la thèse ?
- Combien je perds dans ce scenario ?
- Le maximum de perte tolérable sur cette position est-il dépassé ?

Si la perte dans le pire cas réaliste dépasse 30-50 % du capital alloué à la position, **ne pas investir**.

### Étape 4 — Exiger un catalyseur ou patience explicite

Pour les special situations et asset plays, Klarman exige typiquement un catalyseur :
- Vente d'actifs annoncée
- Spinoff prévu
- Restructuration en cours
- Sortie de Chapter 11

Sans catalyseur, l'attente peut être de 5-10 ans. Il faut accepter explicitement cette horizon.

### Étape 5 — Sizing modeste (vs Pabrai/Munger)

Klarman dilue beaucoup plus que Pabrai :
- 30+ positions long
- Top position rarement > 8-10 %
- Hedging actif (puts, shorts) pour limiter les drawdowns
- 30-50 % cash typique en attendant les opportunités

C'est le profil **absolute return** : viser des rendements positifs **chaque année**, pas le maximum sur cycle. Drawdowns historiques Baupost : -10 à -15 % maximum, vs -50 à -70 % pour Pabrai.

## Le concept central : Absolute vs Relative Return

Klarman vise des **absolute returns** (rendement positif en valeur absolue), pas la performance relative à un index.

| Approche | Optimisé pour | Drawdowns typiques |
|----------|---------------|---------------------|
| Relative return (mutual funds) | Battre le benchmark | Suivent le marché (-30 à -50 % en récession) |
| **Absolute return (Klarman)** | Préservation + croissance | -10 à -20 % maximum |

L'investisseur particulier orienté long-terme peut emprunter cette mentalité en :
- Maintenant 10-30 % cash en marchés cher
- Refusant FOMO sur les hot stocks
- Acceptant la sous-performance temporaire vs index

## Garde-fous

- **La marge de sécurité ne garantit pas le succès**, elle augmente les chances. Klarman insiste : "The margin of safety doesn't preserve you against being wrong; it preserves you from the consequences of being wrong."
- **Pas de FOMO**. Klarman accepte de manquer des bull markets entiers (1995-1999, 2017-2021) plutôt que de relâcher la discipline. C'est psychologiquement coûteux mais protège le capital.
- **Cash = optionalité**. Klarman maintient typiquement 30-50 % cash en marchés chers. Le cash n'est pas un coût d'opportunité — c'est une **option pour acheter à -50 %** lors de la prochaine crise.
- **Méfiance des projections optimistes**. Klarman préfère les valorisations basées sur les **valeurs actuelles** plutôt que sur les améliorations futures. Si l'investissement nécessite que tout aille bien pour fonctionner, il ne fonctionne pas.
- **Distressed demande expertise**. Beaucoup d'investisseurs particuliers ne devraient pas toucher au distressed (analyse complexe, illiquidité, légal). Préférer les fonds spécialisés ou rester sur les compounders simples.
