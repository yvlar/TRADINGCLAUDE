# C-Score (Montier)

## Origine et utilité

James Montier, stratégiste chez SG Securities puis GMO. Présenté dans *Behavioural Investing* (2007) puis dans *Value Investing: Tools and Techniques for Intelligent Investment* (2009).

L'idée : compléter les modèles pondérés (M-Score, Z-Score) par des **drapeaux qualitatifs** observables directement dans les états financiers, sans calcul complexe. Le C-Score est délibérément simple — six signaux binaires — pour rester utilisable sans tableur.

Le "C" signifie *« Cooking the books »* (cuisiner les comptes).

## Les 6 signaux (1 point chacun si présent)

### 1. Divergence croissante entre bénéfice net et flux de trésorerie d'exploitation

Sur 4 ans glissants, l'écart NI − CFO se creuse. Les bénéfices comptables qui ne se transforment pas en cash réel sont la signature classique de l'agressivité comptable.

**Comment vérifier** : trace NI et CFO sur 5 ans. Si la pente du gap augmente, signal coché.

### 2. Augmentation des jours de receivables (DSO)

DSO = (Receivables / Sales) × 365.

Une croissance des DSO peut signifier :
- *Channel stuffing* (livrer aux clients pour gonfler les ventes)
- Clients en difficulté de paiement (= revenus de mauvaise qualité)
- Reconnaissance prématurée de revenu

**Seuil pratique** : signal coché si DSO_t / DSO_{t-1} > 1.10 (10 % de hausse).

### 3. Augmentation des jours d'inventaire (DIO)

DIO = (Inventory / COGS) × 365.

Inventaire qui grossit plus vite que les ventes peut signaler :
- Obsolescence imminente (inventaire qui ne se vendra plus)
- Anticipation de ventes futures qui ne se concrétisent pas
- Production excessive masquée comme stock

**Seuil pratique** : signal coché si DIO_t / DIO_{t-1} > 1.10.

### 4. Croissance des "autres actifs courants" rapportée au CA

"Autres actifs courants" est souvent une catégorie fourre-tout où on cache des charges qui devraient être au compte de résultat (ex : frais de développement capitalisés agressivement, frais payés d'avance excessifs).

**Comment vérifier** : si (Other Current Assets / Sales)_t > (Other Current Assets / Sales)_{t-1} × 1.10, signal coché.

### 5. Baisse de la dépréciation rapportée aux actifs bruts

Un ratio Dépréciation / PP&E gross qui baisse signale un étirement des durées de vie utiles. Étendre la durée de vie d'un actif = moins de dépréciation chaque année = bénéfice gonflé.

**Comment vérifier** : compare (Dep / PP&E gross)_t vs (Dep / PP&E gross)_{t-1}. Si baisse > 5 %, signal coché.

### 6. Croissance élevée du total des actifs

Montier a observé empiriquement que les entreprises avec une croissance d'actifs > 10 %/an sous-performent. Plusieurs explications :
- Sur-investissement / *empire-building* du management
- Acquisitions à prix excessifs (qui se traduisent en goodwill élevé)
- Capacité excédentaire qui pèsera sur les marges futures

**Seuil pratique** : signal coché si (TA_t / TA_{t-1}) − 1 > 0.10.

## Seuils d'interprétation

| C-Score | Lecture |
|---------|---------|
| 0-1 | OK — pas de drapeaux qualitatifs |
| 2-3 | Surveiller — drapeaux jaunes, contexte requis |
| 4-6 | Manipulation comptable probable — éviter sauf investigation forensique poussée |

## Comment combiner avec les autres cadres

Le C-Score est volontairement simpliste — c'est sa force et sa limite. Il **complète** mais ne remplace pas le M-Score (qui est mathématiquement plus rigoureux). En pratique :

- C-Score 0-1 + M-Score ≤ -2.22 → confiance forte sur la qualité comptable
- C-Score 4+ + M-Score > -1.78 → corroboration forte de manipulation, rejeter
- Divergence (un signal, l'autre non) → investiguer manuellement avant conclusion

## Cas limites

- **Acquisition récente** : fait bondir les actifs (signal 6) sans manipulation
- **Cycle d'investissement industriel** : peut comprimer la dépréciation/actifs (signal 5) légitimement
- **Lancement d'un nouveau produit** : peut faire monter inventaires et receivables sans red flag

## Source primaire

Montier, James (2009). *Value Investing: Tools and Techniques for Intelligent Investment*. Wiley. Chapter 17 — *The Cooking of the Books, or, More Sailing Under the Black Flag*.

Voir aussi : Montier (2007). *Behavioural Investing*. Wiley.
