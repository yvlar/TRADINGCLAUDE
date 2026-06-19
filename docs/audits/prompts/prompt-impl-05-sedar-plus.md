# Prompt d'implémentation 05 — SEDAR+ : vraie source ou retrait propre du stub

> **Origine** : audit `docs/audits/01-investissement.md` (faiblesse **B**) ; hypothèse **H-B** confirmée dans `docs/audits/00-synthese-hypotheses.md`.
> **Priorité** : P3. **Domaine** : backend / extraction de données. **Effort** : moyen, 1 session.

---

## Contexte

`SedarPlusExtractor.extract()` retourne **toujours `None`** (`app/skills/tier1/sedar_plus.py:55`,
même après un HTTP 200) : c'est un stub assumé. Aujourd'hui seule la source Yahoo Finance est
opérationnelle. Le stub crée une fausse impression de second canal de données canadiennes.

## LECTURE OBLIGATOIRE (avant de coder)

1. `CLAUDE.md` et `ROADMAP.md`.
2. `.claude/rules/donnees-financieres.md` — traçabilité source + date, suffixe `.TO`, validation None.

## Décision à acter (au début de la session)

- **(b) Recommandé — court terme, faible risque** : retirer proprement le stub et **documenter Yahoo
  Finance comme source unique**, en gardant un point d'extension clair pour une future source.
- **(a) Optionnel — plus de valeur, plus d'effort** : implémenter une vraie extraction canadienne
  (SEDAR+ ne fournit pas de ratios structurés via API publique → viser un fournisseur tiers : il faut
  alors une clé API, l'ajouter à `.env.example`, gérer le quota/erreurs).

Choisir **(b)** par défaut sauf indication contraire de Yves. Le reste du prompt décrit (b) ;
l'option (a) est notée en fin.

## Tâche détaillée — option (b)

1. **Vérifier les appelants** avant tout retrait : `grep` `SedarPlusExtractor` / `sedar` dans `app/`
   (orchestrateur, main, services). Confirmer qu'aucun chemin ne dépend du retour non-`None`.
2. Soit **supprimer** `app/skills/tier1/sedar_plus.py` et ses usages, soit le **réduire** à un point
   d'extension documenté (classe avec `extract()` levant `NotImplementedError` + docstring claire
   « source non implémentée — Yahoo Finance est la source unique actuelle »). Préférer le retrait si
   aucun appelant.
3. S'assurer que la traçabilité reste cohérente : `ratios_source = "Yahoo Finance"` partout
   (constante `RATIOS_SOURCE`, `app/skills/tier1/yahoo_finance.py:165`).
4. Documenter la source unique dans `docs/` (architecture) si une mention SEDAR+ y subsiste.

## Tests

- `tests/skills/` : adapter ou retirer les tests visant le stub `sedar_plus` (s'ils existent — vérifier).
- Suite complète `tests/ --ignore=tests/e2e --ignore=tests/evals` verte.

## Critères d'acceptation

- [ ] Plus de stub trompeur : soit retiré, soit explicitement « non implémenté » (NotImplementedError + doc).
- [ ] Aucun appelant cassé ; traçabilité source cohérente.
- [ ] Tests verts ; mention SEDAR+ obsolète nettoyée de la doc.

## Note — option (a) si choisie

- Identifier un fournisseur de données canadiennes structurées (API). Ajouter la clé à `.env` **et**
  `.env.example` (valeur factice), conformément à `.claude/rules/securite.md`. Implémenter `extract()`
  en async (`httpx.AsyncClient`), avec validation None/div0 et `ratios_fetched_at`/`ratios_source`
  renseignés comme pour Yahoo. Tests d'intégration mockés.

## Branche & commit

- Branche : `claude/impl-sedar-plus` (depuis `dev`). PR **base `dev`**. Push à confirmer.
