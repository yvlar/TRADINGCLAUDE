# Prompt d'implémentation 02 — Durcissement du typage mypy

> **Origine** : audit `docs/audits/03-code.md` (faiblesse **M**) + hypothèse **H-M** confirmée dans `docs/audits/00-synthese-hypotheses.md`.
> **Priorité** : P1. **Domaine** : code/typage. **Effort** : moyen, **itératif** (un lot par session).

---

## Contexte

Le type-check CI est bloquant (`mypy app/` dans `.github/workflows/ci.yml:117`), **mais** 11 modules
sont neutralisés par `ignore_errors = true` dans `pyproject.toml`, et `strict = false`. Les erreurs de
typage s'accumulent donc en silence dans ces modules. Objectif : **réduire la liste `ignore_errors`
graduellement**, sans casser le CI, en traitant un petit lot de modules par session pour ne pas
surcharger le contexte ni produire une PR ingérable.

## LECTURE OBLIGATOIRE (avant de coder)

1. `CLAUDE.md` et `ROADMAP.md`.
2. `.claude/rules/conventions-python.md` — type hints partout, pas de `# type: ignore`/`cast()` non justifié.

## Périmètre de CETTE session

`pyproject.toml:24-47` — `strict = false`, `disable_error_code = ["override", "prop-decorator"]`, et la
liste `[[tool.mypy.overrides]] ignore_errors = true` contenant **11 modules** :

```
app.services.email_service
app.services.backtest
app.services.evals_dashboard
app.skills.tier1.yahoo_finance
app.api.endpoints.telemetry
app.api.endpoints.ticker_report
app.api.endpoints.watchlist
app.rag.client
app.skills.tier2.stock_valuation.skill
app.orchestrator.core
app.observability.langfuse_client
```

- **Traiter 3-4 modules « faciles » ce lot** : commencer par `app.api.endpoints.telemetry`,
  `app.api.endpoints.ticker_report`, `app.api.endpoints.watchlist`, `app.services.email_service`.
- **Différer** explicitement les gros morceaux (`app.orchestrator.core`, `app.skills.tier1.yahoo_finance`,
  `app.skills.tier2.stock_valuation.skill`) à des lots ultérieurs — les laisser dans la liste.

## Tâche détaillée

1. Pour chaque module du lot : le **retirer** de la liste `ignore_errors` dans `pyproject.toml`.
2. Lancer `mypy app/ --ignore-missing-imports` (reproduit la commande CI) ; corriger les erreurs réelles :
   annotations manquantes, `Optional` implicites, retours mal typés. **Pas** de `# type: ignore` sauf
   contrainte externe documentée (commentaire WHY obligatoire).
3. Ne pas modifier le comportement runtime — uniquement des annotations. Si une correction exige un
   changement de logique non trivial, **remettre le module dans la liste** et le noter en différé.
4. Mettre à jour le commentaire/structure de la liste pour refléter les modules restants.

## Tests & vérification

- `mypy app/ --ignore-missing-imports` → 0 erreur.
- `python -m pytest tests/ --ignore=tests/e2e --ignore=tests/evals` vert (aucune régression runtime).

## Critères d'acceptation

- [ ] Liste `ignore_errors` réduite de 3-4 modules.
- [ ] `mypy app/` passe ; CI vert.
- [ ] Aucun `# type: ignore` non justifié ajouté ; aucun changement de comportement.
- [ ] Modules différés explicitement listés dans la PR.

## Branche & commit

- Branche : `claude/impl-mypy-strict-lot1` (depuis `dev`). PR **base `dev`**. Push à confirmer.
- Répéter le prompt en `lot2`, `lot3`… jusqu'à vider la liste (objectif final : passer `strict = true`).
