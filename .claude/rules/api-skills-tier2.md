---
paths:
  - "app/skills/tier2/**"
---

# API — Skills tier2

## Quand cette règle s'applique

Lors de l'édition ou la création de tout fichier dans `app/skills/tier2/`.

## Règles

### Héritage obligatoire

Tout skill tier2 hérite de `SkillBase` (`app/skills/base.py`) :

```python
from app.skills.base import SkillBase

class DorseyMoatSkill(SkillBase):
    ...
```

### Prompt caching

- Le system prompt **doit dépasser 1 024 tokens** pour activer le prompt caching Anthropic
- `get_system_prompt()` applique `cache_control` sur le bloc système (section 8.2 architecture)
- **Source de vérité du prompt** : `.claude/skills/{nom-skill}/SKILL.md` + `references/*.md`
- Lire ce SKILL.md avant d'écrire ou modifier un prompt — le code doit refléter fidèlement les frameworks académiques documentés

### Schemas Pydantic

- Les schemas dans `schemas.py` **font foi** — ne pas contourner avec `.dict()` ou `**kwargs`
- `model_validate()` obligatoire à la sortie de `_parse_claude_json()`
- Utiliser `model_validator`, `field_validator`, `@computed_field` selon le besoin (Pydantic v2)
- Toujours valider que `cost_usd` est calculé et présent dans l'output

### Procédure d'ajout d'un nouveau skill tier2

1. Créer `app/skills/tier2/{skill_name}/` avec : `__init__.py`, `schemas.py`, `skill.py`, `prompts/system.md`
2. Hériter de `SkillBase` dans `skill.py`
3. System prompt > 1 024 tokens — vérifier avant de committer
4. Ajouter le skill dans `app/orchestrator/core.py` (instanciation dans `__init__`)
5. Ajouter le skill dans le ou les `WORKFLOWS` de `app/orchestrator/router.py` (voir `api-orchestrator.md`)
6. Le prompt reflète fidèlement `.claude/skills/{nom}/SKILL.md` — lire ce fichier d'abord
7. Couvrir selon la pyramide : schemas (test unitaire) + endpoint (test d'intégration)

## Exemple — structure minimale d'un skill

```python
# schemas.py
class MonSkillInput(BaseModel):
    ticker: str
    ratios: MonRatios
    context_precedent: ContextPrecedent | None = None

class MonSkillOutput(BaseModel):
    verdict: Literal["FORT", "MOYEN", "FAIBLE"]
    detail: str
    citations: list[Citation] = []
    cost_usd: float

# skill.py
class MonSkill(SkillBase):
    async def execute(self, input_data: MonSkillInput) -> MonSkillOutput:
        """Analyse via Claude avec prompt caching."""
        response = await self._client.messages.create(
            model=self._model,
            system=self.get_system_prompt(),
            messages=[{"role": "user", "content": self._build_user_message(input_data)}],
            max_tokens=2048,
        )
        data = _parse_claude_json(response.content[0].text)
        data["cost_usd"] = _calculate_cost(response.usage, self._model)
        return MonSkillOutput.model_validate(data)
```
