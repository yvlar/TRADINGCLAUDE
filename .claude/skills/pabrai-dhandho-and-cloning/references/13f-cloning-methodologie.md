# 13F Cloning — méthodologie

Aux USA, tout investment manager gérant > 100 M$ doit déclarer ses positions long en actions cotées chaque trimestre via le formulaire **13F-HR** (Holdings Report).

Pabrai a élevé l'**imitation intelligente** de ces filings au rang de stratégie d'investissement. L'idée : les meilleurs investisseurs publient leurs idées chaque trimestre. Pourquoi ne pas en profiter ?

## Mécanique des 13F

### Délai obligatoire
- **45 jours après la fin du trimestre**
- Q1 (mars 31) → publié au plus tard le 15 mai
- Q2 (juin 30) → 14 août
- Q3 (sept 30) → 14 novembre
- Q4 (dec 31) → 14 février

Délai de **6-7 semaines** entre la position et la publication. Les super-investors peuvent avoir partiellement liquidé à la publication.

### Ce qui est déclaré
- Toutes les positions long en actions US
- Quantité d'actions et valeur de marché à la date de fin de trimestre
- Pas de short positions
- Pas de positions en obligations, options, dérivés
- Pas de positions hors-USA

### Ce qui n'est PAS dans les 13F
- **Shorts** : invisible
- **Options/warrants** : déclarés mais incomplet
- **Investissements privés (PE, VC)** : invisibles
- **Cash position** : invisible
- **Stratégie macro** (devises, taux, commodités) : invisible

Conséquence : ne jamais confondre **portefeuille public 13F** avec **portfolio total** d'un super-investor. Les hedge funds peuvent avoir des shorts importants qui changent l'asymétrie de leurs longs.

## Sources de données

### Officielles (gratuites)
- **SEC EDGAR** : sec.gov, recherche par CIK ou nom du gestionnaire
- Filings bruts en XML — peu lisibles, parsing requis

### Aggregators (gratuits ou payants)
- **WhaleWisdom** (whalewisdom.com) : gratuit avec délai, premium pour temps réel
- **Dataroma** (dataroma.com) : gratuit, focus sur ~80 super-investors curated
- **GuruFocus** : payant, large couverture, outils d'analyse
- **Stockcircle** : gratuit, alertes nouvelles positions
- **Finbox** : payant, analyses

### Pour le Canada
Pas d'équivalent direct des 13F. Les fonds canadiens ont des obligations différentes, plus laxistes. Le cloning est **principalement une stratégie sur les actions US**.

## Liste des super-investors à cloner

Pabrai recommande de focuser sur des investisseurs avec :
- **Track record > 15 ans** sur cycles complets
- **Performance ≥ S&P 500 + 5 %/an** annualisé
- **Style identifiable** (value, quality, special situations)
- **Faible turnover** (< 30 %/an idéalement)

### Tier 1 — incontournables
- **Warren Buffett** (Berkshire Hathaway) : 13F vraiment important — Buffett est obligatoire pour cloning
- **Charlie Munger** (Daily Journal) : portfolio minuscule mais conviction extrême
- **Seth Klarman** (Baupost Group) : partial 13F (positions moins illiquides)
- **Howard Marks** (Oaktree) : peu d'actions long, mais qualité
- **Joel Greenblatt** (Gotham) : approche systématique
- **Mohnish Pabrai** (Pabrai Funds) lui-même

### Tier 2 — qualité confirmée
- **Bill Ackman** (Pershing Square) : concentration extrême, attention aux retournements
- **Bruce Berkowitz** (Fairholme) : très concentré
- **David Tepper** (Appaloosa) : macro mais positions actions intéressantes
- **Stanley Druckenmiller** : peu de longs publics mais qualité
- **Li Lu** (Himalaya Capital) : low profile, returns extraordinaires

### Tier 3 — surveillance
Les "stars" récentes méritent skepticisme. Performance récente ≠ track record long.

## Méthodologie de cloning Pabrai

### Étape 1 — Identifier les nouvelles positions
Quand un super-investor **initie** une nouvelle position importante (≥ 3 % de son portefeuille), c'est un signal d'intérêt. Une nouvelle position est plus informative qu'une position existante (qui peut être conservée par inertie).

### Étape 2 — Filtrer par taille de position relative
Une position à **10 %+ du portefeuille** est haute conviction. Une position à 1 % est plus probablement diversification.

### Étape 3 — Chercher la conviction renforcée
Position qui **augmente** sur 2-3 trimestres consécutifs = thèse qui se renforce. Position qui décroît = thèse qui se dégrade.

### Étape 4 — Comprendre la thèse
Avant de copier, **lire les lettres aux investisseurs** ou interviews du super-investor. Si tu ne comprends pas pourquoi il a acheté, ne copie pas.

### Étape 5 — Adapter à ta situation
- **Échelle de temps** : Buffett peut tenir 30 ans. Toi peut-être pas. Ajuster la position.
- **Diversification** : Pabrai concentre extrêmement. Toi peut-être pas. Réduire la position.
- **Tax considerations** : voir `canadian-tax-considerations`. Une position US dans CELI vs REER fait une différence.

## Pièges du cloning

### 1. Information asymétrique masquée

Le super-investor a souvent des informations privées :
- Conversations directes avec management (Buffett a des relations directes avec CEOs)
- Recherche propriétaire approfondie
- Analyse de scenarii non publiée

Tu n'as pas accès à ces informations. Tu copies le résultat (la position) sans le contexte.

### 2. Rationalisation post-hoc

Quand le super-investor parle de sa thèse en lettre annuelle, c'est souvent une **reconstruction post-hoc**. La vraie raison de l'achat peut être différente. Vérifier avec les filings, pas seulement les lettres.

### 3. Position en cours de réduction

Le 13F montre la position au 31 mars (publié 15 mai). Le super-investor peut avoir liquidé la moitié entre le 1er avril et le 15 mai. Tu copies une position **qu'il a déjà commencé à vendre**.

Solution : croiser avec les 13F suivants. Si la position diminue trimestre après trimestre, c'est un signal de sortie.

### 4. Style mismatch

Cloner Klarman (special situations) si tu as une stratégie buy-and-hold est suboptimal. Klarman vend rapidement quand le catalyst se réalise — toi tu garderas trop longtemps.

Cloner uniquement les super-investors **dont la stratégie correspond à la tienne**.

### 5. Performance recency bias

Les super-investors qui font la une récente (Cathie Wood en 2020, Chamath en 2021) ont rarement le track record long terme requis. Préférer les "boring" établis depuis 20+ ans.

## Combien copier

Pabrai recommande **30-50 % du portefeuille en clones** (le reste en idées propres). C'est un compromis :
- Trop peu = on ne profite pas de l'edge
- Trop = on perd l'engagement intellectuel et la flexibilité

Pour un investisseur particulier débutant, **70-80 % en clones** peut être pragmatique le temps de développer ses propres analyses.

## Les meilleurs clones de Pabrai (publiés)

- **Berkshire** — clone de Buffett directement (alternative simpliste : juste acheter Berkshire)
- **Stewart Enterprises** — clone de Klarman 1999
- **Frontier** — clone qui a échoué (rappel que cloning n'est pas garantie de succès)

## Conseil final Pabrai

> *« You don't need to be original. The market doesn't pay you for originality. It pays you for being right. »*

L'égo est l'ennemi de l'investisseur. Cloner intelligemment libère du temps pour l'analyse en profondeur des positions copiées plutôt que la recherche de nouvelles idées.
