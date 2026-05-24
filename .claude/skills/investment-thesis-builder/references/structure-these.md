# Structure d'une Thèse d'Investissement Formelle

Une thèse complète comprend 9 sections. Le format peut varier mais les éléments doivent tous être présents.

## Section 1 — Résumé exécutif (1 paragraphe)

3-5 phrases qui résument l'opportunité :
- Quoi (entreprise, position taille recommandée)
- Pourquoi (la thèse en une phrase)
- Asymétrie (downside vs upside)
- Horizon temporel
- Date de révision

**Exemple** :
> *Recommandation d'achat de 7 % du portfolio en CSU.TO à 4200 CAD. Thèse : Constellation Software est un compounder exceptionnel avec ROIC 28 %, capable de réinvestir 60-70 % de son cash flow à 25 %+ ROIC pendant 10+ ans. Asymétrie : downside -25 % (multiple compression), upside +200 % (compounding 15 % sur 7 ans). Horizon 7+ ans. Révision annuelle (Q4 2026).*

## Section 2 — Description de l'entreprise (1-2 paragraphes)

- Que fait l'entreprise concrètement
- Comment elle gagne de l'argent (structure de revenus)
- Marchés servis et géographies
- Taille relative (revenus, employés, cap. boursière)
- Histoire courte (fondation, jalons importants)

Test : un lecteur qui ne connaît pas l'entreprise doit pouvoir l'expliquer après lecture.

## Section 3 — Avantage concurrentiel (1-2 paragraphes)

- Type de moat (croiser avec `dorsey-moat-analysis`)
- Évidence quantitative (ROIC, marges supérieures, parts de marché)
- Évidence qualitative (scuttlebutt si applicable)
- Durabilité estimée du moat (5 / 10 / 20+ ans)

Sans avantage concurrentiel articulé, ce n'est pas un investissement de qualité.

## Section 4 — Économie de l'entreprise (2-3 paragraphes)

### Métriques actuelles
- Revenus, croissance 5 ans
- Marges (brute, opérationnelle, nette)
- ROIC sur 10 ans (moyenne, stabilité)
- FCF / Owner Earnings
- Bilan (dette nette, ratio dette/EBITDA)

### Projection
- Croissance des revenus projetée 5-10 ans
- Évolution des marges
- Cohérence dynamique vérifiée (g = ROIC × reinvestment) — voir `damodaran-narrative-and-numbers`

### Allocation de capital
- Réinvestissement dans le business
- Acquisitions (track record)
- Buybacks / dividendes
- Discipline de la direction

## Section 5 — Direction et gouvernance (1 paragraphe)

- Background du CEO et CFO
- Stabilité de l'équipe
- Compensation (compatible avec création de valeur ?)
- Insider holdings (% du capital)
- Évaluation Fisher 14 et 15 (transparence et intégrité)
- Drapeaux rouges éventuels

## Section 6 — Valorisation et marge de sécurité (1-2 paragraphes)

### Méthodes utilisées (croiser avec `stock-valuation-triangulation`)
- DCF (hypothèses prudentes)
- Multiples (P/E, EV/EBITDA, P/FCF, EV/Sales selon applicabilité)
- Méthode sectorielle si applicable
- Triangulation (médiane des trois)

### Marge de sécurité
- Calcul : (Valeur intrinsèque - Prix actuel) / Valeur intrinsèque
- Comparaison au seuil exigé selon le type d'opportunité (voir `klarman-margin-of-safety`)

### Catalyseurs (si applicable)
- Quel événement va révéler la valeur ?
- Calendrier estimé

## Section 7 — Scenarios pondérés (1 paragraphe)

| Scenario | Probabilité | Impact (5-7 ans) | Conditions |
|----------|-------------|------------------|------------|
| Bear | x % | -y % | Quoi se passe-t-il |
| Base | x % | +y % | Quoi se passe-t-il |
| Bull | x % | +y % | Quoi se passe-t-il |

Calcul d'EV pondérée. Si EV positive et magnitude bear acceptable, position justifiée.

Voir `scripts/scenarios_ev.py` et `references/scenarios-pondere.md`.

## Section 8 — Risques principaux et kill criteria (1 paragraphe)

### Top 3-5 risques

Pour chaque risque :
- Description spécifique
- Probabilité estimée
- Magnitude d'impact

### Kill criteria

3-5 critères mesurables qui déclenchent la sortie. Voir `references/kill-criteria.md`.

### Devil's advocate

5 raisons les plus convaincantes de NE PAS investir. Voir `references/devils-advocate.md`.

## Section 9 — Décision et exécution (1 paragraphe)

- Position size recommandée (% du portfolio)
- Prix d'achat cible (vs prix actuel)
- Stratégie d'achat (single shot vs DCA sur 4-8 semaines)
- Date de révision

## Annexes (optionnel)

- Calculs détaillés
- Sources (rapports annuels, lettres, analyses)
- Notes de scuttlebutt
- Comparaison avec peers

## Format pratique

### Longueur cible
- Compounders simples : 2-3 pages
- Special situations : 3-5 pages
- Distressed / Complex : 5-8 pages

### Outils
- Fichier Markdown ou Word document
- Versionner (Git, ou simplement dater chaque version)
- Conserver dans un dossier dédié par position

### Révision

Lors de chaque révision (annuelle ou trimestrielle pour positions importantes) :
1. La thèse tient-elle ? (réponse oui/non explicite)
2. Quelles hypothèses ont changé ?
3. Les kill criteria sont-ils déclenchés ?
4. Action : maintenir, augmenter, réduire, sortir

## Exemple complet

Voir `templates/` pour des exemples de thèses formelles sur :
- Compounder qualité (Constellation Software)
- Special situation (Spinoff)
- Distressed (Boeing 2024)

## Pourquoi ce format

### Comparaison avec analystes professionnels

Les analystes du sell-side et hedge fund écrivent des thèses similaires (parfois 20-50 pages). Ce format est le minimum viable pour un investisseur particulier sérieux.

### Différence avec un research report

Une thèse personnelle inclut :
- Position size recommandée (un research report rarement)
- Kill criteria explicites
- Devil's advocate
- Engagement personnel à la révision

### Antidote au "buy-and-forget"

Sans thèse écrite, on garde des positions par inertie même quand les fondamentaux changent. La thèse + révision force la décision active.

## Pièges du format formel

### 1. Sur-précision fictive

Donner une probabilité à 1 % près sur le scenario bull est faux par construction. Préférer des arrondis (5 %, 10 %, 25 %).

### 2. Optimisme caché dans les hypothèses

Le format peut camoufler un biais optimiste partout. Discipline : faire le scenario bear **avant** le scenario bull.

### 3. Confirmation bias dans la rédaction

Une fois qu'on a une intuition positive, le format permet de justifier rétroactivement. Discipline : forcer la section devil's advocate **avant** la conclusion.

### 4. Effort excessif sur les positions petites

Une position 1 % du portfolio ne justifie pas 8 pages d'analyse. Calibrer la longueur de la thèse à la taille de la position.

## Synthèse

Une thèse formelle est un **outil de discipline**. Elle ne garantit pas le succès mais structure la pensée et permet la révision. Pour les positions ≥ 5 % du portfolio, c'est un standard non négociable de l'investisseur sérieux.
