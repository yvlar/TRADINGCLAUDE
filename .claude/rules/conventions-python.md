---
paths:
  - "**/*.py"
---

# Conventions Python

## Quand cette règle s'applique

Lors de l'édition ou la création de tout fichier Python dans le projet.

## Règles

### Pattern skill — `async def execute()`

Tout skill tier2 suit ce patron exact (voir aussi `api-skills-tier2.md`) :

```python
async def execute(self, input_data: MonSkillInput) -> MonSkillOutput:
    """Retourne l'analyse validée depuis Claude."""
    response = await self._client.messages.create(
        model=self._model,
        system=self.get_system_prompt(),   # cache_control activé dans get_system_prompt()
        messages=[{"role": "user", "content": self._build_user_message(input_data)}],
        max_tokens=2048,
    )
    data = _parse_claude_json(response.content[0].text)
    data["cost_usd"] = _calculate_cost(response.usage, self._model)
    return MonSkillOutput.model_validate(data)
```

### Docstrings
- Une ligne courte en français — pas de blocs multi-paragraphes
- Documenter uniquement ce que le nom ne dit pas (contrainte cachée, comportement surprenant)
- Pas de section `Args:` / `Returns:` automatique — les types hints suffisent

### Imports
- Grouper : stdlib → tiers → interne, séparés par une ligne vide
- `from __future__ import annotations` en tête des fichiers avec annotations complexes (cycles)
- Imports relatifs dans les packages internes : `from app.skills.base import SkillBase`

### Style général
- Pas de `print()` dans le code de production — utiliser `logging` (`app/logging_config.py`)
- Pas de variables globales mutables — passer les dépendances par injection (constructeur)
- Nommage : `snake_case` pour fonctions et variables, `PascalCase` pour classes, `SCREAMING_SNAKE` pour constantes
