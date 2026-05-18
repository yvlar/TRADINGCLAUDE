---
paths:
  - "app/skills/**"
  - "analyses/**"
---

# Données financières — validation et traçabilité

## Quand cette règle s'applique

Lors de l'édition de skills (tier1 ou tier2) ou de fichiers d'analyse dans `analyses/`.

## Règles

### Validation des données

Avant tout calcul, valider systématiquement :

- **Valeurs `None`** : ne jamais supposer qu'un ratio est présent
  ```python
  # ✅ Correct
  graham_number = (
      (22.5 * eps * bvps) ** 0.5
      if eps is not None and eps > 0 and bvps is not None and bvps > 0
      else None
  )
  # ❌ Incorrect — plante si eps est None
  graham_number = (22.5 * eps * bvps) ** 0.5
  ```
- **Division par zéro** : vérifier le dénominateur avant division
  ```python
  pe = price / eps if eps and eps != 0 else None
  ```
- **Valeurs aberrantes** : signaler si un ratio semble hors plage (ex. P/E < 0 hors pertes, ROIC > 300 %)

### Traçabilité obligatoire

Toute analyse ou rapport doit préciser :
- **Source** des données : Yahoo Finance, SEDAR+, données manuelles, etc.
- **Date** de récupération — les ratios sont volatils ; une donnée sans date est inutilisable

### Backtesting vs live

Distinguer explicitement dans le code et les analyses :

```python
# données historiques — simulation backtesting
# données live — Yahoo Finance 2026-05-17
```

### Cas spéciaux

#### `current_ratio` pour institutions financières

Les banques et assureurs n'ont pas de `current_ratio` significatif (bilan structurellement différent).

- Valeur `null` = **normal** pour `BNS.TO`, `TD.TO`, `RY.TO`, `NA.TO`, `BMO.TO`, `CM.TO`, etc.
- Ne pas éliminer une banque des critères Graham uniquement sur ce champ nul
- Adapter le critère de liquidité au secteur (ratio Tier 1 capital, etc.)

#### Tickers TSX — suffixe `.TO` obligatoire

Yahoo Finance retourne les données canadiennes **uniquement** avec le suffixe `.TO` :

```python
# ✅ Correct — données TSX
ticker = "BNS.TO"   # Banque de Nouvelle-Écosse
ticker = "NA.TO"    # Banque Nationale
ticker = "BCE.TO"   # BCE Inc.
ticker = "CNR.TO"   # Canadien National

# ❌ Incorrect — retourne OTC américain ou erreur
ticker = "BNS"
ticker = "NA"
```

Normaliser via `app/utils/ticker_sanitizer.py` à l'entrée des endpoints.
