# Marge de sécurité — niveaux requis selon le type d'investissement

Klarman calibre la marge de sécurité requise selon le **degré d'incertitude** de l'investissement. Plus l'opportunité est complexe ou risquée, plus la marge doit être large.

## Calcul de la marge de sécurité

```
Marge de sécurité (%) = (Valeur intrinsèque − Prix) / Valeur intrinsèque
```

Exemple : VI estimée 100, prix 65 → marge = (100-65)/100 = **35 %**

## Échelle des marges requises (Klarman)

### Tier 1 — Compounders de qualité (25-30 %)

Entreprises avec :
- Moat clair et durable
- ROIC élevé maintenu sur 10+ ans
- Bilan solide
- Croissance prévisible
- Direction prouvée

**Exemples** : Berkshire Hathaway, Costco, Visa, Microsoft (post-2015), Constellation Software

Marge minimum exigée : **25-30 %**.

Pourquoi cette marge plus modeste ? L'incertitude est faible. La valeur intrinsèque elle-même est plus prévisible.

### Tier 2 — Cycliques au creux (40-50 %)

Entreprises dans :
- Industries cycliques visibles (acier, automobile, chimie, énergie aval)
- Au creux du cycle ou en début de récupération
- Avec bilan tenable pour traverser le cycle

**Exemples** : Magna en récession, Methanex en creux du cycle methanol, US steel à -60 %

Marge minimum exigée : **40-50 %**.

Pourquoi plus large ? La valeur intrinsèque dépend de la position dans le cycle (incertaine). Et les cycles peuvent durer plus longtemps que prévu.

### Tier 3 — Special situations (30-40 %)

- Spinoffs (rejoint Greenblatt)
- Restructurations en cours
- Sorties de Chapter 11 récentes
- Asset plays avec catalyseur identifié

**Exemples** : Topicus à la sortie de Constellation, Berkshire à la sortie d'AmEx 1962

Marge minimum exigée : **30-40 %**.

Pourquoi cette zone ? L'analyse fondamentale révèle une valeur cachée que le marché n'a pas (encore) reconnue. La thèse est claire mais demande du temps.

### Tier 4 — Distressed debt (50 %+)

Obligations d'entreprises en difficulté financière, négociées 30-70 cents pour 100 cents de valeur nominale.

**Exemples** : Lehman Brothers debt post-2008, GM debt 2009 (avant Chapter 11), Frontier Communications debt 2018

Marge minimum exigée : **50 %+** (parfois 70 % pour les cas vraiment risqués).

Pourquoi cette marge énorme ? Les distressed peuvent voir le capital totalement effacé en cas de Chapter 11 mal géré. La marge protège contre l'erreur d'analyse.

### Tier 5 — Asset plays en distress profond (50-60 %+)

Entreprises où la thèse repose sur des actifs spécifiques (immobilier, royalties, IP) sous-évalués, **mais** dans un contexte de distress organisationnel.

**Exemples** : Sears Holdings 2010-2018 (Real estate value cachée mais entreprise en hémorragie), General Growth Properties bankruptcy 2009

Marge minimum exigée : **50-60 %**.

Pourquoi le plus large ? Combinaison du risque distressed + risque de l'évaluation des actifs eux-mêmes (l'immobilier peut perdre 30 % en récession).

## Application au calcul

### Formule pour valider une opportunité

```python
def opportunite_acceptable(valeur_intrinseque, prix, type_opportunite):
    marge_actuelle = (valeur_intrinseque - prix) / valeur_intrinseque

    seuils = {
        'compounder': 0.25,
        'cyclique': 0.40,
        'special_situation': 0.30,
        'distressed': 0.50,
        'asset_play_distress': 0.55,
    }

    seuil = seuils[type_opportunite]
    return marge_actuelle >= seuil
```

### Exemple

Tesla en 2025 :
- Valeur intrinsèque (DCF conservateur) : 250 USD/action
- Prix actuel : 200 USD/action
- Marge actuelle : (250-200)/250 = 20 %

Type : compounder (croissance + maturité partielle).
Seuil requis : 25 %.

Marge actuelle (20 %) < seuil (25 %) → **Pas acceptable**.

Attendre une baisse à ~187 USD pour atteindre 25 % de marge.

## Pourquoi cette discipline marche

### 1. Compense les erreurs d'analyse

Tu vas te tromper sur la valeur intrinsèque. La marge de sécurité absorbe l'erreur :
- Si VI réelle = 80 (au lieu de 100 estimé), prix d'achat 65 reste rentable
- Sans marge, achat à 95 → perte si VI réelle = 80

### 2. Compense les chocs externes

Récessions, scandales, événements géopolitiques. Une position avec 30 % de marge peut absorber un choc de -25 % sans perte permanente.

### 3. Protège contre l'optimisme

Toi-même tu auras tendance à voir le verre à moitié plein. La marge force à acheter quand le marché est à moitié vide.

## Pièges courants

### 1. Marge calculée sur VI optimiste

Si tu calcules la VI avec hypothèses optimistes (g 15 % au lieu de 5 %, marges qui s'améliorent au lieu de stables), la marge est artificielle.

**Solution** : utiliser les hypothèses **les plus prudentes** justifiables. Vérifier avec un sanity check : aux hypothèses prudentes, la marge tient-elle encore ?

### 2. Catégorisation lâche

Classer un cyclique en compounder pour réduire le seuil de marge. Discipline : si la cyclicité est visible dans l'historique, c'est un cyclique, pas un compounder.

### 3. "Cette fois c'est différent"

Je ne peux pas attendre 30 % de marge sur cette opportunité parce que la qualité est exceptionnelle. C'est exactement le piège que la marge protège contre.

### 4. Paralysie d'analyse

À l'inverse, exiger 50 % de marge sur tout fait rater toutes les opportunités. La calibration par tier permet d'ajuster intelligemment.

## Résumé pratique

Avant d'acheter, se poser :

1. **Quel type d'opportunité ?** (Tier 1-5)
2. **Quelle est la marge minimum exigée pour ce tier ?** (25-60 %)
3. **Quelle est la marge actuelle au prix de marché ?**
4. **Si insuffisante, quel prix d'achat cible offre la marge requise ?**

Patience jusqu'à ce que le prix atteigne le cible — ou abandonner l'idée si ça ne se réalise pas dans les 12-18 mois.
