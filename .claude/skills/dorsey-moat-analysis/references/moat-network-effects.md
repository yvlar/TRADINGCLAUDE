# Moat #3 — Effets de réseau

La valeur du produit augmente avec le nombre d'utilisateurs. Chaque utilisateur supplémentaire **renforce** la position concurrentielle pour les utilisateurs existants. C'est le moat avec le potentiel de croissance le plus rapide — mais aussi parmi les plus volatils.

## Mécanique

Loi de Metcalfe (approximative) : la valeur d'un réseau croît avec le carré du nombre de nœuds. Pour un service à effets de réseau, doubler les utilisateurs **quadruple** approximativement la valeur perçue.

Conséquence pratique : un leader avec 60 % de parts de marché vaut souvent **8-10×** plus qu'un challenger à 10 % — pas seulement 6×.

## Types d'effets de réseau

### 1. Réseau direct (one-sided)
Tous les utilisateurs interagissent entre eux. Plus il y a d'utilisateurs, plus le réseau est utile pour tous.

**Exemples** :
- Téléphone : un téléphone seul est inutile
- WhatsApp, WeChat : utiles seulement si tes contacts y sont
- Skype, Zoom (initialement) : valeur croît avec adoption générale
- Bitcoin : sécurité du réseau ∝ hashrate

### 2. Réseau bilatéral (two-sided / multi-sided)
Deux groupes (ou plus) qui se cherchent mutuellement. Chaque groupe valorise la taille de l'autre groupe.

**Exemples** :
- **Visa, Mastercard** : commerçants ↔ titulaires de carte
- **Amazon Marketplace, eBay** : acheteurs ↔ vendeurs
- **Uber, Lyft** : passagers ↔ chauffeurs
- **App Store, Google Play** : développeurs ↔ utilisateurs
- **TMX, NYSE** : acheteurs ↔ vendeurs de titres

### 3. Réseau de données (data network effects)
Plus d'utilisateurs = plus de données = meilleur produit = plus d'utilisateurs.

**Exemples** :
- **Google Search** : plus de queries = meilleurs algorithmes = meilleurs résultats
- **Waze** : plus d'utilisateurs = meilleur trafic temps réel = utilisateurs supplémentaires
- **TikTok** : plus de viewers = meilleur algorithme de recommendation
- **Spotify** : plus de listeners = meilleurs algorithmes de découverte

## Exemples canadiens d'effets de réseau

### TMX Group (X.TO)
Bourse + chambre de compensation. Effets de réseau bilatéraux : acheteurs ↔ vendeurs. Le winner-takes-most des bourses régionales (Vancouver, Montréal absorbés). Moat solide mais menacé par dark pools et plates-formes alternatives (CSE).

### CGI Group (GIB.A.TO)
Pas un effet de réseau classique mais réseau de relations long-terme avec gouvernements et grandes entreprises = créa une moat de référencement.

### Constellation Software (acquisitions)
Pour chacune de ses acquisitions, l'effet de réseau interne aux niches (utilisateurs spécifiques d'un logiciel municipal, de dispatch police) est mince mais réel. Ce qui rend CSU exceptionnel n'est pas l'effet de réseau mais plutôt les switching costs (voir référence dédiée).

### Shopify (SHOP.TO)
Effets de réseau **partiels** : developpeurs apps ↔ marchands. Moins forts qu'Amazon Marketplace parce que les marchands gardent leur propre site et n'interagissent pas directement entre eux.

## Pièges des effets de réseau

### Réseaux **locaux**, pas globaux

Uber a découvert que les effets de réseau sont **par marché géographique**, pas globaux :
- Avoir des chauffeurs à San Francisco n'aide pas à NYC
- Concurrence locale (Lyft, taxi traditionnel) toujours possible
- Coût d'expansion à chaque nouvelle ville énorme

Les bourses ont des effets de réseau **par classe d'actifs** (NYSE pour US large cap, mais pas globalement dominante).

**Test** : si on retire 90 % des utilisateurs hors d'une zone géographique, l'utilisateur local en souffre-t-il ? Si non, l'effet de réseau est local.

### Réseaux qui se retournent

Les effets de réseau peuvent **devenir négatifs** :
- **Spam** sur un service de chat = qualité dégradée → utilisateurs partent
- **Trafic excessif** sur Waze = routes congestionnées par Waze users eux-mêmes
- **Saturation** sur TikTok For You = perte d'engagement

Les leaders doivent **gérer activement** la qualité du réseau pour préserver l'effet positif.

### Réseaux multi-homing

Quand les utilisateurs peuvent appartenir à **plusieurs réseaux simultanément** sans coût, l'effet de réseau s'affaiblit :
- Un consommateur peut avoir Visa **et** Mastercard
- Un chauffeur peut conduire pour Uber **et** Lyft
- Un dev peut publier sur App Store **et** Google Play

Quand le multi-homing est facile, le winner-take-most ne s'applique pas, et l'effet de réseau ne crée qu'un moat partiel.

### Cas historiques de retournement

Les effets de réseau **ne sont pas éternels** :
- **MySpace → Facebook** (2008) : génération suivante a basculé en 18 mois
- **Yahoo → Google** (2003) : changement de mode de découverte
- **BlackBerry → iPhone** (2010) : nouvelle génération technologique
- **Snapchat → TikTok** (2019-2020) : nouveau format video

Conséquence pratique : appliquer un **discount de durabilité** sur les moats d'effet de réseau (présumer 7-10 ans plutôt que 20+).

## Calibration du moat d'effets de réseau

### Wide moat
- Effet de réseau global ou national fort
- Multi-homing impossible ou coûteux
- Données accumulées difficilement reproductibles
- Position dominante > 60 % de marché
- Exemples : Visa/Mastercard, Google Search, Microsoft Office network

### Narrow moat
- Effet de réseau local ou sectoriel
- Multi-homing possible avec friction
- Position de leader mais pas dominant écrasant
- Exemples : Uber par métropole, LinkedIn pour recrutement professionnel

### Pas de moat durable
- Effet de réseau facilement reproductible (rebooté par concurrent avec subvention)
- Multi-homing sans friction
- Pas de barrière de données
- Exemples : la plupart des dating apps, services de livraison food

## Test pour détecter un effet de réseau réel

Trois questions :

1. **Les utilisateurs partiraient-ils en masse si X % de leurs contacts/contreparties partaient ?**
   - Oui = effet de réseau confirmé

2. **Un concurrent avec 100 M$ de capital pourrait-il bâtir un réseau équivalent en 2 ans ?**
   - Non = barrière à l'entrée par effet de réseau

3. **L'utilisateur principal est-il "captif" ou peut-il facilement utiliser plusieurs services ?**
   - Captif = effet de réseau plus fort
   - Multi-homing facile = effet de réseau partiel seulement

Si les trois réponses confirment l'effet de réseau fort, c'est un moat qui justifie une prime de valorisation significative.
