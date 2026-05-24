---
name: marks-cycles-and-risk
description: Applique le cadre de Howard Marks (Oaktree Capital) — pendule du sentiment de marché, second-level thinking, risque comme perte permanente plutôt que volatilité, contrarian quand le pendule est aux extrêmes. À utiliser dès que l'utilisateur mentionne Marks, Oaktree, "pendulum", second-level thinking, market cycle, "where are we in the cycle", risk vs uncertainty, contrarian, sentiment de marché, ou veut évaluer la position actuelle dans un cycle. Utilise toujours ce skill avant les décisions d'allocation tactique (cash vs equity).
---

# Marks — Cycles et Risque

Howard Marks a co-fondé Oaktree Capital en 1995 (~190 G$ AUM en 2024). Ses *memos* trimestriels sont lus par tous les grands investisseurs depuis 30+ ans. Ses livres *The Most Important Thing* (2011) et *Mastering the Market Cycle* (2018) condensent sa philosophie.

Différence clé avec Buffett : Marks pense **explicitement en termes de cycles**. Il accepte l'idée qu'il y a des moments où il faut être agressif et d'autres où il faut être prudent — pas un permanent buy-and-hold.

## Quand utiliser quelle référence

| Question | Référence |
|----------|-----------|
| Position actuelle dans le cycle | `references/pendule-sentiment.md` |
| Définition de risque vs volatilité | `references/risque-perte-permanente.md` |
| Second-level thinking en pratique | `references/second-level-thinking.md` |

## Workflow

### Étape 1 — Évaluer la position dans le cycle

Marks utilise une métaphore : le **pendule** oscille entre deux extrêmes :
- **Greed / Optimisme / Risk Tolerance** (sommet)
- **Fear / Pessimisme / Risk Aversion** (creux)

```bash
python scripts/cycle_position.py inputs.json
```

Le script évalue ~10 indicateurs (multiples, sentiment, conditions de crédit, IPO activity, M&A volume) et positionne le pendule sur une échelle de -10 (panique extrême) à +10 (euphorie extrême).

### Étape 2 — Adapter l'allocation

| Position du pendule | Allocation typique Marks |
|----------------------|--------------------------|
| Euphorie extrême (+8 à +10) | 20-30 % equity, 70-80 % cash/defensives |
| Optimisme normal (+3 à +7) | 60-70 % equity, 30-40 % cash |
| Neutre (-2 à +2) | 80-90 % equity, 10-20 % cash |
| Pessimisme normal (-7 à -3) | 95-100 % equity, 0-5 % cash |
| Panique extrême (-10 à -8) | 100 % equity + levier modeste si capital permanent |

Cette stratégie est **contre-cyclique** par construction. Marks insiste : la majorité de l'investisseur particulier fait l'inverse (acheter en sommet, vendre en creux).

### Étape 3 — Second-level thinking

Pour chaque opportunité, distinguer :
- **First-level thinking** : "C'est une bonne entreprise, donc c'est un bon investissement"
- **Second-level thinking** : "C'est une bonne entreprise, mais le marché le sait. Le prix reflète déjà cette qualité. Le rendement sera-t-il supérieur au consensus ?"

Le rendement vient de **différer du consensus** — pas de répéter le consensus.

### Étape 4 — Définir risque correctement

Pour Marks, le risque n'est **pas la volatilité** (définition académique) mais la **probabilité de perte permanente de capital**. Voir `references/risque-perte-permanente.md`.

Cette définition change radicalement les décisions :
- Une action volatile mais à -50 % de sa valeur intrinsèque a peu de risque (Marks)
- Une action stable à +50 % au-dessus de sa valeur intrinsèque a beaucoup de risque (Marks)

## Le concept central : "We can't predict, but we can prepare"

Marks rejette explicitement la prédiction du timing court-terme :
- Personne ne peut prédire la prochaine récession à 6 mois
- Personne ne peut prédire les taux d'intérêt à 12 mois
- Personne ne peut prédire les prix individuels à court terme

**Mais** il accepte la prédictabilité des cycles long-terme :
- Les multiples extrêmes finissent par se normaliser
- Les rentes excessives attirent la concurrence
- Le sentiment extrême est typiquement suivi d'un retournement

Stratégie : ne pas timer, **se préparer**. En sommet de cycle, accumuler cash pour saisir la prochaine crise. En creux, déployer agressivement.

## Garde-fous

- **Le pendule peut rester aux extrêmes longtemps**. 1995-1999 : valorisations en sommet pendant 5 ans avant la correction. 2009-2013 : pessimisme malgré la reprise. La position contre-cyclique demande une **patience extrême** et coûte en sous-performance temporaire.
- **Marks lui-même n'est pas un market timer parfait**. Oaktree achète "trop tôt" en cycle baissier (achat au début de la crise, pas au creux). C'est la conséquence acceptable de la stratégie — préférer rater le bottom plutôt que le rater du tout.
- **Cash a un coût d'opportunité**. En période de bull market prolongé, 30 % cash sous-performe massivement. Ce coût est le **prix de l'option** sur la prochaine crise. Accepter ce coût est psychologiquement difficile.
- **Pas de levier**. Marks n'utilise jamais de levier directement. Le levier amplifie les erreurs et peut forcer la liquidation au creux du cycle (le pire moment).
- **Indicators de cycle subjectifs**. Les indicateurs du pendule sont qualitatifs en partie. Différentes personnes peuvent lire le même marché différemment. La discipline est dans le processus, pas dans une formule magique.
