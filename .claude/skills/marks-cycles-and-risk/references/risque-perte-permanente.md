# Le Risque selon Marks — Perte Permanente plutôt que Volatilité

L'une des contributions les plus importantes de Marks est sa **redéfinition du risque**. Pour la finance académique, le risque = volatilité (déviation standard des rendements). Pour Marks, c'est faux et dangereux.

## La définition académique du risque (et pourquoi elle est mauvaise)

### Modern Portfolio Theory
- Risque = écart-type des rendements
- Plus une action varie, plus elle est risquée
- Mathématiquement élégant, fondement du CAPM

### Pourquoi c'est inadéquat

**Cas 1** : Action A trade entre 80 et 120 (volatile) avec valeur intrinsèque 100. Risque réel = faible (le prix oscille autour de la valeur).

**Cas 2** : Action B trade stable à 95 avec valeur intrinsèque 50. Risque réel = très élevé (sur-évaluation) malgré faible volatilité.

La volatilité ne mesure pas le risque que l'investisseur subit. Une action qui baisse temporairement à 80 puis remonte à 120 a "volatilité" mais zéro perte permanente.

## La définition Marks du risque

> *« Risk means more things can happen than will happen. »*

Et plus pratiquement :

> *« Risk is the probability of permanent loss of capital. »*

**Permanent** est le mot clé. Une action qui chute -40 % puis remonte n'a pas causé de perte permanente. Une action qui passe de 100 à 60 et reste à 60 indéfiniment a causé une perte permanente de 40 %.

## Conséquences pratiques

### 1. Volatilité ≠ Risque

Une action qui oscille -30 % +30 % autour de sa valeur intrinsèque est moins risquée qu'une action stable mais à un prix structurellement excessif.

### 2. Risque vient du prix

Plus le prix est haut vs valeur intrinsèque, plus le risque est élevé. Une excellente entreprise à un mauvais prix est risquée. Une entreprise médiocre à un excellent prix peut être moins risquée.

C'est l'inverse de l'intuition courante (investir dans la meilleure entreprise est "sûr").

### 3. Compounders payés cher = risque souvent ignoré

Les "Nifty Fifty" en 1972 : excellentes entreprises (Coca-Cola, Avon, Polaroid, Xerox) à 60-100x earnings. Les investisseurs disaient "ces entreprises ne peuvent pas perdre".

**Résultat** : drawdown de -50 % à -90 % dans la décennie suivante. Plusieurs (Polaroid, Avon) ne sont jamais revenues. Perte permanente sur des "blue chips".

### 4. Tail risk vs central risk

La volatilité capture la **moyenne** des fluctuations. Le risque réel vient typiquement des **événements rares mais catastrophiques** (faillite, fraude, perte de moat).

Une distribution avec faible volatilité **mais** queue grasse vers le négatif (fat tail) est plus risquée que la volatilité ne le suggère.

## Sources de risque réel (Marks)

### 1. Surpaiement du prix

Le risque #1. Toute action achetée significativement au-dessus de la valeur intrinsèque a une probabilité élevée de perte permanente.

### 2. Détérioration des fondamentaux

L'entreprise change pour le pire :
- Disruption technologique (Kodak vs digital)
- Erosion de moat (Sears vs Walmart vs Amazon)
- Mauvaise allocation de capital (acquisitions ratées)
- Fraude

### 3. Choc externe non anticipé

- Récession sévère qui détruit la demande
- Pandémie (COVID 2020)
- Guerre / crise géopolitique
- Faillite d'un client clé concentré

### 4. Levier en cycle baissier

L'entreprise endettée qui voit sa cash flow baisser peut faire faillite avec ses créanciers se partageant la valeur restante. Les actionnaires sont effacés.

### 5. Risque comportemental de l'investisseur

Vendre au creux par panique. Acheter au sommet par FOMO. Ces erreurs créent des pertes permanentes même dans des actions qui n'avaient pas de problème.

## Mesurer le risque (selon Marks)

Marks rejette les mesures purement quantitatives. Il propose :

### Test 1 — Probabilité de perte permanente
Si tu devais articuler le scenario d'échec total, quelle est sa probabilité ?
- < 5 % = risque acceptable
- 5-15 % = risque modéré (justifie marge de sécurité)
- > 15 % = risque élevé (sizing très limité)

### Test 2 — Magnitude de la perte
Dans le scenario d'échec, combien je perds ?
- 0-30 % = supportable
- 30-60 % = significatif
- > 60 % = catastrophique

### Test 3 — Asymétrie risque-récompense
Probabilité × magnitude pour scenarios positifs ET négatifs.
- Si EV positive et magnitude perte < 50 % : acceptable
- Sinon : passer

## Le piège du "good company = safe investment"

Les investisseurs commettent constamment cette erreur :
- "Apple est une excellente entreprise, c'est un investissement sûr"
- "Microsoft a un moat, je peux acheter à n'importe quel prix"
- "Costco continue à grandir, valorisation n'importe pas"

Ces affirmations confondent **qualité d'entreprise** et **risque d'investissement**. Une excellente entreprise à un prix excessif est un investissement risqué.

### Test
Pour chaque "blue chip" qu'on considère "safe", se poser :
- À quel prix l'entreprise serait-elle clairement chère ?
- Le prix actuel est-il sous, autour, ou au-dessus de ce seuil ?

Si > seuil "clairement chère", l'investissement n'est pas safe.

## Implications portfolio

### Diversification limitée
La diversification académique (20-30 stocks) réduit la volatilité mais pas nécessairement le risque réel. Si tous tes 30 stocks sont dans des bulles, ta diversification est illusoire.

### Concentration justifiée par marge de sécurité
Marks accepte la concentration **uniquement** sur des positions avec marge de sécurité significative. La concentration sur des positions chères est gambling.

### Hedging asymétrique
Plutôt que diversifier, Marks utilise du hedging asymétrique (puts OTM, allocation cash, certains shorts) pour limiter les drawdowns en cas de tail event.

## Le risque caché : opportunity cost de cash

Critique légitime de Marks : maintenir 30 % cash en bull market = sous-performance énorme.

Réponse Marks : ce coût est le **prix de l'option** sur les opportunités futures. Sur un cycle complet (10-15 ans), la stratégie gagne typiquement contre l'index parce qu'elle évite les drawdowns -50 %.

Mais si tu n'as pas la patience pour traverser 5 ans de sous-performance, **ne pas l'appliquer**. Préférer DCA constant sur index.

## Synthèse

| Définition académique | Définition Marks |
|-----------------------|-------------------|
| Volatilité (déviation standard) | Probabilité de perte permanente |
| Mesurable précisément | Mesurable approximativement |
| Symétrique (haut et bas) | Asymétrique (perte > gain de même magnitude) |
| Court-terme (mois, trimestres) | Long-terme (sur cycle complet) |
| Idéal pour modèles mathématiques | Idéal pour décisions réelles |

**La définition Marks est plus utile** pour l'investisseur. La définition académique est plus utile pour les chercheurs et certaines stratégies systématiques.
