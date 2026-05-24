# Retenues d'impôt américain pour résident canadien

Particularité critique pour tout investisseur canadien détenant des actions ou ETF américains.

## Convention fiscale Canada-US

Signée en 1980, dernière révision majeure 2007. Couvre la double imposition pour les résidents canadiens détenant des actifs américains.

## Formulaire W-8BEN — obligatoire

Tout courtier qui détient des titres américains pour un résident canadien doit recevoir un W-8BEN signé par le client. **Sans W-8BEN, la retenue par défaut est 30 %** (le double du taux conventionnel).

Le W-8BEN est valide 3 ans (à renouveler avant échéance). Tous les courtiers canadiens (Questrade, Wealthsimple, Disnat, RBC Direct, etc.) gèrent le formulaire à l'ouverture de compte avec accès aux marchés US.

## Taux de retenue par type de compte

### Compte non-enregistré
- **Dividendes US** : retenue 15 %
- **Intérêts US** : retenue 0 % (généralement exempté par convention)
- **Récupération via crédit d'impôt étranger** sur la déclaration canadienne (annexe T2209 fédérale + TP-772 Québec)

### CELI / TFSA
- **Dividendes US** : retenue 15 %
- **NON récupérable** — perte sèche définitive
- Exemple : action US à 4 % de dividende → rendement effectif en CELI = 3.4 %
- ⚠️ Conséquence pratique : éviter les actions US à dividendes élevés en CELI

### REER / RRSP
- **Dividendes US** : retenue 0 % par convention (exemption REER explicite)
- Mais condition : détenir des **actions américaines directement** ou un **ETF coté aux US**
- ⚠️ Détenir un **ETF canadien détenant des actions US** (VFV, XUS, XQQ) ne donne PAS l'exemption — la retenue est appliquée au niveau de l'ETF avant distribution

### CELIAPP / FHSA
Traité comme CELI. **Retenue 15 % non récupérable** pour les dividendes US.

### REEE / RESP
Traité similairement au CELI pour les retenues. Retenue 15 % non récupérable.

## Tableau de décision

| Actif | Compte optimal | Pourquoi |
|-------|----------------|----------|
| Apple, Microsoft (low div, croissance) | CELI | Dividendes faibles, capital gains protégés |
| AT&T, Verizon (high div) | REER (titres directs) | Évite la retenue 15 % |
| ETF US coté aux USA (VOO, QQQ, VTI) | REER | Évite retenue, économise frais sur conversion |
| ETF canadien d'actions US (VFV, XUS) | CELI ou non-enreg | Pas d'avantage REER pour ces ETF |
| Bons du Trésor US | CELI ou REER | Intérêts exemptés de retenue |

## Erreur courante : la "double retenue" sur les ETF en couches

Un ETF canadien (ex. XAW de iShares) qui détient un ETF irlandais (ex. CSPX) qui détient des actions US peut subir une retenue à **deux niveaux** :
1. Actions US → ETF irlandais : 15 %
2. ETF irlandais → ETF canadien : 0 % (Irlande exempte par convention)

Si l'ETF canadien détient directement des actions US (sans intermédiaire), il y a **une seule** couche de retenue 15 % au niveau de l'ETF.

Pour minimiser : préférer des **ETF cotés aux USA** détenus directement en REER (option la plus efficace fiscalement pour les actions US).

## Crédit d'impôt étranger — comment ça marche en non-enregistré

Sur la déclaration canadienne :
1. Déclarer le **brut des dividendes US** (avant retenue) en revenu
2. Réclamer un crédit pour impôt étranger sur le 15 % retenu
3. Le crédit s'applique d'abord au fédéral (T2209), puis au provincial (TP-772 au Québec)

### Limite du crédit
Le crédit est plafonné au **montant d'impôt canadien dû sur ce revenu spécifique**. Si tu es en haut taux, le crédit complet de 15 % est généralement utilisable. Si tu es en bas taux, une partie du crédit peut être perdue.

## Cas particuliers

### Sociétés à responsabilité limitée (LLC) américaines
Traitement compliqué — les LLC sont des entités hybrides souvent traitées différemment au Canada qu'aux US. **Éviter les LLC pour résident canadien** sauf conseil fiscaliste spécialisé.

### Limited Partnerships (LP) américaines
Les distributions de LP US génèrent un **K-1 form** complexe. Préférer les actions de corporations US pour simplicité. Les LP US peuvent aussi déclencher des obligations de déclaration aux US (formulaire 1040NR).

### Revenus de fiducie (REIT US)
Les distributions de REIT US sont parfois reclassifiées en intérêts ou retour de capital — chacun avec un traitement fiscal différent. Le formulaire 1099-DIV reçu en fin d'année détaille la composition.

### Liens US substantiels (US person par mariage, naissance, green card)
Si tu es considéré "US person" (citoyen US, green card holder, ou ayant passé > 183 jours/an aux US sur 3 ans selon SPT), tu dois déposer une déclaration US (1040) **en plus** de la canadienne. Cas hors scope de ce skill — consulter un fiscaliste cross-border.

## Ressources

- IRS W-8BEN : irs.gov/forms-pubs/about-form-w-8-ben
- Convention fiscale Canada-US : canada.ca → conventions fiscales
- Tax-loss harvesting et règles US/Canada : Adam Mayers (MoneySense), Jamie Golombek (CIBC)
