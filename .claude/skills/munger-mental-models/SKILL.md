---
name: munger-mental-models
description: Applique les modèles mentaux et la psychologie du jugement de Charlie Munger — les 25 biais cognitifs (Psychology of Human Misjudgment), inversion ("invert, always invert"), lollapalooza effects, multidisciplinarité (latticework of mental models). À utiliser dès que l'utilisateur mentionne Munger, "Poor Charlie's Almanack", modèles mentaux, biais cognitifs, inversion, lollapalooza, "invert always invert", framing biais, sunk cost, social proof, ou veut analyser un investissement / décision via les biais comportementaux. Utilise toujours ce skill quand une analyse fondamentale a été faite et qu'il faut prendre du recul psychologique avant de décider.
---

# Munger — Mental Models

Charlie Munger (1924-2023), partenaire de Buffett pendant 60 ans, a popularisé l'idée que la majorité des erreurs d'investissement viennent de **biais cognitifs prévisibles** et que l'antidote est un cadre multidisciplinaire de modèles mentaux.

## Quand utiliser quelle référence

| Question | Référence |
|----------|-----------|
| Les 25 biais avec exemples concrets | `references/25-biais-cognitifs.md` |
| Inversion comme outil de décision | `references/inversion-thinking.md` |
| Lollapalooza et effets combinés | `references/lollapalooza-effects.md` |
| Multidisciplinarité et latticework | `references/latticework-multidisciplinaire.md` |

## Workflow

### Étape 1 — Lister les biais potentiels affectant la décision

Avant chaque décision majeure d'investissement, passer en revue les 25 biais :
- Lesquels pourraient s'appliquer à cette situation ?
- Lesquels pourraient affecter mon analyse ?
- Lesquels pourraient affecter le marché (créant l'opportunité) ?

```bash
python scripts/biais_audit.py --decision "achat-tesla-200usd"
```

Le script présente les 25 biais en groupes thématiques pour audit systématique.

### Étape 2 — Inversion

> *« Invert, always invert. »* — Munger (citant Carl Jacobi)

Pour chaque thèse, demander : **comment cet investissement pourrait-il échouer ?**

Lister les scenarios d'échec **avant** d'investir, pas après. Si tu peux articuler 3-5 scenarios d'échec spécifiques, tu comprends mieux le risque.

### Étape 3 — Identifier les lollapalooza

Quand **plusieurs biais s'alignent** dans la même direction, leur effet combiné est exponentiel — pas linéaire. Le piège est massivement plus dangereux qu'un biais isolé.

Exemple : bulle dot-com 2000 = social proof + scarcity (FOMO) + commitment bias + reciprocity (analystes payés par investment banking) + envy = collective madness.

### Étape 4 — Croiser avec autres disciplines

Munger insistait : ne pas analyser une décision avec un seul angle. Croiser :
- **Économie** (incentives, supply & demand, marginal cost)
- **Psychologie** (biais, social proof, autorité)
- **Mathématiques** (probabilités, espérance, statistiques)
- **Biologie** (évolution, sélection, équilibre)
- **Histoire** (précédents, cycles)
- **Physique** (équilibres, pressions)

Un investissement qui semble bon vu d'un seul angle peut être désastreux quand on croise plusieurs perspectives.

### Étape 5 — Test "would I bet against myself"

Munger conseillait : avant d'engager du capital, énumérer les meilleures raisons de **ne pas** prendre cette position. Si tu ne peux pas, tu n'as pas suffisamment analysé.

## Le concept central : Pensée seconde-ordre par modèles mentaux

> *« To a man with a hammer, everything looks like a nail. »*

L'investisseur avec un seul cadre (par exemple uniquement Graham value) verra des "value plays" partout, y compris dans les value traps. L'investisseur avec un latticework multidisciplinaire identifie correctement la nature de chaque situation.

## Garde-fous

- **Connaître les biais ne les fait pas disparaître.** Munger lui-même reconnaissait être affecté par les biais qu'il analysait. La connaissance permet de **les reconnaître et compenser**, pas de les éliminer.
- **L'inversion peut devenir paralysante.** Énumérer trop de scenarios d'échec mène à la non-action. Calibrer : 3-5 scenarios par décision majeure suffit.
- **Multidisciplinarité demande du temps**. Le latticework Munger se construit sur des décennies de lecture (300+ livres, biographies, sciences). Pas une checklist applicable en 10 minutes.
- **Modèles mentaux ≠ vérité absolue**. Les modèles sont des outils d'approximation. Tous les modèles sont faux ; certains sont utiles. Toujours questionner.
- **Munger lui-même se trompait**. Il a été en désaccord avec Buffett plusieurs fois (notamment sur Apple), parfois Munger avait raison, parfois Buffett. Personne n'a la vérité — la rigueur du processus compte.
