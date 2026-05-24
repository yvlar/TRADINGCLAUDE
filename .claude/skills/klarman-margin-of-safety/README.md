# klarman-margin-of-safety

Cadre Seth Klarman — primauté absolue de la marge de sécurité, préservation du capital, situations spéciales et distressed (avec discipline).

## À quoi ça sert

Seth Klarman (Baupost Group, 1982-présent, +20 % CAGR sur 35+ ans) a écrit *Margin of Safety* (1991), considéré comme le successeur intellectuel de Graham. Différence avec Buffett : Klarman accepte des positions **distressed et special situations** que Buffett évite, mais avec une **marge de sécurité plus stricte**.

Quatre axes principaux :

1. **Marge de sécurité** calibrée par tier d'opportunité (25 %–60 %)
2. **Préservation du capital** comme objectif primaire (avant la performance)
3. **Distressed debt** — analyse rigoureuse des recoveries
4. **Absolute return** vs relative return (positif chaque année plutôt que battre l'index)

## Quand l'utiliser

- "Quelle marge de sécurité Klarman exige sur un compounder ?"
- "Distressed debt sur Boeing — comment l'analyser ?"
- "Cash position 40 % en bull market — justifié ?"
- "Préservation du capital — discipline psychologique ?"
- Avant toute position où l'incertitude est élevée

## Quand ne pas l'utiliser

- Pour le trading systématique court-terme
- Pour les fonds indiciels passifs
- Pour les momentum strategies

## Composants

```
klarman-margin-of-safety/
├── SKILL.md
├── references/
│   ├── marge-securite-niveau.md           ← 25%–60% selon le tier
│   ├── distressed-debt-restructurations.md ← Recovery rates, chap 11
│   ├── situations-speciales-klarman.md    ← Spinoffs vs Greenblatt (plus strict)
│   └── preservation-capital.md            ← Discipline psychologique
├── scripts/
│   └── marge_securite.py                  ← Calcul + verdict par tier
└── evals/
    └── evals.json
```

## Échelle des marges requises

| Tier | Type d'opportunité | Marge minimum |
|------|---------------------|---------------|
| 1 | Compounder de qualité | **25-30 %** |
| 2 | Cyclique au creux | **40-50 %** |
| 3 | Special situation (spinoff, restructuration) | **30-40 %** |
| 4 | Distressed debt | **50-70 %** |
| 5 | Asset play en distress | **50-60 %** |

Plus l'incertitude est élevée, plus la marge exigée est large.

## Exemples d'utilisation

### Via prompt

> "Apple à 200 USD vs valeur intrinsèque 250 USD — la marge est-elle suffisante selon Klarman ?"

### Via script direct

```bash
cd klarman-margin-of-safety
python scripts/marge_securite.py --intrinsic 250 --price 200 --type compounder
```

Output :
```
MARGE DE SÉCURITÉ KLARMAN — Compounder de qualité
Marge actuelle    : 20.0%
Seuil minimum     : 25%
Seuil recommandé  : 30%

Prix cible (min)         : 187.5
Prix cible (recommandé)  : 175.0

❌ ATTENDRE — marge insuffisante (< 25%)
```

## Absolute Return vs Relative Return

| Approche | Optimisé pour | Drawdowns typiques |
|----------|---------------|---------------------|
| Mutual funds (relative) | Battre le benchmark | -30 à -50 % en récession |
| **Klarman (absolute)** | Préservation + croissance | -10 à -20 % maximum |

Cash position de Baupost typiquement 30-50 % en marchés chers.

## Le concept central

> *« The margin of safety doesn't preserve you against being wrong; it preserves you from the consequences of being wrong. »*

Tu vas te tromper sur la valeur intrinsèque. La marge absorbe l'erreur :
- VI estimée 100, prix d'achat 65 (35 % marge) — si VI réelle = 80, achat reste rentable
- VI estimée 100, prix d'achat 95 (5 % marge) — si VI réelle = 80, perte de 15 %

## Préservation du capital — disciplines clés

1. **Cash comme position légitime** (30-50 % en marchés chers)
2. **Filtre aggressif** (analyser 100+ idées par mois, investir dans 5-10)
3. **Patience** (attendre prix d'achat cible 6-12 mois)
4. **Hedging actif** (puts OTM, allocation cash)
5. **Pas de levier** (jamais de margin)
6. **Lettre trimestrielle** (forcer l'articulation des thèses)

## Drawdown récupération

Une perte permanente prend des années à compenser :
- -30 % → besoin de +43 % pour rattraper
- -50 % → besoin de +100 %
- -70 % → besoin de +233 %

Une seule erreur catastrophique peut effacer 10 ans de bons rendements. D'où la primauté de l'évitement.

## Ce qu'il ne fait pas

- Ne fournit pas la liste des distressed disponibles (recherche manuelle requise)
- Ne couvre pas le timing parfait — Klarman lui-même achète "trop tôt" en cycle baissier
- N'élimine pas tous les risques (Klarman a perdu sur certaines positions, ex: K-Mart)

## Garde-fous

- La marge demande une **estimation prudente** de la valeur intrinsèque (ne pas gonfler les hypothèses)
- Cash position en bull market = sous-performance temporaire (acceptée comme prix de l'optionnalité)
- Distressed demande **expertise** — déconseillé aux investisseurs particuliers sans préparation
- "FOMO" sur les hot stocks est l'ennemi de la discipline — résister coûteusement

## Voir aussi

- [graham-stock-screening](../graham-stock-screening/) — Klarman est le successeur intellectuel de Graham
- [greenblatt-magic-formula](../greenblatt-magic-formula/) — special situations chez Greenblatt (plus tolérant)
- [marks-cycles-and-risk](../marks-cycles-and-risk/) — Marks et Klarman partagent la philosophie de cycle
- [investment-thesis-builder](../investment-thesis-builder/) — kill criteria + scenarios formels
