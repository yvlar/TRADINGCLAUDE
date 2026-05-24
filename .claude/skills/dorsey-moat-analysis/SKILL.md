---
name: dorsey-moat-analysis
description: Applique le cadre d'analyse des moats économiques de Pat Dorsey (The Five Rules for Successful Stock Investing, The Little Book That Builds Wealth) — identification et qualification des cinq sources d'avantages concurrentiels durables. À utiliser dès que l'utilisateur mentionne Dorsey, moat, "économic moat", "wide moat", "narrow moat", avantages concurrentiels durables, switching costs, network effects, intangible assets, cost advantages, efficient scale, ou veut évaluer la durabilité du leadership concurrentiel d'une entreprise. Utilise toujours ce skill avant de qualifier une entreprise de "wide moat" ou d'envisager un holding très long terme.
---

# Dorsey — Moat Analysis

Applique le cadre de Pat Dorsey (ex-Morningstar) qui rend opérationnel le concept buffettien de moat. L'idée centrale : les rendements élevés attirent la concurrence ; une entreprise qui maintient ROIC > coût du capital pendant 10+ ans le fait grâce à un **moat structurel identifiable**, pas par chance.

## Quand utiliser quelle référence

| Source de moat | Référence |
|----------------|-----------|
| Actifs intangibles (marques, brevets, licences) | `references/moat-intangibles.md` |
| Coûts de transfert (switching costs) | `references/moat-switching-costs.md` |
| Effets de réseau | `references/moat-network-effects.md` |
| Avantages de coût | `references/moat-cost-advantages.md` |
| Échelle efficiente | `references/moat-efficient-scale.md` |

## Workflow

### Étape 1 — Test préalable : ROIC durable

Avant même de chercher la source du moat, vérifier que les chiffres confirment qu'il en existe un :

```bash
python scripts/roic_durability.py inputs.json
```

Indicateurs d'un moat probable :
- **ROIC > 15 % sur 10 ans** (moyenne) sans levier excessif
- **Dispersion faible** d'année en année (stabilité = signal de moat fort)
- **Spread ROIC − CMPC** durablement positif (création de valeur)

Si le ROIC est volatile ou en érosion → moat absent ou disparaissant.

### Étape 2 — Identifier les sources de moat

Pour chaque entreprise, déterminer laquelle (ou lesquelles) des 5 sources s'applique. Lire la référence correspondante pour chaque source plausible.

**Si aucune source ne s'applique clairement, le ROIC élevé n'est probablement pas durable** — c'est probablement une rente temporaire qui se compressera.

### Étape 3 — Qualifier la profondeur

Pour chaque moat identifié, évaluer :

| Profondeur | Test |
|------------|------|
| **Wide** | Avantage substantiel, durable > 20 ans probable |
| **Narrow** | Avantage réel, durable > 10 ans probable |
| **None** | ROIC élevé sans protection durable identifiée |

### Étape 4 — Évaluer la trajectoire

| Trend | Signal |
|-------|--------|
| **Croissant** | Moat se renforce — très positif |
| **Stable** | Moat préservé — neutre positif |
| **Erosion** | Moat menacé — drapeau rouge majeur |

Indicateurs d'érosion :
- Marges en compression progressive sur 5+ ans
- ROIC qui plafonne ou descend
- Parts de marché qui glissent
- Croissance ralentit alors que le marché continue de croître

## Industries qui systématiquement manquent de moat

Dorsey signale les secteurs où les moats sont rares ou impossibles à construire durablement :
- **Compagnies aériennes** (commodity transport, capex énorme, pricing power nul)
- **Construction résidentielle** (cyclique, fragmenté, peu différencié)
- **Restauration indépendante** (faibles barrières à l'entrée)
- **Commerce de détail non-spécialisé** (Amazon a écrasé les moats existants)
- **Production de matières premières** sans avantage de coût géologique

Ces secteurs peuvent offrir des opportunités de **prix** (deep value à la Graham), mais pas de **qualité durable**.

## Garde-fous

- **Pas de moat = pas de prime de qualité.** Une entreprise sans moat clair ne mérite pas un multiple supérieur à la moyenne, même si ses chiffres récents sont excellents. La concurrence ramène le ROIC à la moyenne.
- **Méfiance face aux "moats narratifs".** Beaucoup d'entreprises racontent une histoire de moat (« notre marque », « notre technologie ») non confirmée par les chiffres. Le ROIC durable est le test ultime.
- **Les moats s'érodent souvent silencieusement.** Avant la chute spectaculaire (Kodak, Nokia, Blockbuster), il y a typiquement 5-10 ans de signaux faibles : ROIC qui plafonne, marges qui se compriment graduellement, parts de marché qui glissent. Surveiller activement.
- **Croissance ≠ moat.** Une entreprise peut croître rapidement sans moat (puis être détruite par la concurrence). Une entreprise peut avoir un moat large sans croître (vache à lait). Distinguer les deux dimensions.
- **Les moats numériques sont volatils.** Les effets de réseau dans le numérique se retournent vite (MySpace → Facebook, Yahoo → Google). Appliquer un facteur de prudence supplémentaire — réduire mentalement la durée présumée du moat.
