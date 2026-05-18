---
paths:
  - "app/orchestrator/**"
---

# API — Orchestrateur et workflows

## Quand cette règle s'applique

Lors de l'édition de `app/orchestrator/core.py` ou `app/orchestrator/router.py`.

## Règles

### Pattern `WORKFLOWS` dans `router.py`

Les workflows sont déclarés comme un dictionnaire de `SkillStep` ordonné :

```python
from app.orchestrator.router import SkillStep

WORKFLOWS: dict[str, list[SkillStep]] = {
    "nom_workflow": [
        SkillStep("skill_id"),                        # obligatoire — échec = workflow échoue
        SkillStep("skill_id_optionnel", optional=True), # optionnel — workflow continue si échec
    ],
}
```

- **`skill_id`** : clé d'enregistrement dans `Orchestrator.__init__` de `core.py`
- **`optional=False`** (défaut) : échec du skill = échec du workflow complet
- **`optional=True`** : le workflow continue et le champ correspondant dans `AnalyzeResponse` reste `None`

### `compounder_buffett` — exemple canonique (10 steps)

`compounder_buffett` est un **workflow d'orchestrateur**, pas un skill tier2. Il enchaîne 10 skills pour une analyse de compounder de longue durée (~5 min/ticker).

```python
"compounder_buffett": [
    SkillStep("graham_analysis"),                          # 1 — obligatoire
    SkillStep("earnings_quality",              optional=True),  # 2
    SkillStep("dorsey_moat",                   optional=True),  # 3
    SkillStep("buffett_quality",               optional=True),  # 4
    SkillStep("fisher_scuttlebutt",            optional=True),  # 5
    SkillStep("stock_valuation_triangulation", optional=True),  # 6
    SkillStep("investment_thesis_builder",     optional=True),  # 7
    SkillStep("munger_mental_models",          optional=True),  # 8
    SkillStep("marks_cycles_risk",             optional=True),  # 9
    SkillStep("canadian_tax_considerations",   optional=True),  # 10
],
```

Voir `gotchas-operationnels.md` pour la contrainte `max_parallel=3` dans le screener.

### Procédure d'ajout d'un nouveau workflow

1. Ajouter une entrée dans `WORKFLOWS` dans `router.py`
2. Vérifier que tous les `skill_id` listés sont enregistrés dans `Orchestrator.__init__` de `core.py`
3. Décider quels steps sont `optional=True` selon les dépendances logiques entre skills
4. Si le workflow est accessible via `POST /analyze`, l'ajouter comme valeur valide dans le schema `AnalyzeRequest.workflow`
5. Documenter le workflow dans `ROADMAP.md` section « Skills opérationnels »
6. Ajouter un test dans `tests/test_workflow_router.py`

### Inventaire des workflows disponibles

| Workflow | Steps | Description |
|---|---|---|
| `value_graham` | 5 | Analyse value classique (Graham → earnings → valuation → thesis → tax) |
| `compounder_buffett` | 10 | Analyse compounder profonde — voir ci-dessus |
| `fast_grower_lynch` | 6 | Croissance Lynch + Damodaran + valuation |
| `special_situation` | 4 | Situations spéciales Klarman + Greenblatt |
| `distressed_pabrai` | 5 | Distressed Pabrai + Klarman + earnings |
