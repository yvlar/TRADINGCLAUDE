# pabrai-dhandho-and-cloning

Cadre Mohnish Pabrai — 9 principes Dhandho ("heads I win, tails I don't lose much"), cloning intelligent des super-investors via 13F, position sizing concentré.

## À quoi ça sert

Mohnish Pabrai (Pabrai Investment Funds, +25 % CAGR 1999-2018) combine deux idées centrales :

1. **Dhandho — asymétrie radicale** : peu à perdre, beaucoup à gagner (downside -30 %, upside +200-500 %)
2. **Cloning intelligent** : copier les 13F des meilleurs investisseurs (Buffett, Klarman, Munger) plutôt que générer toutes ses idées

Plus la **concentration extrême** : 8-15 positions au total, top conviction à 15-25 %.

## Quand l'utiliser

- "Pabrai aurait-il acheté Boeing à 150 USD ?"
- "Comment cloner Buffett via les 13F ?"
- "Position size pour une opportunité asymétrique 4:1 ?"
- "Klarman dernières positions ?"
- Pour évaluer une opportunité asymétrique
- Pour démarrer son investissement (cloner avant d'avoir ses propres idées)

## Quand ne pas l'utiliser

- Pour la diversification large (style index)
- Pour le trading court-terme
- Pour les financières complexes (Pabrai préfère businesses simples)

## Composants

```
pabrai-dhandho-and-cloning/
├── SKILL.md
├── references/
│   ├── dhandho-9-principes.md         ← Les 9 principes des Patel
│   ├── 13f-cloning-methodologie.md    ← Comment cloner intelligemment
│   └── position-sizing-concentre.md   ← Kelly fractionnel, plafond 25%
├── scripts/
│   └── dhandho_checklist.py           ← Score 0-9 + asymétrie + EV
└── evals/
    ├── evals.json
    └── test_baba.json                 ← BABA Dhandho 9/9, asymétrie 5.71:1
```

## Les 9 principes Dhandho

1. **Invest in existing businesses** (pas de startups)
2. **Invest in simple businesses** (compréhensible en 5 min)
3. **Invest in distressed businesses in distressed industries**
4. **Invest in businesses with durable moats**
5. **Make few bets, big bets, infrequent bets** (concentration)
6. **Fixate on arbitrage** (mispricing)
7. **Buy businesses with strong tailwinds**
8. **Invest in low-risk, high-uncertainty businesses**
9. **Invest in copycats rather than innovators**

## Cloning — Tier 1 super-investors

| Investor | Fund | Style | Pourquoi cloner |
|----------|------|-------|------------------|
| Warren Buffett | Berkshire | Quality compounders | Track record 60 ans |
| Charlie Munger | Daily Journal | Concentration extrême | Conviction extrême |
| Seth Klarman | Baupost | Special situations + distressed | Discipline absolue |
| Howard Marks | Oaktree | Cycles + distressed | Macro + tactique |
| Joel Greenblatt | Gotham | Special situations | Approche systématique |
| Mohnish Pabrai | Pabrai Funds | Dhandho | Le penseur lui-même |

Sources de 13F :
- **WhaleWisdom** (gratuit avec délai)
- **Dataroma** (focus 80 super-investors curated)
- **GuruFocus** (payant, large couverture)

## Exemples d'utilisation

### Via prompt

> "BABA en 2022 — passe-t-il les 9 principes Dhandho ?"

### Via script direct

```bash
cd pabrai-dhandho-and-cloning
python scripts/dhandho_checklist.py evals/test_baba.json
```

Output :
```
DHANDHO CHECKLIST — BABA
✓ P1. Entreprise existante (5+ ans)
✓ P2. Business simple
✓ P3. En distress / unloved
✓ P4. Moat durable
✓ P5. Concentration (12 positions)
✓ P6. Asymétrie 5.71:1
✓ P7. Tailwind sectoriel
✓ P8. Low risk / High uncertainty
✓ P9. Clone d'un super-investor (Munger / Pabrai)

Score: 9/9
Asymétrie: 5.71:1
EV attendue: 117.8%

✅ DHANDHO FORTE
```

## Position Sizing concentré

Méthode Pabrai : **Kelly fractionnel** (Kelly intégral / 4)

Configuration cible :
- **8-15 positions** au total
- **Top 3-4 positions** : 15-25 % chacune (50-70 % du portfolio)
- **Mid positions** : 5-10 %
- **Plafond** : 25 % par position individuelle (pas plus)
- **Pas de filler** : soit > 5 %, soit pas de position

## Drawdowns acceptés

Pabrai accepte des **drawdowns -50 à -70 %** (vs Klarman -10 à -20 %). Trade-off :
- 1999-2018 : +25 % CAGR Pabrai
- 2008-2009 : drawdown -65 %
- Reprise en 2009-2012 : massive

Sans le tempérament + capital permanent (LP non-redeemable), **ne pas appliquer cette concentration**.

## "Heads I win, tails I don't lose much"

Recherche systématique d'asymétrie :
- 60-70 % probabilité de gain ×2-5
- 30-40 % probabilité de perte -20 à -40 %
- EV mathématiquement positive même avec faible probabilité

```
EV = p_gain × multiple_gain + p_perte × multiple_perte
EV = 0.65 × (+200%) + 0.35 × (-30%) = +120%
```

## Ce qu'il ne fait pas

- Ne fournit pas la liste actuelle des positions Pabrai
- Ne valide pas un investissement seul (cloning ≠ pas d'analyse)
- Ne couvre pas les positions internationales (13F sont actions US)

## Garde-fous

- **Cloning n'est pas garanti** — Pabrai a perdu sur Frontier (cloned), Klarman sur Theranos
- **Délai 13F** : 45 jours après fin trimestre — la position copiée peut avoir été partiellement liquidée
- **Position size demande tempérament** — drawdowns -50 % impossibles à digérer pour beaucoup
- **Concentration sans edge** = gambling. Si tu n'as pas d'edge réel, indexer.

## Voir aussi

- [klarman-margin-of-safety](../klarman-margin-of-safety/) — Klarman est dans le tier 1 cloning
- [buffett-quality-investing](../buffett-quality-investing/) — Buffett est le n° 1 à cloner
- [greenblatt-magic-formula](../greenblatt-magic-formula/) — Greenblatt aussi tier 1
- [marks-cycles-and-risk](../marks-cycles-and-risk/) — Marks tier 1 pour le contexte macro
