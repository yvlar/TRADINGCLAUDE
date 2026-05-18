---
paths:
  - "analyses/**"
---

# Format des analyses financières

## Quand cette règle s'applique

Lors de la génération ou l'édition de fichiers d'analyse dans `analyses/` (ex. `BNS-2026-05.md`).

## Règles

### Langue et ton

- Toutes les analyses sont rédigées **en français**
- Réponses orientées **décision** : verdict clair d'abord, justification ensuite
- Pas de remplissage — chaque phrase porte une information ou un jugement
- Ne pas reformuler ce que les chiffres disent déjà : interpréter, pas décrire

### Formules financières

Montrer le calcul intermédiaire, jamais juste le résultat :

```
Graham Number = √(22.5 × EPS × BVPS)
             = √(22.5 × 7.25 × 61.50)
             = √(10 048.31)
             = 100.24 $

Cours actuel : 80.00 $  →  décote de 20.2 % par rapport à la valeur Graham
```

### Structure des analyses

Suivre la structure du modèle `analyses/BNS-2026-05.md` :

1. **En-tête** : ticker, date d'analyse, source et date des données
2. **Résumé exécutif** : verdict global + score composite (1 paragraphe, action recommandée)
3. **Résultats par skill** : dans l'ordre du workflow utilisé, chaque section inclut le verdict du skill + points clés
4. **Tableau synthèse** : scores par skill, composite_score, label (FORT / CORRECT / FAIBLE)
5. **Décision d'investissement** : action recommandée (Acheter / Surveiller / Éviter) + conditions (prix cible, catalyseurs, kill criteria)

### Citations RAG

Si des citations Qdrant sont disponibles dans le output d'un skill (champ `citations`), les inclure en bas de la section correspondante avec la source et le score de pertinence.
