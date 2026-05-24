---
name: investment-thesis-builder
description: Construit une thèse d'investissement structurée et défendable en synthétisant l'analyse fondamentale (Graham, Buffett, Lynch, Greenblatt), qualitative (Fisher, Dorsey moat), comportementale (Marks, Munger), et la marge de sécurité (Klarman). Génère un document de thèse formel avec scenarios bull/base/bear, kill criteria, devil's advocate, et position size recommandée. À utiliser dès que l'utilisateur veut formaliser une décision d'investissement, écrire une thèse, structurer une analyse complète, ou avant de prendre une position significative (≥ 5 % du portfolio). Utilise toujours ce skill comme étape finale avant d'exécuter une décision majeure.
---

# Investment Thesis Builder

Synthèse multi-skills pour construire une thèse d'investissement formelle. Le but : forcer l'articulation explicite de l'analyse pour réduire les biais et créer un document révisable.

## Pourquoi écrire une thèse formelle

### 1. Discipline analytique
Si tu peux écrire ta thèse en 1-2 pages structurées, tu la comprends. Si tu ne peux pas, tu n'as pas de vraie thèse — tu as une intuition.

### 2. Document de révision
Une thèse écrite permet de **vérifier annuellement** si la thèse tient toujours. Sans ce point d'ancrage, on dérive avec les marchés.

### 3. Antidote aux biais
Articuler explicitement les hypothèses, les scenarios d'échec, et les kill criteria force la compensation des biais cognitifs (commitment, denial, etc.).

### 4. Communication
Si tu gères de l'argent pour autrui (familial, partner, etc.), une thèse écrite est la base de la communication transparente.

## Quand utiliser quelle référence

| Étape | Référence |
|-------|-----------|
| Structure complète d'une thèse | `references/structure-these.md` |
| Scenarios bull/base/bear avec probabilités | `references/scenarios-pondere.md` |
| Kill criteria et exit triggers | `references/kill-criteria.md` |
| Devil's advocate test | `references/devils-advocate.md` |
| Templates de thèses (compounder, special situation, distressed) | `templates/` |

## Workflow

### Étape 1 — Pré-conditions

Avant de construire la thèse, **avoir effectué** les analyses des skills appropriés :

| Type d'opportunité | Skills à appliquer en pré-condition |
|---------------------|--------------------------------------|
| Compounder Buffett | buffett-quality + dorsey-moat + fisher-scuttlebutt |
| Value Graham | graham-stock-screening + earnings-quality + canadian-tax |
| Special situation | greenblatt-magic-formula + klarman-margin |
| Fast grower Lynch | lynch-categories + damodaran-narrative |
| Distressed / Pabrai | pabrai-dhandho + klarman-margin |

Si ces analyses préalables n'ont pas été faites, **stop** et les faire d'abord.

### Étape 2 — Construire la thèse formelle

```bash
python scripts/build_thesis.py inputs.json
```

Le script génère un document structuré avec toutes les sections obligatoires (voir `references/structure-these.md`).

### Étape 3 — Scenarios pondérés

Pour chaque thèse, articuler 3 scenarios :
- **Bear** (downside) : que se passe-t-il si la thèse échoue ?
- **Base** (most likely) : projection médiane
- **Bull** (upside) : que se passe-t-il si tout va mieux que prévu ?

Avec probabilités estimées et impact sur la valeur. Le calcul d'EV pondérée donne l'espérance.

```bash
python scripts/scenarios_ev.py --bear-pct -30 --bear-prob 25 --base-pct 50 --base-prob 50 --bull-pct 200 --bull-prob 25
```

### Étape 4 — Kill criteria explicites

Lister 3-5 critères qui, s'ils se réalisent, déclenchent la sortie automatique. Sans ces critères, on rationalise les pertes après coup.

Exemples typiques :
- ROIC < 12 % pendant 2 années consécutives
- Perte d'un client représentant > 20 % des revenus
- Changement de CEO non planifié
- Ratio dette/EBITDA > 3.0×
- Marge brute en compression > 5 pts sur 2 ans

### Étape 5 — Devil's advocate

Forcer la liste des **5 raisons les plus convaincantes de NE PAS investir**. Si tu ne peux pas en identifier 5, tu n'as pas suffisamment investigué.

### Étape 6 — Position size

Selon la conviction et le profil du portfolio :

| Niveau de conviction | Position size suggérée |
|----------------------|------------------------|
| Très haute (compounder + qualité Fisher 14-15/15) | 8-15 % |
| Haute (3 skills convergents positivement) | 5-8 % |
| Moyenne (analyse positive mais avec doutes) | 2-5 % |
| Spéculative (asymétrie attractive mais risque réel) | 1-2 % |

### Étape 7 — Calendrier de révision

Fixer une date de révision (annuelle au minimum, semestrielle pour positions > 10 %). Lors de la révision :
- La thèse tient-elle toujours ?
- Les kill criteria sont-ils déclenchés ?
- Les scenarios projetés se réalisent-ils ?

## Le concept central : "Slow thinking" structuré

Référence aux travaux de Kahneman (System 1 vs System 2). Le "slow thinking" structuré :
- Force la rationalisation explicite
- Réduit l'impulsivité
- Crée un document révisable
- Combat les biais comportementaux

C'est l'antidote aux décisions d'investissement basées sur intuition + FOMO.

## Garde-fous

- **Une thèse n'est pas une garantie**. Même les thèses bien écrites peuvent échouer. Le but n'est pas la certitude — c'est la rigueur du processus.
- **Pas de thèse n'est pire que mauvaise thèse**. Investir sans articulation explicite est pire qu'investir sur une thèse qu'on peut critiquer.
- **Les thèses doivent être falsifiables**. Si aucun fait ne peut "prouver" la thèse fausse, ce n'est pas une thèse — c'est une croyance. Articulater les conditions de falsification.
- **L'écriture force la précision**. Si tu hésites entre 5 et 10 ans pour la croissance, l'écriture force le choix. Cette précision révèle souvent que tu n'as pas vraiment d'opinion fondée.
- **Réviser, pas réécrire**. Quand la thèse échoue, ne pas la réécrire pour la rendre cohérente avec la réalité actuelle. Reconnaître l'erreur, sortir, apprendre.
