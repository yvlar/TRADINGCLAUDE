# Audit — Dimension Investissement

> Produit par l'agent `audit-investissement`. Constats sourcés `fichier:ligne`. Les hypothèses en fin de document ont été soumises à l'agent `verificateur-hypotheses` (voir [`00-synthese-hypotheses.md`](00-synthese-hypotheses.md)).

## Résumé exécutif

TradingClaude est un copilote d'analyse fondamentale solide sur le plan de la *rigueur de calcul*. Les 16 frameworks tier2 couvrent l'essentiel du canon value/quality/growth (Graham, Buffett, Lynch, Dorsey, Greenblatt, Klarman, Damodaran, Fisher, Marks, Munger, Pabrai…), et la décision d'architecture la plus importante côté finance — **substituer les scores déterministes (M/Z/F/C-Score, Sloan, Nombre de Graham, ossature DCF) calculés en Python au bloc généré par le LLM** — est correcte et bien appliquée. Le modèle interprète, il ne fabrique plus les chiffres. Les faiblesses ne portent pas sur la conception des frameworks mais sur la **fraîcheur et la provenance des données** (un extracteur canadien non fonctionnel, aucune validation d'ancienneté des ratios) et sur la **couverture des piliers** (passif/thématique non implémentés).

**Note globale : A− (excellente conception, lacunes de données).**

## Forces

- Calculs déterministes auditables et substitués au LLM : `app/services/financial_calculations.py` (M/Z/F/C-Score, Sloan, Nombre de Graham, sous-composantes Beneish DSRI/GMI/… et termes Altman X1-X5).
- Ossature DCF déterministe (WACC, valeur intrinsèque, matrice de sensibilité) dans `app/services/valuation_calculations.py`, exclusion correcte des financières/REIT.
- Validation des données disciplinée dans `app/skills/tier1/yahoo_finance.py` (filtrage NaN/Inf, gardes division par zéro, repli de source tracé).
- Orchestration métier cohérente : 5 workflows séquencés (`app/orchestrator/router.py`), 1er skill obligatoire, suivants `optional=True`.
- Fiscalité canadienne intégrée (CELI/REER/CELIAPP, retenue US, inclusion gains en capital) : `app/skills/tier2/canadian_tax/`.
- Traçabilité présente : champs `ratios_source`, `ratios_fetched_at`, `ratios_provenance` dans les schémas de ratios.

## Faiblesses observées

| ID | Sévérité | Constat | fichier:ligne | Impact investisseur |
|----|----------|---------|---------------|---------------------|
| A | Haute | Aucune validation de fraîcheur : un ratio vieux de plusieurs mois (saisie manuelle ou cache long) est analysé sans avertissement ni blocage | `app/orchestrator/core.py` (chemin extract→analyse) ; champ `ratios_fetched_at` présent mais non contrôlé | L'utilisateur peut décider sur des données périmées sans le savoir |
| B | Moyenne | `SedarPlusExtractor.extract()` retourne `None` de façon inconditionnelle — source de données canadienne non opérationnelle | `app/skills/tier1/sedar_plus.py:40,55` | Pas de second canal pour les titres TSX ; dépendance unique à Yahoo Finance |
| C | Basse (révisée) | Croissance EPS sur un horizon **dynamique** (souvent 2-4 ans selon yfinance), inférieur aux 10 ans de Graham — **vérif. : le code ne fixe pas 4 ans, il calcule `len(values)-1` et trace `eps_growth_years`** | `app/skills/tier1/yahoo_finance.py:52` (`_compute_eps_growth`), repli `:73` ; documenté `.claude/rules/variables-financieres.md` | Horizon court — biais possible. **Limite documentée et assumée, plus honnête que prévu** | PARTIELLE |
| D | Basse | Le Nombre de Graham n'est calculé que si EPS>0 ET BVPS>0 — exclut les capitaux propres négatifs | `app/services/financial_calculations.py` (garde Graham Number) ; conforme `.claude/rules/donnees-financieres.md` | Perd les situations distressed légitimes ; **comportement intentionnel** (formule indéfinie sinon) |
| E | Basse | Frameworks Marks (cycles), Damodaran (narrative), Fisher (scuttlebutt) reposent sur l'interprétation LLM sans proxy quantitatif | `app/skills/tier2/{marks_cycles,damodaran_narrative,fisher_scuttlebutt}/` | Moins reproductible que les cadres déterministes ; verdicts sensibles au prompt |
| F | Info | Piliers « ETF passif » et « thématique » du modèle four-pillar non implémentés (seuls value + algo/screener existent) | `README.md` (four-pillar) ; absence de skills correspondants | Couverture de portefeuille partielle vs ambition affichée |

## Améliorations priorisées

| ID | Action | Effort | Valeur |
|----|--------|--------|--------|
| A | Ajouter un contrôle de fraîcheur (`now − ratios_fetched_at`) : avertissement > 30 j, blocage/flag > 90 j ; propager le flag dans l'output | Moyen | Haute |
| B | Implémenter une vraie source canadienne (ou intégrer un fournisseur tiers) ou retirer le stub et documenter Yahoo comme source unique | Élevé | Moyenne |
| C | Afficher systématiquement l'horizon réel (`eps_growth_years`) dans chaque analyse Graham et dans le screener | Faible | Moyenne |
| E | Ajouter des proxies quantitatifs optionnels (spreads, percentile de volatilité) pour ancrer Marks/Damodaran | Élevé | Moyenne |
| F | Décider explicitement : implémenter les piliers manquants, ou recadrer la doc sur les 2 piliers réellement couverts | Faible | Basse |

## Hypothèses à vérifier

- **H-A** : aucun chemin de code ne compare `ratios_fetched_at` à `now()` pour avertir/bloquer sur des données périmées.
- **H-B** : `SedarPlusExtractor.extract()` (`app/skills/tier1/sedar_plus.py`) retourne toujours `None` (ligne 55 renvoie `None` même quand la requête HTTP réussit).
- **H-C** : la croissance EPS du ratio Graham est calculée sur ~4 ans, pas 10, et cette limite est documentée dans les règles.
- **H-D** : le Nombre de Graham (`financial_calculations.py`) est `None` dès que EPS≤0 ou BVPS≤0.
