---
name: fisher-scuttlebutt
description: Applique les méthodes de Phil Fisher (Common Stocks and Uncommon Profits, 1958) — les 15 points pour évaluer une entreprise et la méthode "scuttlebutt" (recherche qualitative auprès des clients, fournisseurs, ex-employés, concurrents). À utiliser dès que l'utilisateur mentionne Fisher, scuttlebutt, "15 points", "Common Stocks Uncommon Profits", recherche qualitative sur une entreprise, ou veut compléter l'analyse fondamentale par enquête terrain. Utilise toujours ce skill avant de prendre une position significative pour vérifier la qualité de la direction et la culture d'entreprise.
---

# Fisher — 15 Points and Scuttlebutt

Phil Fisher (1907-2004) a été un des premiers à insister sur l'**analyse qualitative** au-delà des chiffres. Son livre *Common Stocks and Uncommon Profits* (1958) a profondément influencé Buffett, qui se décrit comme *"85% Graham, 15% Fisher"*.

L'innovation Fisher : la qualité de la direction et de la culture compte plus que les multiples actuels. Et pour l'évaluer, il faut **sortir des chiffres** et faire de la recherche terrain.

## Quand utiliser quelle référence

| Question | Référence |
|----------|-----------|
| Les 15 points avec applications | `references/15-points-fisher.md` |
| Méthode scuttlebutt — comment faire | `references/scuttlebutt-methode.md` |
| Évaluer la qualité de la direction | `references/qualite-direction.md` |

## Workflow

### Étape 1 — Pré-screen quantitatif

Fisher acceptait que l'analyse quantitative préalable filtre l'univers. Utiliser `graham-stock-screening` ou `dorsey-moat-analysis` pour identifier les candidats avec fondamentaux solides.

### Étape 2 — Appliquer les 15 points

```bash
python scripts/fisher_15_points.py inputs.json
```

Le script évalue les 15 points Fisher (capacité de recherche, marges, relations employés-direction, intégrité, etc.) et flagge les drapeaux rouges.

### Étape 3 — Conduire le scuttlebutt

Le terme "scuttlebutt" vient du jargon naval — les rumeurs informelles partagées au tonneau d'eau (le "scuttlebutt"). Fisher l'utilise pour décrire la **recherche qualitative auprès des stakeholders**.

**Sources à interroger** (par ordre d'importance) :
1. **Ex-employés** (LinkedIn, Glassdoor — le plus accessible)
2. **Clients** (interviews, enquêtes industrie)
3. **Fournisseurs** (relations commerciales)
4. **Concurrents** (interview les leaders pour avoir leur vue sur l'entreprise cible)
5. **Distributeurs**
6. **Analystes du sell-side** (avec filtre des biais)
7. **Régulateurs sectoriels** (rare mais précieux)

Voir `references/scuttlebutt-methode.md` pour les techniques pratiques.

### Étape 4 — Synthèse qualitative

Combiner les 15 points + scuttlebutt pour répondre :
- La direction est-elle compétente, intègre, alignée avec les actionnaires ?
- La culture d'entreprise favorise-t-elle l'innovation et la qualité ?
- Y a-t-il des drapeaux rouges éliminatoires ?

### Étape 5 — Décision finale

Fisher préconisait :
- **Concentration** sur 10-20 entreprises de très haute qualité
- **Holding period très long** (15-30 ans)
- **Vente rare** (uniquement si fondamentaux changent)

## Le concept central : "Wonderful businesses run by wonderful people"

Buffett doit cette philosophie en grande partie à Fisher. L'idée :
- Acheter une entreprise médiocre à un excellent prix peut donner un ×2 sur 5 ans
- Acheter une entreprise exceptionnelle à un prix correct peut donner un ×10 sur 20 ans

La qualité durable surpasse la valorisation déprimée pour le long-terme.

## Garde-fous

- **Le scuttlebutt demande du temps**. Fisher passait des semaines sur chaque entreprise. Pas adapté pour les portfolios de 50+ positions ou les idées rapides.
- **Risque de biais de confirmation**. Une fois qu'on a une thèse positive, on cherche les confirmations. Discipline : interroger spécifiquement les sceptiques.
- **Insider trading vs research légitime**. Le scuttlebutt doit rester sur des **opinions et perceptions**, pas sur des **informations matérielles non publiques**. Une conversation avec un employé qui révèle les chiffres trimestriels avant publication = délit.
- **Glassdoor et LinkedIn ont leurs biais**. Les employés mécontents écrivent plus que les contents. Filtrer pour les patterns récurrents, pas les opinions isolées.
- **Les 15 points ne sont pas tous égaux**. Les points 14 (transparence en cas de problème) et 15 (intégrité) sont **éliminatoires**. Sans eux, refuser indépendamment des autres scores.
