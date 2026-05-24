# Formule de valeur intrinsèque de Graham

Graham a proposé deux formules pour estimer rapidement la valeur intrinsèque d'une action. Ce sont des **estimations**, pas des vérités — Graham lui-même les a présentées comme des heuristiques rapides, pas des modèles de valorisation rigoureux.

## Formule simple

```
V = BPA × (8.5 + 2g)
```

Où :
- **V** = valeur intrinsèque par action
- **BPA** = bénéfice par action (sur les 12 derniers mois ou moyenne 3 ans)
- **g** = croissance attendue du BPA sur 7-10 ans (en pourcentage, ex: 5 pour 5 %)

### Interprétation
- Une entreprise sans croissance (g=0) vaut 8.5× son BPA
- Chaque point de croissance attendu ajoute 2× au multiple
- Une entreprise à 10 % de croissance attendue vaut (8.5 + 20) × BPA = 28.5× BPA

### Exemple
RBC en 2026 :
- BPA TTM ~12 CAD
- g attendu ~6 % (croissance long terme du secteur bancaire canadien)
- V = 12 × (8.5 + 12) = 246 CAD

À comparer avec le prix actuel — si RBC trade à 130 CAD, marge de sécurité ~47 %.

## Formule ajustée du taux sans risque

Graham a proposé une variante pour tenir compte du niveau des taux d'intérêt :

```
V = BPA × (8.5 + 2g) × 4.4 / Y
```

Où :
- **4.4** = rendement moyen des obligations AAA à l'époque où Graham a calibré (~4.4 % dans les années 1960)
- **Y** = rendement actuel des obligations AAA (10 ans corporate AAA)

### Interprétation
- Quand les taux montent, le multiple acceptable diminue (la formule ajuste à la baisse)
- Quand les taux baissent (ex. 2% comme en 2020-2021), le multiple acceptable augmente — la formule ajuste à la hausse

### Exemple ajusté pour 2026
Y ≈ 5 % (corporate AAA 10 ans en 2026)
RBC ajusté :
- V = 12 × (8.5 + 12) × 4.4 / 5 = 216 CAD

L'ajustement réduit légèrement la valeur estimée car les taux 2026 sont supérieurs aux 4.4 % de calibration.

## Limites importantes

### 1. La formule n'a pas de fondement théorique solide
Graham l'a présentée comme une **heuristique pratique**, pas comme un DCF rigoureux. Elle implique des hypothèses sur le P/E "juste" et la durabilité de la croissance qui ne sont jamais explicitées formellement.

### 2. Sensibilité énorme à g
Une erreur de 2 % sur la croissance attendue change radicalement V :
- g = 6 % → multiplicateur 20.5×
- g = 8 % → multiplicateur 24.5× (+20 %)
- g = 10 % → multiplicateur 28.5× (+39 %)

L'estimation de g est donc le facteur dominant. Tirer g du passé (CAGR 10 ans) **et** de l'analyse fondamentale (durabilité du moat).

### 3. Formule simple inadaptée aux sociétés cycliques
Pour une société cyclique, le BPA TTM peut être anormalement haut (sommet de cycle) ou bas (creux). Utiliser une **moyenne sur cycle complet** (10-15 ans) plutôt que BPA TTM.

### 4. Limite supérieure raisonnable
Graham conseillait de **ne pas appliquer la formule pour g > 15 %**. Une croissance > 15 % sur 7-10 ans est rarement durable, et le multiplicateur devient irréaliste.

## Modernisation : variantes contemporaines

Plusieurs analystes ont proposé des variantes :

### Variante de John Price (NYU)
Limite g à 15 % maximum dans la formule pour éviter la sur-extrapolation.

### Variante avec g normalisé
Utiliser une moyenne pondérée :
```
g_normalisé = 0.5 × g_passé(10 ans) + 0.5 × g_analyste_consensus
```

## Marge de sécurité

Une fois V calculée, la **marge de sécurité** est :
```
Marge = (V − Prix actuel) / V
```

Graham conseillait **30 à 50 %** de marge de sécurité avant d'acheter. C'est strict, mais explique pourquoi il achetait peu et concentrait fort. En 2026, viser 25-40 % est généralement plus pragmatique pour avoir un univers d'opportunités exploitable.

## Quand utiliser cette formule

✅ **Approprié** :
- Premier screening rapide
- Comparaison entre plusieurs candidats du même secteur
- Sanity check sur une valorisation DCF complexe (ordres de grandeur cohérents ?)

❌ **Inapproprié** :
- Décision finale d'investissement (trop simpliste)
- Sociétés en transformation (le BPA actuel n'est pas représentatif)
- Sociétés cycliques au sommet ou creux du cycle (utiliser BPA normalisé)
- Sociétés non rentables ou jeunes (BPA non significatif)

Pour la décision finale, utiliser un cadre plus rigoureux : `stock-valuation-triangulation` avec DCF + multiples + sectoriel.

## Source

Graham, B. (1973). *The Intelligent Investor*, chapitre 11, "Security Analysis for the Lay Investor: General Approach", note de bas de page sur la formule simplifiée.

La formule a été popularisée bien au-delà de ce que Graham lui-même considérait — il la mentionne presque en passant comme une approximation rapide, pas comme la pierre angulaire de sa méthode.
