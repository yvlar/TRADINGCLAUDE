---
name: pabrai-dhandho-and-cloning
description: Applique le cadre de Mohnish Pabrai (Pabrai Investment Funds, +25% CAGR 1999-2018) — 9 principes Dhandho ("heads I win, tails I don't lose much"), cloning de super-investors via 13F filings, position sizing concentré, low risk / high uncertainty. À utiliser dès que l'utilisateur mentionne Pabrai, Dhandho, "heads I win", cloning, 13F, super-investors, position sizing concentré, "low risk high uncertainty", asymetric bets, ou veut analyser le portefeuille d'un investisseur célèbre. Utilise toujours ce skill pour évaluer une idée d'investissement asymétrique ou pour clôner un portefeuille de super-investor.
---

# Pabrai — Dhandho and Cloning

Mohnish Pabrai a généré +25 % CAGR sur 1999-2018 en combinant deux idées : **acheter avec une asymétrie radicale** (peu à perdre, beaucoup à gagner) et **copier intelligemment les meilleurs investisseurs** via les filings 13F obligatoires aux USA.

## Quand utiliser quelle référence

| Question | Référence |
|----------|-----------|
| Les 9 principes Dhandho et leur application | `references/dhandho-9-principes.md` |
| Cloning via 13F : méthodologie et pièges | `references/13f-cloning-methodologie.md` |
| Position sizing concentré (Kelly fractionnel) | `references/position-sizing-concentre.md` |

## Workflow

### Étape 1 — Identifier l'opportunité

Pabrai ne cherche pas n'importe quelle bonne action. Il cherche des **paris asymétriques** :
- Downside limité (perte max acceptable, ex: -30 %)
- Upside multiple du downside (potentiel ≥ 2-3× le downside)
- Probabilité de l'upside ≥ 60-70 %

L'asymétrie compte plus que la qualité absolue. Un compounder à 25 % de croissance est moins intéressant **à plein prix** qu'une entreprise médiocre à -50 % de sa valeur.

### Étape 2 — Tester contre les 9 principes Dhandho

```bash
python scripts/dhandho_checklist.py inputs.json
```

Le script applique les 9 principes, signale les drapeaux rouges et confirme si l'opportunité passe le filtre.

### Étape 3 — Si idée venue de cloning, valider la conviction du super-investor

```bash
python scripts/clone_validate.py 13f_data.json
```

Confirme :
- Position size significative (> 5 % du portefeuille du super-investor)
- Position en cours d'achat (pas de vente sur les derniers trimestres)
- Cohérence avec la thèse historique du super-investor

### Étape 4 — Position sizing

Pabrai concentre fortement (10-25 % par position pour les meilleures convictions). Voir `references/position-sizing-concentre.md` pour la méthodologie Kelly fractionnel.

## Le principe central : "Heads I Win, Tails I Don't Lose Much"

C'est l'asymétrie radicale recherchée par Pabrai :
- Si la thèse marche : ×3-5
- Si la thèse échoue : -20 à -40 %

L'EV (espérance mathématique) est positive **même avec faible probabilité de succès** :
- 60 % × (+200 %) + 40 % × (-30 %) = +108 % attendu

C'est pourquoi Pabrai accepte volontiers des positions **avec risque réel** à condition que l'asymétrie soit bonne.

## Exemples Pabrai

### Stewart Enterprises (1999)
Funeral home consolidator stressé. Achat à $2, sortie à $11 deux ans plus tard. Asymétrie 5× pour risque -50 % maximal.

### Frontier Communications (vers 2010)
Ratée — l'entreprise a effectivement fait faillite. **Pabrai a perdu** sur cette position. Confirme que toutes les Dhandho ne marchent pas, mais l'asymétrie attendue restait positive.

### Sears Holdings (vers 2007-2008)
Asset play sur l'immobilier de Sears. Échec à grande échelle — Pabrai a perdu plus que prévu parce que la valeur de l'immobilier s'est érodée plus vite que prévu.

### IPSCO (vers 2003)
Steel company canadienne. Multiple bagger sur 2-3 ans.

### Coca-Cola India (FMCG India)
Approche compounding pure plutôt que Dhandho.

## Garde-fous

- **L'asymétrie demande un downside calculé.** Pabrai estime systématiquement le pire cas réaliste. Si tu ne peux pas expliquer le scénario "pire cas et pourquoi je perds 30%", tu n'as pas l'asymétrie — tu as un pari.
- **Le cloning n'est pas exempt d'erreur.** Les super-investors aussi se trompent. Buffett a perdu sur IBM, Klarman sur Theranos. Le cloning ne dispense pas de l'analyse propre.
- **Les 13F sont publiés avec 45 jours de retard**. La position que tu copies peut avoir été partiellement liquidée depuis. Vérifier avec les 13F suivants si possible.
- **La concentration amplifie les erreurs.** Pabrai accepte des drawdowns -50 % parce qu'il a le temperament et le capital permanent (LP) pour traverser. Un investisseur particulier n'a souvent pas cette flexibilité — modérer la concentration en conséquence.
- **Tous les 13F ne valent pas la peine d'être clonés.** Berkshire, Klarman (Baupost), Greenblatt (Gotham), Munger (Daily Journal) sont qualité Tier 1. Beaucoup d'autres "stars" sont moins fiables. Croiser avec performance multi-décennies, pas dernier 5 ans.
