# ESG par Proxy Financier — Justification et Limites

## Pourquoi des proxies financiers pour l'ESG ?

Les données ESG primaires (émissions CO2 vérifiées, indice de satisfaction employés, composition du conseil
d'administration) sont coûteuses, rarement comparables entre entreprises, et souvent non disponibles pour
les petites capitalisations. Les agences spécialisées (MSCI ESG, Sustainalytics, ISS) couvrent bien les
grandes capitalisations nord-américaines et européennes mais les méthodologies divergent considérablement.

L'approche proxy repose sur une corrélation documentée entre comportements financiers et comportements ESG :

| Constat empirique | Corrélation ESG |
|---|---|
| Les entreprises avec ROE élevé et stable gaspillent moins de capital | Efficience des ressources (E) |
| Les entreprises peu endettées résistent mieux aux chocs (financiers ou environnementaux) | Résilience E + protection emplois S |
| Les entreprises qui versent des dividendes 20+ ans ont des structures stables | Gouvernance disciplinée (G) + stabilité emplois (S) |
| Les grandes entreprises (≥ 5 Md$) ont plus de ressources pour les programmes sociaux | Capital social disponible (S) |
| BPA croissant sur 10 ans sans endettement explosif = modèle économique durable | Durabilité G + dimension S |

## Limites fondamentales de l'approche proxy

### Ce que les proxies financiers NE peuvent PAS mesurer

1. **Émissions directes de GES (Scope 1, 2, 3)** — Aucune donnée financière standard ne proxy les émissions réelles
2. **Conditions de travail réelles** — Taux de satisfaction, accidents du travail, diversité réelle
3. **Indépendance réelle du conseil d'administration** — La structure formelle ne garantit pas l'indépendance effective
4. **Chaîne d'approvisionnement** — Pratiques ESG des fournisseurs et sous-traitants
5. **Controverses ESG passées** — Amendes environnementales, scandales sociaux, litiges
6. **Politique de lobbying** — Influence sur les régulateurs et les politiques publiques

### Biais sectoriels connus

| Secteur | Biais structurel | Impact |
|---|---|---|
| Banques | ROE élevé structurel | Surévalue E1 si non ajusté |
| Énergie/Mines | Impact environnemental direct non capturé | Sousestime le risque E réel |
| Utilities | Transition énergétique non capturée | Score E peut ne pas refléter le mix énergétique |
| Technologie | Faible empreinte physique | Surestime les scores E si les standards restent stricts |
| Consommation | Chaîne d'approvisionnement non évaluée | Score S incomplet pour marques mondiales |

## Comparaison avec les sources primaires

### Quand utiliser ce skill vs une agence ESG

| Situation | Recommandation |
|---|---|
| Présélection rapide d'un univers d'actions | Skill `esg_simplified` suffisant |
| Décision d'investissement significative (≥ 5% portefeuille) | Croiser avec MSCI ou Sustainalytics |
| Fonds ISR (Investissement Socialement Responsable) | Sources primaires obligatoires |
| Comparaison intra-sectorielle précise | Sources primaires préférées |
| Exclusion d'un secteur entier (ex. tabac, armement) | Critères explicites, pas ce skill |

### Divergences MSCI / Sustainalytics vs proxy financier

Les deux agences peuvent diverger de 50%+ sur un même ticker (étude Berk & van Binsbergen, 2021).
Le score proxy peut donc aligner ou diverger avec les sources primaires — **les deux sont valides dans leur contexte**.

## Utilisation dans TradingClaude

Ce skill est complémentaire aux frameworks d'analyse fondamentale :

- **Avant** `graham_analysis` ou `buffett_quality` : contexte ESG pour éviter les value traps sectorielles (ex. industrie charbonnière avec bons multiples)
- **Après** `investment_thesis_builder` : enrichir une thèse avec une dimension ESG pour portefeuilles responsables
- **Dans le screener** : filtre optionnel `esg_input` dans `AnalyzeRequest` — non bloquant, non obligatoire

Le champ `esg: EsgOutput | None` dans `AnalyzeResponse` est optionnel : l'absence d'ESG dans une analyse ne la disqualifie pas.
