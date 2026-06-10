---
name: graham-screener
description: Screening systématique des 7 critères de Benjamin Graham (chapitre 14, L'Investisseur Intelligent) sur un univers de titres. Utiliser ce skill dès que l'utilisateur veut filtrer, screener, classer ou comparer plusieurs actions selon des critères value quantitatifs — y compris des formulations comme « trouve-moi des actions sous-évaluées », « passe ces tickers au filtre Graham », « lesquels de ces titres sont de la vraie value », « screen le S&P 500 », « calcule le Graham Number », ou toute demande de validation quantitative avant une analyse value qualitative approfondie. Ce skill est le pont entre le pilier value (analyse discrétionnaire) et le pilier algorithmique (règles mécaniques).
---

# Graham Screener — Filtre systématique des 7 critères

Ce skill applique mécaniquement les 7 critères de l'investisseur défensif de
Benjamin Graham (chapitre 14, *The Intelligent Investor*, éd. 1973) à une liste
de tickers, produit un score composite /7, calcule le Graham Number et la marge
de sécurité, et classe les candidats. Il transforme le filtre Graham — normalement
appliqué titre par titre — en screening d'univers complet.

## Philosophie

Le screening est un **filtre d'élimination, pas une recommandation d'achat**.
Un score 7/7 signifie « mérite une analyse qualitative complète » (moat Dorsey,
qualité du management, thèse), jamais « acheter ». Un score < 4/7 élimine le
titre du pilier value sans plus d'effort. Toujours rappeler cette distinction
à l'utilisateur dans la synthèse.

## Workflow

1. **Obtenir l'univers** : liste de tickers fournie par l'utilisateur, ou
   univers prédéfini (voir `assets/universes.json` pour des listes de départ).
2. **Exécuter le screening** (depuis la racine du dépôt; `yfinance` est déjà
   dans `requirements.txt`) :
   ```bash
   python .claude/skills/graham-screener/scripts/graham_screener.py \
       --tickers AAPL,BMY,KO,JNJ --output results.csv
   ```

   Mode démo sans réseau (données d'exemple embarquées) :

   ```bash
   python .claude/skills/graham-screener/scripts/graham_screener.py --demo
   ```

3. **Lire les résultats** : le script produit un tableau console + CSV avec,
   pour chaque titre : verdict par critère (PASS/FAIL/N/A), score /7,
   Graham Number, marge de sécurité, et drapeau de couverture de données.
4. **Synthétiser** : classer par score puis par marge de sécurité. Signaler
   explicitement les critères évalués sur données partielles (voir Limites).
5. **Pont vers l'analyse qualitative** : pour les titres ≥ 5/7, proposer de
   poursuivre avec les skills d'analyse value (Graham complet, Dorsey moat,
   Buffett owner earnings) sur les 2-3 meilleurs candidats seulement.

## Les 7 critères (résumé — détails dans references/graham_criteria.md)

|#|Critère                 |Seuil original 1973                               |Adaptation moderne (défaut du script)              |
|-|------------------------|--------------------------------------------------|---------------------------------------------------|
|1|Taille adéquate         |Revenus ≥ 100 M$                                  |Revenus ≥ 2 G$ (ajusté inflation)                  |
|2|Solidité financière     |Current ratio ≥ 2 ET dette LT ≤ fonds de roulement|Identique                                          |
|3|Stabilité des bénéfices |Bénéfices positifs 10 ans consécutifs             |Positifs sur toutes les années disponibles (min. 4)|
|4|Dividendes ininterrompus|20 ans                                            |Versement continu sur l'historique disponible      |
|5|Croissance des bénéfices|BPA +33 % sur 10 ans                              |CAGR BPA ≥ 3 %/an sur la fenêtre disponible        |
|6|P/E modéré              |≤ 15 (bénéfices moyens 3 ans)                     |Identique                                          |
|7|P/B modéré              |≤ 1,5 OU P/E × P/B ≤ 22,5                         |Identique                                          |

**Graham Number** = √(22,5 × BPA × valeur comptable par action). C'est le prix
maximal théorique qu'un investisseur défensif paierait. Marge de sécurité =
(Graham Number − prix) / Graham Number.

## Limites — à toujours communiquer

- **Couverture de données** : yfinance ne fournit que ~4-5 ans d'états
  financiers. Les critères 3, 4 et 5 (conçus pour 10-20 ans) sont donc évalués
  sur fenêtre courte — le script le signale par un drapeau `partial_data`.
  Un PASS sur données partielles est plus faible qu'un PASS sur 10 ans.
- **Secteurs inadaptés** : les critères Graham pénalisent structurellement les
  banques (current ratio non pertinent), les techs asset-light (P/B élevé par
  nature) et les REIT. Le signaler si l'univers en contient.
- **Value trap** : passer le filtre n'élimine pas le risque de décote
  perpétuelle. Le filtre mesure le prix, pas le catalyseur.
- Les données proviennent de sources publiques gratuites; vérifier les chiffres
  critiques aux états financiers (10-K/10-Q) avant toute décision.

## Workflow batch : univers complet → Qdrant

Pour screener un univers entier (S&P 500) et alimenter le pipeline RAG :

```bash
# 1. Screening complet avec checkpoint (interruptible, reprise via --resume)
python .claude/skills/graham-screener/scripts/batch_screen.py --universe sp500 --min-score 5

# 2. Ingestion des candidats dans Qdrant (text-embedding-3-small, même modèle
#    que le corpus investment_knowledge; URL lue depuis $QDRANT_URL)
python .claude/skills/graham-screener/scripts/ingest_qdrant.py \
    --input output/candidates.jsonl --collection graham_screening

# Test du flux complet sans réseau ni serveur :
python .claude/skills/graham-screener/scripts/batch_screen.py --universe demo --output-dir /tmp/t
python .claude/skills/graham-screener/scripts/ingest_qdrant.py \
    --input /tmp/t/candidates.jsonl --url ":memory:" --embedder dummy
```

Chaque candidat devient un document daté (`graham-AAAA-MM-JJ-TICKER`) avec
résumé français pour l'embedding et payload structuré (score, marge, critères
échoués) pour le filtrage — payload aligné sur `RagClient.search`
(`source_file` + `chunk_text`). Les ré-ingestions sont idempotentes (UUID
déterministe). Screener périodiquement crée un historique interrogeable :
« quels titres sont passés de 4/7 à 6/7 ce trimestre? »

## Format de sortie attendu

Synthèse en 3 blocs : (1) tableau classé score décroissant puis marge de
sécurité, (2) candidats ≥ 5/7 avec leurs critères échoués nommés explicitement,
(3) rappel filtre ≠ recommandation + prochaine étape qualitative proposée.
