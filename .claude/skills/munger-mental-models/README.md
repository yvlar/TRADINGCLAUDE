# munger-mental-models

Cadre Charlie Munger — 25 biais cognitifs (*Psychology of Human Misjudgment*), inversion ("invert, always invert"), lollapalooza effects, latticework multidisciplinaire.

## À quoi ça sert

Charlie Munger (1924-2023), partenaire de Buffett pendant 60 ans, a popularisé l'idée que **la majorité des erreurs d'investissement viennent de biais cognitifs prévisibles**. L'antidote est :

1. **25 biais cognitifs** — checklist pour audit avant chaque décision majeure
2. **Inversion** — "tell me where I'm going to die, so I'll never go there"
3. **Lollapalooza effects** — quand 3+ biais s'alignent, l'effet est exponentiel
4. **Latticework multidisciplinaire** — combiner économie, psychologie, math, biologie, histoire

## Quand l'utiliser

- "Audit des biais avant d'acheter Tesla à 200 USD"
- "Comment Munger appliquait l'inversion ?"
- "Lollapalooza effect — exemple concret ?"
- Avant une décision d'investissement majeure
- Quand tu détectes une narrative trop séduisante

## Quand ne pas l'utiliser

- Pour les décisions purement quantitatives
- Pour le trading systématique
- Pour les positions petites (effort disproportionné)

## Composants

```
munger-mental-models/
├── SKILL.md
├── references/
│   ├── 25-biais-cognitifs.md          ← Détail des 25 biais avec exemples
│   ├── inversion-thinking.md          ← Inverser pour identifier les modes d'échec
│   ├── lollapalooza-effects.md        ← Bulles dot-com, real estate, crypto
│   └── latticework-multidisciplinaire.md ← Construire le treillis sur 5-10 ans
├── scripts/
│   └── biais_audit.py                  ← Présentation thématique des 25 biais
└── evals/
    └── evals.json
```

## Les 25 biais (regroupés par thème)

### Incitatifs
1. Reward and punishment superresponse

### Émotions
2. Liking / Loving tendency
3. Disliking / Hating tendency
8. Envy / Jealousy
10. Influence-from-mere-association
14. Deprival-superreaction (loss aversion)

### Décision
4. Doubt-avoidance
5. Inconsistency-avoidance / Commitment
11. Pain-avoiding denial
12. Excessive self-regard
17. Stress-influence

### Foule / Sources
9. Reciprocation
15. Social-proof
22. Authority-misinfluence

### Logique / Communication
13. Over-optimism
16. Contrast-misreaction
18. Availability-misweighing
23. Twaddle
24. Reason-respecting

### Combinaison
25. Lollapalooza ← le combo destructeur

## Exemples d'utilisation

### Via prompt

> "Avant d'acheter une position 10 % en Tesla, audit les biais cognitifs qui pourraient affecter ma décision"

### Via script direct

```bash
cd munger-mental-models
python scripts/biais_audit.py --decision "achat-tesla-200usd"
```

Output :
```
AUDIT DES 25 BIAIS COGNITIFS — achat-tesla-200usd

━━━ INCITATIFS ━━━
 1. Reward and punishment superresponse
    → Quels incitatifs animent les acteurs (direction, analystes) ?

━━━ ÉMOTIONS ━━━
 2. Liking / Loving tendency
    → Suis-je biaisé par charisme du CEO ?
 8. Envy / Jealousy
    → Est-ce que je veux acheter parce d'autres ont fait fortune ?
...

ÉTAPES SUIVANTES:
1. Identifier les biais qui s'appliquent à TOI
2. Identifier les biais qui s'appliquent au MARCHÉ (lollapalooza)
3. Effectuer l'inversion
4. Si 5+ scenarios d'échec plausibles, refuser ou réduire le sizing
```

## Inversion — exemple

Au lieu de "comment réussir cet investissement ?", demander **"comment cet investissement pourrait-il échouer ?"**

Lister 5-10 modes d'échec spécifiques :
- Disruption technologique
- Réglementation hostile
- Perte de moat
- Mauvaise allocation de capital
- Détérioration du business model
- Choc macro
- Fraude révélée
- Erreurs comportementales (mienne)

Si tu ne peux pas en identifier 5, **tu n'as pas suffisamment investigué**.

## Lollapalooza historiques

| Période | Biais alignés | Effet | Conséquence |
|---------|---------------|-------|-------------|
| Dot-com 1999 | Social proof + envy + reciprocity + authority + twaddle | Multiples 100×+ | Crash -78 % NASDAQ |
| Real estate 2007 | Social proof + authority + reciprocity + over-optimism | Prix maisons ×2 | Crash -33 % moyen US |
| Crypto 2021 | Social proof + envy + twaddle + scarcity + greater fool | BTC 70k$ | Crash -77 % en 2022 |

Quand tu vois 3+ biais alignés sur un asset/secteur, **suspecter une bulle** et inverser la position.

## Latticework — disciplines clés

Munger lisait largement au-delà de la finance :
- **Économie** : supply/demand, marginal analysis
- **Psychologie** : les 25 biais
- **Math** : probabilité, compound interest
- **Biologie** : sélection naturelle, écosystèmes
- **Physique** : équilibre, bottleneck
- **Histoire** : cycles, "this time it's different" usually isn't
- **Chimie** : catalyse, activation energy

L'investisseur avec un seul cadre ("hammer") voit tout comme un clou. Le treillis multidisciplinaire révèle les angles morts.

## Reading list Munger

- *Influence: The Psychology of Persuasion* (Cialdini)
- *Thinking, Fast and Slow* (Kahneman)
- *The Selfish Gene* (Dawkins)
- *Guns, Germs, and Steel* (Diamond)
- *Poor Charlie's Almanack* (Munger / Kaufman)
- *Seeking Wisdom* (Bevelin)

## Ce qu'il ne fait pas

- Ne **élimine pas** les biais (Munger lui-même reconnaissait être affecté)
- Ne donne pas un score numérique d'investissement
- Ne remplace pas l'analyse fondamentale

## Garde-fous

- Connaître les biais ≠ s'en libérer — la connaissance permet de **compenser**, pas de éliminer
- L'inversion peut devenir paralysante (5-10 modes d'échec, pas 50)
- Le latticework demande des années à construire
- Munger lui-même se trompait (désaccord avec Buffett sur Apple, fund Daily Journal sous-performé)

## Voir aussi

- [marks-cycles-and-risk](../marks-cycles-and-risk/) — pendule du sentiment lié aux biais collectifs
- [klarman-margin-of-safety](../klarman-margin-of-safety/) — discipline psychologique pour résister aux biais
- [investment-thesis-builder](../investment-thesis-builder/) — devil's advocate intégré
- [buffett-quality-investing](../buffett-quality-investing/) — Buffett-Munger philosophie commune
